# SIH 26101 — Research & Requirements Report

**Project codename:** PRAMANA (Sanskrit: *pramāṇa* — valid means of knowledge / evidence)
**Problem statement owner:** Ministry of Statistics and Programme Implementation (MoSPI)
**Category / Theme:** Software / Smart Education
**Research date:** 2026-11-07

---

## 1. Official problem statement (verbatim from sih.gov.in/sih2026PS)

Retrieved directly from the official SIH 2026 problem-statement listing page (row 165 of the
"Smart India Hackathon 2026" statement table):

> **SIH26101** — *Develop an AI enabled learning platform that identifies competency gaps,
> recommends personalized training through integration with the iGOT Karmayogi ecosystem, and
> capable of generating Quizzes and Multiple choice questions (MCQs) from uploaded learning
> materials to strengthen capacity building in India's Official Statistical System.*
>
> Ministry: **MoSPI** · Type: **Software** · Theme: **Smart Education** · Published: 5 October 2026

**Status: OFFICIAL / VERIFIED** (primary source: the SIH portal itself).
No assumptions are made beyond this sentence. The extended requirements below are derived from
the statement's three explicit capabilities plus our own product reasoning, and are labelled as
such.

### 1.1 Decomposition of the official statement into mandatory capabilities

| # | Capability stated in the PS | Our implementation |
|---|---|---|
| 1 | Identify competency gaps | Competency framework + assessment + deterministic gap engine (`services/gap.py`) |
| 2 | Recommend personalized training | Explainable rule-ranked recommender (`services/recommend.py`) + learning plan generator |
| 3 | Integration with iGOT Karmayogi ecosystem | Adapter boundary + truthful status surface (`integrations/`) |
| 4 | Generate quizzes and MCQs from uploaded learning materials | Source-grounded generation + validation pipeline (`services/quizgen.py`) |
| 5 | Strengthen capacity building in India's Official Statistical System | Domain taxonomy seeded with official-statistics subject areas |

---

## 2. Domain research: India's Official Statistical System (OSS)

### 2.1 Institutional landscape — VERIFIED

| Institution | Role | Source |
|---|---|---|
| **MoSPI** | Nodal ministry for official statistics; cadre controlling authority for the Indian Statistical Service (ISS) | mospi.gov.in — *ISS Cadre Deployment* document; *Compendium of Roles and Responsibilities of Divisions and Units of MoSPI* (25 Mar 2025) |
| **NSO (National Statistical Office)** | Statistical wing of MoSPI; formed by merging NSSO and CSO. Produces National Accounts (GDP), CPI, WPI, IIP, PLFS, HCES, ASUSE and other official series | MoSPI publications / PIB releases |
| **NSC (National Statistical Commission)** | Apex advisory/statistical-coordination body; sets statistical priorities and standards | MoSPI — *National Policy on Official Statistics* (draft, 17 May 2018); NSC reports |
| **NSSTA (National Statistical Systems Training Academy)** | Central Training Institute under MoSPI, Greater Noida; conducts training in Official Statistics for central/state statistical personnel and ISS/IES officer trainees | nssta.gov.in (*About Us*, *History*); PIB release on NSSTA Foundation Day 2026 |
| **iGOT Karmayogi** | Government digital learning platform under Mission Karmayogi (DoPT + Capacity Building Commission + Karmayogi Bharat SPV) | igotkarmayogi.gov.in; portal.igotkarmayogi.gov.in |

### 2.2 Statistical job roles that the platform must model

Derived from verified role descriptions in the MoSPI *Compendium of Roles and Responsibilities*
and the NSSTA *Reference Manual for ISS Probationary Officers*, cross-checked against public
descriptions of ISS/NSSO work:

- **Junior Statistical Officer / Statistical Investigator** — field data collection, CAPI/CAWI
  schedule administration, primary validation.
- **Statistical Officer (Sub-divisional / Regional / Zonal)** — survey supervision, sample
  allocation, scrutiny of schedules, quality audit of field work.
- **ISS Officer (JTS/STS) — Survey Design & Operations** — sampling design, instrument design,
  estimation methodology, survey documentation.
- **ISS Officer — National Accounts** — compilation of GDP/GVA estimates, SUT, base revision.
- **ISS Officer — Price & Industrial Statistics** — CPI/WPI/IIP methodology, item baskets,
  weighting, deflation.
- **Statistical Data Analyst** — estimation, imputation, weighting, statistical computing (R/Python),
  reproducibility.
- **Statistical Data Quality & Dissemination Officer** — metadata, quality dimensions, revision
  policy, dissemination standards, confidentiality.
- **Statistical Trainer / Capacity Building Officer** — training needs analysis, curriculum design,
  assessment.

**Status: CREDIBLE SECONDARY / PROVISIONAL.** These are *role archetypes* synthesised from public
official documents describing ISS/NSSO work. They are **not** an officially gazetted competency
framework. The application labels these mappings `PROVISIONAL` in the UI and API and requires an
authorised review to promote any mapping to `OFFICIAL`.

### 2.3 Competency framing — what is official and what is ours

| Item | Status |
|---|---|
| Mission Karmayogi uses a **FRAC** (Framework of Roles, Activities and Competencies) approach for capacity building | **VERIFIED** — ISTM publication *The Framework of Roles, Activities and Competencies*, DoPT/Mission Karmayogi |
| Mission Karmayogi competency taxonomy distinguishes **behavioural**, **functional** and **domain** competencies | **VERIFIED** (same FRAC source; CBC *Annual Capacity Building Plan* approach papers) |
| A published, machine-readable **MoSPI-specific competency dictionary with proficiency levels and job-role mappings available to the public** | **NOT FOUND / UNAVAILABLE.** We therefore model our own framework, explicitly marked provisional. |
| The specific competency list, 5-level proficiency scale and per-role required levels shipped in this prototype | **PROVISIONAL DESIGN ARTEFACT**, authored for this prototype, informed by the FRAC concept and by OSS subject matter. It is *not* an official MoSPI/DoPT framework. |

This distinction is enforced in code: every competency, role mapping and course carries an
`evidence_status` field (`OFFICIAL`, `PROVISIONAL`, `DEMONSTRATION`) that is rendered in the UI.

### 2.4 Learning subject areas prioritised (from official OSS work domains)

Official statistics, survey/sampling design, estimation theory, national accounts, price &
industrial statistics, data quality & metadata, economic statistics, statistical computing
(Python/R/SQL), econometrics, GIS/geospatial statistics, big data for official statistics,
responsible AI in statistics, and statistical communication/dissemination.

These are treated as **learning content domains**, not as an officially approved competency
framework.

---

## 3. Integration research: iGOT Karmayogi & NSSTA

### 3.1 What was checked

| Check | Result |
|---|---|
| Public iGOT Karmayogi site (igotkarmayogi.gov.in / portal.igotkarmayogi.gov.in) | Reachable, but login-gated; no public developer/API documentation surfaced |
| Public developer portal / API key self-service for iGOT | **Not found** |
| Documented public REST endpoints for iGOT course catalogue or learner records | **Not found** |
| Any published integration agreement / MoU permitting third-party sync | **Not found** |
| NSSTA course catalogue as machine-readable data/API | **Not found**; courses are published as web pages / PDF calendar |
| Authentication model for iGOT APIs | Not publicly documented; presumably government SSO / API gateway gated |
| SPARROW–APAR training-data integration | Referenced only in a third-party video/tutorial; **not** an accessible specification | 

### 3.2 Conclusion — HONEST INTEGRATION STATUS

> **No publicly documented, lawfully accessible iGOT Karmayogi or NSSTA API was found.**
> Therefore this prototype ships **adapter interfaces plus a verified status surface**, not a live
> sync. It will report `NOT_CONFIGURED` / `UNREACHABLE` / `AUTH_FAILED` truthfully, and it never
> fabricates iGOT records.

The integration layer implements:
- `IGOTAdapter` / `NSSTAAdapter` protocol with `health()`, `fetch_catalogue()`, `push_completion()`,
  `fetch_learner_record()`.
- An `HttpAdapter` that performs a **real** HTTP call against a configurable base URL + bearer
  token and reports the real outcome (status code, latency, error class).
- A `StatusService` that classifies: `NOT_CONFIGURED`, `UNREACHABLE`, `AUTH_FAILED`,
  `OK`, `DEGRADED`.
- Admin UI showing what was actually attempted and when, so a demonstration never implies live
  government connectivity.

**Activation path (documented, not claimed):** supply `IGOT_BASE_URL` + `IGOT_API_TOKEN` in the
environment; the same adapter code path then performs real requests. Any payload-shape change
required by the real gateway is confined to `integrations/igot.py`.

### 3.3 What is explicitly NOT done

- No invented iGOT course titles are presented as real. The catalogue includes
  `provider = "NSSTA (indicative)"`/`"iGOT Karmayogi (indicative)"` records **only** when their
  `evidence_status = DEMONSTRATION` and the UI shows a "Demonstration data" badge.
- No claim of MoSPI endorsement.

---

## 4. AI capability research

- **LLM + embeddings access:** an OpenAI-compatible endpoint is available in this environment and
  was **verified working** (chat completion and `text-embedding-3-small` 1536-dim embeddings both
  returned HTTP 200). The application is provider-neutral: `AI_PROVIDER`, `AI_BASE_URL`,
  `AI_API_KEY`, `AI_CHAT_MODEL`, `AI_EMBEDDING_MODEL` are all environment-driven.
- **Retrieval design:** pgvector 0.8.0 is available (verified) → HNSW index over 1536-dim
  embeddings; chunking ~900 chars with 120-char overlap, page-anchored metadata.
- **Grounding:** answers must cite retrieved chunk IDs; a post-generation citation verifier rejects
  citations whose chunk IDs were not in the retrieved set (prevents hallucinated citations).
- **Degraded mode:** if no AI credentials are configured, the assistant returns a deterministic
  extractive answer built from retrieved passages with citations, and quiz generation falls back to
  an extractive cloze generator whose items are flagged `extractive_fallback`. No silent failure.

---

## 5. Functional requirements (derived)

Traceable IDs used in tests and in the README feature matrix.

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Email+password auth, Argon2id hashing, short-lived access JWT + rotating refresh token, logout/revocation | Must |
| FR-02 | Backend-enforced RBAC for Learner / Administrator / Training Manager / Competency Assessor | Must |
| FR-03 | Org metadata: department, job role, designation | Must |
| FR-04 | Versioned competency framework: domains → competencies → skills, 5 proficiency levels with criteria | Must |
| FR-05 | Job-role → competency required-level mappings with importance and evidence status | Must |
| FR-06 | Prerequisite edges between competencies | Should |
| FR-07 | Self-assessment and structured assessment; assessor review; method + confidence + evidence stored | Must |
| FR-08 | Deterministic, explainable gap analysis with priority scoring | Must |
| FR-09 | Recommendations ranked by deterministic score with human-readable reasons | Must |
| FR-10 | Course catalogue: search, filters, competency mapping, enrolment, progress | Must |
| FR-11 | Document upload (PDF/DOCX/TXT), signature validation, async-style processing status | Must |
| FR-12 | Grounded RAG assistant with page-level citations and refusal on insufficient evidence | Must |
| FR-13 | MCQ generation from a document, validation pipeline, preview/edit/approve, attempt, scoring, explanations | Must |
| FR-14 | Learning plan generated from gaps, ordered by prerequisites/priority, recalculated on progress | Must |
| FR-15 | Learner, Manager (aggregate), Admin dashboards from persisted records | Must |
| FR-16 | iGOT/NSSTA adapter + truthful status | Must |
| FR-17 | Audit log for admin/assessor/data-access actions | Must |
| FR-18 | Destructive operations (document/course delete) with cascade/archival + authorization | Must |
| FR-19 | Pagination on list endpoints | Should |

## 6. Non-functional requirements

- Security controls per Phase 6 (see `docs/03-SECURITY.md`).
- ≤ 3 fix-and-retest cycles per defect.
- Responsive at 360 / 768 / 1280 / 1600 px.
- WCAG AA contrast on text; visible focus rings; no keyboard traps.
- p95 API latency < 400 ms for non-AI endpoints (measured on seed dataset).

---

## 7. Source register

| ID | Source | Used for | Status |
|---|---|---|---|
| S1 | https://sih.gov.in/sih2026PS (row 165) | Exact PS text, ministry, theme, category | **Official / verified** |
| S2 | https://www.mospi.gov.in — *Compendium of Roles and Responsibilities of Divisions and Units of MoSPI* (25 Mar 2025) | Institutional roles, ISS division duties | Official publication |
| S3 | https://www.mospi.gov.in — *ISS Cadre Deployment* (04 Mar 2020) | ISS cadre spread, postings | Official publication |
| S4 | https://www.mospi.gov.in — *Reference Manual for ISS Probationary Officers* (NSSTA/NSC, 2018) | ISS training content domains | Official publication |
| S5 | https://nssta.gov.in/aboutus, /history; PIB NSSTA Foundation Day 2026 | NSSTA mandate and training scope | Official |
| S6 | https://www.istm.gov.in/uploads/mission_karmayogi/FRAC.pdf | FRAC concept: roles→activities→competencies | Official (DoPT/ISTM) |
| S7 | https://cbc.gov.in — *Mission Karmayogi: A silent revolution* (2023) | Mission Karmayogi institutional framework | Official (CBC) |
| S8 | https://mospi.gov.in — *National Policy on Official Statistics* (draft, 2018) | NSC role, statistical standards | Official draft |
| S9 | https://igotkarmayogi.gov.in and portal.igotkarmayogi.gov.in | Establishing that no public API docs are available | Official site, negative finding |
| S10 | Third-party SIH summary sites (zaidsayyed.in, sihbuddy.in, blinknbuild catalogue PDF) | Cross-check only; **never** treated as authoritative | Secondary — corroborative only |

## 8. Evidence-status register (shipped in-app)

| Data class | Examples in app | Badge |
|---|---|---|
| `OFFICIAL` | SIH PS text itself; institution names; NSSTA/MoSPI mandate facts | "Official" |
| `PROVISIONAL` | 5-level proficiency scale; competency dictionary; job-role→competency required levels | "Provisional — pending expert validation" |
| `DEMONSTRATION` | Seeded courses, seeded documents, seeded learner cohort | "Demonstration data" |
| `INTEGRATION PENDING` | iGOT/NSSTA adapter surfaces | "Not configured / unreachable" |

---

## 9. Documented assumptions (where information was unavailable)

1. No public MoSPI competency dictionary exists → we author a provisional one; the schema accepts a
   future official import without change (all rows carry `evidence_status`, `source_ref`, `version`).
2. No iGOT API access → adapter + status, activated by env vars; no fabricated sync.
3. No official NSSTA course feed → seeded courses are marked demonstration content, with URLs left
   blank rather than invented.
4. Individual employee assessment data is treated as personal data → aggregate-only manager views
   with k-anonymity suppression (n < 5 hidden).
5. Single-tenant institutional deployment assumed (one organisation per instance) — simpler and
   matches a ministry/state-directorate deployment model.
