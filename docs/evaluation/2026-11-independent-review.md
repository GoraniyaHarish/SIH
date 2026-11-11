# PRAMANA — Independent SIH 26101 Review & Stabilization

**Review date:** 11 November 2026  
**Repository:** `GoraniyaHarish/SIH`  
**Reviewed baseline:** `main` at `1d54f2770b124f986bd28f22157764c3cbed90a2`  
**Stabilization branch:** `pramana-judge-review-stabilization`  
**Review status:** Static repository review plus targeted code changes. Runtime tests, Docker build and browser E2E have **not** been run in this review environment.

> This is an independent assessment rubric created for this review. It is not an official SIH marking scheme and does not predict selection or winning.

---

## 1. Problem-statement research

### 1.1 What SIH 26101 asks for

The SIH 26101 listing identifies MoSPI and the Data Informatics & Innovation Division (DIID), under Software / Smart Education. Its stated purpose is an AI-enabled learning platform that identifies competency gaps, recommends personalized training through the iGOT Karmayogi ecosystem, and generates quizzes/MCQs from uploaded learning materials.

The full problem description surfaced in the SIH 2026 problem-statement listing mirrored by an academic institution. The official SIH problem-statement directory is linked below, but the exact SIH 26101 record was not independently retrieved from the official portal during this review. Therefore, the full text is treated as **secondary-source transcription**, not as a directly verified official portal capture.

Key requirements in that listing:

- Create a comprehensive employee competency profile from designation, department, role, current assignment, qualifications, experience and previous training.
- Assess competencies against a predefined Official Statistics framework.
- Cover statistical, technical, digital-governance, behavioural and managerial competencies.
- Identify competency gaps and recommend personalized pathways using role, experience, learning history, departmental priorities and future requirements.
- Integrate with iGOT to retrieve course catalogues, recommend courses, monitor enrolment/completion and update competency scores.
- Include NSSTA TPAC-recommended training programmes in the recommendation scope.
- Provide AI virtual assistance, adaptive assessment, quizzes, feedback and multilingual learning support.
- Generate MCQs and quizzes from uploaded learning material, including documents, presentations and videos.
- Provide learner and administrator dashboards, including competencies, gaps, learning hours, training effectiveness, emerging skills and predictive insights.
- Provide a secure, scalable, cloud-ready and interoperable application, including RBAC and SSO.

### 1.2 Verified domain context from government sources

- MoSPI's March 2025 statement on the Statistical Training Needs Assessment (STA) Survey says the survey evaluates the training ecosystem, identifies critical gaps—particularly in emerging areas—and prioritizes required skills. It also confirms NSSTA training in Official Statistics and advanced technologies such as AI, big data analytics and machine learning, with use of iGOT Karmayogi. Source: https://www.pib.gov.in/PressReleseDetailm.aspx?PRID=2114354&lang=2&reg=48
- MoSPI's 22 October 2026 announcement describes a committee report on future-ready ISS capacity building aligned to Mission Karmayogi's competency-based framework. It describes role-linked competency-based capacity building across functional, domain and behavioural areas, with NSSTA as a key institutional anchor. Source: https://www.pib.gov.in/PressReleasePage.aspx?PRID=2327053&lang=1&reg=3
- NSSTA's public documents page lists TPAC meeting minutes and training-related documents. Source: https://nssta.gov.in/document
- NSSTA's public offerings page lists induction and refresher training programmes. Source: https://nssta.gov.in/offerings
- The official SIH 2026 problem-statement directory is https://sih.gov.in/sih2026PS

**Important implication:** PRAMANA should not invent a generic skill framework and call it the approved MoSPI framework. It should provide provenance for each competency and map to approved role/capability frameworks only when the underlying documents are available and validated by domain experts. The newly announced MoSPI capacity-building report is highly relevant and should be acquired and mapped when its full report becomes publicly available.

### 1.3 Problem interpretation

The actual problem is not simply “make courses easier to find.” It is a workforce capability intelligence problem:

1. Establish role and assignment context.
2. Determine expected capability using an authoritative framework.
3. Establish current capability using evidence, not only self-rating.
4. Identify and explain gaps.
5. Select suitable learning interventions from iGOT and NSSTA TPAC programmes.
6. Monitor enrolment, participation and completion.
7. Measure learning and capability change.
8. Feed evidence back into the profile and next development plan.

PRAMANA's differentiator should be the traceable connection between **role → expected competency → evidence-based gap → relevant training → reassessment → measurable improvement**.

---

## 2. Repository understanding

The repository is a React/TypeScript/Vite frontend and a FastAPI/Python backend with PostgreSQL/pgvector, SQLAlchemy, Alembic, Redis support, a provider-neutral AI HTTP client, Docker Compose and backend tests.

The source review inspected the README, Docker and environment configuration, backend API routers, authentication, configuration, database models, competency/gap/recommendation services, document ingestion, RAG, quiz generation and grading, integration adapters, seed script, test suite and architecture/security/test documentation. This was a source-level review; not every frontend component or every line of every file was executed.

### Feature status matrix

| SIH capability | Repository evidence | Assessment |
|---|---|---|
| Employee profile and role | User model, profile API, job-role and department relationships | **Partial** — role/department/designation exist; completeness against all requested profile attributes must be checked and expanded |
| Competency framework | Versioned domains, competencies, skills, proficiency scale, role requirements and review workflow | **Implemented as a configurable/provisional framework**; not an officially approved MoSPI framework |
| Competency assessment | Self, structured and assessor-reviewed assessment paths | **Implemented**; AI-based assessment should not be claimed merely because quiz generation uses AI |
| Automated skill-gap analysis | Deterministic gap engine with documented priority formula and explanations | **Implemented** |
| Personalized learning recommendations | Recommendation service and learning plans | **Implemented for available local catalogue**; quality and coverage depend on framework and catalogue provenance |
| iGOT catalogue, enrolment and completion sync | Adapter boundary only; no verified authorized production API integration | **Not implemented as live integration** |
| NSSTA TPAC programme recommendations | Generic NSSTA adapter boundary; no demonstrated TPAC programme catalogue mapping/sync | **Not implemented end to end** |
| Upload-based MCQ/quiz generation | Document processing, quiz generation/validation, draft-review-publish-attempt-grade lifecycle | **Implemented**, with deterministic fallback clearly identified |
| Grounded AI assistant | RAG, SQL access filters, citations, refusal path, keyword/extractive fallback | **Implemented with limitations**; citation ID validation is not proof of semantic entailment |
| Learner/admin dashboards | Learner, manager and admin analytics routes and pages | **Implemented in current prototype**; predictive analytics and training-effectiveness attribution need stronger evidence |
| Learning hours and course history | Learning/enrolment data and dashboard structures | **Partial** — validate data provenance and full SIH reporting semantics |
| Multilingual learning | No verified complete multilingual workflow | **Not implemented / unverified** |
| Virtual labs / hands-on modules | No verified sandbox or lab execution system | **Not implemented** |
| SSO | No verified government SSO integration | **Not implemented** |
| RBAC and access isolation | Backend role dependencies, scoped analytics, document access filters and tests | **Implemented and meaningfully tested in the reported suite** |
| Production deployment | Dockerfiles, Compose, migrations and health checks exist | **Partial** — deployment has not been verified by a Docker build/start in this review |
| Auditability | Audit service and audit records | **Implemented**, but production DB-level immutability and operational retention need work |

---

## 3. Independent judge assessment

### Score: 72 / 100

| Dimension | Max | Score | Reason |
|---|---:|---:|---|
| Problem alignment | 15 | 12 | The core role-to-gap-to-learning cycle is represented, but live iGOT and TPAC recommendations are central explicit requirements and are not delivered |
| Competency intelligence | 15 | 11 | Versioned framework, evidence provenance, gap calculations and plans are a strong foundation; official framework validation and profile completeness remain open |
| AI and assessment quality | 15 | 10 | RAG and quiz workflow are substantive; semantic citation support, external model evaluation and truly adaptive assessment need stronger proof |
| iGOT / NSSTA ecosystem | 15 | 2 | Adapter boundaries are not the same as course catalogue, enrolment, completion or TPAC integration |
| UX and learner workflow | 10 | 7 | Coherent custom design and role dashboards; multilingual, hands-on labs and complete course-learning feedback loop remain limited |
| Security and privacy | 10 | 7 | Strong RBAC, upload controls and SQL retrieval filters; production cookie default, outbound AI data policy and path containment required hardening |
| Architecture and maintainability | 5 | 4 | Modular monolith is appropriate for the team; architecture is reasonably separated |
| Testing and quality evidence | 10 | 8 | Reported 102 tests cover important flows; this review did not rerun them, and Docker/E2E/dependency checks remain outstanding |
| Demonstration readiness | 3 | 2 | Many core workflows can be demonstrated from the documented implementation; external AI and government integrations must be presented honestly |
| Evidence and claims discipline | 2 | 1 | Evidence-status distinctions are a strength; some README claims about citations and shared demo credentials needed correction |
| **Total** | **100** | **72** | **Strong prototype foundation; key ecosystem requirements and production verification remain material gaps** |

### What is strongest

1. Competency gap calculations are explainable rather than opaque.
2. Assessment evidence has provenance labels; self-rating is not silently treated as verified expertise.
3. The quiz lifecycle is more than a “generate questions” button: draft, validation, review, publish, attempt and bounded competency evidence are represented.
4. Document authorization is enforced in the retrieval query path, not only in the UI.
5. The integration status model is honest and does not fabricate iGOT or NSSTA success.
6. The design system is distinct from a generic dark AI dashboard.

### What could cause a judge to mark it down

1. “Seamless iGOT integration” is not present as a live verified capability.
2. NSSTA TPAC programmes are not demonstrably discoverable and recommended as actual programmes.
3. A provisional framework is not an approved Official Statistics competency framework.
4. AI-based competency assessment is not fully demonstrated; deterministic gap scoring and AI MCQ generation are different capabilities.
5. Predictive analytics, multilingual support, virtual labs and SSO are not evidenced as working end-to-end.
6. Runtime deployment and live user journeys have not been independently verified in this review.
7. Citation markers are checked against retrieved source IDs, but that does not prove that each claim is entailed by its cited passage.

---

## 4. Confirmed code-level findings and changes on the stabilization branch

| Finding on baseline | Change made on stabilization branch | Verification status |
|---|---|---|
| Backend Dockerfile had duplicated `useradd --create-home` command | Corrected to one user creation command; upload directory is created and ownership assigned before switching to non-root user | Static diff reviewed; Docker build not run |
| File containment used string-prefix comparison, which can accept sibling-prefix paths | Uses resolved `Path.is_relative_to(root)` and rejects root itself; added tests for sibling-prefix and symlink escapes | Code and tests committed; tests not run |
| Production cookie default was insecure; Compose default was false | Production settings now reject insecure cookies and wildcard CORS; Compose defaults secure cookies to true | Static diff reviewed; settings tests not run |
| External AI document sharing was enabled by default | Default is false; ingestion does not send document chunks for embeddings unless enabled; RAG does not send query text for embeddings unless explicitly allowed | Static diff reviewed; test coverage still needed |
| README contained shared demo credentials; seed script contained a hard-coded shared password | Removed password/table from README; seed now requires a unique `DEMO_PASSWORD` environment variable of at least 12 characters before database writes | Static diff reviewed; seed execution not run |
| README overstated citation verification | Clarified that source-ID validation does not establish semantic entailment | Documentation change reviewed |
| Demo seeding bypassed the outbound-AI opt-in when an AI provider was configured | Updated `seed_demo_documents()` to require both provider availability and `AI_SEND_DOCUMENTS_EXTERNALLY=true` before embedding demo document text | Static source change reviewed; regression test/runtime execution still pending |

### Security caveat

Removing a credential from the current README and seed source does **not** erase it from previous Git commits, clones, forks or screenshots. Any credential that was previously exposed must be treated as compromised and rotated. Revoke existing sessions and refresh tokens for affected demo accounts where possible. Do not reuse the old demo password.

### Important AI privacy boundary

The external AI setting now defaults to false and gates both document embeddings and RAG query embeddings. The quiz generator already checks the same setting before invoking external generation. Keep this setting disabled unless the data-sharing decision, provider terms, data classification and approval process explicitly permit outbound content. A configured API key is not itself authorization to transmit official or personal data.

---

## 5. Priority roadmap

### P0 — Stabilization and safety

1. Run the complete backend suite on the stabilization branch and fix regressions.
2. Add tests for production configuration validation, outbound AI opt-in, and the new storage containment cases.
3. Run `pip-audit` and `npm audit`; triage findings rather than blindly upgrading.
4. Verify Docker build and Compose startup from a clean database/volume.
5. Rotate previously exposed demo credentials and revoke sessions.
6. Verify the deployed reverse proxy uses HTTPS and forwards headers only from trusted proxies.
7. Review refresh-cookie CSRF exposure and add explicit CSRF protection if cookie-authenticated unsafe requests can be triggered cross-site in the actual deployment model.

### P1 — Close the SIH core gaps

1. **Framework provenance:** add an importable framework source register with source URL, document/version, publication date, effective date, evidence status, approving authority and review history.
2. **Official role mapping:** obtain the full MoSPI capacity-building committee report announced on 22 October 2026 and any approved competency framework; map role expectations only after source validation.
3. **NSSTA TPAC:** create a TPAC programme catalogue model with programme title, target role/cadre, competency mapping, eligibility, delivery mode, schedule, source reference and publication date. Start with manually curated, source-cited public records; label them as public-source catalogue entries, not live integration.
4. **iGOT connector:** implement only against an authorized API specification and credentials. Until then, provide a clearly labelled external-course reference workflow rather than a simulated sync.
5. **Evidence-based assessment:** distinguish self-assessment, structured assessment, assessor validation, course completion and demonstrated task evidence. Do not let course completion alone certify proficiency.
6. **Learning outcome loop:** capture pre/post assessment, learning time, activity completion and assessor evidence, then show competency change with method and confidence.
7. **Role profile completeness:** add assignment, qualifications, experience and previous training fields only with clear data minimization and authorization rules.

### P2 — Competitive differentiators

1. Recommendation explanations that show exactly which gap, role requirement and course competency mapping caused each recommendation.
2. TPAC and iGOT recommendation ranking with fit, eligibility, recency and availability factors.
3. Claim-level RAG support checks and adversarial evaluation sets; source-ID validity alone is insufficient.
4. Multilingual interface/content support with language quality checks.
5. A small, safe statistical coding lab (e.g. sandboxed Python/R exercises) only if execution isolation can be implemented securely.
6. Cohort analytics with privacy suppression and defensible training-effectiveness metrics.
7. Exportable individual development plans and administrator capacity-building reports.

### P3 — Optional after core requirements

- SSO once the target identity provider and authorization are documented.
- AI provider failover.
- Realtime assistant streaming.
- More advanced predictive analytics, only after enough validated longitudinal data exists.

---

## 6. Recommended SIH demonstration narrative

Demonstrate one learner journey with a real source and traceable evidence:

1. Sign in as a learner and show the profile's role, department and evidence status.
2. Open the role competency profile and show where the expected levels came from.
3. Complete a structured assessment; distinguish self-declared values from assessor-verified values.
4. Show the gap engine's formula, ranked gaps and explanations.
5. Open a recommended local course or a clearly labelled NSSTA public-source TPAC programme entry.
6. Upload a statistical learning document and show processing status.
7. Ask the grounded assistant a question; open the cited page/chunk and explain the limits of citation verification.
8. Generate a quiz, show validation, draft review and publish.
9. Attempt the quiz and show score/explanation.
10. Revisit the competency profile and show the bounded evidence update and new recommendation.
11. Finish with the admin dashboard, privacy suppression and honest integration status.

Do not claim live iGOT synchronization, official MoSPI competency approval, predictive accuracy or government compliance unless independently evidenced.

---

## 7. Judge questions to prepare

- What is the difference between PRAMANA and iGOT Karmayogi itself?
- How do you know the required competency level for a role?
- Who approves the competency framework?
- How is self-assessment distinguished from actual proficiency?
- How do you prevent a high quiz score from falsely certifying expertise?
- How does a recommendation map to a competency gap?
- How will you recommend an NSSTA TPAC programme?
- What happens when iGOT APIs or credentials are unavailable?
- How do you ensure an employee cannot retrieve another employee's private documents?
- What evidence proves that an AI answer is supported by a source?
- What data is sent to the external AI provider?
- How will the system measure actual improvement rather than course completion?
- Which features are live, provisional, simulated or not implemented?

---

## 8. Verification record and limitations

- Added `.github/workflows/ci.yml` to run backend tests against PostgreSQL + pgvector, frontend production builds, Docker image builds, and advisory Python/npm dependency audits.
- GitHub Actions run `42956672630`: backend and frontend jobs completed successfully. Backend reached 100% with 109 test progress markers; frontend install and production build passed.
- GitHub Actions run `42957102354` after dependency upgrades: backend tests passed; frontend production build passed; backend and frontend Docker image builds passed; Python dependency audit passed with no known vulnerabilities reported by pip-audit.
- The same run's npm audit failed on two moderate React Router advisories affecting the installed 6.x line. The upstream patched release is 7.18.x. This requires a deliberate major-version migration and lockfile regeneration; it remains an open security task, not a waived finding.
- Upgraded backend pins: FastAPI 0.143.0, Starlette 1.3.1, PyJWT 2.15.1, pypdf 7.0.1, python-multipart 0.0.33, pytest 9.2.0 and pytest-asyncio 1.4.1.post1. The follow-up backend CI passed with these versions.
- Set an explicit pytest asyncio fixture loop scope. The updated backend test run still reports Starlette deprecation warnings about httpx TestClient usage and the legacy 422 status constant; these are cleanup items, not test failures.
- A further CI change now prints verbose per-test output and an explicit pytest summary rather than only progress dots. Its new run is pending; the 109 count above comes from the completed prior run's progress output (72 + 37 markers).
- Docker image builds passed, but full Docker Compose orchestration against a clean database/volume, browser-based user journeys, live deployment verification, penetration testing and government integration tests have not been performed.
- NSSTA/iGOT public-source research is recorded in `docs/research/government-learning-ecosystem-evidence.md`. It deliberately distinguishes public catalogue evidence from authenticated integration and approved competency mapping.
- Previously exposed demo credentials must be rotated and active sessions revoked. Removing them from current files does not erase Git history, clones, forks or screenshots.
- The official SIH portal's exact SIH 26101 record was not independently retrieved in this review; the problem text used in the report was corroborated through a secondary listing. Reconfirm the original portal record before final presentation.
- No official approval of PRAMANA's provisional competency framework is claimed.

## 9. Sources

1. SIH 2026 official problem-statement directory: https://sih.gov.in/sih2026PS
2. SIH 26101 secondary listing/transcription: https://sih2026.vuce.in/ps/SIH26101
3. PIB / MoSPI, “STA Survey Report”, 24 March 2025: https://www.pib.gov.in/PressReleseDetailm.aspx?PRID=2114354&lang=2&reg=48
4. PIB / MoSPI, “Towards Future-Ready Data Leaders: Comprehensive Capacity Building recommendations by Committee in MoSPI”, 22 October 2026: https://www.pib.gov.in/PressReleasePage.aspx?PRID=2327053&lang=1&reg=3
5. NSSTA documents / TPAC: https://nssta.gov.in/document
6. NSSTA training offerings: https://nssta.gov.in/offerings
7. PIB / MoSPI, Year-end review 2025: https://www.pib.gov.in/PressReleasePage.aspx?PRID=2208162&lang=1&reg=3
