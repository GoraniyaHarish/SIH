"""Competency assessment and gap analysis."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Page, Principal, pagination, require_roles
from app.models.assessment import (
    Assessment, AssessmentResponse, CompetencyState,
)
from app.models.base import AssessmentMethod, AssessmentStatus, Role
from app.models.competency import Competency, CompetencyDomain, JobRole
from app.models.users import User
from app.schemas import (
    AssessmentCreateRequest, AssessmentDetailOut, AssessmentOut, AssessmentResponseOut,
    AssessmentReviewRequest, GapAnalysisOut, GapItem,
)
from app.services import audit, gap as gap_service, recommend

router = APIRouter(tags=["assessment"])


def _ensure_can_access_assessment(principal: Principal, assessment: Assessment) -> None:
    """Owner, assessor and admin may read. A manager may read direct reports only."""
    if principal.id == assessment.user_id:
        return
    if principal.role in (Role.ASSESSOR, Role.ADMIN):
        return
    if principal.role == Role.MANAGER:
        return  # checked against the report relationship by the caller
    raise HTTPException(403, "You may not access this assessment")


@router.post("/assessments", response_model=AssessmentDetailOut, status_code=201)
def create_assessment(
    payload: AssessmentCreateRequest, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.LEARNER, Role.MANAGER, Role.ASSESSOR, Role.ADMIN)),
) -> AssessmentDetailOut:
    """Create and submit an assessment in one step: responses + competency state + plan refresh."""
    from app.api.routers.framework import active_framework

    fw = active_framework(db)
    valid_ids = set(db.scalars(select(Competency.id)).all())
    for response in payload.responses:
        if response.competency_id not in valid_ids:
            raise HTTPException(422, f"Unknown competency {response.competency_id}")

    assessment = Assessment(
        user_id=principal.id, framework_version_id=fw.id, method=payload.method,
        status=AssessmentStatus.SUBMITTED, title=payload.title,
        notes=payload.notes, submitted_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(assessment)
    db.flush()

    for response in payload.responses:
        db.add(
            AssessmentResponse(
                assessment_id=assessment.id, competency_id=response.competency_id,
                declared_level=response.declared_level, confidence=response.confidence,
                evidence_note=response.evidence_note,
            )
        )
        existing = db.scalars(
            select(CompetencyState).where(
                CompetencyState.user_id == principal.id,
                CompetencyState.competency_id == response.competency_id,
            )
        ).first()
        if existing is None:
            db.add(
                CompetencyState(
                    user_id=principal.id, competency_id=response.competency_id,
                    level=float(response.declared_level), method=payload.method.value,
                    confidence=response.confidence, source_assessment_id=assessment.id,
                    assessed_at=dt.datetime.now(dt.timezone.utc),
                )
            )
        else:
            existing.level = float(response.declared_level)
            existing.method = payload.method.value
            existing.confidence = response.confidence
            existing.source_assessment_id = assessment.id
            existing.assessed_at = dt.datetime.now(dt.timezone.utc)

    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="assessment.submitted", resource_type="assessment",
                 resource_id=str(assessment.id), detail=f"{len(payload.responses)} competencies")
    db.commit()

    # Recalculate the learning plan from the new evidence.
    recommend.ensure_plan(db, principal.user, force=True)
    db.commit()

    db.refresh(assessment)
    return get_assessment(assessment.id, db, principal)


@router.get("/assessments", response_model=list[AssessmentOut])
def list_assessments(
    db: Session = Depends(get_db), principal: Principal = Depends(require_roles(
        Role.LEARNER, Role.MANAGER, Role.ASSESSOR, Role.ADMIN)),
    page: Page = Depends(pagination), user_id: uuid.UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[AssessmentOut]:
    target = user_id or principal.id
    if target != principal.id:
        if principal.role not in (Role.ASSESSOR, Role.ADMIN, Role.MANAGER):
            raise HTTPException(403, "You may not list another user's assessments")
        if principal.role == Role.MANAGER:
            report = db.get(User, target)
            if report is None or report.manager_id != principal.id:
                raise HTTPException(403, "You may only view assessments of your direct reports")

    stmt = select(Assessment).where(Assessment.user_id == target)
    if status_filter:
        stmt = stmt.where(Assessment.status == status_filter)
    stmt = stmt.order_by(Assessment.created_at.desc()).limit(page.limit).offset(page.offset)
    rows = db.scalars(stmt).all()
    counts = dict(
        db.execute(
            select(AssessmentResponse.assessment_id, func.count(AssessmentResponse.id))
            .where(AssessmentResponse.assessment_id.in_([r.id for r in rows] or [uuid.uuid4()]))
            .group_by(AssessmentResponse.assessment_id)
        ).all()
    )
    out = []
    for row in rows:
        item = AssessmentOut.model_validate(row)
        item.response_count = int(counts.get(row.id, 0))
        out.append(item)
    return out


@router.get("/assessments/{assessment_id}", response_model=AssessmentDetailOut)
def get_assessment(
    assessment_id: uuid.UUID, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(
        Role.LEARNER, Role.MANAGER, Role.ASSESSOR, Role.ADMIN)),
) -> AssessmentDetailOut:
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        raise HTTPException(404, "Assessment not found")
    _ensure_can_access_assessment(principal, assessment)
    if principal.role == Role.MANAGER and principal.id != assessment.user_id:
        subject = db.get(User, assessment.user_id)
        if subject is None or subject.manager_id != principal.id:
            raise HTTPException(403, "You may only view assessments of your direct reports")

    rows = db.execute(
        select(AssessmentResponse, Competency)
        .join(Competency, Competency.id == AssessmentResponse.competency_id)
        .where(AssessmentResponse.assessment_id == assessment.id)
        .order_by(Competency.code)
    ).all()
    out = AssessmentDetailOut.model_validate(assessment)
    out.response_count = len(rows)
    out.responses = [
        AssessmentResponseOut(
            competency_id=comp.id, competency_code=comp.code, competency_name=comp.name,
            declared_level=resp.declared_level, confidence=resp.confidence,
            evidence_note=resp.evidence_note, reviewer_level=resp.reviewer_level,
            reviewer_comment=resp.reviewer_comment,
        )
        for resp, comp in rows
    ]
    return out


@router.post("/assessments/{assessment_id}/review", response_model=AssessmentDetailOut)
def review_assessment(
    assessment_id: uuid.UUID, payload: AssessmentReviewRequest, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.ASSESSOR, Role.ADMIN)),
) -> AssessmentDetailOut:
    """Assessor review sets a verified level. This is the only path that raises confidence to a
    reviewed method; the learner's declared level is preserved for transparency."""
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        raise HTTPException(404, "Assessment not found")
    if assessment.user_id == principal.id:
        raise HTTPException(400, "You cannot review your own assessment")
    if assessment.status == AssessmentStatus.REVIEWED:
        raise HTTPException(409, "This assessment has already been reviewed")

    by_competency = {r.competency_id: r for r in assessment.responses}
    for item in payload.responses:
        response = by_competency.get(item.competency_id)
        if response is None:
            raise HTTPException(422, f"Competency {item.competency_id} is not part of this assessment")
        response.reviewer_level = item.declared_level
        response.reviewer_comment = item.evidence_note

        state = db.scalars(
            select(CompetencyState).where(
                CompetencyState.user_id == assessment.user_id,
                CompetencyState.competency_id == item.competency_id,
            )
        ).first()
        if state is not None:
            state.level = float(item.declared_level)
            state.method = AssessmentMethod.ASSESSOR_REVIEWED.value
            state.confidence = max(item.confidence, 4)
            state.assessed_at = dt.datetime.now(dt.timezone.utc)

    assessment.status = AssessmentStatus.REVIEWED
    assessment.reviewed_at = dt.datetime.now(dt.timezone.utc)
    assessment.reviewer_id = principal.id
    assessment.reviewer_comment = payload.responses[0].evidence_note if payload.responses else None
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="assessment.reviewed", resource_type="assessment",
                 resource_id=str(assessment.id), detail=f"{len(payload.responses)} competencies")
    db.commit()

    subject = db.get(User, assessment.user_id)
    if subject:
        recommend.ensure_plan(db, subject, force=True)
        db.commit()
    return get_assessment(assessment.id, db, principal)


@router.get("/assessments/pending-review", response_model=list[AssessmentOut])
def pending_review(
    db: Session = Depends(get_db), principal: Principal = Depends(require_roles(Role.ASSESSOR, Role.ADMIN)),
    page: Page = Depends(pagination),
) -> list[AssessmentOut]:
    rows = db.scalars(
        select(Assessment)
        .where(Assessment.status == AssessmentStatus.SUBMITTED, Assessment.user_id != principal.id)
        .order_by(Assessment.submitted_at)
        .limit(page.limit).offset(page.offset)
    ).all()
    out = []
    for row in rows:
        item = AssessmentOut.model_validate(row)
        item.response_count = len(row.responses)
        out.append(item)
    return out


# ---------------------------------------------------------------- competency profile + gaps
@router.get("/me/competency-profile", response_model=list[dict])
def my_profile(db: Session = Depends(get_db), principal: Principal = Depends(require_roles(
    Role.LEARNER, Role.MANAGER, Role.ASSESSOR, Role.ADMIN))) -> list[dict]:
    rows = db.execute(
        select(CompetencyState, Competency, CompetencyDomain)
        .join(Competency, Competency.id == CompetencyState.competency_id)
        .join(CompetencyDomain, CompetencyDomain.id == Competency.domain_id)
        .where(CompetencyState.user_id == principal.id)
        .order_by(CompetencyDomain.sort_order, Competency.code)
    ).all()
    return [
        {
            "competency_id": str(comp.id),
            "competency_code": comp.code,
            "competency_name": comp.name,
            "domain_code": domain.code,
            "domain_name": domain.name,
            "level": state.level,
            "method": state.method,
            "confidence": state.confidence,
            "assessed_at": state.assessed_at,
            "quiz_evidence": state.quiz_evidence,
            "is_verified": state.method == AssessmentMethod.ASSESSOR_REVIEWED.value,
        }
        for state, comp, domain in rows
    ]


@router.get("/me/gaps", response_model=GapAnalysisOut)
def my_gaps(
    db: Session = Depends(get_db), principal: Principal = Depends(require_roles(
        Role.LEARNER, Role.MANAGER, Role.ASSESSOR, Role.ADMIN)),
    job_role_id: uuid.UUID | None = None,
) -> GapAnalysisOut:
    data = gap_service.compute(db, principal.user, job_role_id=job_role_id)
    if data["job_role_id"] is None:
        return GapAnalysisOut(
            user_id=principal.id, job_role_id=None, job_role_title=None,
            framework_label="", method_note=gap_service.METHOD_NOTE,
            computed_at=dt.datetime.now(dt.timezone.utc), total_required=0, met_count=0,
            gap_count=0, critical_gap_count=0, overall_readiness_percent=0.0, items=[],
            missing_assessment=data["missing_assessment"],
        )
    return GapAnalysisOut(
        user_id=principal.id,
        job_role_id=data["job_role_id"],
        job_role_title=data["job_role_title"],
        framework_label=data["framework_label"],
        method_note=gap_service.METHOD_NOTE,
        computed_at=data["computed_at"],
        total_required=data["total_required"],
        met_count=data["met_count"],
        gap_count=data["gap_count"],
        critical_gap_count=data["critical_gap_count"],
        overall_readiness_percent=data["overall_readiness_percent"],
        items=[
            GapItem(
                competency_id=row.competency_id, competency_code=row.code,
                competency_name=row.name, domain_name=row.domain_name,
                domain_code=row.domain_code, current_level=row.current_level,
                current_level_source=row.current_source, target_level=row.target_level,
                deficit=row.deficit, severity=row.severity, importance=row.importance,
                is_critical=row.is_critical, priority_score=row.priority_score,
                priority_band=row.priority_band, explanation=row.explanation,
                prerequisite_blocked=row.prerequisite_blocked,
                evidence_status=row.evidence_status,
            )
            for row in data["items"]
        ],
        missing_assessment=data["missing_assessment"],
    )


@router.get("/users/{user_id}/gaps", response_model=GapAnalysisOut)
def user_gaps(
    user_id: uuid.UUID, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.ASSESSOR, Role.ADMIN, Role.MANAGER)),
) -> GapAnalysisOut:
    """Same analysis for another user, restricted to assessor/admin or the person's manager."""
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "User not found")
    if principal.role == Role.MANAGER and target.manager_id != principal.id:
        raise HTTPException(403, "You may only view competency gaps for your direct reports")

    data = gap_service.compute(db, target)
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="competency.gap_viewed", resource_type="user", resource_id=str(user_id))
    db.commit()
    return GapAnalysisOut(
        user_id=target.id,
        job_role_id=data["job_role_id"],
        job_role_title=data["job_role_title"],
        framework_label=data["framework_label"],
        method_note=gap_service.METHOD_NOTE,
        computed_at=data["computed_at"],
        total_required=data["total_required"], met_count=data["met_count"],
        gap_count=data["gap_count"], critical_gap_count=data["critical_gap_count"],
        overall_readiness_percent=data["overall_readiness_percent"],
        items=[
            GapItem(
                competency_id=row.competency_id, competency_code=row.code,
                competency_name=row.name, domain_name=row.domain_name,
                domain_code=row.domain_code, current_level=row.current_level,
                current_level_source=row.current_source, target_level=row.target_level,
                deficit=row.deficit, severity=row.severity, importance=row.importance,
                is_critical=row.is_critical, priority_score=row.priority_score,
                priority_band=row.priority_band, explanation=row.explanation,
                prerequisite_blocked=row.prerequisite_blocked,
                evidence_status=row.evidence_status,
            )
            for row in data["items"]
        ],
        missing_assessment=data["missing_assessment"],
    )
