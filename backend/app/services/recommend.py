"""Deterministic, explainable recommendations.

Ranking rule (reproducible by hand):

    course_score = gap_priority
                 * level_fit          (1.0 if course covers the needed level, 0.6 if it overshoots,
                                       0.4 if it only partially covers)
                 * novelty            (1.0 if not enrolled, 0.5 if in progress, 0.15 if completed)
                 * freshness          (0.8 if completed within 90 days -> revision suppressed)
                 + prereq_bonus       (0.3 when all listed course prerequisites are met)

Only gaps that are not prerequisite-blocked are recommended. AI is not used here: the ranking is
pure arithmetic on persisted records so that every recommendation can be justified in one sentence.
"""
from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment import LearningPlan, PlanItem, Quiz, QuizAttempt
from app.models.competency import Competency, CompetencyDomain, JobRole
from app.models.learning import Course, CourseCompetency, CourseMaterial, Enrolment
from app.models.users import User
from app.services import gap as gap_service


@dataclass
class Recommendation:
    kind: str
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
    evidence_status: str | None = None


def _course_progress(percent: int) -> str:
    if percent <= 0:
        return "not started"
    if percent >= 100:
        return "completed"
    return f"{percent}% complete"


def recommend_courses(
    db: Session, user: User, *, limit: int = 8, job_role_id: uuid.UUID | None = None
) -> list[Recommendation]:
    analysis = gap_service.compute(db, user, job_role_id=job_role_id, include_met=False)
    gap_by_competency = {row.competency_id: row for row in analysis["items"]}
    if not gap_by_competency:
        return []

    enrolments = {
        e.course_id: e
        for e in db.scalars(select(Enrolment).where(Enrolment.user_id == user.id))
    }

    links = db.execute(
        select(CourseCompetency, Course)
        .join(Course, Course.id == CourseCompetency.course_id)
        .where(
            Course.is_archived.is_(False),
            CourseCompetency.competency_id.in_(list(gap_by_competency.keys())),
        )
    ).all()

    scored: dict[uuid.UUID, Recommendation] = {}
    for link, course in links:
        gap_row = gap_by_competency[link.competency_id]
        if gap_row.prerequisite_blocked:
            continue

        needed = gap_row.target_level
        if link.covers_level >= needed:
            level_fit, fit_note = 1.0, f"covers up to level {link.covers_level} (needs {needed})"
        elif link.covers_level >= max(1, needed - 1):
            level_fit, fit_note = 0.6, f"partially covers the level (reaches {link.covers_level})"
        else:
            level_fit, fit_note = 0.4, f"foundational only (reaches {link.covers_level})"

        enrolment = enrolments.get(course.id)
        if enrolment is None:
            novelty, novelty_note = 1.0, "not yet started"
        elif enrolment.status == "completed":
            novelty, novelty_note = 0.15, "already completed"
        else:
            novelty, novelty_note = 0.5, _course_progress(enrolment.progress_percent)

        freshness_penalty = 0.0
        if enrolment and enrolment.completed_at is not None:
            age_days = (dt.datetime.now(dt.timezone.utc) - enrolment.completed_at).days
            if age_days < 90:
                freshness_penalty = 0.2
                novelty_note += f", completed {age_days} days ago"

        score = gap_row.priority_score * level_fit * novelty * (1.0 - freshness_penalty)
        score = round(score, 3)

        reasons = [
            f"Gap in {gap_row.code} {gap_row.name}: level {gap_row.current_level:g} of "
            f"{gap_row.target_level} required ({gap_row.severity} severity, {gap_row.priority_band}).",
            f"This course {fit_note}.",
            f"Status: {novelty_note}.",
        ]
        if gap_row.is_critical:
            reasons.append("The competency is marked critical for your job role.")

        existing = scored.get(course.id)
        if existing and existing.score >= score:
            continue
        scored[course.id] = Recommendation(
            kind="course", ref_id=course.id, title=course.title,
            subtitle=course.summary, score=score, reasons=reasons,
            competency_code=gap_row.code, competency_name=gap_row.name,
            target_level=gap_row.target_level, current_level=gap_row.current_level,
            duration_minutes=course.duration_minutes, provider=course.provider,
            evidence_status=course.evidence_status,
        )

    return sorted(scored.values(), key=lambda r: (-r.score, r.title))[:limit]


def recommend_all(db: Session, user: User, *, limit: int = 10) -> list[Recommendation]:
    """Courses plus the two non-course interventions that close the loop."""
    recs = recommend_courses(db, user, limit=limit)
    analysis = gap_service.compute(db, user, include_met=False)

    if analysis["missing_assessment"]:
        recs.insert(
            0,
            Recommendation(
                kind="assessment", ref_id=None,
                title="Complete your baseline competency assessment",
                subtitle="No assessment on record, so gaps cannot be computed yet.",
                score=99.0,
                reasons=["Gap analysis requires at least one submitted assessment.",
                         "It takes about 10 minutes and can be reviewed later by an assessor."],
            ),
        )

    # Suggest a quiz when a published quiz exists for a deficient competency.
    top_gap_ids = [row.competency_id for row in analysis["items"][:5]]
    if top_gap_ids:
        quizzes = db.scalars(
            select(Quiz).where(Quiz.status == "published").limit(50)
        ).all()
        passed_ids = {
            a.quiz_id for a in db.scalars(
                select(QuizAttempt).where(QuizAttempt.user_id == user.id, QuizAttempt.passed.is_(True))
            )
        }
        for quiz in quizzes:
            if quiz.id in passed_ids:
                continue
            overlap = set(str(c) for c in top_gap_ids) & set(quiz.competency_ids or [])
            if not overlap:
                continue
            recs.insert(
                1,
                Recommendation(
                    kind="quiz", ref_id=quiz.id, title=f"Practise: {quiz.title}",
                    subtitle=f"{quiz.difficulty} · pass mark {quiz.pass_percent}%",
                    score=6.0,
                    reasons=[f"Published assessment covering {len(overlap)} of your gap competencies.",
                             "Attempts feed quiz evidence back into your gap analysis."],
                    evidence_status="provisional",
                ),
            )
            break

    return recs[:limit]


def ensure_plan(db: Session, user: User, *, force: bool = False) -> LearningPlan:
    """Build or refresh the active learning plan from current gaps.

    Recalculation is triggered explicitly (after an assessment or on request) rather than on every
    read, so plan history stays meaningful.
    """
    current = db.scalars(
        select(LearningPlan)
        .where(LearningPlan.user_id == user.id, LearningPlan.is_active.is_(True))
        .order_by(LearningPlan.version.desc())
    ).first()
    if current and not force:
        return current

    analysis = gap_service.compute(db, user, include_met=False)
    role = db.get(JobRole, user.job_role_id) if user.job_role_id else None
    max_version = current.version if current else 0

    if current:
        for old in db.scalars(select(LearningPlan).where(LearningPlan.user_id == user.id)):
            old.is_active = False

    plan = LearningPlan(
        user_id=user.id,
        job_role_id=user.job_role_id,
        title=f"Learning pathway for {role.title}" if role else "Personal learning pathway",
        rationale=(
            f"Generated from {analysis['gap_count']} open competency gaps "
            f"({analysis['critical_gap_count']} critical). Items are ordered so prerequisites come "
            "first; priority follows the documented gap score."
        ),
        version=max_version + 1,
        is_active=True,
        source_snapshot={
            "readiness": analysis["overall_readiness_percent"],
            "gap_count": analysis["gap_count"],
            "critical_gap_count": analysis["critical_gap_count"],
            "job_role": analysis["job_role_title"],
        },
    )
    db.add(plan)
    db.flush()

    order = 0
    for gap_row in analysis["items"]:
        if gap_row.prerequisite_blocked:
            continue
        # Prefer the best-matching course for this competency.
        link = db.execute(
            select(CourseCompetency, Course)
            .join(Course, Course.id == CourseCompetency.course_id)
            .where(
                CourseCompetency.competency_id == gap_row.competency_id,
                Course.is_archived.is_(False),
            )
            .order_by(CourseCompetency.covers_level.desc())
            .limit(1)
        ).first()

        order += 1
        if link:
            lc, course = link
            materials = db.scalars(
                select(CourseMaterial).where(CourseMaterial.course_id == course.id)
            ).all()
            minutes = sum(m.duration_minutes for m in materials) or course.duration_minutes
            db.add(
                PlanItem(
                    plan_id=plan.id, competency_id=gap_row.competency_id, course_id=course.id,
                    activity_type="course", title=course.title,
                    detail=f"Closes a {gap_row.deficit:g}-level gap to reach level "
                           f"{gap_row.target_level}. {gap_row.severity.title()} severity.",
                    target_level=gap_row.target_level, estimated_minutes=minutes,
                    priority=gap_row.priority_score, sort_order=order,
                )
            )
        else:
            db.add(
                PlanItem(
                    plan_id=plan.id, competency_id=gap_row.competency_id, course_id=None,
                    activity_type="self_study",
                    title=f"Self-study: {gap_row.name}",
                    detail="No catalogued course covers this competency yet. Discuss with your "
                           "training manager, or upload relevant material and generate a quiz.",
                    target_level=gap_row.target_level, estimated_minutes=90,
                    priority=gap_row.priority_score, sort_order=order,
                )
            )
        db.add(
            PlanItem(
                plan_id=plan.id, competency_id=gap_row.competency_id, course_id=None,
                activity_type="reassess",
                title=f"Re-assess: {gap_row.name}",
                detail="Take a competency assessment after completing the learning activity so the "
                       "gap can be closed with evidence.",
                target_level=gap_row.target_level, estimated_minutes=15,
                priority=gap_row.priority_score, sort_order=order + 1000,
            )
        )

    db.flush()
    return plan


def plan_progress(db: Session, plan: LearningPlan) -> dict:
    items = db.scalars(select(PlanItem).where(PlanItem.plan_id == plan.id)).all()
    completed = [i for i in items if i.status == "completed"]
    return {
        "total": len(items),
        "completed": len(completed),
        "minutes": sum(i.estimated_minutes for i in items),
        "remaining_minutes": sum(i.estimated_minutes for i in items if i.status != "completed"),
    }
