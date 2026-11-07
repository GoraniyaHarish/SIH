"""Pydantic request/response models. All input is validated here before touching services."""
from __future__ import annotations

import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.base import (
    AssessmentMethod, EvidenceStatus, QuestionType, Role, Visibility,
)

# ------------------------------------------------------------------ auth
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=10, max_length=200)
    department_id: uuid.UUID | None = None
    job_role_id: uuid.UUID | None = None
    designation: str | None = Field(default=None, max_length=160)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserOut"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: Role
    designation: str | None
    department_id: uuid.UUID | None
    department_name: str | None = None
    job_role_id: uuid.UUID | None
    job_role_title: str | None = None
    is_active: bool
    last_login_at: dt.datetime | None
    created_at: dt.datetime


class UserCreateRequest(RegisterRequest):
    role: Role = Role.LEARNER


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    role: Role | None = None
    department_id: uuid.UUID | None = None
    job_role_id: uuid.UUID | None = None
    designation: str | None = Field(default=None, max_length=160)
    is_active: bool | None = None


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=200)


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    designation: str | None = Field(default=None, max_length=160)
    job_role_id: uuid.UUID | None = None


class DepartmentIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    code: str | None = Field(default=None, max_length=32)
    description: str | None = None


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str | None
    description: str | None
    user_count: int | None = None


# ------------------------------------------------------------------ competency framework
class LevelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    level: int
    label: str
    summary: str
    criteria: list[str]
    evidence_status: EvidenceStatus


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    statement: str


class CompetencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    rationale: str | None
    evidence_status: EvidenceStatus
    review_status: str
    source_ref: str | None
    domain_id: uuid.UUID
    domain_name: str | None = None
    domain_code: str | None = None
    skills: list[SkillOut] = []


class DomainOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    kind: str
    evidence_status: EvidenceStatus
    competency_count: int = 0


class FrameworkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str
    notes: str | None
    evidence_status: EvidenceStatus
    is_active: bool
    created_at: dt.datetime


class DomainCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=24, pattern=r"^[A-Za-z0-9_\-]+$")
    name: str = Field(min_length=3, max_length=120)
    description: str | None = None
    kind: Literal["behavioural", "functional", "domain"] = "functional"
    evidence_status: EvidenceStatus = EvidenceStatus.PROVISIONAL
    source_ref: str | None = Field(default=None, max_length=255)


class CompetencyCreateRequest(BaseModel):
    domain_id: uuid.UUID
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9_.\-]+$")
    name: str = Field(min_length=3, max_length=160)
    description: str | None = None
    rationale: str | None = None
    evidence_status: EvidenceStatus = EvidenceStatus.PROVISIONAL
    source_ref: str | None = Field(default=None, max_length=255)
    skills: list[str] = []

    @field_validator("skills")
    @classmethod
    def _cap_skills(cls, v: list[str]) -> list[str]:
        return [s.strip()[:400] for s in v if s.strip()][:12]


class CompetencyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = None
    rationale: str | None = None
    evidence_status: EvidenceStatus | None = None
    review_status: Literal["pending", "approved", "retired"] | None = None
    source_ref: str | None = Field(default=None, max_length=255)


class RoleRequirementIn(BaseModel):
    competency_id: uuid.UUID
    required_level: int = Field(ge=1, le=6)
    importance: int = Field(default=3, ge=1, le=5)
    is_critical: bool = False
    rationale: str | None = None


class JobRoleCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9_\-]+$")
    title: str = Field(min_length=3, max_length=160)
    description: str | None = None
    cadre: str | None = Field(default=None, max_length=60)
    grade: str | None = Field(default=None, max_length=40)
    evidence_status: EvidenceStatus = EvidenceStatus.PROVISIONAL
    source_ref: str | None = Field(default=None, max_length=255)
    requirements: list[RoleRequirementIn] = []


class RoleRequirementOut(BaseModel):
    competency_id: uuid.UUID
    competency_code: str
    competency_name: str
    domain_name: str
    required_level: int
    importance: int
    is_critical: bool
    rationale: str | None
    evidence_status: EvidenceStatus


class JobRoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str
    description: str | None
    cadre: str | None
    grade: str | None
    evidence_status: EvidenceStatus
    review_status: str
    requirement_count: int = 0
    requirements: list[RoleRequirementOut] = []


class PrerequisiteIn(BaseModel):
    competency_id: uuid.UUID
    prerequisite_competency_id: uuid.UUID
    min_level: int = Field(default=2, ge=1, le=6)


# ------------------------------------------------------------------ assessment
class ResponseIn(BaseModel):
    competency_id: uuid.UUID
    declared_level: int = Field(ge=1, le=6)
    confidence: int = Field(default=3, ge=1, le=5)
    evidence_note: str | None = Field(default=None, max_length=1000)


class AssessmentCreateRequest(BaseModel):
    method: AssessmentMethod = AssessmentMethod.SELF
    title: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)
    responses: list[ResponseIn] = Field(min_length=1, max_length=200)


class AssessmentReviewRequest(BaseModel):
    responses: list[ResponseIn]


class AssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    method: AssessmentMethod
    status: str
    title: str | None
    notes: str | None
    submitted_at: dt.datetime | None
    reviewed_at: dt.datetime | None
    created_at: dt.datetime
    response_count: int = 0
    reviewer_comment: str | None = None


class AssessmentResponseOut(BaseModel):
    competency_id: uuid.UUID
    competency_code: str
    competency_name: str
    declared_level: int
    confidence: int
    evidence_note: str | None
    reviewer_level: int | None
    reviewer_comment: str | None


class AssessmentDetailOut(AssessmentOut):
    responses: list[AssessmentResponseOut] = []


# ------------------------------------------------------------------ gaps
class GapItem(BaseModel):
    competency_id: uuid.UUID
    competency_code: str
    competency_name: str
    domain_name: str
    domain_code: str
    current_level: float
    current_level_source: str
    target_level: int
    deficit: float
    severity: Literal["none", "low", "moderate", "high", "critical"]
    importance: int
    is_critical: bool
    priority_score: float
    priority_band: Literal["P1", "P2", "P3", "P4"]
    explanation: str
    prerequisite_blocked: bool = False
    evidence_status: EvidenceStatus


class GapAnalysisOut(BaseModel):
    user_id: uuid.UUID
    job_role_id: uuid.UUID | None
    job_role_title: str | None
    framework_label: str
    method_note: str
    computed_at: dt.datetime
    total_required: int
    met_count: int
    gap_count: int
    critical_gap_count: int
    overall_readiness_percent: float
    items: list[GapItem]
    missing_assessment: bool = False


# ------------------------------------------------------------------ courses
class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str
    summary: str | None
    provider: str
    provider_url: str | None
    level: str
    duration_minutes: int
    language: str
    tags: list[str]
    objectives: list[str]
    prerequisites: list[str]
    evidence_status: EvidenceStatus
    is_archived: bool
    competency_ids: list[uuid.UUID] = []
    competency_names: list[str] = []


class CourseMaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    kind: str
    description: str | None
    duration_minutes: int
    sort_order: int
    external_url: str | None


class CourseDetailOut(CourseOut):
    description: str | None
    materials: list[CourseMaterialOut] = []
    enrolment: "EnrolmentOut | None" = None


class CourseCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_\-]+$")
    title: str = Field(min_length=3, max_length=200)
    summary: str | None = Field(default=None, max_length=500)
    description: str | None = None
    objectives: list[str] = []
    prerequisites: list[str] = []
    provider: str = Field(min_length=2, max_length=120)
    provider_url: str | None = Field(default=None, max_length=400)
    level: Literal["foundation", "intermediate", "advanced"] = "intermediate"
    duration_minutes: int = Field(default=60, ge=5, le=6000)
    tags: list[str] = []
    evidence_status: EvidenceStatus = EvidenceStatus.DEMONSTRATION
    competency_ids: list[uuid.UUID] = []


class CourseUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    summary: str | None = Field(default=None, max_length=500)
    description: str | None = None
    provider: str | None = Field(default=None, min_length=2, max_length=120)
    provider_url: str | None = Field(default=None, max_length=400)
    level: Literal["foundation", "intermediate", "advanced"] | None = None
    duration_minutes: int | None = Field(default=None, ge=5, le=6000)
    tags: list[str] | None = None
    evidence_status: EvidenceStatus | None = None
    competency_ids: list[uuid.UUID] | None = None


class EnrolmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    status: str
    progress_percent: int
    completed_material_ids: list[str]
    started_at: dt.datetime
    completed_at: dt.datetime | None
    course_title: str | None = None


class ProgressRequest(BaseModel):
    material_id: uuid.UUID
    completed: bool = True


class RecommendationOut(BaseModel):
    kind: Literal["course", "quiz", "review", "assessment"]
    ref_id: uuid.UUID | None
    title: str
    subtitle: str | None
    score: float
    reasons: list[str]
    competency_code: str | None = None
    competency_name: str | None = None
    target_level: int | None = None
    current_level: float | None = None
    duration_minutes: int | None = None
    provider: str | None = None
    evidence_status: EvidenceStatus | None = None


# ------------------------------------------------------------------ documents
class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    original_filename: str
    mime_type: str
    size_bytes: int
    visibility: Visibility
    status: str
    error_code: str | None
    page_count: int
    char_count: int
    chunk_count: int
    embedding_model: str | None
    processed_at: dt.datetime | None
    created_at: dt.datetime
    owner_id: uuid.UUID
    owner_name: str | None = None
    course_id: uuid.UUID | None
    topic_hint: str | None


class DocumentUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=220)
    visibility: Visibility | None = None
    topic_hint: str | None = Field(default=None, max_length=160)


class ChunkPreview(BaseModel):
    ordinal: int
    page_from: int
    page_to: int
    section: str | None
    preview: str
    has_embedding: bool


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    document_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)


class Citation(BaseModel):
    document_id: uuid.UUID
    document_title: str
    chunk_id: uuid.UUID
    page_from: int
    page_to: int
    section: str | None
    snippet: str
    similarity: float


class AskResponse(BaseModel):
    answer: str
    grounded: bool
    mode: Literal["llm", "extractive", "refused"]
    citations: list[Citation]
    insufficient_evidence: bool
    noanswer_reason: str | None = None
    latency_ms: int | None = None


# ------------------------------------------------------------------ quizzes
class QuestionDraft(BaseModel):
    stem: str
    options: list[str]
    correct_index: int
    explanation: str
    source_chunk_id: uuid.UUID | None = None
    source_page: int | None = None
    source_quote: str | None = None
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    question_type: QuestionType = QuestionType.SINGLE_MCQ


class QuizGenerateRequest(BaseModel):
    document_id: uuid.UUID
    question_count: int = Field(default=5, ge=1, le=20)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    question_types: list[QuestionType] = [QuestionType.SINGLE_MCQ]
    title: str | None = Field(default=None, max_length=200)
    competency_ids: list[uuid.UUID] = []


class QuizQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stem: str
    options: list[dict]
    correct_index: int
    explanation: str
    source_page: int | None
    source_quote: str | None
    source_document_id: uuid.UUID | None
    difficulty: str
    question_type: str
    validation_state: str
    validation_notes: list[str]
    sort_order: int


class QuizOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    status: str
    difficulty: str
    generation_mode: str
    pass_percent: int
    time_limit_minutes: int
    source_document_id: uuid.UUID | None
    created_at: dt.datetime
    question_count: int = 0
    best_score: float | None = None
    attempt_count: int = 0


class QuizDetailOut(QuizOut):
    questions: list[QuizQuestionOut] = []
    can_manage: bool = False


class QuizPublishRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class QuestionUpdateRequest(BaseModel):
    stem: str | None = Field(default=None, min_length=5)
    options: list[str] | None = None
    correct_index: int | None = Field(default=None, ge=0, le=5)
    explanation: str | None = Field(default=None, min_length=3)
    difficulty: Literal["easy", "medium", "hard"] | None = None


class AttemptSubmitRequest(BaseModel):
    answers: dict[str, int | None]


class AttemptAnswerOut(BaseModel):
    question_id: uuid.UUID
    stem: str
    options: list[dict]
    correct_index: int
    selected_index: int | None
    is_correct: bool
    explanation: str
    source_page: int | None
    source_quote: str | None


class AttemptResultOut(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: str
    score_correct: int
    score_total: int
    score_percent: float
    passed: bool
    submitted_at: dt.datetime | None
    answers: list[AttemptAnswerOut]


# ------------------------------------------------------------------ plans
class PlanItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    competency_id: uuid.UUID
    competency_code: str | None = None
    competency_name: str | None = None
    course_id: uuid.UUID | None
    course_title: str | None = None
    activity_type: str
    title: str
    detail: str | None
    target_level: int
    estimated_minutes: int
    priority: float
    sort_order: int
    status: str
    completed_at: dt.datetime | None


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    rationale: str | None
    generated_at: dt.datetime
    is_active: bool
    version: int
    items: list[PlanItemOut] = []
    total_minutes: int = 0
    completed_items: int = 0


class PlanItemUpdateRequest(BaseModel):
    status: Literal["pending", "in_progress", "completed", "skipped"]


# ------------------------------------------------------------------ analytics
class DomainGapAggregate(BaseModel):
    domain_code: str
    domain_name: str
    competency_count: int
    average_deficit: float
    learners_with_gap: int


class ManagerAnalyticsOut(BaseModel):
    scope: str
    as_of: dt.datetime
    headcount_considered: int
    assessed_learners: int
    suppression_applied: bool
    suppression_threshold: int
    average_readiness_percent: float | None
    critical_gap_learners: int | None
    domain_gaps: list[DomainGapAggregate]
    course_completion: list[dict]
    assessment_outcomes: list[dict]
    quiz_performance: list[dict]


class AdminOverviewOut(BaseModel):
    users_by_role: dict[str, int]
    active_users: int
    documents_by_status: dict[str, int]
    courses_total: int
    quizzes_total: int
    attempts_total: int
    ai_configured: bool
    ai_calls_24h: int
    ai_error_rate_24h: float | None
    integrations: list[dict]
    audit_events_24h: int


# ------------------------------------------------------------------ integrations
class IntegrationStatusOut(BaseModel):
    provider: str
    status: str
    configured: bool
    base_url_host: str | None
    http_status: int | None
    latency_ms: int | None
    detail: str | None
    checked_at: dt.datetime | None
    capabilities: list[str]
    notes: str


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_role: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    outcome: str
    detail: str | None
    created_at: dt.datetime


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    title: str
    body: str | None
    link: str | None
    read_at: dt.datetime | None
    created_at: dt.datetime


class HealthOut(BaseModel):
    status: str
    version: str
    database: str
    redis: str
    ai: str
    integrations: list[str]
    warnings: list[str]


TokenResponse.model_rebuild()
CourseDetailOut.model_rebuild()
