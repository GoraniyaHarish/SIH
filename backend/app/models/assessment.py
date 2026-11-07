"""Assessments, competency state, quizzes, attempts, learning plans."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    AssessmentMethod, AssessmentStatus, Base, PlanItemStatus, QuestionType, QuizStatus,
    TimestampMixin, uuid_pk,
)


class Assessment(Base, TimestampMixin):
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    framework_version_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("framework_versions.id", ondelete="CASCADE"), index=True
    )
    method: Mapped[str] = mapped_column(String(24), default=AssessmentMethod.SELF, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=AssessmentStatus.DRAFT, nullable=False)
    title: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)

    submitted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewer_comment: Mapped[str | None] = mapped_column(Text)

    responses: Mapped[list["AssessmentResponse"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_assessment_user_status", "user_id", "status"),)


class AssessmentResponse(Base, TimestampMixin):
    __tablename__ = "assessment_responses"

    id: Mapped[uuid.UUID] = uuid_pk()
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assessments.id", ondelete="CASCADE"), index=True
    )
    competency_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("competencies.id", ondelete="CASCADE"), index=True
    )
    declared_level: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    evidence_note: Mapped[str | None] = mapped_column(Text)
    reviewer_level: Mapped[int | None] = mapped_column(Integer)
    reviewer_comment: Mapped[str | None] = mapped_column(Text)

    assessment: Mapped[Assessment] = relationship(back_populates="responses")

    __table_args__ = (
        UniqueConstraint("assessment_id", "competency_id", name="uq_response_assessment_comp"),
        CheckConstraint("declared_level >= 1 AND declared_level <= 6", name="declared_level_range"),
        CheckConstraint("confidence >= 1 AND confidence <= 5", name="confidence_range"),
    )


class CompetencyState(Base, TimestampMixin):
    """Materialised current proficiency per user+competency, with provenance.

    A self-rating never silently becomes 'verified': `method` and `confidence` are stored and
    surfaced in the UI. Each new assessment replaces the state row (history lives in assessments).
    """

    __tablename__ = "competency_states"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    competency_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("competencies.id", ondelete="CASCADE"), index=True
    )
    level: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(String(24), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    source_assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assessments.id", ondelete="SET NULL")
    )
    assessed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    quiz_evidence: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (
        UniqueConstraint("user_id", "competency_id", name="uq_state_user_competency"),
        CheckConstraint("level >= 0 AND level <= 6", name="state_level_range"),
    )


class Quiz(Base, TimestampMixin):
    __tablename__ = "quizzes"

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default=QuizStatus.DRAFT, nullable=False)

    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), index=True
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("courses.id", ondelete="SET NULL"), index=True
    )
    competency_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)
    generation_mode: Mapped[str] = mapped_column(String(24), default="llm", nullable=False)
    pass_percent: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    time_limit_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    shuffle_options: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_by_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    visibility: Mapped[str] = mapped_column(String(20), default="organisation", nullable=False)

    questions: Mapped[list["QuizQuestion"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan", order_by="QuizQuestion.sort_order"
    )

    __table_args__ = (Index("ix_quiz_status_doc", "status", "source_document_id"),)


class QuizQuestion(Base, TimestampMixin):
    __tablename__ = "quiz_questions"

    id: Mapped[uuid.UUID] = uuid_pk()
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("quizzes.id", ondelete="CASCADE"), index=True
    )
    question_type: Mapped[str] = mapped_column(
        String(20), default=QuestionType.SINGLE_MCQ, nullable=False
    )
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    correct_index: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )
    source_chunk_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_quote: Mapped[str | None] = mapped_column(Text)
    competency_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("competencies.id", ondelete="SET NULL")
    )
    difficulty: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    validation_state: Mapped[str] = mapped_column(String(20), default="validated", nullable=False)
    validation_notes: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    quiz: Mapped[Quiz] = relationship(back_populates="questions")

    __table_args__ = (CheckConstraint("correct_index >= 0", name="correct_index_nonneg"),)


class QuizAttempt(Base, TimestampMixin):
    __tablename__ = "quiz_attempts"

    id: Mapped[uuid.UUID] = uuid_pk()
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("quizzes.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    submitted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    score_correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    option_order: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    answers: Mapped[list["QuizAnswer"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_attempt_user_quiz", "user_id", "quiz_id"),)


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    id: Mapped[uuid.UUID] = uuid_pk()
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("quiz_attempts.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("quiz_questions.id", ondelete="CASCADE")
    )
    selected_index: Mapped[int | None] = mapped_column(Integer)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    attempt: Mapped[QuizAttempt] = relationship(back_populates="answers")

    __table_args__ = (UniqueConstraint("attempt_id", "question_id", name="uq_answer_attempt_q"),)


class LearningPlan(Base, TimestampMixin):
    __tablename__ = "learning_plans"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    job_role_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("job_roles.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    generated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    source_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    items: Mapped[list["PlanItem"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="PlanItem.sort_order"
    )

    __table_args__ = (Index("ix_plan_user_active", "user_id", "is_active"),)


class PlanItem(Base, TimestampMixin):
    __tablename__ = "plan_items"

    id: Mapped[uuid.UUID] = uuid_pk()
    plan_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("learning_plans.id", ondelete="CASCADE"), index=True
    )
    competency_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("competencies.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("courses.id", ondelete="SET NULL")
    )
    activity_type: Mapped[str] = mapped_column(String(24), default="course", nullable=False)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    target_level: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    priority: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=PlanItemStatus.PENDING, nullable=False)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    plan: Mapped[LearningPlan] = relationship(back_populates="items")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(String(200))
    read_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class IntegrationCheck(Base):
    """Append-only probe history so integration status is demonstrably real, not asserted."""

    __tablename__ = "integration_checks"

    id: Mapped[uuid.UUID] = uuid_pk()
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[str | None] = mapped_column(String(400))
    checked_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    checked_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )


class AiUsageLog(Base):
    """Per-call AI telemetry: latency, tokens, outcome. Never stores prompt or document text."""

    __tablename__ = "ai_usage_logs"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    operation: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    model: Mapped[str | None] = mapped_column(String(80))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(24), default="ok", nullable=False)
    error_class: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
