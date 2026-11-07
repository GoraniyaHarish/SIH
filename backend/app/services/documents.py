"""Text extraction, chunking and untrusted-content handling for uploaded documents.

Security posture: extracted text is treated as UNTRUSTED DATA. It is never concatenated into a
system prompt, and retrieval results are fenced and clearly labelled as data in every prompt.
"""
from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass, field

from app.core.config import settings

# Signatures are checked before any parser touches the bytes.
PDF_MAGIC = b"%PDF-"
ZIP_MAGIC = b"PK\x03\x04"  # docx is a zip container
DOCX_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_CT = "application/pdf"
TXT_CT = "text/plain"

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"disregard (all )?(previous|prior|above) (instructions|rules)",
    r"you are now (a|an) ",
    r"system promp?t",
    r"reveal (your|the) (system )?(prompt|instructions)",
    r"print (your|the) (system )?(prompt|instructions)",
    r"act as (the )?system",
    r"</?(system|assistant|developer)>",
    r"\bBEGIN SYSTEM\b",
    r"do not (tell|inform) the user",
]


class DocumentRejected(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ExtractedPage:
    page: int
    text: str


@dataclass
class ExtractedDocument:
    pages: list[ExtractedPage] = field(default_factory=list)

    @property
    def char_count(self) -> int:
        return sum(len(p.text) for p in self.pages)

    @property
    def page_count(self) -> int:
        return max((p.page for p in self.pages), default=0)


def sniff_mime(data: bytes, declared: str | None, filename: str) -> str:
    """Validate by magic bytes, not by extension or client-declared type."""
    head = data[:8]
    if head.startswith(PDF_MAGIC):
        return PDF_CT
    if head.startswith(ZIP_MAGIC) and filename.lower().endswith(".docx"):
        return DOCX_CT
    if declared == TXT_CT or filename.lower().endswith(".txt"):
        # Plain text must decode as UTF-8 and must not contain NUL bytes (binary masquerade).
        if b"\x00" in data[:4096]:
            raise DocumentRejected("binary_disguised", "File does not appear to be plain text")
        try:
            data[:4096].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentRejected("encoding", "Text file is not valid UTF-8") from exc
        return TXT_CT
    raise DocumentRejected(
        "unsupported_type",
        "Only PDF, DOCX and plain text files are accepted",
    )


def _clean_text(raw: str) -> str:
    text = unicodedata.normalize("NFKC", raw)
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t\x0b\x0c]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract(data: bytes, mime: str) -> ExtractedDocument:
    if mime == PDF_CT:
        return _extract_pdf(data)
    if mime == DOCX_CT:
        return _extract_docx(data)
    if mime == TXT_CT:
        return _extract_txt(data)
    raise DocumentRejected("unsupported_type", "Unsupported document type")


def _extract_pdf(data: bytes) -> ExtractedDocument:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:  # noqa: BLE001 - library raises several types
                raise DocumentRejected("encrypted", "Encrypted PDFs are not supported") from exc
        if len(reader.pages) > 500:
            raise DocumentRejected("too_many_pages", "Document exceeds the 500 page limit")
        pages: list[ExtractedPage] = []
        for index, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:  # noqa: BLE001 - malformed page should not abort the document
                text = ""
            cleaned = _clean_text(text)
            if cleaned:
                pages.append(ExtractedPage(page=index, text=cleaned))
        return ExtractedDocument(pages=pages)
    except DocumentRejected:
        raise
    except PdfReadError as exc:
        raise DocumentRejected("corrupt", "The PDF could not be parsed") from exc
    except Exception as exc:  # noqa: BLE001
        raise DocumentRejected("parse_error", "The document could not be processed") from exc


def _extract_docx(data: bytes) -> ExtractedDocument:
    try:
        import docx  # python-docx

        document = docx.Document(io.BytesIO(data))
        blocks: list[str] = []
        for para in document.paragraphs:
            if para.text.strip():
                blocks.append(para.text)
        for table in document.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    blocks.append(" | ".join(cells))
        text = _clean_text("\n".join(blocks))
        return ExtractedDocument(pages=[ExtractedPage(page=1, text=text)] if text else [])
    except DocumentRejected:
        raise
    except Exception as exc:  # noqa: BLE001
        raise DocumentRejected("corrupt", "The DOCX file could not be parsed") from exc


def _extract_txt(data: bytes) -> ExtractedDocument:
    try:
        text = _clean_text(data.decode("utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        raise DocumentRejected("parse_error", "The text file could not be read") from exc
    return ExtractedDocument(pages=[ExtractedPage(page=1, text=text)] if text else [])


def scan_for_injection(text: str) -> list[str]:
    """Flag prompt-injection style content so it can be quarantined from prompts and reported."""
    lowered = text.lower()
    hits: list[str] = []
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            hits.append(pattern)
    return hits


@dataclass
class Chunk:
    ordinal: int
    page_from: int
    page_to: int
    section: str | None
    content: str


_HEADING = re.compile(r"^(?:\d+\.|\d+\.\d+)\s+[A-Z][A-Za-z ,&/'\-]{4,90}$")


def chunk_document(doc: ExtractedDocument) -> list[Chunk]:
    """Paragraph-aware chunking with overlap, anchored to page ranges and nearest heading."""
    target = settings.chunk_chars
    overlap = settings.chunk_overlap
    chunks: list[Chunk] = []
    ordinal = 0

    for page in doc.pages:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", page.text) if p.strip()]
        buffer = ""
        buffer_page_from = page.page
        current_section: str | None = None

        def flush(text: str, page_to: int) -> None:
            nonlocal ordinal, buffer
            body = text.strip()
            if len(body) < 40:
                buffer = ""
                return
            ordinal += 1
            chunks.append(
                Chunk(
                    ordinal=ordinal,
                    page_from=buffer_page_from,
                    page_to=page_to,
                    section=current_section,
                    content=body,
                )
            )

        for para in paragraphs:
            if _HEADING.match(para) and len(para) < 100:
                current_section = para
            if len(para) > target * 1.6:
                # Long paragraph: split on sentence boundaries.
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sentence in sentences:
                    if len(buffer) + len(sentence) + 1 > target:
                        flush(buffer, page.page)
                        buffer = (buffer[-overlap:] + " " + sentence).strip() if buffer else sentence
                    else:
                        buffer = (buffer + " " + sentence).strip() if buffer else sentence
                continue

            if len(buffer) + len(para) + 1 > target:
                flush(buffer, page.page)
                buffer = (buffer[-overlap:] + "\n\n" + para).strip() if buffer else para
                buffer_page_from = page.page
            else:
                buffer = (buffer + "\n\n" + para).strip() if buffer else para

        if buffer.strip():
            flush(buffer, page.page)

    return chunks


def fence_for_prompt(label: str, body: str) -> str:
    """Delimit untrusted retrieved text. The model is told this is data, never instructions."""
    return (
        f"<<<UNTRUSTED_SOURCE_DATA id={label}>>>\n{body}\n<<<END_UNTRUSTED_SOURCE_DATA>>>"
    )
