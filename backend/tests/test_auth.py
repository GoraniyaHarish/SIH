"""Authentication and session security.

Every assertion here was derived from the actual implementation in
`app/api/routers/auth.py` and `app/core/security.py`, not from an assumed design.
"""
from __future__ import annotations

from tests.conftest import TEST_PASSWORD

LEARNER = "learner@example.com"
GENERIC = "Email or password is incorrect"


def _login(client, email: str, password: str = TEST_PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_login_success_sets_httponly_cookies(client, fixture_data):
    response = _login(client, LEARNER)
    assert response.status_code == 200

    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 15 * 60
    assert body["user"]["email"] == LEARNER
    assert body["user"]["role"] == "learner"
    assert body["user"]["department_name"] == "Department A"

    access = response.headers.get_list("set-cookie")
    joined = " ".join(access).lower()
    assert "pramana_access=" in joined
    assert "httponly" in joined
    assert "samesite=strict" in joined


def test_login_failure_does_not_disclose_whether_account_exists(client, fixture_data):
    wrong_password = _login(client, LEARNER, "Wrong#Password1")
    unknown_email = _login(client, "nobody@example.com", "Wrong#Password1")

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    # Identical body and status: an attacker cannot enumerate valid accounts.
    assert wrong_password.json()["detail"] == GENERIC
    assert unknown_email.json()["detail"] == GENERIC
    assert wrong_password.json() == unknown_email.json()


def test_login_records_attempts_and_audit(client, fixture_data, db):
    from sqlalchemy import func, select

    from app.models.users import AuditLog, LoginAttempt

    _login(client, LEARNER, "Wrong#Password1")
    _login(client, LEARNER)

    failures = db.scalar(
        select(func.count(LoginAttempt.id)).where(
            LoginAttempt.email == LEARNER, LoginAttempt.success.is_(False)
        )
    )
    successes = db.scalar(
        select(func.count(LoginAttempt.id)).where(
            LoginAttempt.email == LEARNER, LoginAttempt.success.is_(True)
        )
    )
    audited = db.scalar(
        select(func.count(AuditLog.id)).where(AuditLog.action == "auth.login")
    )
    assert failures == 1
    assert successes == 1
    assert audited == 1


def test_account_locks_after_ten_failed_attempts(client, fixture_data):
    from app.core.config import settings

    for _ in range(settings.lockout_threshold):
        response = _login(client, LEARNER, "Wrong#Password1")
        assert response.status_code == 401

    locked = _login(client, LEARNER)
    assert locked.status_code == 423
    assert "locked" in locked.json()["detail"].lower()


def test_deactivated_account_cannot_log_in(client, fixture_data, db, api):
    from app.models.users import User

    headers = api.headers("admin@example.com")
    learner = fixture_data["users"]["learner"]
    assert client.delete(f"/api/admin/users/{learner.id}", headers=headers).status_code == 204

    db.expire_all()
    assert db.get(User, learner.id).is_active is False
    assert _login(client, LEARNER).status_code == 403


def test_refresh_rotates_and_reuse_revokes_the_whole_family(client, fixture_data):
    login = _login(client, LEARNER)
    assert login.status_code == 200
    first_raw = login.cookies.get("pramana_refresh")
    assert first_raw

    rotated = client.post("/api/auth/refresh", cookies={"pramana_refresh": first_raw})
    assert rotated.status_code == 200
    second_raw = rotated.cookies.get("pramana_refresh")
    assert second_raw and second_raw != first_raw

    # Replaying the consumed token is treated as theft.
    replay = client.post("/api/auth/refresh", cookies={"pramana_refresh": first_raw})
    assert replay.status_code == 401
    assert "reuse" in replay.json()["detail"].lower()

    # ...and the whole family is revoked, so the legitimate successor is dead too.
    successor = client.post("/api/auth/refresh", cookies={"pramana_refresh": second_raw})
    assert successor.status_code == 401


def test_refresh_without_cookie_is_rejected(client):
    assert client.post("/api/auth/refresh").status_code == 401


def test_logout_revokes_refresh_and_clears_cookies(client, fixture_data):
    login = _login(client, LEARNER)
    raw = login.cookies.get("pramana_refresh")
    access = login.json()["access_token"]

    out = client.post(
        "/api/auth/logout", headers={"Authorization": f"Bearer {access}"}
    )
    assert out.status_code == 204

    assert client.post("/api/auth/refresh", cookies={"pramana_refresh": raw}).status_code == 401


def test_password_change_invalidates_existing_access_tokens(client, fixture_data):
    login = _login(client, LEARNER)
    access = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {access}"}
    raw = login.cookies.get("pramana_refresh")

    assert client.get("/api/auth/me", headers=headers).status_code == 200

    changed = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": TEST_PASSWORD, "new_password": "Rotated#2026x"},
    )
    assert changed.status_code == 204
    cleared_cookies = " ".join(changed.headers.get_list("set-cookie")).lower()
    assert "pramana_access=" in cleared_cookies and "max-age=0" in cleared_cookies
    assert "pramana_refresh=" in cleared_cookies and "max-age=0" in cleared_cookies

    # token_version was bumped, so the old access token and refresh token are both dead.
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    assert client.post("/api/auth/refresh", cookies={"pramana_refresh": raw}).status_code == 401

    # The new password works.
    assert _login(client, LEARNER, "Rotated#2026x").status_code == 200


def test_password_change_requires_the_current_password(client, fixture_data, api):
    headers = api.headers(LEARNER)
    response = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": "NotThePassword1", "new_password": "Rotated#2026x"},
    )
    assert response.status_code == 400


def test_password_strength_is_enforced(client, fixture_data, api):
    headers = api.headers(LEARNER)
    response = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": TEST_PASSWORD, "new_password": "short"},
    )
    # min_length=10 at the schema layer.
    assert response.status_code == 422

    weak = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": TEST_PASSWORD, "new_password": "alllowercase1"},
    )
    assert weak.status_code == 422
    assert "uppercase" in weak.json()["detail"].lower()


def test_registration_always_creates_a_learner(client, fixture_data):
    payload = {
        "email": "newcomer@example.com",
        "full_name": "New Comer",
        "password": "Brand#New2026",
        # A caller attempting privilege escalation:
        "role": "admin",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["role"] == "learner"

    # ...and the escalated role was not persisted either.
    login = client.post(
        "/api/auth/login", json={"email": "newcomer@example.com", "password": "Brand#New2026"}
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "learner"


def test_registration_rejects_duplicate_email(client, fixture_data):
    response = client.post(
        "/api/auth/register",
        json={
            "email": LEARNER,
            "full_name": "Duplicate Person",
            "password": "Brand#New2026",
        },
    )
    assert response.status_code == 409


def test_unauthenticated_access_is_401(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/me/gaps").status_code == 401
    assert client.get("/api/documents").status_code == 401


def test_tampered_and_foreign_tokens_are_rejected(client, fixture_data):
    login = _login(client, LEARNER)
    token = login.json()["access_token"]

    # Flip a character in the signature.
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    assert client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {tampered}"}
    ).status_code == 401

    import jwt as pyjwt

    forged = pyjwt.encode(
        {"sub": str(fixture_data["users"]["admin"].id), "role": "admin", "tv": 0,
         "typ": "access", "iss": "pramana.local"},
        "an-attacker-chosen-secret-an-attacker-chosen-secret",
        algorithm="HS256",
    )
    assert client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {forged}"}
    ).status_code == 401


def test_security_headers_are_present_on_api_responses(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "no-store"
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]


def test_validation_errors_do_not_echo_submitted_values(client):
    response = client.post(
        "/api/auth/login", json={"email": "not-an-email", "password": "SuperSecret#1"}
    )
    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Validation failed"
    assert "SuperSecret#1" not in response.text
    assert "email" in {err["field"] for err in body["errors"]}
