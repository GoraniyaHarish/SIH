"""Authentication: login, refresh rotation, logout, registration, profile."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import client_ip, get_current_user, get_principal, Principal, rate_limit
from app.core.security import (
    create_access_token, hash_ip, hash_password, new_refresh_token, password_needs_rehash,
    sha256_hex, validate_password_strength, verify_password,
)
from app.models.base import Role
from app.models.users import LoginAttempt, RefreshToken, User
from app.schemas import (
    LoginRequest, PasswordChangeRequest, ProfileUpdateRequest, RegisterRequest, TokenResponse,
    UserOut,
)
from app.services import audit

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "pramana_refresh"
ACCESS_COOKIE = "pramana_access"

GENERIC_LOGIN_ERROR = "Email or password is incorrect"


def _user_out(db: Session, user: User) -> UserOut:
    out = UserOut.model_validate(user)
    out.department_name = user.department.name if user.department else None
    out.job_role_title = user.job_role.title if user.job_role else None
    return out


def _set_cookies(response: Response, access: str, refresh: str) -> None:
    max_age = settings.access_token_minutes * 60
    response.set_cookie(
        ACCESS_COOKIE, access, max_age=max_age, httponly=True, samesite="strict",
        secure=settings.cookie_secure, path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE, refresh, max_age=settings.refresh_token_days * 86400, httponly=True,
        samesite="strict", secure=settings.cookie_secure, path="/api/auth",
    )


def _issue_tokens(db: Session, user: User, request: Request) -> tuple[str, str, int]:
    access, expires_in = create_access_token(user.id, user.role, user.token_version)
    raw, digest = new_refresh_token()
    family = uuid.uuid4()
    db.add(
        RefreshToken(
            user_id=user.id, token_hash=digest, family_id=family,
            expires_at=dt.datetime.now(dt.timezone.utc)
            + dt.timedelta(days=settings.refresh_token_days),
            user_agent=(request.headers.get("user-agent") or "")[:255],
            ip_hash=hash_ip(client_ip(request)),
        )
    )
    return access, raw, expires_in


@router.post("/login", response_model=TokenResponse,
             dependencies=[Depends(rate_limit("login", 20, 300))])
def login(
    payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)
) -> TokenResponse:
    email = payload.email.lower().strip()
    ip = hash_ip(client_ip(request))
    now = dt.datetime.now(dt.timezone.utc)

    user = db.scalars(select(User).where(User.email == email)).first()

    # Per-account lockout, independent of IP so a distributed attempt cannot bypass it.
    if user and user.locked_until and user.locked_until > now:
        db.add(LoginAttempt(email=email, ip_hash=ip, success=False, reason="locked"))
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked after repeated failed attempts. Try again later.",
        )

    ok = bool(user) and verify_password(payload.password, user.password_hash)
    if not ok or user is None:
        if user:
            user.failed_attempts += 1
            if user.failed_attempts >= settings.lockout_threshold:
                user.locked_until = now + dt.timedelta(seconds=settings.lockout_seconds)
                user.failed_attempts = 0
        db.add(LoginAttempt(email=email, ip_hash=ip, success=False, reason="bad_credentials"))
        db.commit()
        # Constant response shape: never reveal whether the email exists.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_LOGIN_ERROR)

    if not user.is_active:
        db.add(LoginAttempt(email=email, ip_hash=ip, success=False, reason="inactive"))
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="This account has been deactivated")

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)

    user.failed_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    access, refresh, expires_in = _issue_tokens(db, user, request)
    db.add(LoginAttempt(email=email, ip_hash=ip, success=True, reason=None))
    audit.record(db, actor_id=user.id, actor_role=user.role, action="auth.login",
                 resource_type="user", resource_id=str(user.id), ip_hash=ip)
    db.commit()
    db.refresh(user)

    _set_cookies(response, access, refresh)
    return TokenResponse(access_token=access, expires_in=expires_in, user=_user_out(db, user))


@router.post("/refresh", response_model=TokenResponse,
             dependencies=[Depends(rate_limit("refresh", 60, 300))])
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(401, "No refresh token")
    digest = sha256_hex(raw)
    token = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == digest)).first()
    now = dt.datetime.now(dt.timezone.utc)

    if token is None:
        raise HTTPException(401, "Invalid refresh token")

    if token.revoked_at is not None:
        # Reuse of a rotated token: assume theft and revoke the whole family.
        for sibling in db.scalars(
            select(RefreshToken).where(RefreshToken.family_id == token.family_id)
        ):
            sibling.revoked_at = sibling.revoked_at or now
        db.commit()
        raise HTTPException(401, "Refresh token reuse detected; please sign in again")

    if token.expires_at <= now:
        raise HTTPException(401, "Refresh token expired")

    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise HTTPException(401, "Account unavailable")

    access, expires_in = create_access_token(user.id, user.role, user.token_version)
    new_raw, new_digest = new_refresh_token()
    replacement = RefreshToken(
        user_id=user.id, token_hash=new_digest, family_id=token.family_id, parent_id=token.id,
        expires_at=now + dt.timedelta(days=settings.refresh_token_days),
        user_agent=(request.headers.get("user-agent") or "")[:255],
        ip_hash=hash_ip(client_ip(request)),
    )
    db.add(replacement)
    db.flush()
    token.revoked_at = now
    token.replaced_by = replacement.id
    db.commit()

    _set_cookies(response, access, new_raw)
    return TokenResponse(access_token=access, expires_in=expires_in, user=_user_out(db, user))


@router.post("/logout", status_code=204, response_model=None)
def logout(
    request: Request, response: Response, db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> Response:
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        digest = sha256_hex(raw)
        token = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == digest)).first()
        if token:
            for sibling in db.scalars(
                select(RefreshToken).where(RefreshToken.family_id == token.family_id)
            ):
                sibling.revoked_at = sibling.revoked_at or dt.datetime.now(dt.timezone.utc)
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="auth.logout", resource_type="user", resource_id=str(principal.id))
    db.commit()
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")
    response.status_code = 204
    return response


@router.get("/me", response_model=UserOut)
def me(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(db, user)


@router.post("/register", response_model=UserOut, status_code=201,
             dependencies=[Depends(rate_limit("register", 10, 3600))])
def register(
    payload: RegisterRequest, request: Request, db: Session = Depends(get_db)
) -> UserOut:
    """Self-service registration always creates a LEARNER. Elevated roles are granted only by an
    administrator through /admin/users, so role escalation is impossible from this endpoint."""
    email = payload.email.lower().strip()
    if db.scalars(select(User).where(User.email == email)).first():
        raise HTTPException(409, "An account with this email already exists")

    problems = validate_password_strength(payload.password)
    if problems:
        raise HTTPException(422, "Password must contain " + ", ".join(problems))

    user = User(
        email=email, full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password), role=Role.LEARNER,
        department_id=payload.department_id, job_role_id=payload.job_role_id,
        designation=payload.designation,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    audit.record(db, actor_id=user.id, actor_role=Role.LEARNER.value, action="auth.register",
                 resource_type="user", resource_id=str(user.id),
                 ip_hash=hash_ip(client_ip(request)))
    db.commit()
    return _user_out(db, user)


@router.patch("/me", response_model=UserOut)
def update_profile(
    payload: ProfileUpdateRequest, db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserOut:
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.designation is not None:
        user.designation = payload.designation.strip() or None
    if payload.job_role_id is not None:
        from app.models.competency import JobRole

        if db.get(JobRole, payload.job_role_id) is None:
            raise HTTPException(422, "Unknown job role")
        user.job_role_id = payload.job_role_id
    db.commit()
    db.refresh(user)
    return _user_out(db, user)


@router.post("/change-password", status_code=204, response_model=None)
def change_password(
    payload: PasswordChangeRequest, response: Response, db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    problems = validate_password_strength(payload.new_password)
    if problems:
        raise HTTPException(422, "Password must contain " + ", ".join(problems))
    if payload.new_password == payload.current_password:
        raise HTTPException(422, "New password must differ from the current password")

    user.password_hash = hash_password(payload.new_password)
    user.token_version += 1  # revoke every existing session
    user.must_change_password = False
    for token in db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id)):
        token.revoked_at = token.revoked_at or dt.datetime.now(dt.timezone.utc)
    audit.record(db, actor_id=user.id, actor_role=user.role, action="auth.password_changed",
                 resource_type="user", resource_id=str(user.id))
    db.commit()
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")
    response.status_code = 204
    return response
