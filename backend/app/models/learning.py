"""Courses, materials, enrolments, uploads, document chunks (pgvector)."""
from __future__ import annotations

import datetime as dt
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.models.base import (
    Base, DocumentStatus, EnrolmentStatus, EvidenceStatus, ReviewStatus, TimestampMixin,
    Visibility, uuid_pk,
)


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    objectives: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    prerequisites: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_url: Mapped[str | None] = mapped_column(String(400))
    external_id: Mapped[str | None] = mapped_column(String(120))

    level: Mapped[str] = mapped_column(String(20), default="intermediate", nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    language: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    evidence_status: Mapped[str] = mapped_column(String(20), default=EvidenceStatus.DEMONSTRATION)
    review_status: Mapped[str] = mapped_column(String(16), default=ReviewStatus.PENDING)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    competency_links: Mapped[list["CourseCompetency"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    materials: Mapped[list["CourseMaterial"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="CourseMaterial.sort_order"
    )

    __table_args__ = (
        Index("ix_courses_archive_level", "is_archived", "level"),
        CheckConstraint("duration_minutes > 0", name="duration_positive"),
    )


class CourseCompetency(Base, TimestampMixin):
    """A course contributes to a competency, targeting a specific level."""

    __tablename__ = "course_competencies"

    id: Mapped[uuid.UUID] = uuid_pk()
    course_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    competency_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("competencies.id", ondelete="CASCADE"), index=True
    )
    covers_level: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    weight: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(20), default=EvidenceStatus.PROVISIONAL)

    course: Mapped[Course] = relationship(back_populates="competency_links")

    __table_args__ = (UniqueConstraint("course_id", "competency_id", name="uq_course_competency"),)


class CourseMaterial(Base, TimestampMixin):
    __tablename__ = "course_materials"

    id: Mapped[uuid.UUID] = uuid_pk()
    course_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), default="reading", nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    external_url: Mapped[str | None] = mapped_column(String(400))

    course: Mapped[Course] = relationship(back_populates="materials")


class Enrolment(Base, TimestampMixin):
    __tablename__ = "enrolments"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default=EnrolmentStatus.ENROLLED, nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_material_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_enrolment_user_course"),
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="progress_range"),
    )


class Document(Base, TimestampMixin):
    """Uploaded learning material. Files live outside the webroot; access is always authorized."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("courses.id", ondelete="SET NULL"), index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), index=True
    )

    title: Mapped[str] = mapped_column(String(220), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    visibility: Mapped[str] = mapped_column(String(20), default=Visibility.PRIVATE, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=DocumentStatus.QUEUED, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(60))
    error_detail: Mapped[str | None] = mapped_column(String(300))
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(80))
    processed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    topic_hint: Mapped[str | None] = mapped_column(String(160))
    competency_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_documents_owner_status", "owner_id", "status"),
        Index("ix_documents_visibility", "visibility"),
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    page_from: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    page_to: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    section: Mapped[str | None] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_estimate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.ai_embedding_dim))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped[Document] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("document_id", "ordinal", name="uq_chunk_doc_ordinal"),
        Index("ix_chunk_embedding_hnsw", "embedding", postgresql_using="hnsw",
              postgresql_with={"m": 16, "ef_construction": 64},
              postgresql_ops={"embedding": "vector_cosine_ops"}),
    )
