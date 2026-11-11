# Architecture

## Shape: modular monolith

One FastAPI process, one React SPA, one PostgreSQL database. No microservices, no message broker.
Rationale: the workload is bounded (document ingestion, per-request retrieval, per-request gap
computation), the team is 1–2 developers, and every extra process is an extra thing to secure,
deploy and explain. Redis is optional and used only for rate-limit coordination; the app degrades to
an in-process sliding-window limiter when it is unreachable (verified in `/api/health`).

```
Browser (React SPA, port 3000)
  │  same-origin fetch, httpOnly cookies, Vite proxies /api
  ▼
FastAPI (port 8000)  ── middleware: CORS → body-size cap → request-id/log → security headers
  ├── /api/auth          Argon2id, JWT access, rotating refresh
  ├── /api/framework     versioned competency model
  ├── /api/assessments   assessment → competency_state
  ├── /api/me/gaps       deterministic gap engine
  ├── /api/courses, /me/plan, /me/recommendations
  ├── /api/documents     upload → extract → chunk → embed
  ├── /api/assistant     authorise → embed → retrieve → generate → verify citations
  ├── /api/quizzes       generate → validate → review → publish → attempt
  ├── /api/manager, /api/admin
  └── integrations/      iGOT · NSSTA adapters (HTTP)
        │
        ▼
PostgreSQL 17 + pgvector (HNSW) ─── storage/uploads (outside webroot)
```

## Modules and their boundary

| Module | Owns | Emits |
|---|---|---|
| `core/config` | env-driven settings, no secrets in code | — |
| `core/security` | hashing, JWT, token digests, limiter | tokens |
| `core/deps` | authentication, RBAC, pagination, rate limits | `Principal` |
| `models/*` | schema + enums (`EvidenceStatus` is the truthfulness axis) | ORM entities |
| `services/gap` | **the** scoring rule | `GapRow[]` |
| `services/recommend` | ranking rule + plan generation | `Recommendation[]`, `LearningPlan` |
| `services/rag` | authorisation-before-retrieval, prompting, citation verification | `AskResponse` |
| `services/quizgen` | generation + 6-rule validation | validated drafts |
| `services/ingest` | file validation, processing state machine | `Document` |
| `services/analytics` | aggregate computation + k-anonymity suppression | aggregate dicts |
| `integrations/adapters` | external boundaries, real probes | `ProbeResult` |
| `api/routers/*` | HTTP shape only — thin; business rules live in services | — |

Business rules are **only** on the backend. The SPA never computes a gap, a priority or a score; it
renders what the API returns.

## Data model (14 core tables)

```
departments ──< users >── job_roles ──< role_competency_requirements >── competencies
                 │                                                            │
                 │  refresh_tokens, login_attempts, audit_logs                 │
                 │                                                            │
   framework_versions ──< competency_domains ──< competencies ──< skills      │
                                    │                    └──< competency_prerequisites
                                    └──< proficiency_levels
                 │
                 ├──< assessments ──< assessment_responses
                 ├──< competency_states  (unique user+competency; carries method/confidence)
                 ├──< enrolments >── courses ──< course_competencies >──────┘
                 │                     └──< course_materials
                 ├──< documents ──< document_chunks (vector(1536), HNSW cosine)
                 ├──< learning_plans ──< plan_items
                 ├──< quiz_attempts ──< quiz_answers
                 └──< notifications
courses ──< quizzes ──< quiz_questions
```

Design decisions that matter:

- **`competency_states` is a materialised current position**, not a log. History lives in
  `assessments` + `assessment_responses`, so the current reading is one indexed lookup while the
  full audit path is still reconstructible.
- **`evidence_status` on every domain artefact** makes the official/provisional/demonstration
  distinction a data property, not a UI convention.
- **`document_chunks.embedding` is `vector(1536)` with an HNSW cosine index**, so retrieval is a
  single indexed query and authorisation is applied as a SQL predicate in the same statement.
- **Destructive deletes cascade deliberately**: deleting a document removes chunks (CASCADE) and the
  file; quizzes keep their stored source quotes but lose the FK (`SET NULL`) so no citation dangles
  into deleted content. Deleting a course with enrolments archives instead, preserving learner history.

## Data flow: the closed loop

1. **Assess** → `POST /assessments` writes responses, upserts `competency_states`, forces plan rebuild.
2. **Diagnose** → `GET /me/gaps` reads states + role requirements, applies the published formula,
   returns per-competency explanation strings.
3. **Recommend** → `GET /me/recommendations` intersects gap competencies with `course_competencies`,
   scores by gap priority × level fit × novelty, returns human-readable reasons.
4. **Plan** → `learning_plans` + `plan_items`, ordered so prerequisites precede dependents.
5. **Learn** → enrolment and per-material progress persisted; completion flips `enrolments.status`.
6. **Verify** → quiz generation from the same document the learner read; attempt scoring writes
   `quiz_evidence`; reassessment overwrites the state with a new method.

## API surface

71 routes under `/api`, OpenAPI at `/api/docs`. Auth-classed:

- **public** `/health`, `/departments`, `/framework/*` (read)
- **authenticated** `/auth/me`, `/me/*`, `/courses`, `/documents`, `/assistant/ask`, `/quizzes`
- **staff** (`manager|assessor|admin`) `/manager/analytics`, `/quizzes/generate`, `/quizzes/*/publish`,
  `/framework/competencies/{id}` (review only), `/assessments/*/review`, `/users/{id}/gaps`
- **admin** `/admin/*`, `/framework/*` (write)

Ownership checks are per-resource inside the routers (e.g. `load_document` returns 404 for
non-readable documents so existence is not disclosed; `update_plan_item` rejects items whose plan
belongs to another user).

## Concurrency and performance

- pgvector HNSW (`m=16`, `ef_construction=64`) for approximate nearest neighbour.
- Indexes follow real access paths: `(user_id, status)` on assessments, `(owner_id, status)` on
  documents, `(user_id, competency_id)` unique on states, `(domain_id, code)` on competencies.
- `statement_timeout=15s` and `idle_in_transaction_session_timeout=20s` set at connect time, so a
  pathological query cannot pin a worker.
- List endpoints paginate (`limit` capped at 100).
- Document processing runs inline for bounded work plus a daemon worker thread for queued items —
  deliberately not Celery, because the only async workload is ingestion.

## Deployment

Docker Compose (api + web + postgres/pgvector + redis), defined in `docker-compose.yml` with
`backend/Dockerfile`, `frontend/Dockerfile` and `deploy/init-db.sql`. Postgres and Redis are never
exposed publicly; only the web container publishes a port. Alembic is the single migration path and
runs in the API container's start command, before uvicorn binds.

> **Verification status:** GitHub Actions has built both images, started a clean production-mode
> Compose stack, applied the Alembic migration, checked API/database/Redis health and exercised the
> web application through Playwright role journeys. This is repeatable CI verification, not a
> production deployment or an independent operational review. See `docs/04-TEST-REPORT.md`.
