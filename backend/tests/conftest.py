"""Test harness.

Design decisions that matter for honesty of the results:

* The environment is configured BEFORE any application module is imported, because
  ``app.core.config`` builds a cached Settings instance and ``app.core.db`` builds its
  engine at import time.
* The schema comes from the real Alembic migration (not ``create_all``), so the tests run
  against exactly the schema that production deploys.
* Each test runs inside one outer transaction that is rolled back afterwards. Application
  sessions are bound to that connection with ``join_transaction_mode="create_savepoint"``,
  so the endpoints really call ``commit()`` while the outer transaction still isolates tests.
* AI credentials are explicitly blanked so the deterministic (extractive / keyword) code
  paths are exercised and no test depends on network access or provider availability.
"""
from __future__ import annotations

import datetime as dt
import os
import tempfile
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

# --- environment must be set before importing app modules -------------------------------
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://pramana:pramana_local_dev@127.0.0.1:5432/pramana_test",
)
_UPLOAD_DIR = Path(tempfile.mkdtemp(prefix="pramana-test-uploads-"))

os.environ.update(
    {
        "APP_ENV": "test",
        "DATABASE_URL": TEST_DATABASE_URL,
        "JWT_SECRET": "test-only-secret-not-used-anywhere-real-0123456789",
        "COOKIE_SECURE": "false",
        "UPLOAD_DIR": str(_UPLOAD_DIR),
        "PROCESS_INLINE_WORKER": "false",
        "REDIS_URL": "",  # force the in-process limiter: deterministic, no external service
        "AI_BASE_URL": "",
        "AI_API_KEY": "",
        "AI_SEND_DOCUMENTS_EXTERNALLY": "false",
        "LOG_LEVEL": "WARNING",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, select, text  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

import app.models  # noqa: F401,E402  (registers every mapper on Base.metadata)
from app.core.config import settings  # noqa: E402
from app.core.db import get_db  # noqa: E402
from app.core.security import hash_password, limiter  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.models.assessment import Assessment, AssessmentResponse, CompetencyState  # noqa: E402
from app.models.base import (  # noqa: E402
    AssessmentMethod, AssessmentStatus, EvidenceStatus, ReviewStatus, Role,
)
from app.models.competency import (  # noqa: E402
    Competency, CompetencyDomain, CompetencyPrerequisite, FrameworkVersion, JobRole,
    ProficiencyLevel, RoleCompetencyRequirement,
)
from app.models.users import Department, User  # noqa: E402

TEST_PASSWORD = "Pramana#Test1"


# ------------------------------------------------------------------ schema
@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DATABASE_URL, pool_pre_ping=True, future=True)

    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")
    yield eng
    eng.dispose()


@pytest.fixture()
def connection(engine):
    conn = engine.connect()
    outer = conn.begin()
    try:
        yield conn
    finally:
        outer.rollback()
        conn.close()


@pytest.fixture()
def db(connection):
    maker = sessionmaker(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
        class_=Session,
    )
    session = maker()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The limiter is a process-wide singleton; every test starts with an empty window."""
    limiter._hits.clear()
    yield
    limiter._hits.clear()


@pytest.fixture()
def client(db):
    def _get_db():
        yield db

    fastapi_app.dependency_overrides[get_db] = _get_db
    with TestClient(fastapi_app, raise_server_exceptions=False) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


# ------------------------------------------------------------------ domain seed
def _make_user(
    db: Session,
    email: str,
    role: Role,
    *,
    department_id=None,
    job_role_id=None,
    manager_id=None,
    full_name: str | None = None,
) -> User:
    user = User(
        email=email,
        full_name=full_name or email.split("@")[0].replace(".", " ").title(),
        password_hash=hash_password(TEST_PASSWORD),
        role=role,
        department_id=department_id,
        job_role_id=job_role_id,
        manager_id=manager_id,
        designation="Test designation",
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture()
def fixture_data(db) -> dict:
    """A small, hand-computable framework plus one account per role.

    Requirements are chosen so that the expected gap scores can be derived by hand:

      STAT.01  required 5, importance 5, critical -> learner at 3.0, conf 5
               deficit 2.0 * 1.00 * 1.35 * 1.00 = 2.700  -> P1, severite 'critical'
      STAT.02  required 3, importance 3,          -> learner at 2.5, conf 3
               deficit 0.5 * 0.84 * 1.00 * 0.94 = 0.395  -> P4, severity 'low'
      DQ.01    required 4, importance 4,          -> learner at 3.0, conf 4
               deficit 1.0 * 0.92 * 1.00 * 0.97 = 0.892  -> P3, severity 'moderate'
      STAT.03  required 2                          -> learner at 2.0 (met)

      readiness = 100 * (3 + 2.5 + 3 + 2) / (5 + 3 + 4 + 2) = 75.0
    """
    fw = FrameworkVersion(
        label="TEST-FW-1",
        notes="Synthetic framework used only by the automated test suite.",
        evidence_status=EvidenceStatus.PROVISIONAL.value,
        is_active=True,
    )
    db.add(fw)
    db.flush()

    for level in range(1, 6):
        db.add(
            ProficiencyLevel(
                framework_version_id=fw.id,
                level=level,
                label=f"Level {level}",
                summary=f"Summary for level {level}",
                criteria=[f"Observable criterion {level}.1", f"Observable criterion {level}.2"],
                evidence_status=EvidenceStatus.PROVISIONAL.value,
            )
        )

    dom_stat = CompetencyDomain(
        framework_version_id=fw.id, code="STAT", name="Statistical Methods", kind="functional",
        sort_order=0, evidence_status=EvidenceStatus.PROVISIONAL.value,
    )
    dom_dq = CompetencyDomain(
        framework_version_id=fw.id, code="DQ", name="Data Quality", kind="functional",
        sort_order=1, evidence_status=EvidenceStatus.PROVISIONAL.value,
    )
    db.add_all([dom_stat, dom_dq])
    db.flush()

    comp_defs = [
        (dom_stat, "STAT.01", "Sampling Design", 0),
        (dom_stat, "STAT.02", "Estimation Theory", 1),
        (dom_stat, "STAT.03", "Survey Instrumentation", 2),
        (dom_dq, "DQ.01", "Validation and Imputation", 0),
    ]
    comps: dict[str, Competency] = {}
    for domain, code, name, order in comp_defs:
        comp = Competency(
            domain_id=domain.id, code=code, name=name,
            description=f"{name} description.", rationale=f"{name} rationale.",
            sort_order=order, evidence_status=EvidenceStatus.PROVISIONAL.value,
            review_status=ReviewStatus.PENDING.value,
        )
        db.add(comp)
        comps[code] = comp
    db.flush()

    db.add(
        CompetencyPrerequisite(
            competency_id=comps["STAT.02"].id,
            prerequisite_competency_id=comps["STAT.01"].id,
            min_level=2,
            evidence_status=EvidenceStatus.PROVISIONAL.value,
        )
    )

    role = JobRole(
        framework_version_id=fw.id, code="TEST-ROLE", title="Test Statistical Officer",
        description="Role used by the automated test suite.",
        cadre="ISS", grade="JSO",
        evidence_status=EvidenceStatus.PROVISIONAL.value,
        review_status=ReviewStatus.PENDING.value,
    )
    db.add(role)
    db.flush()

    reqs = [
        ("STAT.01", 5, 5, True),
        ("STAT.02", 3, 3, False),
        ("STAT.03", 2, 3, False),
        ("DQ.01", 4, 4, False),
    ]
    for code, required, importance, critical in reqs:
        db.add(
            RoleCompetencyRequirement(
                job_role_id=role.id, competency_id=comps[code].id,
                required_level=required, importance=importance, is_critical=critical,
                evidence_status=EvidenceStatus.PROVISIONAL.value,
                review_status=ReviewStatus.PENDING.value,
            )
        )

    dept_a = Department(name="Department A", code="DEPT_A")
    dept_b = Department(name="Department B", code="DEPT_B")
    db.add_all([dept_a, dept_b])
    db.flush()

    admin = _make_user(db, "admin@example.com", Role.ADMIN, department_id=dept_a.id)
    manager = _make_user(
        db, "manager@example.com", Role.MANAGER, department_id=dept_a.id
    )
    assessor = _make_user(
        db, "assessor@example.com", Role.ASSESSOR, department_id=dept_a.id
    )
    learner = _make_user(
        db, "learner@example.com", Role.LEARNER, department_id=dept_a.id,
        job_role_id=role.id, manager_id=manager.id,
    )
    learner2 = _make_user(
        db, "learner2@example.com", Role.LEARNER, department_id=dept_a.id,
        job_role_id=role.id, manager_id=manager.id,
    )
    outsider = _make_user(
        db, "outsider@example.com", Role.LEARNER, department_id=dept_b.id,
        job_role_id=role.id,
    )
    manager2 = _make_user(
        db, "manager2@example.com", Role.MANAGER, department_id=dept_b.id
    )
    db.flush()

    return {
        "framework": fw,
        "role": role,
        "competencies": comps,
        "domains": {"STAT": dom_stat, "DQ": dom_dq},
        "departments": {"A": dept_a, "B": dept_b},
        "users": {
            "admin": admin,
            "manager": manager,
            "manager2": manager2,
            "assessor": assessor,
            "learner": learner,
            "learner2": learner2,
            "outsider": outsider,
        },
    }


@pytest.fixture()
def seeded_learner(db, fixture_data) -> dict:
    """Give `learner` a known assessment history so gap arithmetic is hand-checkable.

    Levels: STAT.01=3.0 (conf 5), STAT.02=2.5 (conf 3), STAT.03=2.0 (conf 3), DQ.01=3.0 (conf 4).
    Expected gap rows are documented in `fixture_data`.
    """
    learner = fixture_data["users"]["learner"]
    comps = fixture_data["competencies"]

    assessment = Assessment(
        user_id=learner.id,
        framework_version_id=fixture_data["framework"].id,
        method=AssessmentMethod.SELF.value,
        status=AssessmentStatus.SUBMITTED.value,
        title="Baseline self assessment",
        submitted_at=dt.datetime.now(dt.timezone.utc),
    )
    db.add(assessment)
    db.flush()

    declared = {
        "STAT.01": (3, 5),
        "STAT.02": (2.5, 3),  # stored as a float level on the state, int on the response
        "STAT.03": (2, 3),
        "DQ.01": (3, 4),
    }
    for code, (level, confidence) in declared.items():
        comp = comps[code]
        db.add(
            AssessmentResponse(
                assessment_id=assessment.id,
                competency_id=comp.id,
                declared_level=max(1, int(round(level))),
                confidence=confidence,
                evidence_note="Fixture response",
            )
        )
        db.add(
            CompetencyState(
                user_id=learner.id,
                competency_id=comp.id,
                level=float(level),
                method=AssessmentMethod.SELF.value,
                confidence=confidence,
                source_assessment_id=assessment.id,
                assessed_at=dt.datetime.now(dt.timezone.utc),
            )
        )
    db.flush()
    return {"assessment": assessment, "declared": declared}


# ------------------------------------------------------------------ helpers
class Api:
    """Thin helper that logs in and returns auth headers."""

    def __init__(self, client: TestClient) -> None:
        self.client = client
        self._cache: dict[str, dict[str, str]] = {}

    def headers(self, email: str) -> dict[str, str]:
        if email not in self._cache:
            response = self.client.post(
                "/api/auth/login", json={"email": email, "password": TEST_PASSWORD}
            )
            assert response.status_code == 200, f"login failed for {email}: {response.text}"
            self._cache[email] = {
                "Authorization": f"Bearer {response.json()['access_token']}"
            }
        return self._cache[email]

    def get(self, email: str, path: str, **kw):
        return self.client.get(path, headers=self.headers(email), **kw)

    def post(self, email: str, path: str, **kw):
        return self.client.post(path, headers=self.headers(email), **kw)

    def patch(self, email: str, path: str, **kw):
        return self.client.patch(path, headers=self.headers(email), **kw)

    def delete(self, email: str, path: str, **kw):
        return self.client.delete(path, headers=self.headers(email), **kw)


@pytest.fixture()
def api(client) -> Api:
    return Api(client)


def make_text_document(topic: str = "sampling", extra: str = "") -> bytes:
    """A plain-text fixture long enough to chunk, with words the extractive
    generator can use as cloze terms and distractors."""
    body = f"""Principles of {topic} for official statistics.

Stratification divides a heterogeneous population into internally homogeneous strata so that
estimator variance is reduced without increasing the nominal sample size. This document explains
the practical derivation of sample allocation across strata.

Design effect quantifies the loss of efficiency caused by clustering and unequal selection
probabilities relative to simple random sampling. Practitioners compute it before finalising an
allocation.

Calibration adjusts design weights so that known population totals are reproduced exactly by the
weighted estimates, which reduces nonresponse bias in the published aggregates.

Variance estimation for complex designs is normally performed with replication methods such as
jackknife or bootstrap, because closed form expressions understate uncertainty.

Response burden must be balanced against precision requirements, and the trade off is documented
in the survey design report filed before fieldwork begins.

{extra}"""
    return body.encode("utf-8")


def upload(client: TestClient, headers: dict[str, str], data: bytes, *,
           filename: str = "material.txt", content_type: str = "text/plain",
           title: str | None = None, visibility: str = "private",
           course_id: str | None = None):
    form = {"visibility": visibility}
    if title:
        form["title"] = title
    if course_id:
        form["course_id"] = course_id
    return client.post(
        "/api/documents",
        headers=headers,
        files={"file": (filename, data, content_type)},
        data=form,
    )


def unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


__all__ = [
    "Api", "TEST_PASSWORD", "TEST_DATABASE_URL", "fixture_data", "make_text_document",
    "settings", "select", "text", "upload", "unique",
]
