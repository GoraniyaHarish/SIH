"""Backend-enforced authorization: role gates, ownership, and IDOR resistance.

The principle under test: authorisation is decided by the API, never by the client. Where a
resource belongs to someone else and must not be revealed, the API answers 404 rather than 403 so
that existence itself is not disclosed.
"""
from __future__ import annotations

import uuid

import pytest

from tests.conftest import upload

LEARNER = "learner@example.com"
LEARNER2 = "learner2@example.com"
OUTSIDER = "outsider@example.com"
MANAGER = "manager@example.com"
MANAGER2 = "manager2@example.com"
ASSESSOR = "assessor@example.com"
ADMIN = "admin@example.com"


# ------------------------------------------------------------------ role gates
@pytest.mark.parametrize(
    "path",
    [
        "/api/admin/users",
        "/api/admin/audit",
        "/api/admin/overview",
        "/api/admin/system",
        "/api/admin/integrations",
    ],
)
def test_admin_endpoints_reject_every_non_admin_role(client, fixture_data, api, path):
    for email in (LEARNER, MANAGER, ASSESSOR):
        response = api.get(email, path)
        assert response.status_code == 403, f"{email} unexpectedly reached {path}"


def test_admin_endpoints_allow_admin(client, fixture_data, api):
    assert api.get(ADMIN, "/api/admin/users").status_code == 200
    assert api.get(ADMIN, "/api/admin/overview").status_code == 200
    assert api.get(ADMIN, "/api/admin/audit").status_code == 200


def test_learner_cannot_manage_the_catalogue(client, fixture_data, api):
    payload = {
        "code": "ESCALATED-1",
        "title": "Attempted Learner Created Course",
        "provider": "Self",
    }
    assert api.post(LEARNER, "/api/courses", json=payload).status_code == 403


def test_learner_cannot_generate_quizzes(client, fixture_data, api):
    body = {"document_id": str(uuid.uuid4()), "question_count": 3}
    assert api.post(LEARNER, "/api/quizzes/generate", json=body).status_code == 403


def test_learner_cannot_read_aggregate_analytics(client, fixture_data, api):
    assert api.get(LEARNER, "/api/manager/analytics").status_code == 403
    assert api.get(LEARNER, "/api/manager/analytics/export").status_code == 403


def test_learner_cannot_use_the_staff_gaps_endpoint(client, fixture_data, api):
    other = fixture_data["users"]["learner2"]
    assert api.get(LEARNER, f"/api/users/{other.id}/gaps").status_code == 403


def test_manager_may_read_direct_report_gaps_only(client, fixture_data, api):
    report = fixture_data["users"]["learner"]
    stranger = fixture_data["users"]["learner2"]

    assert api.get(MANAGER, f"/api/users/{report.id}/gaps").status_code == 200
    # A different manager's scope:
    assert api.get(MANAGER2, f"/api/users/{stranger.id}/gaps").status_code == 403


def test_manager_analytics_scope_cannot_be_widened_by_a_query_parameter(
    client, fixture_data, api
):
    dept_b = fixture_data["departments"]["B"]
    # manager belongs to Department A; asking for Department B must not expand scope.
    response = api.get(MANAGER, f"/api/manager/analytics?department_id={dept_b.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["scope"] == "department"
    # Only Department A learners are ever counted (learner, learner2).
    assert body["headcount_considered"] <= 2


def test_assessor_cannot_edit_competency_content_but_may_review(
    client, fixture_data, api
):
    comp = fixture_data["competencies"]["STAT.01"]

    denied = api.patch(
        ASSESSOR, f"/api/framework/competencies/{comp.id}", json={"name": "Renamed By Assessor"}
    )
    assert denied.status_code == 403
    assert "review decisions" in denied.json()["detail"].lower()

    approved = api.patch(
        ASSESSOR,
        f"/api/framework/competencies/{comp.id}",
        json={"review_status": "approved"},
    )
    assert approved.status_code == 200
    assert approved.json()["review_status"] == "approved"


def test_only_admin_can_create_departments(client, fixture_data, api):
    body = {"name": "Unauthorised Department", "code": "UNAUTH"}
    assert api.post(MANAGER, "/api/admin/departments", json=body).status_code == 403
    assert api.post(ADMIN, "/api/admin/departments", json=body).status_code == 201


# ------------------------------------------------------------------ document IDOR
def test_private_document_is_invisible_to_other_learners(client, fixture_data, api):
    owner_headers = api.headers(LEARNER)
    created = upload(client, owner_headers, _material(), title="Private learner notes")
    assert created.status_code == 201, created.text
    doc_id = created.json()["id"]
    assert created.json()["visibility"] == "private"

    # The owner sees it.
    assert client.get(f"/api/documents/{doc_id}", headers=owner_headers).status_code == 200

    # A different learner gets 404 — not 403 — so existence is not disclosed.
    other_headers = api.headers(LEARNER2)
    response = client.get(f"/api/documents/{doc_id}", headers=other_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"

    # It is absent from the other learner's list as well.
    listing = client.get("/api/documents", headers=other_headers).json()
    assert doc_id not in {item["id"] for item in listing}


def test_private_document_listing_is_scoped_and_mine_filter_works(client, fixture_data, api):
    created = upload(client, api.headers(LEARNER), _material(), title="Scoped note")
    doc_id = created.json()["id"]

    mine = client.get("/api/documents?mine=true", headers=api.headers(LEARNER)).json()
    assert doc_id in {item["id"] for item in mine}

    theirs = client.get("/api/documents?mine=true", headers=api.headers(OUTSIDER)).json()
    assert doc_id not in {item["id"] for item in theirs}


def test_assistant_rejects_an_unauthorized_document_id(client, fixture_data, api):
    created = upload(client, api.headers(LEARNER), _material(), title="Owner only source")
    doc_id = created.json()["id"]

    response = api.post(
        LEARNER2,
        "/api/assistant/ask",
        json={"question": "What does this material say about design effect?", "document_ids": [doc_id]},
    )
    # The scope is validated before retrieval, so the request fails closed.
    assert response.status_code == 404


def test_learner_cannot_publish_to_organisation_scope(client, fixture_data, api):
    response = upload(
        client, api.headers(LEARNER), _material(), title="Escalated visibility",
        visibility="organisation",
    )
    assert response.status_code == 403
    assert "staff role" in response.json()["detail"].lower()


def test_manager_may_publish_department_scope(client, fixture_data, api):
    response = upload(
        client, api.headers(MANAGER), _material(), title="Department material",
        visibility="department",
    )
    assert response.status_code == 201
    assert response.json()["visibility"] == "department"


def test_department_document_visible_inside_department_only(client, fixture_data, api):
    created = upload(
        client, api.headers(MANAGER), _material(), title="Dept A shared",
        visibility="department",
    )
    assert created.status_code == 201
    doc_id = created.json()["id"]

    # Same department (Department A)
    assert client.get(f"/api/documents/{doc_id}", headers=api.headers(LEARNER)).status_code == 200
    # Different department (Department B)
    assert client.get(f"/api/documents/{doc_id}", headers=api.headers(OUTSIDER)).status_code == 404


def test_document_chunks_are_authorized_like_the_document(client, fixture_data, api):
    created = upload(client, api.headers(LEARNER), _material(), title="Chunk scope")
    doc_id = created.json()["id"]

    assert client.get(
        f"/api/documents/{doc_id}/chunks", headers=api.headers(LEARNER)
    ).status_code == 200
    assert client.get(
        f"/api/documents/{doc_id}/chunks", headers=api.headers(LEARNER2)
    ).status_code == 404


def test_delete_requires_ownership_or_admin(client, fixture_data, api):
    created = upload(client, api.headers(LEARNER), _material(), title="Deletable")
    doc_id = created.json()["id"]

    assert api.delete(LEARNER2, f"/api/documents/{doc_id}").status_code == 404
    assert api.delete(ADMIN, f"/api/documents/{doc_id}").status_code == 204


# ------------------------------------------------------------------ plan / attempt IDOR
def test_plan_item_belongs_to_exactly_one_user(client, fixture_data, seeded_learner, api):
    plan = api.get(LEARNER, "/api/me/plan")
    assert plan.status_code == 200
    items = plan.json()["items"]
    assert items, "the seeded learner must have plan items to test ownership"

    item_id = items[0]["id"]
    stolen = api.patch(LEARNER2, f"/api/me/plan/items/{item_id}", json={"status": "completed"})
    assert stolen.status_code == 403
    assert "does not belong" in stolen.json()["detail"].lower()

    # The rightful owner can advance it.
    owned = api.patch(LEARNER, f"/api/me/plan/items/{item_id}", json={"status": "in_progress"})
    assert owned.status_code == 200


def test_quiz_attempt_cannot_be_submitted_by_another_user(
    client, fixture_data, seeded_learner, db, api
):
    quiz = _published_quiz(db, fixture_data, created_by=fixture_data["users"]["assessor"])

    started = api.post(LEARNER, f"/api/quizzes/{quiz.id}/attempts")
    assert started.status_code == 201, started.text
    attempt_id = started.json()["attempt_id"]

    # Another learner may not submit it...
    stolen = api.post(LEARNER2, f"/api/attempts/{attempt_id}/submit", json={"answers": {}})
    assert stolen.status_code == 403
    assert "does not belong" in stolen.json()["detail"].lower()

    # ...nor read it.
    assert api.get(LEARNER2, f"/api/attempts/{attempt_id}").status_code == 403

    # The owner can.
    assert api.get(LEARNER, f"/api/attempts/{attempt_id}").status_code == 200


def test_assessment_of_another_learner_is_not_readable(client, fixture_data, seeded_learner, api):
    assessment_id = seeded_learner["assessment"].id

    assert api.get(LEARNER, f"/api/assessments/{assessment_id}").status_code == 200
    assert api.get(LEARNER2, f"/api/assessments/{assessment_id}").status_code == 403
    # Assessors and admins may read for review purposes.
    assert api.get(ASSESSOR, f"/api/assessments/{assessment_id}").status_code == 200
    assert api.get(ADMIN, f"/api/assessments/{assessment_id}").status_code == 200


def test_assessor_cannot_review_their_own_assessment(client, fixture_data, api):
    created = api.post(
        ASSESSOR,
        "/api/assessments",
        json={
            "method": "self",
            "title": "Assessor self review",
            "responses": [
                {
                    "competency_id": str(fixture_data["competencies"]["STAT.01"].id),
                    "declared_level": 3,
                    "confidence": 3,
                }
            ],
        },
    )
    assert created.status_code == 201
    assessment_id = created.json()["id"]

    denied = api.post(
        ASSESSOR,
        f"/api/assessments/{assessment_id}/review",
        json={
            "responses": [
                {
                    "competency_id": str(fixture_data["competencies"]["STAT.01"].id),
                    "declared_level": 4,
                    "confidence": 5,
                }
            ]
        },
    )
    assert denied.status_code == 400
    assert "your own" in denied.json()["detail"].lower()


def test_learner_cannot_review_any_assessment(client, fixture_data, seeded_learner, api):
    assessment_id = seeded_learner["assessment"].id
    response = api.post(
        LEARNER,
        f"/api/assessments/{assessment_id}/review",
        json={
            "responses": [
                {
                    "competency_id": str(fixture_data["competencies"]["STAT.01"].id),
                    "declared_level": 5,
                    "confidence": 5,
                }
            ]
        },
    )
    assert response.status_code == 403


def test_admin_cannot_deactivate_self_or_strand_the_system(client, fixture_data, api):
    admin = fixture_data["users"]["admin"]
    assert api.delete(ADMIN, f"/api/admin/users/{admin.id}").status_code == 400
    assert api.patch(
        ADMIN, f"/api/admin/users/{admin.id}", json={"is_active": False}
    ).status_code == 400
    # Role change on self is also refused.
    assert api.patch(
        ADMIN, f"/api/admin/users/{admin.id}", json={"role": "learner"}
    ).status_code == 400


def test_role_change_invalidates_the_target_users_sessions(client, fixture_data, api):
    learner = fixture_data["users"]["learner2"]
    stale_headers = dict(api.headers(LEARNER2))
    assert client.get("/api/auth/me", headers=stale_headers).status_code == 200

    promoted = api.patch(ADMIN, f"/api/admin/users/{learner.id}", json={"role": "manager"})
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "manager"

    # token_version was bumped, so the pre-change access token is dead.
    assert client.get("/api/auth/me", headers=stale_headers).status_code == 401


# ------------------------------------------------------------------ helpers
def _material() -> bytes:
    body = """Scope note on survey quality control.

Supervision visits verify that enumerators follow the sampling instructions and record responses
without substitution. A minimum of ten percent of primary sampling units is re-verified in the
field so that fabrication can be detected early.

Consistency checks compare the reported household roster against the listing frame and flag any
unit that reports an implausible number of members for editing follow up.

Back checks are conducted by an independent team, and the disagreement rate is reported to the
survey coordination unit within fifteen days of the visit.
"""
    return body.encode("utf-8")


def _published_quiz(db, fixture_data, *, created_by):
    from app.models.assessment import Quiz, QuizQuestion
    from app.models.base import QuizStatus

    quiz = Quiz(
        title="Authorisation fixture quiz",
        description="Created directly in the database for an IDOR test.",
        status=QuizStatus.PUBLISHED.value,
        difficulty="easy",
        generation_mode="extractive_fallback",
        created_by_id=created_by.id,
        visibility="organisation",
    )
    db.add(quiz)
    db.flush()
    for index in range(3):
        db.add(
            QuizQuestion(
                quiz_id=quiz.id,
                stem=f"Which statement about supervision visits is correct number {index}?",
                options=[
                    {"text": "Option A about supervision", "index": 0},
                    {"text": "Option B about supervision", "index": 1},
                    {"text": "Option C about supervision", "index": 2},
                    {"text": "Option D about supervision", "index": 3},
                ],
                correct_index=index % 4,
                explanation="Fixture explanation tied to the passage.",
                difficulty="easy",
                sort_order=index,
            )
        )
    db.flush()
    return quiz
