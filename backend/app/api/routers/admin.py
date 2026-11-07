"""Administration: users, departments, audit log, AI configuration, system health."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.provider import ai
from app.core.config import settings
from app.core.db import get_db
from app.core.deps import (
    Page, Principal, client_ip, pagination, require_admin, require_manager_scope,
)
from app.core.security import hash_ip, hash_password, validate_password_strength
from app.integrations.adapters import latest_status, probe_all
from app.models.assessment import AiUsageLog
from app.models.base import Role
from app.models.users import AuditLog, Department, User
from app.schemas import (
    AdminOverviewOut, AuditEventOut, DepartmentIn, DepartmentOut, IntegrationStatusOut,
    UserCreateRequest, UserOut, UserUpdateRequest,
)
from app.services import analytics, audit

router = APIRouter(tags=["admin"])


def _user_out(db: Session, user: User) -> UserOut:
    out = UserOut.model_validate(user)
    out.department_name = user.department.name if user.department else None
    out.job_role_title = user.job_role.title if user.job_role else None
    return out


# ---------------------------------------------------------------- departments (public list for signup)
@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db)) -> list[DepartmentOut]:
    counts = dict(
        db.execute(
            select(User.department_id, func.count(User.id)).group_by(User.department_id)
        ).all()
    )
    rows = db.scalars(select(Department).order_by(Department.name)).all()
    out = []
    for d in rows:
        item = DepartmentOut.model_validate(d)
        item.user_count = int(counts.get(d.id, 0))
        out.append(item)
    return out


@router.post("/admin/departments", response_model=DepartmentOut, status_code=201)
def create_department(
    payload: DepartmentIn, db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> DepartmentOut:
    if db.scalars(select(Department).where(Department.name == payload.name)).first():
        raise HTTPException(409, "A department with this name already exists")
    dept = Department(name=payload.name.strip(), code=payload.code, description=payload.description)
    db.add(dept)
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="department.create", resource_type="department", detail=payload.name)
    db.commit()
    db.refresh(dept)
    return DepartmentOut.model_validate(dept)


# ---------------------------------------------------------------- users
@router.get("/admin/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db), principal: Principal = Depends(require_admin),
    page: Page = Depends(pagination), q: str | None = Query(default=None, max_length=80),
    role: Role | None = None, department_id: uuid.UUID | None = None,
) -> list[UserOut]:
    stmt = select(User)
    if q:
        pattern = f"%{q.strip().lower()}%"
        stmt = stmt.where(func.lower(User.full_name).like(pattern) | User.email.like(pattern))
    if role:
        stmt = stmt.where(User.role == role)
    if department_id:
        stmt = stmt.where(User.department_id == department_id)
    stmt = stmt.order_by(User.created_at.desc()).limit(page.limit).offset(page.offset)
    return [_user_out(db, u) for u in db.scalars(stmt)]


@router.post("/admin/users", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreateRequest, request: Request, db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> UserOut:
    email = payload.email.lower().strip()
    if db.scalars(select(User).where(User.email == email)).first():
        raise HTTPException(409, "An account with this email already exists")
    problems = validate_password_strength(payload.password)
    if problems:
        raise HTTPException(422, "Password must contain " + ", ".join(problems))

    user = User(
        email=email, full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password), role=payload.role,
        department_id=payload.department_id, job_role_id=payload.job_role_id,
        designation=payload.designation, must_change_password=True,
    )
    db.add(user)
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="user.create", resource_type="user", detail=f"{email} role={payload.role.value}",
                 ip_hash=hash_ip(client_ip(request)))
    db.commit()
    db.refresh(user)
    return _user_out(db, user)


@router.patch("/admin/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: uuid.UUID, payload: UserUpdateRequest, db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> UserOut:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")

    if payload.role is not None and payload.role != user.role:
        if user.id == principal.id:
            raise HTTPException(400, "You cannot change your own role")
        # Never leave the system without an administrator.
        if user.role == Role.ADMIN:
            remaining = db.scalar(
                select(func.count(User.id)).where(
                    User.role == Role.ADMIN, User.is_active.is_(True), User.id != user.id
                )
            )
            if not remaining:
                raise HTTPException(400, "At least one active administrator must remain")
        user.role = payload.role
        user.token_version += 1  # role change invalidates existing sessions
        audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                     action="user.role_changed", resource_type="user", resource_id=str(user.id),
                     detail=f"new role {payload.role.value}")

    if payload.is_active is not None and payload.is_active != user.is_active:
        if user.id == principal.id and not payload.is_active:
            raise HTTPException(400, "You cannot deactivate your own account")
        if user.role == Role.ADMIN and not payload.is_active:
            remaining = db.scalar(
                select(func.count(User.id)).where(
                    User.role == Role.ADMIN, User.is_active.is_(True), User.id != user.id
                )
            )
            if not remaining:
                raise HTTPException(400, "At least one active administrator must remain")
        user.is_active = payload.is_active
        if not payload.is_active:
            user.token_version += 1
        audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                     action="user.activation_changed", resource_type="user", resource_id=str(user.id),
                     detail=f"active={payload.is_active}")

    for field in ("full_name", "designation", "department_id", "job_role_id"):
        value = getattr(payload, field)
        if value is not None:
            setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return _user_out(db, user)


@router.delete("/admin/users/{user_id}", status_code=204, response_model=None)
def deactivate_user(
    user_id: uuid.UUID, db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> None:
    """Deactivation, not deletion: assessment history and audit trail must be preserved."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    if user.id == principal.id:
        raise HTTPException(400, "You cannot deactivate your own account")
    user.is_active = False
    user.token_version += 1
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="user.deactivated", resource_type="user", resource_id=str(user.id))
    db.commit()


# ---------------------------------------------------------------- audit
@router.get("/admin/audit", response_model=list[AuditEventOut])
def audit_log(
    db: Session = Depends(get_db), principal: Principal = Depends(require_admin),
    page: Page = Depends(pagination), action: str | None = Query(default=None, max_length=60),
) -> list[AuditEventOut]:
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(page.limit).offset(page.offset)
    return [AuditEventOut.model_validate(row) for row in db.scalars(stmt)]


# ---------------------------------------------------------------- overview + system
@router.get("/admin/overview", response_model=AdminOverviewOut)
def overview(
    db: Session = Depends(get_db), principal: Principal = Depends(require_admin),
) -> AdminOverviewOut:
    data = analytics.admin_overview(db)
    data["integrations"] = latest_status(db)
    return AdminOverviewOut(**data)


@router.get("/admin/system", response_model=dict)
def system_status(
    db: Session = Depends(get_db), principal: Principal = Depends(require_admin),
) -> dict:
    from app.core.deps import ensure_env_sane

    ok, message = ai.health()
    recent = db.execute(
        select(AiUsageLog.operation, func.count(AiUsageLog.id), func.avg(AiUsageLog.latency_ms))
        .group_by(AiUsageLog.operation)
    ).all()
    return {
        "ai": {
            "configured": settings.ai_configured,
            "reachable": ok,
            "message": message,
            "provider": settings.ai_provider,
            "chat_model": settings.ai_chat_model,
            "embedding_model": settings.ai_embedding_model,
            "embedding_dim": settings.ai_embedding_dim,
            "external_documents_enabled": settings.ai_send_documents_externally,
            "operations": [
                {"operation": op, "calls": int(n), "avg_latency_ms": int(lat or 0)}
                for op, n, lat in recent
            ],
        },
        "security": {
            "warnings": ensure_env_sane(),
            "cors_origins": settings.origins,
            "access_token_minutes": settings.access_token_minutes,
            "refresh_token_days": settings.refresh_token_days,
            "login_max_attempts": settings.login_max_attempts,
            "lockout_threshold": settings.lockout_threshold,
        },
        "storage": {
            "max_upload_mb": settings.max_upload_bytes // (1024 * 1024),
            "allowed_mime": sorted(settings.mime_allowlist),
            "upload_dir": str(settings.upload_dir),
        },
    }


@router.post("/admin/integrations/probe", response_model=list[IntegrationStatusOut])
def probe_integrations(
    db: Session = Depends(get_db), principal: Principal = Depends(require_admin),
) -> list[IntegrationStatusOut]:
    results = probe_all(db, actor_id=principal.id)
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="integration.probe", resource_type="integration",
                 detail=", ".join(f"{r['provider']}={r['status']}" for r in results))
    db.commit()
    return [IntegrationStatusOut(**{**r, "checked_at": None}) for r in results]


@router.get("/admin/integrations", response_model=list[IntegrationStatusOut])
def integration_status(
    db: Session = Depends(get_db), principal: Principal = Depends(require_admin),
) -> list[IntegrationStatusOut]:
    return [IntegrationStatusOut(**r) for r in latest_status(db)]
