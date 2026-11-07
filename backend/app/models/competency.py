"""Versioned competency framework: domains, competencies, skills, levels, job roles."""
from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean, CheckConstraint, ForeignKey, Index, Integer, SmallInteger, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, EvidenceStatus, ReviewStatus, TimestampMixin, uuid_pk


class FrameworkVersion(Base, TimestampMixin):
    __tablename__ = "framework_versions"

    id: Mapped[uuid.UUID] = uuid_pk()
    label: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    evidence_status: Mapped[str] = mapped_column(
        String(20), default=EvidenceStatus.PROVISIONAL, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )


class CompetencyDomain(Base, TimestampMixin):
    __tablename__ = "competency_domains"

    id: Mapped[uuid.UUID] = uuid_pk()
    framework_version_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("framework_versions.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(24), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20), default="functional", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(20), default=EvidenceStatus.PROVISIONAL)
    source_ref: Mapped[str | None] = mapped_column(String(255))

    competencies: Mapped[list["Competency"]] = relationship(
        back_populates="domain", cascade="all, delete-orphan", order_by="Competency.sort_order"
    )

    __table_args__ = (UniqueConstraint("framework_version_id", "code", name="uq_domain_version_code"),)


class Competency(Base, TimestampMixin):
    __tablename__ = "competencies"

    id: Mapped[uuid.UUID] = uuid_pk()
    domain_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("competency_domains.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    rationale: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    evidence_status: Mapped[str] = mapped_column(String(20), default=EvidenceStatus.PROVISIONAL)
    review_status: Mapped[str] = mapped_column(String(16), default=ReviewStatus.PENDING)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    source_ref: Mapped[str | None] = mapped_column(String(255))

    domain: Mapped[CompetencyDomain] = relationship(back_populates="competencies")
    skills: Mapped[list["Skill"]] = relationship(
        back_populates="competency", cascade="all, delete-orphan", order_by="Skill.sort_order"
    )

    __table_args__ = (
        UniqueConstraint("domain_id", "code", name="uq_competency_domain_code"),
        Index("ix_competency_code", "code"),
    )


class Skill(Base, TimestampMixin):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = uuid_pk()
    competency_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("competencies.id", ondelete="CASCADE"), index=True
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    competency: Mapped[Competency] = relationship(back_populates="skills")


class ProficiencyLevel(Base, TimestampMixin):
    """Configurable 1..N scale with observable criteria. Provisional unless reviewed."""

    __tablename__ = "proficiency_levels"

    id: Mapped[uuid.UUID] = uuid_pk()
    framework_version_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("framework_versions.id", ondelete="CASCADE"), index=True
    )
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    label: Mapped[str] = mapped_column(String(60), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    criteria: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(20), default=EvidenceStatus.PROVISIONAL)

    __table_args__ = (
        UniqueConstraint("framework_version_id", "level", name="uq_level_version_level"),
        CheckConstraint("level >= 1 AND level <= 6", name="level_range"),
    )


class JobRole(Base, TimestampMixin):
    __tablename__ = "job_roles"

    id: Mapped[uuid.UUID] = uuid_pk()
    framework_version_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("framework_versions.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    cadre: Mapped[str | None] = mapped_column(String(60))
    grade: Mapped[str | None] = mapped_column(String(40))
    evidence_status: Mapped[str] = mapped_column(String(20), default=EvidenceStatus.PROVISIONAL)
    review_status: Mapped[str] = mapped_column(String(16), default=ReviewStatus.PENDING)
    source_ref: Mapped[str | None] = mapped_column(String(255))

    requirements: Mapped[list["RoleCompetencyRequirement"]] = relationship(
        back_populates="job_role", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("framework_version_id", "code", name="uq_role_version_code"),)


class RoleCompetencyRequirement(Base, TimestampMixin):
    __tablename__ = "role_competency_requirements"

    id: Mapped[uuid.UUID] = uuid_pk()
    job_role_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("job_roles.id", ondelete="CASCADE"), index=True
    )
    competency_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("competencies.id", ondelete="CASCADE"), index=True
    )
    required_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    importance: Mapped[int] = mapped_column(SmallInteger, default=3, nullable=False)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(20), default=EvidenceStatus.PROVISIONAL)
    review_status: Mapped[str] = mapped_column(String(16), default=ReviewStatus.PENDING)
    rationale: Mapped[str | None] = mapped_column(Text)

    job_role: Mapped[JobRole] = relationship(back_populates="requirements")
    competency: Mapped[Competency] = relationship()

    __table_args__ = (
        UniqueConstraint("job_role_id", "competency_id", name="uq_role_competency"),
        CheckConstraint("importance >= 1 AND importance <= 5", name="importance_range"),
        CheckConstraint("required_level >= 1 AND required_level <= 6", name="req_level_range"),
    )


class CompetencyPrerequisite(Base, TimestampMixin):
    __tablename__ = "competency_prerequisites"

    id: Mapped[uuid.UUID] = uuid_pk()
    competency_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("competencies.id", ondelete="CASCADE"), index=True
    )
    prerequisite_competency_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("competencies.id", ondelete="CASCADE"), index=True
    )
    min_level: Mapped[int] = mapped_column(SmallInteger, default=2, nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(20), default=EvidenceStatus.PROVISIONAL)

    __table_args__ = (
        UniqueConstraint("competency_id", "prerequisite_competency_id", name="uq_prereq_pair"),
        CheckConstraint("competency_id <> prerequisite_competency_id", name="no_self_prereq"),
    )
