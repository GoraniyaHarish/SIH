"""Password hashing, JWT issuance/verification, token digests and rate limiting."""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import secrets
import threading
import time
import uuid
from collections import defaultdict, deque

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import settings

# Argon2id is the default type in argon2-cffi.
_hasher = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2, hash_len=32, salt_len=16)

MIN_PASSWORD_LENGTH = settings.password_min_length


def hash_password(raw: str) -> str:
    return _hasher.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, raw)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False


def password_needs_rehash(hashed: str) -> bool:
    try:
        return _hasher.check_needs_rehash(hashed)
    except (InvalidHashError, ValueError):
        return True


def validate_password_strength(raw: str) -> list[str]:
    problems: list[str] = []
    if len(raw) < MIN_PASSWORD_LENGTH:
        problems.append(f"at least {MIN_PASSWORD_LENGTH} characters")
    if not any(c.islower() for c in raw):
        problems.append("a lowercase letter")
    if not any(c.isupper() for c in raw):
        problems.append("an uppercase letter")
    if not any(c.isdigit() for c in raw):
        problems.append("a digit")
    return problems


# ---------------------------------------------------------------- tokens
def _encode(payload: dict, expires: dt.timedelta, kind: str) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    body = {
        **payload,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + expires).timestamp()),
        "iss": settings.jwt_issuer,
        "typ": kind,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(body, settings.jwt_secret, algorithm="HS256")


def create_access_token(user_id: uuid.UUID, role: str, token_version: int) -> tuple[str, int]:
    ttl = dt.timedelta(minutes=settings.access_token_minutes)
    token = _encode(
        {"sub": str(user_id), "role": role, "tv": token_version}, ttl, "access"
    )
    return token, int(ttl.total_seconds())


def decode_token(token: str, expected_kind: str = "access") -> dict:
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        issuer=settings.jwt_issuer,
        options={"require": ["exp", "iat", "sub", "typ"]},
    )
    if payload.get("typ") != expected_kind:
        raise jwt.InvalidTokenError("unexpected token type")
    return payload


def new_refresh_token() -> tuple[str, str]:
    """Returns (raw token, sha256 digest). Only the digest is persisted."""
    raw = secrets.token_urlsafe(48)
    return raw, hashlib.sha256(raw.encode()).digest().hex()


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def hash_ip(ip: str | None) -> str | None:
    """Pseudonymise client IPs: we keep abuse signals without storing raw addresses."""
    if not ip:
        return None
    return hmac.new(settings.jwt_secret.encode(), ip.encode(), hashlib.sha256).hexdigest()[:32]


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


# ---------------------------------------------------------------- rate limiting
class SlidingWindowLimiter:
    """In-process fallback limiter. Redis is used when reachable (see services/ratelimit)."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = int(window_seconds - (now - bucket[0])) + 1
                return False, max(retry_after, 1)
            bucket.append(now)
            if len(self._hits) > 5000:  # bound memory in long-lived processes
                for k in [k for k, v in self._hits.items() if not v]:
                    self._hits.pop(k, None)
            return True, 0


limiter = SlidingWindowLimiter()
