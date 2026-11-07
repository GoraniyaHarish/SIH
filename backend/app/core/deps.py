"""FastAPI dependencies: authentication, RBAC, rate limiting, pagination.

Every authorisation decision happens here or in the service layer — never in the frontend.
"""
from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.security import decode_token, hash_ip, limiter
from app.models.base import Role
from app.models.users import User

bearer = HTTPBearer(auto_error=False)

ROLE_RANK = {Role.LEARNER: 1, Role.MANAGER: 2, Role.ASSESSOR: 3, Role.ADMIN: 4}


@dataclass(frozen=True)
class Principal:
    user: User
    role: Role

    @property
    def id(self) -> uuid.UUID:
        return self.user.id

    def has_role(self, *roles: Role) -> bool:
        return self.role in roles


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    token = creds.credentials if creds else request.cookies.get("pramana_access")
    if not token:
        raise _unauthorized()
    try:
        payload = decode_token(token, "access")
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Session expired") from None
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid session") from None

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise _unauthorized("Invalid session") from None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("Account unavailable")
    # Token revocation: bumping token_version invalidates all outstanding access tokens.
    if payload.get("tv") != user.token_version:
        raise _unauthorized("Session revoked")
    return user


def get_principal(user: User = Depends(get_current_user)) -> Principal:
    return Principal(user=user, role=Role(user.role))


def require_roles(*roles: Role) -> Callable[[Principal], Principal]:
    allowed = set(roles)

    def _dep(principal: Principal = Depends(get_principal)) -> Principal:
        if principal.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return principal

    return _dep


require_admin = require_roles(Role.ADMIN)
require_staff = require_roles(Role.ADMIN, Role.MANAGER, Role.ASSESSOR)


def require_manager_scope(principal: Principal = Depends(get_principal)) -> Principal:
    """Managers, assessors and admins may view aggregates; learners may not."""
    if ROLE_RANK[principal.role] < ROLE_RANK[Role.MANAGER]:
        raise HTTPException(403, "Aggregate analytics requires a manager, assessor or admin role")
    return principal


def rate_limit(bucket: str, limit: int, window_seconds: int) -> Callable[[Request], None]:
    def _dep(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        key = f"{bucket}:{hash_ip(ip)}"
        allowed, retry_after = limiter.hit(key, limit, window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down.",
                headers={"Retry-After": str(retry_after)},
            )

    return _dep


@dataclass
class Page:
    limit: int
    offset: int


def pagination(limit: int = 20, offset: int = 0) -> Page:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    return Page(limit=limit, offset=offset)


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def ensure_env_sane() -> list[str]:
    """Non-fatal startup warnings surfaced in /api/health/config."""
    warnings: list[str] = []
    if settings.is_production and settings.cookie_secure is False:
        warnings.append("cookie_secure is disabled in a production environment")
    if settings.is_production and "*" in settings.origins:
        warnings.append("wildcard CORS origin in production")
    if not settings.ai_configured:
        warnings.append("AI provider not configured — grounded assistant runs in extractive mode")
    return warnings


__all__ = [
    "Principal", "Page", "get_current_user", "get_principal", "require_roles", "require_admin",
    "require_staff", "require_manager_scope", "rate_limit", "pagination", "client_ip",
    "ensure_env_sane", "select",
]
