"""Competency framework: domains, competencies, levels, job roles, prerequisites."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Page, Principal, pagination, require_admin, require_roles
from app.models.base import EvidenceStatus, ReviewStatus, Role
from app.models.competency import (
    Competency, CompetencyDomain, CompetencyPrerequisite, FrameworkVersion, JobRole,
    ProficiencyLevel, RoleCompetencyRequirement, Skill,
)
from app.models.users import User
from app.schemas import (
    CompetencyCreateRequest, CompetencyOut, CompetencyUpdateRequest, DomainCreateRequest,
    DomainOut, FrameworkOut, JobRoleCreateRequest, JobRoleOut, LevelOut, PrerequisiteIn,
    RoleRequirementOut, SkillOut,
)
from app.services import audit

router = APIRouter(tags=["framework"])


def active_framework(db: Session) -> FrameworkVersion:
    fw = db.scalars(
        select(FrameworkVersion).where(FrameworkVersion.is_active.is_(True))
    ).first()
    if fw is None:
        raise HTTPException(503, "No active competency framework is configured")
    return fw


def _job_role_base(role: JobRole) -> JobRoleOut:
    """Serialise only the flat columns of a job role.

    `JobRoleOut.model_validate(role)` cannot be used directly: the ORM `requirements`
    relationship would be coerced into `RoleRequirementOut`, which needs joined
    competency_code / competency_name / domain_name values that the ORM object does not carry.
    Callers attach the joined requirements themselves.
    """
    return JobRoleOut(
        id=role.id,
        code=role.code,
        title=role.title,
        description=role.description,
        cadre=role.cadre,
        grade=role.grade,
        evidence_status=role.evidence_status,
        review_status=role.review_status,
        requirement_count=0,
        requirements=[],
    )


# ---------------------------------------------------------------- read (any authenticated user)
@router.get("/framework", response_model=FrameworkOut)
def get_framework(db: Session = Depends(get_db)) -> FrameworkOut:
    return FrameworkOut.model_validate(active_framework(db))


@router.get("/framework/levels", response_model=list[LevelOut])
def get_levels(db: Session = Depends(get_db)) -> list[LevelOut]:
    fw = active_framework(db)
    rows = db.scalars(
        select(ProficiencyLevel)
        .where(ProficiencyLevel.framework_version_id == fw.id)
        .order_by(ProficiencyLevel.level)
    ).all()
    return [LevelOut.model_validate(r) for r in rows]


@router.get("/framework/domains", response_model=list[DomainOut])
def get_domains(db: Session = Depends(get_db)) -> list[DomainOut]:
    fw = active_framework(db)
    counts = dict(
        db.execute(
            select(Competency.domain_id, func.count(Competency.id))
            .join(CompetencyDomain, CompetencyDomain.id == Competency.domain_id)
            .where(CompetencyDomain.framework_version_id == fw.id)
            .group_by(Competency.domain_id)
        ).all()
    )
    rows = db.scalars(
        select(CompetencyDomain)
        .where(CompetencyDomain.framework_version_id == fw.id)
        .order_by(CompetencyDomain.sort_order, CompetencyDomain.code)
    ).all()
    out = []
    for d in rows:
        item = DomainOut.model_validate(d)
        item.competency_count = int(counts.get(d.id, 0))
        out.append(item)
    return out


@router.get("/framework/competencies", response_model=list[CompetencyOut])
def get_competencies(
    db: Session = Depends(get_db), domain_id: uuid.UUID | None = None,
    q: str | None = Query(default=None, max_length=80),
    page: Page = Depends(pagination),
) -> list[CompetencyOut]:
    fw = active_framework(db)
    stmt = (
        select(Competency, CompetencyDomain)
        .join(CompetencyDomain, CompetencyDomain.id == Competency.domain_id)
        .where(CompetencyDomain.framework_version_id == fw.id)
    )
    if domain_id:
        stmt = stmt.where(Competency.domain_id == domain_id)
    if q:
        pattern = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            func.lower(Competency.name).like(pattern) | func.lower(Competency.code).like(pattern)
        )
    stmt = stmt.order_by(CompetencyDomain.sort_order, Competency.sort_order)
    rows = db.execute(stmt).all()

    skills_by_comp: dict[uuid.UUID, list[Skill]] = {}
    for skill in db.scalars(select(Skill).order_by(Skill.sort_order)):
        skills_by_comp.setdefault(skill.competency_id, []).append(skill)

    out = []
    for comp, domain in rows:
        item = CompetencyOut.model_validate(comp)
        item.domain_name = domain.name
        item.domain_code = domain.code
        item.skills = [SkillOut.model_validate(s) for s in skills_by_comp.get(comp.id, [])]
        out.append(item)
    return out


@router.get("/framework/prerequisites", response_model=list[dict])
def get_prerequisites(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(CompetencyPrerequisite, Competency, Competency)
    ).all()
    # Explicit aliasing below avoids ambiguity between the two competency references.
    edges = db.scalars(select(CompetencyPrerequisite)).all()
    codes = {c.id: c.code for c in db.scalars(select(Competency))}
    return [
        {
            "competency_id": str(e.competency_id),
            "competency_code": codes.get(e.competency_id),
            "prerequisite_id": str(e.prerequisite_competency_id),
            "prerequisite_code": codes.get(e.prerequisite_competency_id),
            "min_level": e.min_level,
            "evidence_status": e.evidence_status,
        }
        for e in edges
    ]


@router.get("/framework/job-roles", response_model=list[JobRoleOut])
def get_job_roles(db: Session = Depends(get_db)) -> list[JobRoleOut]:
    fw = active_framework(db)
    roles = db.scalars(
        select(JobRole).where(JobRole.framework_version_id == fw.id).order_by(JobRole.title)
    ).all()
    counts = dict(
        db.execute(
            select(RoleCompetencyRequirement.job_role_id, func.count(RoleCompetencyRequirement.id))
            .group_by(RoleCompetencyRequirement.job_role_id)
        ).all()
    )
    out = []
    for role in roles:
        # requirements is left empty here: RoleRequirementOut needs joined competency fields that
        # do not exist on the ORM relationship, so a direct model_validate would fail.
        item = _job_role_base(role)
        item.requirement_count = int(counts.get(role.id, 0))
        out.append(item)
    return out


@router.get("/framework/job-roles/{role_id}", response_model=JobRoleOut)
def get_job_role(role_id: uuid.UUID, db: Session = Depends(get_db)) -> JobRoleOut:
    role = db.get(JobRole, role_id)
    if role is None:
        raise HTTPException(404, "Job role not found")
    rows = db.execute(
        select(RoleCompetencyRequirement, Competency, CompetencyDomain)
        .join(Competency, Competency.id == RoleCompetencyRequirement.competency_id)
        .join(CompetencyDomain, CompetencyDomain.id == Competency.domain_id)
        .where(RoleCompetencyRequirement.job_role_id == role.id)
        .order_by(RoleCompetencyRequirement.importance.desc(), Competency.code)
    ).all()
    out = _job_role_base(role)
    out.requirements = [
        RoleRequirementOut(
            competency_id=comp.id, competency_code=comp.code, competency_name=comp.name,
            domain_name=domain.name, required_level=req.required_level,
            importance=req.importance, is_critical=req.is_critical,
            rationale=req.rationale, evidence_status=req.evidence_status,
        )
        for req, comp, domain in rows
    ]
    out.requirement_count = len(out.requirements)
    return out


# ---------------------------------------------------------------- write (admin only)
@router.post("/framework/domains", response_model=DomainOut, status_code=201)
def create_domain(
    payload: DomainCreateRequest, db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> DomainOut:
    fw = active_framework(db)
    existing = db.scalars(
        select(CompetencyDomain).where(
            CompetencyDomain.framework_version_id == fw.id, CompetencyDomain.code == payload.code
        )
    ).first()
    if existing:
        raise HTTPException(409, "A domain with this code already exists in the active framework")
    max_order = db.scalar(
        select(func.max(CompetencyDomain.sort_order)).where(
            CompetencyDomain.framework_version_id == fw.id
        )
    ) or 0
    domain = CompetencyDomain(
        framework_version_id=fw.id, code=payload.code.upper(), name=payload.name.strip(),
        description=payload.description, kind=payload.kind,
        evidence_status=payload.evidence_status, source_ref=payload.source_ref,
        sort_order=max_order + 1,
    )
    db.add(domain)
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="framework.domain_created", resource_type="competency_domain",
                 detail=payload.code)
    db.commit()
    db.refresh(domain)
    return DomainOut.model_validate(domain)


@router.post("/framework/competencies", response_model=CompetencyOut, status_code=201)
def create_competency(
    payload: CompetencyCreateRequest, db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> CompetencyOut:
    domain = db.get(CompetencyDomain, payload.domain_id)
    if domain is None:
        raise HTTPException(404, "Domain not found")
    dup = db.scalars(
        select(Competency).where(
            Competency.domain_id == payload.domain_id, Competency.code == payload.code
        )
    ).first()
    if dup:
        raise HTTPException(409, "A competency with this code already exists in the domain")

    max_order = db.scalar(
        select(func.max(Competency.sort_order)).where(Competency.domain_id == payload.domain_id)
    ) or 0
    comp = Competency(
        domain_id=payload.domain_id, code=payload.code.upper(), name=payload.name.strip(),
        description=payload.description, rationale=payload.rationale,
        evidence_status=payload.evidence_status, source_ref=payload.source_ref,
        sort_order=max_order + 1,
    )
    db.add(comp)
    db.flush()
    for index, statement in enumerate(payload.skills):
        db.add(Skill(competency_id=comp.id, statement=statement, sort_order=index))
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="framework.competency_created", resource_type="competency",
                 resource_id=str(comp.id), detail=payload.code)
    db.commit()
    db.refresh(comp)
    out = CompetencyOut.model_validate(comp)
    out.domain_name = domain.name
    out.domain_code = domain.code
    out.skills = [SkillOut.model_validate(s) for s in comp.skills]
    return out


@router.patch("/framework/competencies/{competency_id}", response_model=CompetencyOut)
def update_competency(
    competency_id: uuid.UUID, payload: CompetencyUpdateRequest, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.ADMIN, Role.ASSESSOR)),
) -> CompetencyOut:
    comp = db.get(Competency, competency_id)
    if comp is None:
        raise HTTPException(404, "Competency not found")

    # Assessors may only record a review decision; structural edits stay with admins.
    if principal.role == Role.ASSESSOR:
        if payload.review_status is None:
            raise HTTPException(403, "Assessors may only submit review decisions")
        disallowed = [f for f in ("name", "description", "rationale", "evidence_status", "source_ref")
                      if getattr(payload, f) is not None]
        if disallowed:
            raise HTTPException(403, "Assessors may not edit competency content")

    if payload.review_status is not None:
        comp.review_status = payload.review_status
        comp.reviewed_by_id = principal.id
        audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                     action=f"framework.review_{payload.review_status}",
                     resource_type="competency", resource_id=str(comp.id))
        # Approving a mapping is the only path that may raise it to OFFICIAL.
        if payload.review_status == ReviewStatus.APPROVED.value and \
                comp.evidence_status == EvidenceStatus.PROVISIONAL.value:
            comp.evidence_status = EvidenceStatus.OFFICIAL.value

    for field in ("name", "description", "rationale", "evidence_status", "source_ref"):
        value = getattr(payload, field)
        if value is not None and principal.role == Role.ADMIN:
            setattr(comp, field, value)
    db.commit()
    db.refresh(comp)
    out = CompetencyOut.model_validate(comp)
    out.domain_name = comp.domain.name
    out.domain_code = comp.domain.code
    out.skills = [SkillOut.model_validate(s) for s in comp.skills]
    return out


@router.post("/framework/job-roles", response_model=JobRoleOut, status_code=201)
def create_job_role(
    payload: JobRoleCreateRequest, db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> JobRoleOut:
    fw = active_framework(db)
    if db.scalars(
        select(JobRole).where(JobRole.framework_version_id == fw.id, JobRole.code == payload.code)
    ).first():
        raise HTTPException(409, "A job role with this code already exists")

    role = JobRole(
        framework_version_id=fw.id, code=payload.code.upper(), title=payload.title.strip(),
        description=payload.description, cadre=payload.cadre, grade=payload.grade,
        evidence_status=payload.evidence_status, source_ref=payload.source_ref,
    )
    db.add(role)
    db.flush()
    for requirement in payload.requirements:
        if db.get(Competency, requirement.competency_id) is None:
            raise HTTPException(422, f"Unknown competency {requirement.competency_id}")
        db.add(
            RoleCompetencyRequirement(
                job_role_id=role.id, competency_id=requirement.competency_id,
                required_level=requirement.required_level, importance=requirement.importance,
                is_critical=requirement.is_critical, rationale=requirement.rationale,
                evidence_status=payload.evidence_status,
            )
        )
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="framework.job_role_created", resource_type="job_role",
                 resource_id=str(role.id), detail=payload.code)
    db.commit()
    return get_job_role(role.id, db)


@router.put("/framework/job-roles/{role_id}/requirements", response_model=JobRoleOut)
def replace_requirements(
    role_id: uuid.UUID, payload: list[RoleRequirementOut] | list[dict],
    db: Session = Depends(get_db), principal: Principal = Depends(require_admin),
) -> JobRoleOut:
    from app.schemas import RoleRequirementIn

    role = db.get(JobRole, role_id)
    if role is None:
        raise HTTPException(404, "Job role not found")

    parsed = [
        RoleRequirementIn(**item) if isinstance(item, dict) else item for item in payload
    ]
    db.query(RoleCompetencyRequirement).filter(
        RoleCompetencyRequirement.job_role_id == role.id
    ).delete()
    for requirement in parsed:
        if db.get(Competency, requirement.competency_id) is None:
            raise HTTPException(422, f"Unknown competency {requirement.competency_id}")
        db.add(
            RoleCompetencyRequirement(
                job_role_id=role.id, competency_id=requirement.competency_id,
                required_level=requirement.required_level, importance=requirement.importance,
                is_critical=requirement.is_critical, rationale=requirement.rationale,
                evidence_status=role.evidence_status,
            )
        )
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="framework.requirements_replaced", resource_type="job_role",
                 resource_id=str(role.id), detail=f"{len(parsed)} requirements")
    db.commit()
    return get_job_role(role.id, db)


@router.post("/framework/prerequisites", status_code=201)
def add_prerequisite(
    payload: PrerequisiteIn, db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> dict:
    if payload.competency_id == payload.prerequisite_competency_id:
        raise HTTPException(422, "A competency cannot be its own prerequisite")
    if db.get(Competency, payload.competency_id) is None:
        raise HTTPException(404, "Competency not found")
    if db.get(Competency, payload.prerequisite_competency_id) is None:
        raise HTTPException(404, "Prerequisite competency not found")
    exists = db.scalars(
        select(CompetencyPrerequisite).where(
            CompetencyPrerequisite.competency_id == payload.competency_id,
            CompetencyPrerequisite.prerequisite_competency_id == payload.prerequisite_competency_id,
        )
    ).first()
    if exists:
        raise HTTPException(409, "This prerequisite already exists")
    edge = CompetencyPrerequisite(
        competency_id=payload.competency_id,
        prerequisite_competency_id=payload.prerequisite_competency_id,
        min_level=payload.min_level,
    )
    db.add(edge)
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="framework.prerequisite_added", resource_type="competency",
                 resource_id=str(payload.competency_id))
    db.commit()
    return {"id": str(edge.id)}
