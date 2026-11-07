"""Declarative base, shared mixins and domain enums."""
from __future__ import annotations

import datetime as dt
import enum
import uuid

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


class Role(str, enum.Enum):
    LEARNER = "learner"
    ADMIN = "admin"
    MANAGER = "manager"
    ASSESSOR = "assessor"


class EvidenceStatus(str, enum.Enum):
    """Truthfulness axis for every domain artefact. Rendered in the UI as a badge."""

    OFFICIAL = "official"
    PROVISIONAL = "provisional"
    DEMONSTRATION = "demonstration"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    RETIRED = "retired"


class AssessmentMethod(str, enum.Enum):
    SELF = "self"
    STRUCTURED = "structured"
    ASSESSOR_REVIEWED = "assessor_reviewed"


class AssessmentStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"


class DocumentStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Visibility(str, enum.Enum):
    PRIVATE = "private"
    DEPARTMENT = "department"
    ORGANISATION = "organisation"
    COURSE = "course"


class QuizStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class QuestionType(str, enum.Enum):
    SINGLE_MCQ = "single_mcq"
    TRUE_FALSE = "true_false"


class PlanItemStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class EnrolmentStatus(str, enum.Enum):
    ENROLLED = "enrolled"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"


class IntegrationStatus(str, enum.Enum):
    NOT_CONFIGURED = "not_configured"
    UNREACHABLE = "unreachable"
    AUTH_FAILED = "auth_failed"
    OK = "ok"
    DEGRADED = "degraded"
