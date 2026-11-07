"""Single import surface for every ORM model, so Alembic and the app see identical metadata."""
from app.models.assessment import (  # noqa: F401
    Assessment, AssessmentResponse, CompetencyState, LearningPlan, PlanItem, Quiz, QuizAnswer,
    QuizAttempt, QuizQuestion,
)
from app.models.base import Base  # noqa: F401
from app.models.competency import (  # noqa: F401
    Competency, CompetencyDomain, CompetencyPrerequisite, FrameworkVersion, JobRole,
    ProficiencyLevel, RoleCompetencyRequirement, Skill,
)
from app.models.learning import (  # noqa: F401
    Course, CourseCompetency, CourseMaterial, Document, DocumentChunk, Enrolment,
)
from app.models.users import (  # noqa: F401
    AuditLog, Department, LoginAttempt, RefreshToken, User,
)

__all__ = ["Base"]
