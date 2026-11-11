# PRAMANA

**Competency intelligence and grounded learning for India's Official Statistical System**

Built for **SIH 26101** (Ministry of Statistics and Programme Implementation, Software / Smart Education).

> *pramāṇa* — a valid means of knowledge; evidence.

---

## What this is

PRAMANA starts from the competencies a **statistical job role requires**, not from a course list.
A learner is assessed, their gaps are computed by a published formula, an explainable pathway is
generated, grounded material is studied with cited answers, generated MCQs verify learning, and the
reassessment closes the loop.

It is deliberately **not** a generic LMS, a generic chatbot, or a generic admin dashboard.

---

## Verified working (tested in this sandbox)

| Flow | Result |
|---|---|
| `GET /api/health` | `status: ok`, database ok, redis ok, both integrations `not_configured` (truthful) |
| Login (Argon2id + rotating refresh) | 200, access token issued |
| `GET /api/me/gaps` | readiness **70.8%**, 9 gaps, 7 critical, P1/P3 bands with explanations |
| `GET /api/me/recommendations` | deterministic scores (2.33, 1.52, 1.40) with reasons |
| `POST /api/assistant/ask` | grounded answer, **3 page-anchored citations** |
| Seed | 32 competencies, 8 job roles, 17 courses, 14 users, 3 indexed documents |
| Automated tests | **102 passed** (`pytest tests/` — auth, RBAC/IDOR, gap engine, malicious uploads, pgvector RAG SQL isolation, citation stripping, quiz validation V1–V6) |
| Frontend | `tsc --noEmit` clean, `vite build` OK (191 kB main / 62 kB gzip) |

**AI mode note.** External AI processing is disabled by default. With `AI_SEND_DOCUMENTS_EXTERNALLY=false`,
source text and user queries are not sent to an external embedding or chat provider; the assistant
uses local keyword retrieval and extractive passages. Enable outbound processing only after an
explicit data-sharing decision and provider review. Set `AI_BASE_URL` / `AI_API_KEY` to configure
a compatible provider; configuration alone does not constitute government approval.

---

## Stack

- **Backend** FastAPI · Pydantic v2 · SQLAlchemy 2 · Alembic · PostgreSQL 17 + pgvector (HNSW)
- **Frontend** React 18 · TypeScript · Vite · hand-written CSS design system (no UI framework)
- **AI** provider-neutral OpenAI-compatible client: timeouts, bounded retries, rate gate, telemetry
- **Auth** Argon2id · 15-min access JWT · rotating single-use refresh tokens with family reuse detection

## Layout

```
backend/   app/{core,models,schemas,services,ai,api/routers,integrations} · alembic/ · tests/ · seed.py
frontend/  src/{components,pages,lib,styles}
docs/      01-RESEARCH-AND-REQUIREMENTS.md · 02-ARCHITECTURE.md · 03-SECURITY.md
```

## Run locally

```bash
# 1. Postgres + pgvector (already provisioned in this sandbox)
sudo pg_ctlcluster 17 main start
createdb pramana   # user: pramana / pramana_local_dev

# 2. Backend
cd backend && export PYTHONPATH=. 
../.venv/bin/alembic upgrade head
DEMO_PASSWORD="choose-a-unique-local-password" ../.venv/bin/python seed.py
../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# 3. Frontend (proxies /api → :8000)
cd frontend && npm install && npm run dev     # http://localhost:3000
```

### Demonstration accounts

Seeded demonstration accounts are created by `backend/seed.py`. Set a unique `DEMO_PASSWORD` (at least 12 characters) when running the seed command; the seed script contains no shared default password. Never reuse that password in a shared deployment.

---

## Design decisions worth knowing

**Gap formula** (`services/gap.py`, printed in the UI):

```
deficit  = max(0, required − current)
priority = deficit × (0.6 + 0.4·importance/5) × (1.35 if critical) × (0.85 + 0.15·confidence/5)
band     = P1 ≥ 2.2 · P2 ≥ 1.4 · P3 ≥ 0.7 · P4
```

Quiz evidence moves a level by at most ±0.5. Every level stores its **method** (`self`,
`structured`, `assessor_reviewed`, `quiz_only`) so a self-rating is never displayed as proof.

**RAG authorisation happens in SQL, before text leaves the database.** Retrieved passages are fenced
as untrusted data, and citations that don't map to a retrieved chunk are stripped — the model cannot
invent a document, page or quotation. Weak retrieval returns a refusal, not a guess.

**MCQ validation** runs six checks before an item is stored: structure, duplicate options, source
grounding, answer support, ambiguity, cross-question duplication. Items persist as `draft` and need
explicit approval to publish. If no LLM is available, a deterministic cloze generator is used and
flagged `extractive_fallback` — never silently.

**Integrations are honest.** Research found **no publicly documented, lawfully accessible iGOT
Karmayogi or NSSTA API**. The adapters are complete boundaries that perform real HTTP probes and
report `not_configured` / `unreachable` / `auth_failed` truthfully. No iGOT record is fabricated;
seeded courses are labelled `demonstration`.

**Evidence tags** (`official` / `provisional` / `demonstration`) appear on every framework item,
course and document. The competency framework is **provisional** — authored from public MoSPI/NSSTA
role descriptions and the Mission Karmayogi FRAC concept, not a gazetted standard.

---

## Visual identity

Deliberately not a dark SaaS dashboard. The concept is a **printed statistical instrument**:
archival-paper ground with a graph-paper substrate, hairline rules, registration marks on feature
cards, Fraunces headings against Inter body text, and a **five-segment proficiency ladder** instead
of percentage bars — because proficiency is a discrete defined scale, not an arbitrary score.
Palette: paper `#f6f2e9`, ink `#1a2130`, teal `#0d6b60`, ochre `#b96a15`, violet `#59508f`.
Icons are hand-drawn SVG; the hero figure is a deterministic CSS competency matrix.

---

## Implemented vs not implemented

**Implemented** — RBAC (4 roles, backend-enforced) · versioned competency framework with domains,
competencies, skills, 5-level scale, prerequisites, job-role mappings and review/approve workflow ·
self/structured/assessor-reviewed assessments · gap analysis and recommendations · course catalogue,
enrolment, progress · document upload (PDF/DOCX/TXT, magic-byte validated) with real processing
states · grounded RAG with citations and refusal · MCQ generation, validation, review, publish,
attempt, scoring, explanations · learning plans with regeneration · learner/manager/admin dashboards
with k-anonymity suppression · audit log · iGOT/NSSTA adapter boundaries.

**Not implemented** (honest list): password-reset email flow (needs SMTP) · live iGOT/NSSTA sync
(blocked on credentials, see docs) · OCR for scanned PDFs (fails explicitly instead) · WebSocket
streaming for the assistant · role-specific bulk CSV user import · automated provider-failover across
multiple AI vendors (interfaces allow it; one provider is wired).

## Documentation

- `docs/01-RESEARCH-AND-REQUIREMENTS.md` — official PS text, domain research, source register,
  evidence-status register, documented assumptions
- `docs/02-ARCHITECTURE.md` — modules, data model, data flow, API surface
- `docs/03-SECURITY.md` — threat model, controls, what was tested and what remains unverified

## Status

Prototype. **Not** audited, **not** penetration-tested, **not** a government platform, and **not**
claimed compliant with any regulation. The competency framework requires domain-expert validation
before operational use.
