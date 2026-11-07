"""Document ingestion: storage, validation, processing state machine, embedding."""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.provider import AiUnavailable, ai
from app.core.config import settings
from app.core.logging import get_logger
from app.models.base import DocumentStatus
from app.models.learning import Course, Document, DocumentChunk
from app.models.users import User
from app.services.documents import (
    DocumentRejected, chunk_document, extract, scan_for_injection, sniff_mime,
)

log = get_logger("ingest")

MAX_PARALLEL_EMBED = 16


def safe_filename(original: str) -> str:
    """Never trust the client filename for storage. Generate our own name; keep the original only
    as a display label (already length-capped by the schema)."""
    suffix = Path(original).suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt"}:
        suffix = ".bin"
    return f"{uuid.uuid4().hex}{suffix}"


def store_file(data: bytes, original_filename: str) -> tuple[str, str]:
    stored = safe_filename(original_filename)
    target = settings.upload_dir / stored
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    # Written outside any web-served directory; access is only through authorised endpoints.
    target.write_bytes(data)
    return stored, hashlib.sha256(data).hexdigest()


def create_document(
    db: Session,
    actor: User,
    *,
    data: bytes,
    filename: str,
    title: str,
    visibility: str,
    course_id: uuid.UUID | None,
    topic_hint: str | None,
) -> Document:
    if len(data) == 0:
        raise DocumentRejected("empty", "The uploaded file is empty")
    if len(data) > settings.max_upload_bytes:
        raise DocumentRejected(
            "too_large", f"File exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit"
        )

    mime = sniff_mime(data, None, filename)
    if mime not in settings.mime_allowlist:
        raise DocumentRejected("unsupported_type", f"Content type {mime} is not permitted")

    if course_id is not None:
        course = db.get(Course, course_id)
        if course is None or course.is_archived:
            raise DocumentRejected("bad_course", "The selected course does not exist")

    stored_name, digest = store_file(data, filename)

    doc = Document(
        owner_id=actor.id,
        course_id=course_id,
        department_id=actor.department_id,
        title=title.strip()[:220],
        original_filename=filename[:255],
        stored_name=stored_name,
        mime_type=mime,
        size_bytes=len(data),
        sha256=digest,
        visibility=visibility,
        status=DocumentStatus.QUEUED,
        topic_hint=(topic_hint or None),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def file_path(document: Document) -> Path:
    candidate = settings.upload_dir / document.stored_name
    resolved = candidate.resolve()
    root = settings.upload_dir.resolve()
    if not str(resolved).startswith(str(root)):
        raise DocumentRejected("path_traversal", "Resolved path escapes the storage root")
    return resolved


def process_document(db: Session, document_id: uuid.UUID) -> None:
    """Idempotent processing: queued|failed -> processing -> completed|failed.

    Called by the background worker thread and directly by tests. Never raises: failures are recorded
    on the document so the UI can show a real error state.
    """
    import datetime as dt

    doc = db.get(Document, document_id)
    if doc is None or doc.status == DocumentStatus.COMPLETED:
        return

    doc.status = DocumentStatus.PROCESSING
    doc.error_code = None
    doc.error_detail = None
    db.commit()

    try:
        raw = file_path(doc).read_bytes()
        extracted = extract(raw, doc.mime_type)
        if extracted.char_count < 200:
            raise DocumentRejected(
                "no_text",
                "No extractable text found. Scanned PDFs need OCR, which is not enabled.",
            )
        chunks = chunk_document(extracted)

        injection_hits = scan_for_injection(
            "\n".join(page.text for page in extracted.pages)
        )

        # Remove any prior chunks (re-processing after a failure)
        db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()

        rows: list[DocumentChunk] = []
        for chunk in chunks:
            rows.append(
                DocumentChunk(
                    document_id=doc.id,
                    ordinal=chunk.ordinal,
                    page_from=chunk.page_from,
                    page_to=chunk.page_to,
                    section=chunk.section,
                    content=chunk.content,
                    token_estimate=max(1, len(chunk.content) // 4),
                )
            )
        db.add_all(rows)
        db.flush()

        if ai.enabled:
            for start in range(0, len(rows), MAX_PARALLEL_EMBED):
                batch = rows[start : start + MAX_PARALLEL_EMBED]
                result = ai.embed([b.content for b in batch])
                for row, vector in zip(batch, result.vectors, strict=True):
                    row.embedding = vector
                doc.embedding_model = result.model
            db.flush()
        else:
            doc.embedding_model = None

        doc.page_count = extracted.page_count
        doc.char_count = extracted.char_count
        doc.chunk_count = len(rows)
        doc.processed_at = dt.datetime.now(dt.timezone.utc)
        doc.status = DocumentStatus.COMPLETED
        if injection_hits:
            # Stored as a warning, not a failure: the content stays quarantined from prompts by
            # construction (fenced as data), but reviewers should know.
            doc.error_code = "prompt_injection_flagged"
            doc.error_detail = (
                "Document text contains instruction-like patterns; it is treated strictly as data."
            )
        db.commit()
        log.info("document processed", extra={"extra_fields": {
            "document_id": str(doc.id), "chunks": len(rows), "injection": bool(injection_hits),
        }})
    except DocumentRejected as exc:
        db.rollback()
        _mark_failed(db, document_id, exc.code, exc.message)
    except AiUnavailable as exc:
        # Text is usable, embeddings are not: keep the document but mark it partial-complete.
        db.rollback()
        _mark_failed(
            db, document_id, f"embedding_{exc.error_class}",
            "Text was extracted but embedding failed. Keyword search will still work; retry "
            "processing when the AI provider is available.",
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        log.exception("document processing crashed")
        _mark_failed(db, document_id, "internal_error", type(exc).__name__)


def _mark_failed(db: Session, document_id: uuid.UUID, code: str, detail: str) -> None:
    doc = db.get(Document, document_id)
    if doc is None:
        return
    doc.status = DocumentStatus.FAILED
    doc.error_code = code[:60]
    doc.error_detail = detail[:300]
    db.commit()


def delete_document(db: Session, document: Document) -> None:
    """Destructive: remove DB rows (chunks cascade) and the stored file."""
    path = file_path(document)
    db.delete(document)
    db.commit()
    try:
        path.unlink(missing_ok=True)
    except OSError:
        log.warning("stored file could not be removed", extra={"extra_fields": {
            "document_id": str(document.id)}})


def pending_documents(db: Session, limit: int = 5) -> list[uuid.UUID]:
    rows = db.scalars(
        select(Document.id)
        .where(Document.status.in_([DocumentStatus.QUEUED, DocumentStatus.PROCESSING]))
        .order_by(Document.created_at)
        .limit(limit)
    ).all()
    return list(rows)
