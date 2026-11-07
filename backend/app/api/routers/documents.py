"""Document upload, processing status, grounded assistant, retrieval preview."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.provider import ai
from app.core.db import get_db
from app.core.deps import Page, Principal, pagination, rate_limit, require_roles
from app.models.assessment import AiUsageLog, Quiz
from app.models.base import DocumentStatus, Role, Visibility
from app.models.learning import Document, DocumentChunk
from app.models.users import User
from app.schemas import (
    AskRequest, AskResponse, ChunkPreview, DocumentOut, DocumentUpdateRequest,
)
from app.services import audit, ingest
from app.services import rag as rag_service
from app.services.documents import DocumentRejected

router = APIRouter(tags=["documents"])

ALLOWED_UPLOAD_ROLES = (Role.LEARNER, Role.MANAGER, Role.ASSESSOR, Role.ADMIN)
TEXT_PREVIEW_CHARS = 400
UPLOAD_LIMIT_BYTES = 20 * 1024 * 1024


def load_document(db: Session, actor: User, document_id: uuid.UUID) -> Document:
    """Fetch a document the actor may read. Non-readable documents return 404 (not 403) so that
    the existence of another user's private material is not disclosed."""
    doc = db.get(Document, document_id)
    if doc is None or not rag_service.can_read_document(db, actor, doc):
        raise HTTPException(404, "Document not found")
    return doc


def _out(db: Session, doc: Document) -> DocumentOut:
    out = DocumentOut.model_validate(doc)
    owner = db.get(User, doc.owner_id)
    out.owner_name = owner.full_name if owner else None
    return out


@router.post("/documents", response_model=DocumentOut, status_code=201,
             dependencies=[Depends(rate_limit("upload", 30, 3600))])
async def upload_document(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*ALLOWED_UPLOAD_ROLES)),
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    visibility: str = Form(default=Visibility.PRIVATE.value),
    course_id: str | None = Form(default=None),
    topic_hint: str | None = Form(default=None),
) -> DocumentOut:
    if visibility not in {v.value for v in Visibility}:
        raise HTTPException(422, "Invalid visibility value")
    if visibility in (Visibility.ORGANISATION.value, Visibility.DEPARTMENT.value) and \
            principal.role not in (Role.ADMIN, Role.MANAGER, Role.ASSESSOR):
        raise HTTPException(403, "Publishing beyond private scope requires a staff role")

    course_uuid = None
    if course_id:
        try:
            course_uuid = uuid.UUID(course_id)
        except ValueError:
            raise HTTPException(422, "Invalid course id") from None

    # Streamed read with a hard cap: a large upload cannot exhaust worker memory.
    blocks: list[bytes] = []
    total = 0
    while True:
        block = await file.read(256 * 1024)
        if not block:
            break
        total += len(block)
        if total > UPLOAD_LIMIT_BYTES:
            raise HTTPException(413, "File exceeds the 20 MB upload limit")
        blocks.append(block)
    data = b"".join(blocks)

    safe_title = (title or file.filename or "Untitled material").strip()[:220]
    try:
        doc = ingest.create_document(
            db, principal.user, data=data, filename=file.filename or "upload.bin",
            title=safe_title, visibility=visibility, course_id=course_uuid,
            topic_hint=(topic_hint or None),
        )
    except DocumentRejected as exc:
        raise HTTPException(422, f"{exc.message} ({exc.code})") from None

    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="document.uploaded", resource_type="document", resource_id=str(doc.id),
                 detail=f"{doc.mime_type} {doc.size_bytes}B visibility={visibility}")
    db.commit()

    # Process inline: bounded work (<=500 pages) and keeps the demo single-process.
    ingest.process_document(db, doc.id)
    db.refresh(doc)
    return _out(db, doc)


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*ALLOWED_UPLOAD_ROLES)),
    page: Page = Depends(pagination),
    status_filter: str | None = Query(default=None, alias="status"),
    course_id: uuid.UUID | None = None,
    mine: bool = False,
) -> list[DocumentOut]:
    allowed = rag_service.accessible_documents_query(principal.user).subquery()
    stmt = select(Document).where(Document.id.in_(select(allowed.c.id)))
    if mine:
        stmt = stmt.where(Document.owner_id == principal.id)
    if status_filter:
        stmt = stmt.where(Document.status == status_filter)
    if course_id:
        stmt = stmt.where(Document.course_id == course_id)
    stmt = stmt.order_by(Document.created_at.desc()).limit(page.limit).offset(page.offset)
    return [_out(db, d) for d in db.scalars(stmt)]


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: uuid.UUID, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*ALLOWED_UPLOAD_ROLES)),
) -> DocumentOut:
    return _out(db, load_document(db, principal.user, document_id))


@router.get("/documents/{document_id}/chunks", response_model=list[ChunkPreview])
def document_chunks(
    document_id: uuid.UUID, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*ALLOWED_UPLOAD_ROLES)),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[ChunkPreview]:
    load_document(db, principal.user, document_id)
    rows = db.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.ordinal)
        .limit(limit)
    ).all()
    return [
        ChunkPreview(
            ordinal=row.ordinal, page_from=row.page_from, page_to=row.page_to,
            section=row.section, preview=row.content[:TEXT_PREVIEW_CHARS],
            has_embedding=row.embedding is not None,
        )
        for row in rows
    ]


@router.patch("/documents/{document_id}", response_model=DocumentOut)
def update_document(
    document_id: uuid.UUID, payload: DocumentUpdateRequest, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*ALLOWED_UPLOAD_ROLES)),
) -> DocumentOut:
    doc = load_document(db, principal.user, document_id)
    is_owner = doc.owner_id == principal.id
    is_admin = principal.role == Role.ADMIN
    if not is_owner and not is_admin:
        raise HTTPException(403, "Only the owner or an administrator may edit this document")

    if payload.title is not None:
        doc.title = payload.title.strip()
    if payload.topic_hint is not None:
        doc.topic_hint = payload.topic_hint or None
    if payload.visibility is not None:
        if payload.visibility in (Visibility.ORGANISATION, Visibility.DEPARTMENT) and \
                principal.role not in (Role.ADMIN, Role.MANAGER, Role.ASSESSOR):
            raise HTTPException(403, "Publishing beyond private scope requires a staff role")
        doc.visibility = payload.visibility.value

    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="document.updated", resource_type="document", resource_id=str(doc.id))
    db.commit()
    db.refresh(doc)
    return _out(db, doc)


@router.post("/documents/{document_id}/reprocess", response_model=DocumentOut)
def reprocess_document(
    document_id: uuid.UUID, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*ALLOWED_UPLOAD_ROLES)),
) -> DocumentOut:
    doc = load_document(db, principal.user, document_id)
    if doc.owner_id != principal.id and principal.role != Role.ADMIN:
        raise HTTPException(403, "Only the owner or an administrator may reprocess a document")
    doc.status = DocumentStatus.QUEUED
    doc.error_code = None
    doc.error_detail = None
    db.commit()
    ingest.process_document(db, doc.id)
    db.refresh(doc)
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="document.reprocessed", resource_type="document", resource_id=str(doc.id),
                 detail=doc.status)
    db.commit()
    return _out(db, doc)


@router.delete("/documents/{document_id}", status_code=204, response_model=None)
def delete_document(
    document_id: uuid.UUID, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*ALLOWED_UPLOAD_ROLES)),
) -> None:
    doc = load_document(db, principal.user, document_id)
    if doc.owner_id != principal.id and principal.role != Role.ADMIN:
        raise HTTPException(403, "Only the owner or an administrator may delete this document")

    linked_quizzes = db.scalar(
        select(func.count(Quiz.id)).where(Quiz.source_document_id == doc.id)
    ) or 0
    title = doc.title

    # Chunks cascade. Linked quizzes keep their questions and stored source quotes, but the FK is
    # set to NULL so the citation can no longer dangle into a deleted document.
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="document.deleted", resource_type="document", resource_id=str(doc.id),
                 detail=f"'{title}'; {linked_quizzes} linked quiz(zes) retained without source link")
    ingest.delete_document(db, doc)
    db.commit()


@router.post("/assistant/ask", response_model=AskResponse,
             dependencies=[Depends(rate_limit("ask", 40, 300))])
def ask(
    payload: AskRequest, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*ALLOWED_UPLOAD_ROLES)),
) -> AskResponse:
    # Explicit document scope is validated before retrieval, so an unauthorized id fails closed.
    if payload.document_ids:
        for document_id in payload.document_ids:
            load_document(db, principal.user, document_id)

    response = rag_service.answer(
        db, principal.user, payload.question, payload.document_ids or None
    )

    db.add(
        AiUsageLog(
            user_id=principal.id,
            operation="rag_answer",
            model=ai.chat_model if ai.enabled else None,
            latency_ms=response.latency_ms,
            outcome="ok" if not response.insufficient_evidence else "insufficient_evidence",
        )
    )
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="assistant.query", resource_type="document",
                 detail=f"docs={len(payload.document_ids)} grounded={response.grounded}")
    db.commit()
    return response
