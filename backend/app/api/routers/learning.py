"""Courses, enrolment, progress, recommendations and learning plans."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Page, Principal, pagination, require_admin, require_roles
from app.models.assessment import LearningPlan, PlanItem, Quiz
from app.models.base import EnrolmentStatus, Role
from app.models.competency import Competency
from app.models.learning import Course, CourseCompetency, CourseMaterial, Enrolment
from app.models.users import User
from app.schemas import (
    CourseCreateRequest, CourseDetailOut, CourseMaterialOut, CourseOut, CourseUpdateRequest,
    EnrolmentOut, PlanItemOut, PlanItemUpdateRequest, PlanOut, ProgressRequest,
    RecommendationOut,
)
from app.services import audit, recommend

router = APIRouter(tags=["learning"])


def _course_out(db: Session, course: Course) -> CourseOut:
    out = CourseOut.model_validate(course)
    links = db.execute(
        select(CourseCompetency, Competency)
        .join(Competency, Competency.id == CourseCompetency.competency_id)
        .where(CourseCompetency.course_id == course.id)
    ).all()
    out.competency_ids = [link.competency_id for link, _ in links]
    out.competency_names = [f"{comp.code} {comp.name}" for _, comp in links]
    return out


def _enrolment_out(db: Session, enrolment: Enrolment) -> EnrolmentOut:
    out = EnrolmentOut.model_validate(enrolment)
    course = db.get(Course, enrolment.course_id)
    out.course_title = course.title if course else None
    return out


# ---------------------------------------------------------------- courses
@router.get("/courses", response_model=list[CourseOut])
def list_courses(
    db: Session = Depends(get_db), page: Page = Depends(pagination),
    q: str | None = Query(default=None, max_length=80),
    level: str | None = Query(default=None, max_length=20),
    competency_id: uuid.UUID | None = None,
    include_archived: bool = False,
) -> list[CourseOut]:
    stmt = select(Course)
    if not include_archived:
        stmt = stmt.where(Course.is_archived.is_(False))
    if q:
        pattern = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            func.lower(Course.title).like(pattern)
            | func.lower(func.coalesce(Course.summary, "")).like(pattern)
            | func.lower(Course.provider).like(pattern)
        )
    if level:
        stmt = stmt.where(Course.level == level)
    if competency_id:
        stmt = stmt.join(CourseCompetency, CourseCompetency.course_id == Course.id).where(
            CourseCompetency.competency_id == competency_id
        )
    stmt = stmt.order_by(Course.title).limit(page.limit).offset(page.offset)
    return [_course_out(db, c) for c in db.scalars(stmt)]


@router.get("/courses/{course_id}", response_model=CourseDetailOut)
def get_course(
    course_id: uuid.UUID, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.LEARNER, Role.MANAGER, Role.ASSESSOR, Role.ADMIN)),
) -> CourseDetailOut:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(404, "Course not found")
    base = _course_out(db, course)
    out = CourseDetailOut(**base.model_dump())
    out.description = course.description
    out.materials = [CourseMaterialOut.model_validate(m) for m in course.materials]
    enrolment = db.scalars(
        select(Enrolment).where(
            Enrolment.user_id == principal.id, Enrolment.course_id == course.id
        )
    ).first()
    out.enrolment = _enrolment_out(db, enrolment) if enrolment else None
    return out


@router.post("/courses", response_model=CourseOut, status_code=201)
def create_course(
    payload: CourseCreateRequest, db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> CourseOut:
    if db.scalars(select(Course).where(Course.code == payload.code.upper())).first():
        raise HTTPException(409, "A course with this code already exists")
    for competency_id in payload.competency_ids:
        if db.get(Competency, competency_id) is None:
            raise HTTPException(422, f"Unknown competency {competency_id}")

    course = Course(
        code=payload.code.upper(), title=payload.title.strip(), summary=payload.summary,
        description=payload.description, objectives=payload.objectives,
        prerequisites=payload.prerequisites, provider=payload.provider.strip(),
        provider_url=payload.provider_url, level=payload.level,
        duration_minutes=payload.duration_minutes, tags=payload.tags,
        evidence_status=payload.evidence_status, created_by_id=principal.id,
    )
    db.add(course)
    db.flush()
    for competency_id in payload.competency_ids:
        db.add(
            CourseCompetency(course_id=course.id, competency_id=competency_id, covers_level=3)
        )
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="course.created", resource_type="course", resource_id=str(course.id),
                 detail=payload.code)
    db.commit()
    db.refresh(course)
    return _course_out(db, course)


@router.patch("/courses/{course_id}", response_model=CourseOut)
def update_course(
    course_id: uuid.UUID, payload: CourseUpdateRequest, db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> CourseOut:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(404, "Course not found")
    for field in ("title", "summary", "description", "provider", "provider_url", "level",
                  "duration_minutes", "tags", "evidence_status"):
        value = getattr(payload, field)
        if value is not None:
            setattr(course, field, value)
    if payload.competency_ids is not None:
        db.query(CourseCompetency).filter(CourseCompetency.course_id == course.id).delete()
        for competency_id in payload.competency_ids:
            if db.get(Competency, competency_id) is None:
                raise HTTPException(422, f"Unknown competency {competency_id}")
            db.add(CourseCompetency(course_id=course.id, competency_id=competency_id, covers_level=3))
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="course.updated", resource_type="course", resource_id=str(course.id))
    db.commit()
    db.refresh(course)
    return _course_out(db, course)


@router.delete("/courses/{course_id}", status_code=204, response_model=None)
def delete_course(
    course_id: uuid.UUID, db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> None:
    """Archive when learners are enrolled (history must survive), hard delete otherwise.

    The response reports which happened via the audit log; callers see 204 either way.
    """
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(404, "Course not found")

    enrolment_count = db.scalar(
        select(func.count(Enrolment.id)).where(Enrolment.course_id == course.id)
    ) or 0

    if enrolment_count:
        course.is_archived = True
        audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                     action="course.archived", resource_type="course", resource_id=str(course.id),
                     detail=f"{enrolment_count} enrolments preserved")
    else:
        db.delete(course)
        audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                     action="course.deleted", resource_type="course", resource_id=str(course.id))
    db.commit()


# ---------------------------------------------------------------- enrolment
@router.post("/courses/{course_id}/enrol", response_model=EnrolmentOut, status_code=201)
def enrol(
    course_id: uuid.UUID, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.LEARNER, Role.MANAGER, Role.ASSESSOR, Role.ADMIN)),
) -> EnrolmentOut:
    course = db.get(Course, course_id)
    if course is None or course.is_archived:
        raise HTTPException(404, "Course not found")
    existing = db.scalars(
        select(Enrolment).where(
            Enrolment.user_id == principal.id, Enrolment.course_id == course_id
        )
    ).first()
    if existing:
        return _enrolment_out(db, existing)

    enrolment = Enrolment(user_id=principal.id, course_id=course_id)
    db.add(enrolment)
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="course.enrolled", resource_type="course", resource_id=str(course_id))
    db.commit()
    db.refresh(enrolment)
    return _enrolment_out(db, enrolment)


@router.get("/me/enrolments", response_model=list[EnrolmentOut])
def my_enrolments(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.LEARNER, Role.MANAGER, Role.ASSESSOR, Role.ADMIN)),
) -> list[EnrolmentOut]:
    rows = db.scalars(
        select(Enrolment).where(Enrolment.user_id == principal.id).order_by(
            Enrolment.started_at.desc())
    ).all()
    return [_enrolment_out(db, row) for row in rows]


@router.post("/courses/{course_id}/progress", response_model=EnrolmentOut)
def update_progress(
    course_id: uuid.UUID, payload: ProgressRequest, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.LEARNER, Role.MANAGER, Role.ASSESSOR, Role.ADMIN)),
) -> EnrolmentOut:
    enrolment = db.scalars(
        select(Enrolment).where(
            Enrolment.user_id == principal.id, Enrolment.course_id == course_id
        )
    ).first()
    if enrolment is None:
        raise HTTPException(404, "You are not enrolled in this course")

    material = db.get(CourseMaterial, payload.material_id)
    if material is None or material.course_id != course_id:
        raise HTTPException(422, "That material does not belong to this course")

    completed = set(enrolment.completed_material_ids or [])
    key = str(material.id)
    if payload.completed:
        completed.add(key)
    else:
        completed.discard(key)

    total = db.scalar(
        select(func.count(CourseMaterial.id)).where(CourseMaterial.course_id == course_id)
    ) or 1
    progress = int(round(100 * len(completed) / total))
    enrolment.completed_material_ids = sorted(completed)
    enrolment.progress_percent = min(progress, 100)
    if enrolment.progress_percent >= 100 and enrolment.status != EnrolmentStatus.COMPLETED:
        enrolment.status = EnrolmentStatus.COMPLETED
        enrolment.completed_at = dt.datetime.now(dt.timezone.utc)
        audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                     action="course.completed", resource_type="course", resource_id=str(course_id))
    elif enrolment.progress_percent < 100:
        enrolment.status = EnrolmentStatus.ENROLLED
        enrolment.completed_at = None
    db.commit()
    db.refresh(enrolment)
    return _enrolment_out(db, enrolment)


# ---------------------------------------------------------------- recommendations
@router.get("/me/recommendations", response_model=list[RecommendationOut])
def my_recommendations(
    db: Session = Depends(get_db), limit: int = Query(default=10, ge=1, le=30),
    principal: Principal = Depends(require_roles(Role.LEARNER, Role.MANAGER, Role.ASSESSOR, Role.ADMIN)),
) -> list[RecommendationOut]:
    recs = recommend.recommend_all(db, principal.user, limit=limit)
    return [
        RecommendationOut(
            kind=r.kind, ref_id=r.ref_id, title=r.title, subtitle=r.subtitle, score=r.score,
            reasons=r.reasons, competency_code=r.competency_code,
            competency_name=r.competency_name, target_level=r.target_level,
            current_level=r.current_level, duration_minutes=r.duration_minutes,
            provider=r.provider, evidence_status=r.evidence_status,
        )
        for r in recs
    ]


# ---------------------------------------------------------------- learning plan
def _plan_out(db: Session, plan: LearningPlan) -> PlanOut:
    items = sorted(plan.items, key=lambda i: (i.sort_order, i.title))
    comp_ids = {i.competency_id for i in items}
    comps = {
        c.id: c for c in db.scalars(select(Competency).where(Competency.id.in_(comp_ids or [uuid.uuid4()])))
    }
    course_ids = {i.course_id for i in items if i.course_id}
    courses = {
        c.id: c for c in db.scalars(select(Course).where(Course.id.in_(course_ids or [uuid.uuid4()])))
    }
    out = PlanOut.model_validate(plan)
    out.items = []
    for item in items:
        comp = comps.get(item.competency_id)
        course = courses.get(item.course_id) if item.course_id else None
        out.items.append(
            PlanItemOut(
                id=item.id, competency_id=item.competency_id,
                competency_code=comp.code if comp else None,
                competency_name=comp.name if comp else None,
                course_id=item.course_id, course_title=course.title if course else None,
                activity_type=item.activity_type, title=item.title, detail=item.detail,
                target_level=item.target_level, estimated_minutes=item.estimated_minutes,
                priority=item.priority, sort_order=item.sort_order, status=item.status,
                completed_at=item.completed_at,
            )
        )
    out.total_minutes = sum(i.estimated_minutes for i in items)
    out.completed_items = sum(1 for i in items if i.status == "completed")
    return out


@router.get("/me/plan", response_model=PlanOut)
def my_plan(
    db: Session = Depends(get_db), regenerate: bool = False,
    principal: Principal = Depends(require_roles(Role.LEARNER, Role.MANAGER, Role.ASSESSOR, Role.ADMIN)),
) -> PlanOut:
    plan = recommend.ensure_plan(db, principal.user, force=regenerate)
    db.commit()
    db.refresh(plan)
    return _plan_out(db, plan)


@router.patch("/me/plan/items/{item_id}", response_model=PlanOut)
def update_plan_item(
    item_id: uuid.UUID, payload: PlanItemUpdateRequest, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.LEARNER, Role.MANAGER, Role.ASSESSOR, Role.ADMIN)),
) -> PlanOut:
    item = db.get(PlanItem, item_id)
    if item is None:
        raise HTTPException(404, "Plan item not found")
    plan = db.get(LearningPlan, item.plan_id)
    if plan is None or plan.user_id != principal.id:
        # IDOR guard: the item must belong to a plan owned by the caller.
        raise HTTPException(403, "This plan item does not belong to you")

    item.status = payload.status
    item.completed_at = (
        dt.datetime.now(dt.timezone.utc) if payload.status == "completed" else None
    )
    db.commit()
    db.refresh(plan)
    return _plan_out(db, plan)
