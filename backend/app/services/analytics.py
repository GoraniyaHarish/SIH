"""Aggregate analytics computed from persisted records only.

Privacy: manager views are aggregate. Any cell derived from fewer than
`SUPPRESSION_THRESHOLD` learners is suppressed (reported as None with an explicit flag) so an
individual's competency position cannot be inferred from a small group.
"""
from __future__ import annotations

import datetime as dt
import uuid
from collections import Counter, defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.assessment import (
    Assessment, CompetencyState, LearningPlan, PlanItem, Quiz, QuizAttempt,
)
from app.models.competency import (
    Competency, CompetencyDomain, JobRole, RoleCompetencyRequirement,
)
from app.models.learning import Course, CourseCompetency, Document, Enrolment
from app.models.users import AuditLog, User
from app.services import gap as gap_service

SUPPRESSION_THRESHOLD = 5


def manager_analytics(
    db: Session,
    actor: User,
    *,
    department_id: uuid.UUID | None = None,
    job_role_id: uuid.UUID | None = None,
) -> dict:
    """Aggregate gaps for the actor's scope.

    Admin: whole organisation (optionally filtered). Manager: own department only. This is enforced
    by intersecting the requested filter with the actor's permitted scope, so a manager cannot widen
    scope by passing another department id.
    """
    from app.models.base import Role

    query = select(User).where(User.is_active.is_(True), User.role == Role.LEARNER)
    if actor.role == Role.MANAGER:
        if actor.department_id is None:
            query = query.where(User.id == actor.id)  # no department: empty scope
        else:
            query = query.where(User.department_id == actor.department_id)
    elif department_id is not None:
        query = query.where(User.department_id == department_id)

    if job_role_id is not None:
        query = query.where(User.job_role_id == job_role_id)

    learners = list(db.scalars(query))
    learner_ids = [u.id for u in learners]
    headcount = len(learner_ids)

    assessed_ids = set(
        db.scalars(
            select(Assessment.user_id).where(
                Assessment.user_id.in_(learner_ids) if learner_ids else False,
                Assessment.status.in_(["submitted", "reviewed"]),
            )
        )
    ) if learner_ids else set()

    states = []
    if learner_ids:
        states = list(
            db.scalars(select(CompetencyState).where(CompetencyState.user_id.in_(learner_ids)))
        )

    domain_deficit: dict[uuid.UUID, list[float]] = defaultdict(list)
    learners_with_gap: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    readiness_values: list[float] = []
    critical_learners = 0

    comp_domain = {
        c.id: c.domain_id
        for c in db.scalars(select(Competency))
    }

    for learner in learners:
        analysis = gap_service.compute(db, learner, include_met=False)
        if analysis["total_required"] == 0:
            continue
        if analysis["gap_count"] > 0:
            readiness_values.append(analysis["overall_readiness_percent"])
            if analysis["critical_gap_count"] > 0:
                critical_learners += 1
        for row in analysis["items"]:
            domain_id = comp_domain.get(row.competency_id)
            if domain_id is None:
                continue
            domain_deficit[domain_id].append(row.deficit)
            learners_with_gap[domain_id].add(learner.id)

    domains = {d.id: d for d in db.scalars(select(CompetencyDomain))}
    domain_gaps = []
    for domain_id, deficits in domain_deficit.items():
        if not deficits:
            continue
        domain = domains.get(domain_id)
        if domain is None:
            continue
        avg = sum(deficits) / len(deficits)
        affected = len(learners_with_gap[domain_id])
        suppress = 0 < affected < SUPPRESSION_THRESHOLD
        domain_gaps.append({
            "domain_code": domain.code,
            "domain_name": domain.name,
            "competency_count": len(deficits),
            "average_deficit": None if suppress else round(avg, 2),
            "learners_with_gap": None if suppress else affected,
        })
    domain_gaps.sort(key=lambda d: -(d["average_deficit"] or 0))

    # course completion, scoped to the same learner set
    completion_rows = db.execute(
        select(
            Course.title,
            func.count(Enrolment.id).label("enrolled"),
            func.sum(func.cast(Enrolment.status == "completed", func.INTEGER())).label("done"),
            func.avg(Enrolment.progress_percent).label("avg_progress"),
        )
        .join(Enrolment, Enrolment.course_id == Course.id)
        .where(Enrolment.user_id.in_(learner_ids) if learner_ids else False)
        .group_by(Course.title)
        .order_by(func.count(Enrolment.id).desc())
        .limit(15)
    ).all() if learner_ids else []

    course_completion = [
        {
            "course": row.title,
            "enrolled": int(row.enrolled or 0),
            "completed": int(row.done or 0),
            "average_progress": None if int(row.enrolled or 0) < SUPPRESSION_THRESHOLD
            else round(float(row.avg_progress or 0), 1),
            "suppressed": int(row.enrolled or 0) < SUPPRESSION_THRESHOLD,
        }
        for row in completion_rows
    ]

    assessment_rows = db.execute(
        select(Assessment.method, func.count(Assessment.id))
        .where(Assessment.user_id.in_(learner_ids) if learner_ids else False)
        .where(Assessment.status.in_(["submitted", "reviewed"]))
        .group_by(Assessment.method)
    ).all() if learner_ids else []
    assessment_outcomes = [
        {"method": method, "count": int(count),
         "suppressed": int(count) < SUPPRESSION_THRESHOLD}
        for method, count in assessment_rows
    ]

    quiz_rows = db.execute(
        select(Quiz.title, func.count(QuizAttempt.id), func.avg(QuizAttempt.score_percent))
        .join(QuizAttempt, QuizAttempt.quiz_id == Quiz.id)
        .where(QuizAttempt.user_id.in_(learner_ids) if learner_ids else False)
        .where(QuizAttempt.submitted_at.is_not(None))
        .group_by(Quiz.title)
        .limit(15)
    ).all() if learner_ids else []
    quiz_performance = [
        {
            "quiz": title,
            "attempts": int(count),
            "average_score": None if int(count) < SUPPRESSION_THRESHOLD else round(float(avg or 0), 1),
            "suppressed": int(count) < SUPPRESSION_THRESHOLD,
        }
        for title, count, avg in quiz_rows
    ]

    scope_label = "organisation"
    if actor.role == Role.MANAGER:
        scope_label = "department"
    elif department_id is not None:
        scope_label = "department_filter"

    suppression_applied = any(
        d["average_deficit"] is None for d in domain_gaps
    ) or any(c["suppressed"] for c in course_completion) or any(
        q["suppressed"] for q in quiz_performance
    )

    return {
        "scope": scope_label,
        "as_of": dt.datetime.now(dt.timezone.utc),
        "headcount_considered": headcount,
        "assessed_learners": len(assessed_ids),
        "suppression_applied": suppression_applied,
        "suppression_threshold": SUPPRESSION_THRESHOLD,
        "average_readiness_percent": (
            None if len(readiness_values) < SUPPRESSION_THRESHOLD
            else round(sum(readiness_values) / len(readiness_values), 1)
        ),
        "critical_gap_learners": (
            None if headcount < SUPPRESSION_THRESHOLD else critical_learners
        ),
        "domain_gaps": domain_gaps,
        "course_completion": course_completion,
        "assessment_outcomes": assessment_outcomes,
        "quiz_performance": quiz_performance,
    }


def admin_overview(db: Session) -> dict:
    from app.models.base import Role

    users_by_role = {
        role.value: int(count)
        for role, count in db.execute(
            select(User.role, func.count(User.id)).group_by(User.role)
        ).all()
    }
    active_users = int(
        db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0
    )
    documents_by_status = {
        status: int(count)
        for status, count in db.execute(
            select(Document.status, func.count(Document.id)).group_by(Document.status)
        ).all()
    }
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)

    from app.models.assessment import AiUsageLog

    ai_calls = int(
        db.scalar(select(func.count(AiUsageLog.id)).where(AiUsageLog.created_at >= since)) or 0
    )
    ai_errors = int(
        db.scalar(
            select(func.count(AiUsageLog.id)).where(
                AiUsageLog.created_at >= since, AiUsageLog.outcome != "ok"
            )
        ) or 0
    )
    audit_events = int(
        db.scalar(select(func.count(AuditLog.id)).where(AuditLog.created_at >= since)) or 0
    )

    return {
        "users_by_role": users_by_role,
        "active_users": active_users,
        "documents_by_status": documents_by_status,
        "courses_total": int(db.scalar(select(func.count(Course.id))) or 0),
        "quizzes_total": int(db.scalar(select(func.count(Quiz.id))) or 0),
        "attempts_total": int(db.scalar(select(func.count(QuizAttempt.id))) or 0),
        "ai_calls_24h": ai_calls,
        "ai_error_rate_24h": (
            round(100.0 * ai_errors / ai_calls, 1) if ai_calls else None
        ),
        "audit_events_24h": audit_events,
    }


def learner_summary(db: Session, user: User) -> dict:
    analysis = gap_service.compute(db, user, include_met=False)
    enrolments = list(db.scalars(select(Enrolment).where(Enrolment.user_id == user.id)))
    attempts = list(
        db.scalars(
            select(QuizAttempt)
            .where(QuizAttempt.user_id == user.id, QuizAttempt.submitted_at.is_not(None))
            .order_by(QuizAttempt.submitted_at.desc())
        )
    )
    plan = db.scalars(
        select(LearningPlan)
        .where(LearningPlan.user_id == user.id, LearningPlan.is_active.is_(True))
        .order_by(LearningPlan.version.desc())
    ).first()
    plan_items = list(db.scalars(select(PlanItem).where(PlanItem.plan_id == plan.id))) if plan else []

    history = [
        {
            "date": a.created_at.date().isoformat(),
            "method": a.method,
            "status": a.status,
        }
        for a in db.scalars(
            select(Assessment)
            .where(Assessment.user_id == user.id)
            .order_by(Assessment.created_at.desc())
            .limit(10)
        )
    ]

    return {
        "readiness_percent": analysis["overall_readiness_percent"],
        "gap_count": analysis["gap_count"],
        "critical_gap_count": analysis["critical_gap_count"],
        "assessed_competencies": analysis["total_required"] - analysis["gap_count"],
        "total_required": analysis["total_required"],
        "active_courses": sum(1 for e in enrolments if e.status == "enrolled"),
        "completed_courses": sum(1 for e in enrolments if e.status == "completed"),
        "quiz_attempts": len(attempts),
        "quiz_average": round(sum(a.score_percent for a in attempts) / len(attempts), 1)
        if attempts else None,
        "plan_items": len(plan_items),
        "plan_completed": sum(1 for i in plan_items if i.status == "completed"),
        "plan_minutes_remaining": sum(
            i.estimated_minutes for i in plan_items if i.status != "completed"
        ),
        "assessment_history": history,
        "top_gaps": [
            {
                "competency_code": row.code,
                "competency_name": row.name,
                "current_level": row.current_level,
                "target_level": row.target_level,
                "severity": row.severity,
                "priority_band": row.priority_band,
            }
            for row in analysis["items"][:5]
        ],
        "missing_assessment": analysis["missing_assessment"],
    }
