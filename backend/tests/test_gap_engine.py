"""Deterministic gap engine and recommendation arithmetic.

These are pure-function tests: every expected number below is derived by hand from the
documented formula in `app/services/gap.py`, not read back from the implementation.

    priority_score = deficit x importance_weight x critical_multiplier x confidence_weight
    importance_weight   = 0.6 + 0.4 * (importance / 5)
    critical_multiplier = 1.35 if is_critical else 1.0
    confidence_weight   = 0.85 + 0.15 * (confidence / 5)
"""
from __future__ import annotations

import datetime as dt
import uuid

import pytest

from app.models.assessment import CompetencyState
from app.services import gap as gap_service

LEARNER = "learner@example.com"


# ------------------------------------------------------------------ pure rules
@pytest.mark.parametrize(
    ("deficit", "expected"),
    [
        (0.0, "none"),
        (-1.0, "none"),
        (0.25, "low"),
        (0.5, "low"),
        (0.51, "moderate"),
        (1.0, "moderate"),
        (1.01, "high"),
        (1.75, "high"),
        (1.76, "critical"),
        (4.0, "critical"),
    ],
)
def test_severity_bands(deficit, expected):
    assert gap_service.severity_of(deficit) == expected


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.0, "P4"),
        (0.69, "P4"),
        (0.7, "P3"),
        (1.39, "P3"),
        (1.4, "P2"),
        (2.19, "P2"),
        (2.2, "P1"),
        (9.0, "P1"),
    ],
)
def test_priority_bands(score, expected):
    assert gap_service.band_of(score) == expected


class _State:
    """Minimal stand-in for CompetencyState (method, level, quiz_evidence)."""

    def __init__(self, level: float, method: str = "self", quiz_evidence=None) -> None:
        self.level = level
        self.method = method
        self.quiz_evidence = quiz_evidence


def test_effective_level_without_state_is_zero_and_unassessed():
    level, source = gap_service.effective_level(None)
    assert level == 0.0
    assert source == "not_assessed"


def test_quiz_evidence_can_nudge_a_level_by_at_most_half():
    up, _ = gap_service.effective_level(_State(3.0, quiz_evidence=1.0))
    down, _ = gap_service.effective_level(_State(3.0, quiz_evidence=0.0))
    neutral, _ = gap_service.effective_level(_State(3.0, quiz_evidence=0.5))

    assert up == 3.5
    assert down == 2.5
    assert neutral == 3.0


def test_quiz_evidence_never_pushes_beyond_the_scale():
    high, _ = gap_service.effective_level(_State(5.0, quiz_evidence=1.0))
    low, _ = gap_service.effective_level(_State(0.0, quiz_evidence=0.0))
    assert high == 5.0
    assert low == 0.0


def test_effective_level_reports_that_quiz_evidence_was_used():
    _, source = gap_service.effective_level(_State(3.0, method="self", quiz_evidence=0.8))
    assert source == "self+quiz"


# ------------------------------------------------------------------ full computation
def test_gap_computation_matches_hand_calculated_scores(db, fixture_data, seeded_learner):
    learner = fixture_data["users"]["learner"]
    data = gap_service.compute(db, learner)

    assert data["total_required"] == 4
    assert data["gap_count"] == 3
    assert data["met_count"] == 1
    assert data["critical_gap_count"] == 1
    # 100 * (3 + 2.5 + 3 + 2) / (5 + 3 + 4 + 2)
    assert data["overall_readiness_percent"] == 75.0

    by_code = {row.code: row for row in data["items"]}

    p1 = by_code["STAT.01"]
    assert p1.deficit == 2.0
    assert p1.severity == "critical"
    # 2.0 * 1.00 * 1.35 * 1.00
    assert p1.priority_score == pytest.approx(2.7)
    assert p1.priority_band == "P1"
    assert p1.is_critical is True

    p4 = by_code["STAT.02"]
    assert p4.deficit == 0.5
    assert p4.severity == "low"
    # 0.5 * 0.84 * 1.00 * 0.94
    assert p4.priority_score == pytest.approx(0.395, abs=1e-3)
    assert p4.priority_band == "P4"

    p3 = by_code["DQ.01"]
    assert p3.deficit == 1.0
    assert p3.severity == "moderate"
    # 1.0 * 0.92 * 1.00 * 0.97
    assert p3.priority_score == pytest.approx(0.892, abs=1e-3)
    assert p3.priority_band == "P3"

    met = by_code["STAT.03"]
    assert met.deficit == 0.0
    assert met.severity == "none"


def test_gaps_are_ordered_by_priority_with_prerequisites_deferred(
    db, fixture_data, seeded_learner
):
    data = gap_service.compute(db, fixture_data["users"]["learner"])
    open_gaps = [row for row in data["items"] if row.deficit > 0]

    # STAT.02 declares STAT.01 as a prerequisite, and STAT.01 is itself deficient.
    by_code = {row.code: row for row in open_gaps}
    assert by_code["STAT.02"].prerequisite_blocked is True
    assert "Deferred: prerequisite STAT.01" in by_code["STAT.02"].explanation
    assert by_code["STAT.01"].prerequisite_blocked is False

    # Unblocked rows come first, then descending priority.
    assert [row.code for row in open_gaps] == ["STAT.01", "DQ.01", "STAT.02"]


def test_every_gap_row_explains_itself(db, fixture_data, seeded_learner):
    data = gap_service.compute(db, fixture_data["users"]["learner"])
    for row in data["items"]:
        assert row.explanation
        assert str(row.target_level) in row.explanation
        # The provenance of the level is always disclosed, so a self-rating is never
        # presented as if it were verified.
        assert "source:" in row.explanation


def test_unassessed_learner_has_a_full_gap_set_and_no_fake_scores(db, fixture_data):
    """A learner with no assessment must not be silently treated as proficient."""
    fresh = fixture_data["users"]["outsider"]
    data = gap_service.compute(db, fresh)

    assert data["missing_assessment"] is True
    assert data["gap_count"] == 4
    assert data["met_count"] == 0
    assert data["overall_readiness_percent"] == 0.0
    for row in data["items"]:
        assert row.current_level == 0.0
        assert row.current_source == "not_assessed"


def test_learner_without_a_job_role_gets_no_invented_analysis(db, fixture_data):
    comp = fixture_data["competencies"]["STAT.01"]
    from app.models.users import User

    unassigned = User(
        email="unassigned@example.com",
        full_name="Unassigned Person",
        password_hash="x",
        role="learner",
        job_role_id=None,
    )
    db.add(unassigned)
    db.flush()

    data = gap_service.compute(db, unassigned)
    assert data["job_role_id"] is None
    assert data["gap_count"] == 0
    assert data["items"] == []
    assert comp is not None


def test_endpoint_exposes_the_same_numbers_with_the_method_note(
    db, fixture_data, seeded_learner, api
):
    response = api.get(LEARNER, "/api/me/gaps")
    assert response.status_code == 200
    body = response.json()

    assert body["overall_readiness_percent"] == 75.0
    assert body["gap_count"] == 3
    assert body["critical_gap_count"] == 1
    assert body["method_note"] == gap_service.METHOD_NOTE
    assert body["job_role_title"] == "Test Statistical Officer"

    top = body["items"][0]
    assert top["competency_code"] == "STAT.01"
    assert top["priority_band"] == "P1"
    assert top["current_level_source"] == "self"


def test_assessment_rerun_updates_states_and_rebuilds_the_plan(
    db, fixture_data, seeded_learner, api
):
    from sqlalchemy import select

    from app.models.assessment import LearningPlan

    comp = fixture_data["competencies"]["STAT.01"]

    # Materialise plan v1 first, so a later re-assessment is observably versioned.
    first_plan = api.get(LEARNER, "/api/me/plan")
    assert first_plan.status_code == 200
    assert first_plan.json()["version"] == 1

    submitted = api.post(
        LEARNER,
        "/api/assessments",
        json={
            "method": "structured",
            "title": "Re-assessment after training",
            "responses": [
                {"competency_id": str(comp.id), "declared_level": 5, "confidence": 4}
            ],
        },
    )
    assert submitted.status_code == 201, submitted.text

    gaps = api.get(LEARNER, "/api/me/gaps").json()
    by_code = {row["competency_code"]: row for row in gaps["items"]}
    # STAT.01 is now met, so it is no longer an open gap.
    assert by_code["STAT.01"]["deficit"] == 0.0
    assert gaps["gap_count"] == 2
    assert gaps["critical_gap_count"] == 0

    plans = db.scalars(
        select(LearningPlan).where(
            LearningPlan.user_id == fixture_data["users"]["learner"].id
        )
    ).all()
    # Force-versioned: the previous plan is retained but inactive.
    assert len(plans) >= 2
    assert sum(1 for plan in plans if plan.is_active) == 1


def test_quiz_evidence_is_bounded_so_it_cannot_certify_expertise(
    db, fixture_data, seeded_learner
):
    learner = fixture_data["users"]["learner"]
    comp = fixture_data["competencies"]["DQ.01"]

    state = db.query(CompetencyState).filter_by(user_id=learner.id, competency_id=comp.id).one()
    assert state.level == 3.0

    state.quiz_evidence = 1.0
    db.flush()

    data = gap_service.compute(db, learner)
    row = next(r for r in data["items"] if r.code == "DQ.01")
    # 3.0 + 0.5 (clamped), never 5.0.
    assert row.current_level == 3.5
    assert row.current_source == "self+quiz"
    assert row.deficit == 0.5
