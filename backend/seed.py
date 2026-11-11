"""Create the local framework, sample catalogue and demonstration user cohort.

Framework records are provisional; sample courses, documents and accounts are demonstration data.
The caller must supply a private DEMO_PASSWORD. Production seeding requires an explicit override.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import uuid

from sqlalchemy import select

from app.ai.provider import AiUnavailable, ai
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.assessment import (
    Assessment, AssessmentResponse, CompetencyState, PlanItem, LearningPlan, Notification,
)
from app.models.base import (
    AssessmentMethod, AssessmentStatus, EnrolmentStatus, EvidenceStatus, ReviewStatus, Role,
)
from app.models.competency import (
    Competency, CompetencyDomain, CompetencyPrerequisite, FrameworkVersion, JobRole,
    ProficiencyLevel, RoleCompetencyRequirement, Skill,
)
from app.models.learning import (
    Course, CourseCompetency, CourseMaterial, Document, DocumentChunk, Enrolment,
)
from app.models.users import Department, User
from app.services import framework_data as fd
from app.services.documents import chunk_document, extract
from app.services.ingest import store_file

DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "")

# Demonstration cohort. The spread of levels is chosen to produce a realistic mix of gaps.
DEMO_USERS = [
    # email, name, role, department, job role code, designation, levels overrides
    ("admin@pramana.example.com", "Ananya Raghavan", Role.ADMIN, "Statistics Wing",
     "ISS-SURVEY", "Director (Statistics)", {}),
    ("assessor@pramana.example.com", "Vikram Deshpande", Role.ASSESSOR, "Statistics Wing",
     "DQOFF", "Deputy Director (Quality Assurance)", {}),
    ("manager@pramana.example.com", "Meera Krishnan", Role.MANAGER, "Survey Operations",
     "SO", "Regional Statistical Officer", {}),
    ("so.north@pramana.example.com", "Rajesh Kumar", Role.MANAGER, "Survey Operations",
     "SO", "Zonal Statistical Officer", {}),
    ("learner.iss@pramana.example.com", "Priya Nair", Role.LEARNER, "Survey Operations",
     "ISS-SURVEY", "Assistant Director (ISS)", {}),
    ("learner.jso@pramana.example.com", "Arun Sharma", Role.LEARNER, "Field Operations",
     "JSO", "Junior Statistical Officer", {}),
    ("learner.analyst@pramana.example.com", "Fatima Sheikh", Role.LEARNER, "Data Processing",
     "ANALYST", "Statistical Analyst", {}),
    ("learner.na@pramana.example.com", "Suresh Iyer", Role.LEARNER, "National Accounts",
     "ISS-NA", "Assistant Director (NA)", {}),
    ("learner.price@pramana.example.com", "Deepa Menon", Role.LEARNER, "Price Statistics",
     "ISS-PRICE", "Statistical Officer (Prices)", {}),
    ("learner.dq@pramana.example.com", "Nikhil Bhatt", Role.LEARNER, "Quality Assurance",
     "DQOFF", "Data Quality Officer", {}),
    ("learner.jso2@pramana.example.com", "Kavita Rao", Role.LEARNER, "Field Operations",
     "JSO", "Statistical Investigator", {}),
    ("learner.jso3@pramana.example.com", "Manoj Verma", Role.LEARNER, "Field Operations",
     "JSO", "Statistical Investigator", {}),
    ("learner.analyst2@pramana.example.com", "Aisha Khan", Role.LEARNER, "Data Processing",
     "ANALYST", "Statistical Analyst", {}),
    ("learner.trainer@pramana.example.com", "Gopal Subramanian", Role.LEARNER, "Training Division",
     "TRAINER", "Training Officer", {}),
]

DEMO_PROFICIENCY = {
    # email -> {competency_code: declared_level}
    "learner.iss@pramana.example.com": {
        "STAT.01": 4, "STAT.02": 3, "STAT.03": 3, "SAMP.01": 3, "SAMP.02": 2,
        "SAMP.03": 4, "EST.01": 3, "EST.02": 2, "EST.03": 2, "COMP.01": 3,
        "DQ.02": 2, "GOV.01": 3,
        "NA.01": 1, "PRICE.01": 1, "GIS.01": 1, "AIDATA.01": 1, "COMM.02": 2,
    },
    "learner.jso@pramana.example.com": {
        "STAT.01": 3, "STAT.02": 2, "STAT.03": 2, "SAMP.03": 2, "SAMP.04": 2,
        "COMP.02": 2, "COMM.01": 2, "GOV.03": 2,
        "SAMP.01": 1, "EST.01": 1, "DQ.01": 1,
    },
    "learner.analyst@pramana.example.com": {
        "STAT.01": 3, "EST.01": 3, "EST.02": 2, "EST.03": 2, "COMP.01": 4,
        "COMP.02": 3, "COMP.03": 4, "ECON.01": 2, "COMM.01": 3,
        "ECON.02": 1, "SAMP.01": 2, "AIDATA.02": 1,
    },
    "learner.na@pramana.example.com": {
        "STAT.01": 4, "NA.01": 4, "NA.02": 3, "EST.01": 3, "ECON.01": 3,
        "ECON.02": 2, "COMP.01": 2, "DQ.02": 3, "GOV.03": 4,
        "PRICE.01": 1, "AIDATA.01": 1,
    },
    "learner.price@pramana.example.com": {
        "STAT.01": 3, "PRICE.01": 4, "PRICE.02": 3, "EST.01": 3, "DQ.01": 4,
        "DQ.03": 3, "COMM.02": 2, "COMP.01": 2,
        "EST.02": 2, "NA.01": 1, "SAMP.01": 2,
    },
    "learner.dq@pramana.example.com": {
        "STAT.01": 3, "STAT.03": 3, "DQ.01": 4, "DQ.02": 4, "DQ.03": 3,
        "EST.02": 2, "COMM.01": 3, "COMM.02": 3,
        "SAMP.01": 2, "AIDATA.03": 1, "GOV.01": 2,
    },
    "learner.jso2@pramana.example.com": {
        "STAT.01": 2, "STAT.02": 1, "STAT.03": 2, "SAMP.03": 2, "SAMP.04": 1,
        "COMP.02": 1, "COMM.01": 1, "GOV.03": 3,
        "SAMP.01": 1, "DQ.01": 1, "EST.01": 2,
    },
    "learner.jso3@pramana.example.com": {
        "STAT.01": 3, "STAT.02": 2, "STAT.03": 3, "SAMP.03": 3, "SAMP.04": 2,
        "COMP.02": 2, "COMM.01": 2, "GOV.03": 3,
        "SAMP.01": 2, "DQ.01": 2, "EST.01": 2,
    },
    "learner.analyst2@pramana.example.com": {
        "STAT.01": 3, "EST.01": 3, "EST.02": 3, "EST.03": 2, "COMP.01": 3,
        "COMP.02": 3, "COMP.03": 3, "ECON.01": 3, "ECON.02": 2, "COMM.01": 2,
        "SAMP.01": 3, "AIDATA.02": 2,
    },
    "learner.trainer@pramana.example.com": {
        "STAT.01": 4, "STAT.02": 3, "GOV.02": 4, "GOV.01": 3, "GOV.03": 4,
        "DQ.01": 3, "COMM.02": 4, "SAMP.01": 3, "EST.01": 2,
        "AIDATA.03": 2, "NA.01": 1, "PRICE.01": 1,
    },
}

DEPARTMENTS = [
    ("Statistics Wing", "SW", "Coordination, ISS cadre management and statistical policy."),
    ("Survey Operations", "SO", "Field survey design, supervision and data collection."),
    ("Field Operations", "FO", "Regional and zonal field data collection units."),
    ("Data Processing", "DP", "Data validation, estimation support and statistical computing."),
    ("National Accounts", "NAD", "Compilation of national accounts aggregates."),
    ("Price Statistics", "PRS", "Consumer and producer price indices."),
    ("Quality Assurance", "QA", "Data quality, metadata and dissemination standards."),
    ("Training Division", "TRG", "Capacity building, training needs analysis and curriculum."),
]


def _get_or_create_department(db, name, code, description) -> Department:
    dept = db.scalars(select(Department).where(Department.name == name)).first()
    if dept:
        return dept
    dept = Department(name=name, code=code, description=description)
    db.add(dept)
    db.flush()
    return dept


def seed_framework(db) -> FrameworkVersion:
    existing = db.scalars(
        select(FrameworkVersion).where(FrameworkVersion.label == fd.FRAMEWORK_LABEL)
    ).first()
    if existing:
        return existing

    fw = FrameworkVersion(
        label=fd.FRAMEWORK_LABEL, notes=fd.FRAMEWORK_NOTES,
        evidence_status=EvidenceStatus.PROVISIONAL.value, is_active=True,
    )
    db.add(fw)
    db.flush()

    for level in fd.LEVELS:
        db.add(
            ProficiencyLevel(
                framework_version_id=fw.id, level=level["level"], label=level["label"],
                summary=level["summary"], criteria=level["criteria"],
                evidence_status=EvidenceStatus.PROVISIONAL.value,
            )
        )

    code_to_competency: dict[str, Competency] = {}
    for order, domain_def in enumerate(fd.DOMAINS):
        domain = CompetencyDomain(
            framework_version_id=fw.id, code=domain_def["code"], name=domain_def["name"],
            description=domain_def["description"], kind=domain_def["kind"],
            sort_order=order, evidence_status=EvidenceStatus.PROVISIONAL.value,
            source_ref=domain_def.get("source_ref"),
        )
        db.add(domain)
        db.flush()
        for c_index, (code, name, description, rationale, skills) in enumerate(
            domain_def["competencies"]
        ):
            comp = Competency(
                domain_id=domain.id, code=code, name=name, description=description,
                rationale=rationale, sort_order=c_index,
                evidence_status=EvidenceStatus.PROVISIONAL.value,
                review_status=ReviewStatus.PENDING.value,
                source_ref=domain_def.get("source_ref"),
            )
            db.add(comp)
            db.flush()
            code_to_competency[code] = comp
            for s_index, statement in enumerate(skills):
                db.add(Skill(competency_id=comp.id, statement=statement, sort_order=s_index))

    for comp_code, prereq_code, min_level in fd.PREREQUISITES:
        db.add(
            CompetencyPrerequisite(
                competency_id=code_to_competency[comp_code].id,
                prerequisite_competency_id=code_to_competency[prereq_code].id,
                min_level=min_level, evidence_status=EvidenceStatus.PROVISIONAL.value,
            )
        )

    for role_def in fd.JOB_ROLES:
        role = JobRole(
            framework_version_id=fw.id, code=role_def["code"], title=role_def["title"],
            description=role_def["description"], cadre=role_def.get("cadre"),
            grade=role_def.get("grade"), evidence_status=EvidenceStatus.PROVISIONAL.value,
            review_status=ReviewStatus.PENDING.value,
            source_ref="Synthesised from public MoSPI/NSSTA role descriptions",
        )
        db.add(role)
        db.flush()
        for comp_code, required, importance, critical in role_def["reqs"]:
            db.add(
                RoleCompetencyRequirement(
                    job_role_id=role.id, competency_id=code_to_competency[comp_code].id,
                    required_level=required, importance=importance, is_critical=critical,
                    evidence_status=EvidenceStatus.PROVISIONAL.value,
                    rationale=f"Required for {role_def['title']} duties.",
                )
            )
    db.commit()
    print(f"  framework {fd.FRAMEWORK_LABEL}: {len(code_to_competency)} competencies, "
          f"{len(fd.JOB_ROLES)} job roles")
    return fw


def seed_courses(db, admin: User) -> list[Course]:
    courses: list[Course] = []
    comp_by_code = {c.code: c for c in db.scalars(select(Competency))}
    for course_def in fd.COURSES:
        existing = db.scalars(select(Course).where(Course.code == course_def["code"])).first()
        if existing:
            courses.append(existing)
            continue
        course = Course(
            code=course_def["code"], title=course_def["title"], summary=course_def["summary"],
            description=course_def["summary"], objectives=course_def["objectives"],
            prerequisites=[], provider=course_def["provider"], level=course_def["level"],
            duration_minutes=course_def["duration_minutes"], tags=course_def["tags"],
            # Seeded catalogue content is explicitly demonstration data, never attributed to iGOT.
            evidence_status=EvidenceStatus.DEMONSTRATION.value,
            created_by_id=admin.id,
        )
        db.add(course)
        db.flush()
        for comp_code, covers in course_def["competencies"]:
            comp = comp_by_code.get(comp_code)
            if comp:
                db.add(
                    CourseCompetency(
                        course_id=course.id, competency_id=comp.id, covers_level=covers,
                        evidence_status=EvidenceStatus.DEMONSTRATION.value,
                    )
                )
        for index, (title, kind, minutes) in enumerate(course_def["materials"]):
            db.add(
                CourseMaterial(
                    course_id=course.id, title=title, kind=kind, duration_minutes=minutes,
                    sort_order=index,
                    description="Demonstration material placeholder for the prototype catalogue.",
                )
            )
        courses.append(course)
    db.commit()
    print(f"  courses: {len(courses)}")
    return courses


def seed_demo_documents(db, admin: User) -> list[Document]:
    docs: list[Document] = []
    comp_by_code = {c.code: c for c in db.scalars(select(Competency))}
    for spec in fd.DEMO_DOCUMENTS:
        existing = db.scalars(
            select(Document).where(Document.title == spec["title"])
        ).first()
        if existing:
            docs.append(existing)
            continue

        data = spec["content"].encode("utf-8")
        stored_name, digest = store_file(data, spec["filename"])
        doc = Document(
            owner_id=admin.id, title=spec["title"], original_filename=spec["filename"],
            stored_name=stored_name, mime_type="text/plain", size_bytes=len(data),
            sha256=digest, visibility="organisation", status="completed",
            topic_hint=spec["topic"],
            competency_ids=[str(comp_by_code[c].id) for c in spec["competencies"]
                            if c in comp_by_code],
        )
        db.add(doc)
        db.flush()

        extracted = extract(data, "text/plain")
        chunks = chunk_document(extracted)
        rows = [
            DocumentChunk(
                document_id=doc.id, ordinal=chunk.ordinal, page_from=chunk.page_from,
                page_to=chunk.page_to, section=chunk.section, content=chunk.content,
                token_estimate=max(1, len(chunk.content) // 4),
            )
            for chunk in chunks
        ]
        db.add_all(rows)
        db.flush()

        # Seeding must obey the same outbound-data policy as normal ingestion.
        # A configured provider is not permission to transmit document text.
        if ai.enabled and settings.ai_send_documents_externally:
            try:
                for start in range(0, len(rows), 16):
                    batch = rows[start:start + 16]
                    result = ai.embed([b.content for b in batch])
                    for row, vector in zip(batch, result.vectors, strict=True):
                        row.embedding = vector
                    doc.embedding_model = result.model
            except AiUnavailable as exc:
                print(f"  ! embeddings unavailable ({exc.error_class}); keyword search only")

        doc.page_count = extracted.page_count
        doc.char_count = extracted.char_count
        doc.chunk_count = len(rows)
        doc.processed_at = dt.datetime.now(dt.timezone.utc)
        db.commit()
        docs.append(doc)
    print(f"  demo documents: {len(docs)}")
    return docs


def seed_users(db, fw: FrameworkVersion, departments: dict[str, Department]) -> dict[str, User]:
    roles = {r.code: r for r in db.scalars(select(JobRole))}
    comp_by_code = {c.code: c for c in db.scalars(select(Competency))}
    users: dict[str, User] = {}

    for email, name, role, dept_name, role_code, designation, _ in DEMO_USERS:
        existing = db.scalars(select(User).where(User.email == email)).first()
        if existing:
            users[email] = existing
            continue
        user = User(
            email=email, full_name=name, password_hash=hash_password(DEMO_PASSWORD),
            role=role, department_id=departments[dept_name].id,
            job_role_id=roles[role_code].id if role_code in roles else None,
            designation=designation,
        )
        db.add(user)
        users[email] = user
    db.commit()

    # manager relationships for the manager-scope tests
    manager = users["manager@pramana.example.com"]
    for email in ("learner.jso@pramana.example.com", "learner.jso2@pramana.example.com",
                  "learner.jso3@pramana.example.com", "learner.iss@pramana.example.com"):
        if email in users and users[email].manager_id is None:
            users[email].manager_id = manager.id
    db.commit()

    # assessments + competency states for learners
    for email, levels in DEMO_PROFICIENCY.items():
        user = users.get(email)
        if user is None:
            continue
        if db.scalars(
            select(Assessment).where(Assessment.user_id == user.id).limit(1)
        ).first():
            continue
        assessment = Assessment(
            user_id=user.id, framework_version_id=fw.id,
            method=AssessmentMethod.SELF.value, status=AssessmentStatus.SUBMITTED.value,
            title="Baseline self-assessment",
            notes="Seeded demonstration assessment for evaluation of the gap engine.",
            submitted_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=14),
        )
        db.add(assessment)
        db.flush()
        for code, level in levels.items():
            comp = comp_by_code.get(code)
            if comp is None:
                continue
            db.add(
                AssessmentResponse(
                    assessment_id=assessment.id, competency_id=comp.id, declared_level=level,
                    confidence=3,
                    evidence_note="Self-reported from recent work experience.",
                )
            )
            db.add(
                CompetencyState(
                    user_id=user.id, competency_id=comp.id, level=float(level),
                    method=AssessmentMethod.SELF.value, confidence=3,
                    source_assessment_id=assessment.id,
                    assessed_at=assessment.submitted_at,
                )
            )
    db.commit()

    # enrolments to make analytics non-empty
    courses = list(db.scalars(select(Course)))
    learners = [u for e, u in users.items() if u.role == Role.LEARNER]
    for index, course in enumerate(courses[:8]):
        for l_index, learner in enumerate(learners[:6]):
            if (index + l_index) % 3 != 0:
                continue
            if db.scalars(
                select(Enrolment).where(
                    Enrolment.user_id == learner.id, Enrolment.course_id == course.id
                )
            ).first():
                continue
            materials = list(
                db.scalars(select(CourseMaterial).where(CourseMaterial.course_id == course.id))
            )
            completed = materials[: max(1, len(materials) // 2)]
            percent = int(100 * len(completed) / max(len(materials), 1))
            db.add(
                Enrolment(
                    user_id=learner.id, course_id=course.id,
                    status=EnrolmentStatus.COMPLETED.value if percent >= 100
                    else EnrolmentStatus.ENROLLED.value,
                    progress_percent=percent,
                    completed_material_ids=[str(m.id) for m in completed],
                    started_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=20 - index),
                    completed_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2)
                    if percent >= 100 else None,
                )
            )
    db.commit()
    print(f"  users: {len(users)} ({sum(1 for u in users.values() if u.role == Role.LEARNER)} learners)")
    return users


def seed_notifications(db, users: dict[str, User]) -> None:
    learner = users.get("learner.iss@pramana.example.com")
    if learner is None:
        return
    if db.scalar(select(Notification).where(Notification.user_id == learner.id).limit(1)):
        return
    db.add(
        Notification(
            user_id=learner.id, kind="assessment",
            title="Baseline assessment recorded",
            body="Your self-assessment has been submitted. Gaps are now calculable for your role.",
            link="/learner/gaps",
        )
    )
    db.add(
        Notification(
            user_id=learner.id, kind="plan",
            title="Learning pathway generated",
            body="A pathway has been created from your open competency gaps.",
            link="/learner/plan",
        )
    )
    db.commit()


def main() -> int:
    if len(DEMO_PASSWORD) < 12:
        print("Set DEMO_PASSWORD to a unique value of at least 12 characters before seeding.")
        return 2
    if settings.is_production and os.getenv("ALLOW_DEMO_SEED") != "1":
        print("Refusing to seed demonstration data in production. Set ALLOW_DEMO_SEED=1 to override.")
        return 1

    print("Seeding PRAMANA demonstration data...")
    db = SessionLocal()
    try:
        departments = {
            name: _get_or_create_department(db, name, code, desc)
            for name, code, desc in DEPARTMENTS
        }
        db.commit()

        fw = seed_framework(db)
        users = seed_users(db, fw, departments)
        admin = users["admin@pramana.example.com"]
        seed_courses(db, admin)
        seed_demo_documents(db, admin)
        seed_notifications(db, users)

        from app.services import recommend

        recalculated = 0
        for email, user in users.items():
            if user.role != Role.LEARNER or user.email not in DEMO_PROFICIENCY:
                continue
            recommend.ensure_plan(db, user, force=True)
            recalculated += 1
        db.commit()
        print(f"  learning plans: {recalculated}")
        print("\nUse the private DEMO_PASSWORD value you supplied when signing in. It is not echoed here.")
        for email, name, role, *_ in DEMO_USERS:
            print(f"  {role.value:<9} {email:<34} {name}")
        print("\nSeed complete.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
