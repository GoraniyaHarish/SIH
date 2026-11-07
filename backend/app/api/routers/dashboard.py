"""Dashboards, notifications, health and AI usage surfaces."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.ai.provider import ai
from app.core.config import settings
from app.core.db import get_db
from app.core.deps import (
    Page, Principal, ensure_env_sane, pagination, require_manager_scope,
    require_roles,
)
from app.integrations.adapters import latest_status
from app.models.assessment import Notification
from app.models.base import Role
from app.schemas import HealthOut, ManagerAnalyticsOut, NotificationOut
from app.services import analytics, recommend

router = APIRouter(tags=["dashboard"])

VERSION = "1.0.0"


@router.get("/health", response_model=HealthOut)
def health(db: Session = Depends(get_db)) -> HealthOut:
    """Unauthenticated liveness/readiness. Reports subsystem truth, never secrets."""
    db_state = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_state = "error"

    redis_state = "not_used"
    try:
        import redis as redis_lib

        client = redis_lib.Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        client.ping()
        redis_state = "ok"
    except Exception:  # noqa: BLE001
        redis_state = "unavailable"

    return HealthOut(
        status="ok" if db_state == "ok" else "degraded",
        version=VERSION,
        database=db_state,
        redis=redis_state,
        ai="configured" if settings.ai_configured else "not_configured",
        integrations=[f"{r['provider']}:{r['status']}" for r in latest_status(db)],
        warnings=ensure_env_sane(),
    )


@router.get("/me/dashboard", response_model=dict)
def learner_dashboard(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.LEARNER, Role.MANAGER, Role.ASSESSOR, Role.ADMIN)),
) -> dict:
    summary = analytics.learner_summary(db, principal.user)
    recs = recommend.recommend_all(db, principal.user, limit=5)
    summary["recommendations"] = [
        {
            "kind": r.kind, "ref_id": str(r.ref_id) if r.ref_id else None, "title": r.title,
            "subtitle": r.subtitle, "score": r.score, "reasons": r.reasons,
            "competency_code": r.competency_code, "competency_name": r.competency_name,
            "duration_minutes": r.duration_minutes, "provider": r.provider,
            "evidence_status": r.evidence_status, "target_level": r.target_level,
            "current_level": r.current_level,
        }
        for r in recs
    ]
    unread = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == principal.id, Notification.read_at.is_(None)
        )
    ) or 0
    summary["unread_notifications"] = int(unread)
    return summary


@router.get("/manager/analytics", response_model=ManagerAnalyticsOut)
def manager_analytics(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_manager_scope),
    department_id=None, job_role_id=None,
) -> ManagerAnalyticsOut:
    from uuid import UUID

    dept = UUID(department_id) if isinstance(department_id, str) and department_id else department_id
    role = UUID(job_role_id) if isinstance(job_role_id, str) and job_role_id else job_role_id
    return ManagerAnalyticsOut(**analytics.manager_analytics(
        db, principal.user, department_id=dept, job_role_id=role
    ))


@router.get("/manager/analytics/export", response_model=dict)
def export_analytics(
    db: Session = Depends(get_db), principal: Principal = Depends(require_manager_scope),
):
    """CSV-ready export of the aggregate view, with suppression applied identically."""
    data = analytics.manager_analytics(db, principal.user)
    rows = [["domain_code", "domain_name", "competency_count", "average_deficit",
             "learners_with_gap"]]
    for row in data["domain_gaps"]:
        rows.append([
            row["domain_code"], row["domain_name"], row["competency_count"],
            "" if row["average_deficit"] is None else row["average_deficit"],
            "" if row["learners_with_gap"] is None else row["learners_with_gap"],
        ])
    csv = "\n".join(",".join(str(c) for c in row) for row in rows)
    return {
        "filename": f"competency-gaps-{dt.date.today().isoformat()}.csv",
        "csv": csv,
        "suppression_threshold": data["suppression_threshold"],
        "suppression_applied": data["suppression_applied"],
    }


@router.get("/me/notifications", response_model=list[NotificationOut])
def notifications(
    db: Session = Depends(get_db), page: Page = Depends(pagination),
    principal: Principal = Depends(require_roles(Role.LEARNER, Role.MANAGER, Role.ASSESSOR, Role.ADMIN)),
) -> list[NotificationOut]:
    rows = db.scalars(
        select(Notification)
        .where(Notification.user_id == principal.id)
        .order_by(Notification.created_at.desc())
        .limit(page.limit).offset(page.offset)
    ).all()
    return [NotificationOut.model_validate(r) for r in rows]


@router.post("/me/notifications/{notification_id}/read", status_code=204, response_model=None)
def mark_read(
    notification_id,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(Role.LEARNER, Role.MANAGER, Role.ASSESSOR, Role.ADMIN)),
) -> None:
    from uuid import UUID

    notif = db.get(Notification, UUID(str(notification_id)))
    if notif is None or notif.user_id != principal.id:
        return  # idempotent and non-disclosing
    notif.read_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
