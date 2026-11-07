"""Deterministic, explainable competency gap analysis.

The scoring rule is fixed and documented so anyone can reproduce a learner's priority list:

    deficit        = max(0, required_level - current_level)        (levels 1..5)
    severity       = none if deficit == 0
                     low if deficit <= 0.5
                     moderate if deficit <= 1.0
                     high if deficit <= 1.75
                     critical otherwise
    priority_score = deficit * importance_weight * critical_multiplier * confidence_weight
    importance_weight  = 0.6 + 0.4 * (importance / 5)      -> 0.68 .. 1.00
    critical_multiplier = 1.35 for critical competencies else 1.0
    confidence_weight  = 0.85 + 0.15 * (confidence / 5)    -> down-weights low-confidence self-ratings
    prerequisite_blocked = True when a prerequisite competency is itself deficient, in which case
                       the item is ordered after fixing the prerequisite.

Priority bands (P1 highest): P1 >= 2.2, P2 >= 1.4, P3 >= 0.7, P4 below.
Assessment evidence from quizzes nudges the effective level (see `effective_level`), and the source
of every level is reported so an unverified self-rating is never presented as proven proficiency.
"""
from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment import Assessment, CompetencyState
from app.models.competency import (
    Competency, CompetencyDomain, CompetencyPrerequisite, JobRole, ProficiencyLevel,
    RoleCompetencyRequirement,
)
from app.models.users import User

METHOD_NOTE = (
    "Gap = required level − current level (floored at 0). Priority = gap × importance weight × "
    "critical multiplier × confidence weight. Quiz evidence adjusts at most ±0.5 level. Every "
    "level carries its assessment method, so self-reported levels are labelled as unverified."
)

P1_THRESHOLD, P2_THRESHOLD, P3_THRESHOLD = 2.2, 1.4, 0.7


@dataclass
class GapRow:
    competency_id: uuid.UUID
    code: str
    name: str
    domain_code: str
    domain_name: str
    current_level: float
    current_source: str
    target_level: int
    deficit: float
    severity: str
    importance: int
    is_critical: bool
    priority_score: float
    priority_band: str
    explanation: str
    prerequisite_blocked: bool
    evidence_status: str


def severity_of(deficit: float) -> str:
    if deficit <= 0:
        return "none"
    if deficit <= 0.5:
        return "low"
    if deficit <= 1.0:
        return "moderate"
    if deficit <= 1.75:
        return "high"
    return "critical"


def band_of(score: float) -> str:
    if score >= P1_THRESHOLD:
        return "P1"
    if score >= P2_THRESHOLD:
        return "P2"
    if score >= P3_THRESHOLD:
        return "P3"
    return "P4"


def effective_level(state: CompetencyState | None) -> tuple[float, str]:
    """Blend assessed level with quiz evidence, bounded so quizzes can never certify expertise."""
    if state is None:
        return 0.0, "not_assessed"
    level = float(state.level)
    source = state.method
    if state.quiz_evidence is not None:
        # quiz_evidence is a 0..1 accuracy. Max influence is +/- 0.5 of a level.
        delta = (float(state.quiz_evidence) - 0.5) * 1.0
        level = max(0.0, min(5.0, level + max(-0.5, min(0.5, delta))))
        source = f"{state.method}+quiz"
    return round(level, 2), source


def compute(
    db: Session,
    user: User,
    *,
    job_role_id: uuid.UUID | None = None,
    include_met: bool = True,
) -> dict:
    role_id = job_role_id or user.job_role_id
    role = db.get(JobRole, role_id) if role_id else None

    states = {
        s.competency_id: s
        for s in db.scalars(select(CompetencyState).where(CompetencyState.user_id == user.id))
    }
    latest_assessment = db.scalars(
        select(Assessment)
        .where(Assessment.user_id == user.id)
        .order_by(Assessment.created_at.desc())
        .limit(1)
    ).first()

    if role is None:
        return {
            "job_role_id": None, "job_role_title": None, "framework_label": "",
            "total_required": 0, "met_count": 0, "gap_count": 0, "critical_gap_count": 0,
            "overall_readiness_percent": 0.0, "items": [],
            "missing_assessment": latest_assessment is None,
        }

    reqs = db.execute(
        select(RoleCompetencyRequirement, Competency, CompetencyDomain)
        .join(Competency, Competency.id == RoleCompetencyRequirement.competency_id)
        .join(CompetencyDomain, CompetencyDomain.id == Competency.domain_id)
        .where(RoleCompetencyRequirement.job_role_id == role.id)
    ).all()

    # prerequisite graph for ordering
    prereq_map: dict[uuid.UUID, list[tuple[uuid.UUID, int]]] = {}
    for edge in db.scalars(select(CompetencyPrerequisite)):
        prereq_map.setdefault(edge.competency_id, []).append(
            (edge.prerequisite_competency_id, edge.min_level)
        )

    raw: list[GapRow] = []
    for req, comp, domain in reqs:
        state = states.get(comp.id)
        level, level_source = effective_level(state)
        deficit = max(0.0, float(req.required_level) - level)
        importance_weight = 0.6 + 0.4 * (req.importance / 5.0)
        critical_mult = 1.35 if req.is_critical else 1.0
        confidence = state.confidence if state else 3
        confidence_weight = 0.85 + 0.15 * (confidence / 5.0)
        score = round(deficit * importance_weight * critical_mult * confidence_weight, 3)

        if deficit <= 0:
            explanation = (
                f"You are at level {level:g} against a required level of {req.required_level}. "
                f"No gap. Current level source: {level_source.replace('_', ' ')}."
            )
        else:
            explanation = (
                f"You are at level {level:g} against a required level of {req.required_level} "
                f"({deficit:g} level{'s' if deficit != 1 else ''} short). "
                f"This competency is rated importance {req.importance}/5"
                f"{' and is marked critical for the role' if req.is_critical else ''}. "
                f"Current level source: {level_source.replace('_', ' ')}; "
                f"confidence {confidence}/5."
            )

        raw.append(
            GapRow(
                competency_id=comp.id, code=comp.code, name=comp.name,
                domain_code=domain.code, domain_name=domain.name,
                current_level=level, current_source=level_source,
                target_level=req.required_level, deficit=round(deficit, 2),
                severity=severity_of(deficit), importance=req.importance,
                is_critical=req.is_critical, priority_score=score,
                priority_band=band_of(score), explanation=explanation,
                prerequisite_blocked=False, evidence_status=req.evidence_status,
            )
        )

    # prerequisite blocking: a gap whose prerequisite is also deficient is deferred
    defective = {row.competency_id: row.deficit for row in raw}
    code_by_id = {row.competency_id: row.code for row in raw}
    for row in raw:
        for prereq_id, _min_level in prereq_map.get(row.competency_id, []):
            if defective.get(prereq_id, 0) > 0:
                row.prerequisite_blocked = True
                prereq_code = code_by_id.get(prereq_id, "a prerequisite competency")
                row.explanation += f" Deferred: prerequisite {prereq_code} is also deficient."
                break

    gap_rows = [r for r in raw if r.deficit > 0]
    gap_rows.sort(
        key=lambda r: (r.prerequisite_blocked, -r.priority_score, r.code)
    )
    met = [r for r in raw if r.deficit <= 0]

    total_required = len(raw)
    readiness = 0.0
    if total_required:
        achieved = sum(min(r.current_level, r.target_level) for r in raw)
        wanted = sum(r.target_level for r in raw)
        readiness = round(100.0 * achieved / wanted, 1) if wanted else 0.0

    items = (gap_rows + (met if include_met else []))
    return {
        "job_role_id": role.id,
        "job_role_title": role.title,
        "framework_label": role.code,
        "total_required": total_required,
        "met_count": len(met),
        "gap_count": len(gap_rows),
        "critical_gap_count": sum(1 for r in gap_rows if r.is_critical),
        "overall_readiness_percent": readiness,
        "items": items,
        "missing_assessment": latest_assessment is None,
        "computed_at": dt.datetime.now(dt.timezone.utc),
    }


def levels_for_framework(db: Session, framework_version_id: uuid.UUID) -> list[ProficiencyLevel]:
    return list(
        db.scalars(
            select(ProficiencyLevel)
            .where(ProficiencyLevel.framework_version_id == framework_version_id)
            .order_by(ProficiencyLevel.level)
        )
    )
