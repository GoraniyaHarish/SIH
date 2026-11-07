# Test Execution Report

**Date:** 2026-11-07
**Command:** `cd backend && PYTHONPATH=. ../.venv/bin/pytest tests/`
**Result:** `102 passed in 50.16s`

Every number in this report was produced by actually running the suite. Nothing here is
projected or estimated.

---

## 1. Environment

| Item | Value |
|---|---|
| Python | 3.13.14 |
| pytest | 8.3.4 |
| Database | PostgreSQL 17.11 + pgvector 0.8.0 + pg_trgm |
| Test database | `pramana_test` (separate from the development database) |
| Schema source | Real Alembic migration (`alembic upgrade head`), **not** `create_all` |
| AI provider | Deliberately **unconfigured** by default (`AI_BASE_URL`/`AI_API_KEY` blanked); targeted mocks exercise LLM citation verification |
| Redis | Deliberately **unset** in pytest — the in-process limiter is exercised deterministically |
| Upload storage | Per-run temporary directory |

### Why the schema comes from the migration

The suite runs `alembic upgrade head` against `pramana_test` rather than calling
`Base.metadata.create_all()`. This means the tests exercise the same DDL that a deployment
runs, so a migration that drifts from the models fails the suite instead of failing at
deploy time.

### Isolation

Each test runs inside one outer transaction that is rolled back afterwards. Application
sessions are bound to that connection with `join_transaction_mode="create_savepoint"`, so
endpoint code really calls `commit()` while the outer transaction still isolates tests from
one another. The rate-limiter singleton is cleared before and after every test.

---

## 2. Results by module

| Module | Tests | Focus | Result |
|---|---:|---|---|
| `test_auth.py` | 17 | Authentication, session lifecycle, token security | **17 passed** |
| `test_authorization.py` | 29 | RBAC role gates, ownership, IDOR resistance | **29 passed** |
| `test_gap_engine.py` | 30 | Deterministic gap arithmetic and recommendation rules | **30 passed** |
| `test_rag_quiz_upload.py` | 26 | Malicious uploads, prompt-injection fencing, SQL-level pgvector RAG isolation, citation stripping, quiz validation V1–V6, quiz attempt lifecycle | **26 passed** |
| **Total** | **102** | | **102 passed, 0 failed, 0 skipped** |

---

## 3. What each module actually verifies

### `test_auth.py` — 17 tests

- **Cookie hardening** — the access cookie is `HttpOnly`, `SameSite=strict`, and the
  response body carries a 15-minute `expires_in`.
- **No account enumeration** — a wrong password and an unknown email return byte-identical
  401 bodies (`Email or password is incorrect`). Asserted as an equality of the two JSON
  payloads, not just matching status codes.
- **Attempt accounting** — one failed + one successful login produce exactly one
  `login_attempts` failure row, one success row, and one `auth.login` audit event.
- **Per-account lockout** — ten consecutive failures (the configured
  `lockout_threshold`) cause the eleventh attempt to return **423 Locked**, independent of
  source IP.
- **Deactivation** — an account deactivated by an admin can no longer authenticate (403).
- **Refresh rotation** — a refresh consumes the presented token and issues a distinct
  successor.
- **Refresh-reuse detection** — replaying the consumed token returns 401 with
  `reuse detected`, **and the legitimate successor is also revoked**, proving the whole
  family is invalidated rather than just the replayed handle.
- **Logout** — revokes the refresh family and clears cookies.
- **Password change** — bumps `token_version`, so the previously valid access token
  returns 401 *and* the outstanding refresh token is dead; the new password then works.
- **Password strength** — short passwords are rejected at the schema layer (422);
  `alllowercase1` is rejected with an explicit `uppercase` requirement message.
- **Privilege escalation via registration** — a registration payload containing
  `"role": "admin"` creates a **learner**, and a subsequent login confirms the escalated
  role was never persisted.
- **Unauthenticated access** — `/auth/me`, `/me/gaps`, `/documents` all return 401.
- **Forged tokens** — both a tampered signature and a JWT signed with an attacker-chosen
  secret are rejected.
- **Security headers** — `nosniff`, `DENY` framing, `no-referrer`, `no-store`,
  `default-src 'none'` CSP.
- **Validation errors do not echo input** — a login attempt with an invalid email and the
  password `SuperSecret#1` returns a field-level error list; the assertion explicitly
  checks the secret does **not** appear anywhere in the response text.

### `test_authorization.py` — 29 tests

Role gates (parametrised over learner, manager, assessor):

- All five `/api/admin/*` routes return 403 for every non-admin role and 200 for admin.
- A learner cannot create a course, generate a quiz, or read aggregate analytics.
- A learner cannot call the staff-only `/users/{id}/gaps` endpoint.
- A manager can read a direct report's gaps (200) but not a stranger's (403).
- **Scope widening is impossible** — a manager passing `department_id` for another
  department still gets `scope: "department"` and a headcount bounded to their own staff.
- An assessor may submit a review decision but is refused when editing competency content
  (403 with an explicit "review decisions" message).
- Only an admin can create departments.

Document authorization:

- A private document uploaded by one learner returns **404 (not 403)** to another learner,
  so existence is not disclosed; it is also absent from that learner's listing.
- `?mine=true` is scoped per user.
- The assistant **rejects an unauthorized document id before retrieval** (404), failing
  closed rather than silently answering from whatever it could read.
- A learner cannot escalate a document to `organisation` visibility (403); a manager may
  publish to `department`.
- A department-scoped document is readable inside its department and 404 outside it.
- Chunk previews enforce the same authorization as the parent document.
- Deletion requires ownership or admin.

Plan and attempt IDOR:

- A plan item belonging to one learner cannot be patched by another (403, "does not
  belong"), while the owner can advance it.
- A quiz attempt cannot be submitted or read by another learner (403); the owner can.
- An assessment is readable by its owner, assessor and admin, but 403 for an unrelated
  learner.
- An assessor cannot review their own assessment (400).
- A learner cannot review any assessment (403).
- An admin cannot deactivate themselves, change their own role, or strand the system
  without an active administrator (all 400).
- **A role change invalidates the target user's live access token** (401 after promotion),
  confirming `token_version` invalidation works end to end.

### `test_gap_engine.py` — 30 tests

Pure rules, parametrised against the documented thresholds:

- Severity bands across all boundaries (0.5 → low, 0.51 → moderate, 1.75 → high,
  1.76 → critical).
- Priority bands across all boundaries (0.69 → P4, 0.7 → P3, 1.4 → P2, 2.2 → P1).
- Quiz evidence nudges the effective level by at most ±0.5 and is clamped to [0, 5], so a
  perfect quiz score cannot certify expertise.

Hand-calculated end-to-end arithmetic on the seeded learner:

| Competency | Current | Target | Deficit | Importance | Critical | Confidence | Expected score | Expected band |
|---|---:|---:|---:|---:|---|---:|---:|---|
| STAT.01 | 3.0 | 5 | 2.0 | 5 | yes | 5 | 2.0 × 1.00 × 1.35 × 1.00 = **2.700** | P1 |
| DQ.01 | 3.0 | 4 | 1.0 | 4 | no | 4 | 1.0 × 0.92 × 1.00 × 0.97 = **0.892** | P3 |
| STAT.02 | 2.5 | 3 | 0.5 | 3 | no | 3 | 0.5 × 0.84 × 1.00 × 0.94 = **0.395** | P4 |
| STAT.03 | 2.0 | 2 | 0.0 | 3 | no | — | **0.000** | met |

Readiness is asserted at exactly **75.0** = 100 × (3 + 2.5 + 3 + 2) / (5 + 3 + 4 + 2).

Additional behaviour verified:

- **Prerequisite deferral** — STAT.02 declares STAT.01 as a prerequisite and STAT.01 is
  itself deficient, so STAT.02 is flagged `prerequisite_blocked` with the deferral reason
  appended to its explanation, and ordering puts unblocked rows first.
- **Every row explains itself** — the explanation contains the target level and the
  provenance of the current level, so a self-rating is never presented as verified.
- **Unassessed learner** — a learner with no assessment gets a full 4-competency gap set at
  level 0.0 with `missing_assessment: true`; they are not silently treated as proficient.
- **No job role** — a learner without a job role gets an empty analysis and no invented
  requirements.
- **API parity** — `/api/me/gaps` returns the same numbers plus the documented
  `METHOD_NOTE` string.
- **Re-assessment closes a gap and versions the plan** — submitting a level-5 assessment for
  STAT.01 drops the gap count from 3 to 2, the critical count from 1 to 0, and leaves
  exactly one active plan with a higher version.
- **Quiz evidence is bounded in the real pipeline** — setting `quiz_evidence = 1.0` on a
  level-3.0 state yields 3.5 (not 5.0), reported with source `self+quiz`.

### `test_rag_quiz_upload.py` — 26 tests

- **Malicious & malformed uploads (9 tests)** — ELF executable disguised as `.pdf` rejected
  by magic bytes (422 `unsupported_type`); raw `.zip` without `.docx` rejected; NUL bytes in
  `.txt` rejected as `binary_disguised`; invalid UTF-8 rejected as `encoding`; empty upload
  rejected; corrupt `%PDF-1.7` body caught during inline processing and marked
  `status=failed` instead of HTTP 500; text under 200 chars marked `no_text`; streamed size
  cap returns **413** when exceeded; client filename is replaced with UUID hex and
  `file_path()` raises `path_traversal` if `stored_name` attempts `../../` escape.
- **Prompt-injection detection & fencing (6 tests)** — `scan_for_injection` detects 5
  canonical override patterns; uploading a document containing injection instructions sets
  `error_code="prompt_injection_flagged"` while wrapping retrieved chunks inside
  `<<<UNTRUSTED_SOURCE_DATA id=S1>>>` fences and keeping `SYSTEM_PROMPT` untainted.
- **Chunk-level RAG SQL authorization & citation verification (3 tests)** —
  1. Seeds 1536-dim pgvector embeddings on a private document, a Department A document, and
     an organisation-wide document with identical 1.000 cosine similarity to the query
     vector. Verifies that an outsider in Department B retrieves **only** the
     organisation-wide chunk (even when explicitly passing the private document ID to
     `retrieve()`), a Department A colleague retrieves Department A + organisation chunks
     but never the private chunk, and the owner retrieves all three.
  2. Verifies `_keyword_retrieve` never leaks private chunk text across users.
  3. Verifies LLM-mode citation stripping: fabricated citation `[S9]` is stripped while
     valid `[S1]` is retained; an answer containing only fabricated citation `[S7]` is
     withheld entirely (`mode="refused"`, `grounded=False`, `insufficient_evidence=True`).
- **Quiz validation rules V1–V6 & end-to-end lifecycle (8 tests)** —
  - Valid item passes all six rules (`state="validated"`).
  - **V1**: rejects <4 options, out-of-range `correct_index`, and `"All of the above"`.
  - **V2**: rejects options that are identical after case/punctuation normalisation.
  - **V3**: rejects ungrounded quotes (low token overlap) and unknown `source_id`.
  - **V4**: rejects correct options whose content words do not appear in the passage.
  - **V5/V3 verbatim**: rejects reordered paraphrases that are not verbatim substrings.
  - **V6**: rejects duplicate question stems within the same quiz.
  - **End-to-end lifecycle**: manager uploads document → generates draft quiz → learner
    gets 404 on draft → manager publishes → learner starts attempt (with shuffled options),
    submits 100% correct answers → `STAT.01` competency level advances from `3.0` to `3.5`
    (`self+quiz`).

---

## 4. Bugs this suite found and fixed

The suite was not written after the fact to confirm working code. **Seven** genuine defects
surfaced during test execution and were fixed in the application:

| # | Location | Defect | Fix |
|---|---|---|---|
| 1 | `analytics.py` `admin_overview` | `role.value` on a value the driver returns as `str` (the column is `String(24)`) → `AttributeError` → **HTTP 500 on `/api/admin/overview`** | Key normalisation that accepts either a `Role` or a `str` |
| 2 | `analytics.py` manager course-completion query | `func.cast(Enrolment.status == "completed", func.INTEGER())` raised `Neither 'Function' object nor 'Comparator' object has an attribute '_isnull'` → **HTTP 500 on `/api/manager/analytics`** | Replaced with a portable `case((..., 1), else_=0)` aggregate |
| 3 | `assessment.py` `get_assessment` | `AssessmentDetailOut.model_validate(assessment)` tried to coerce the ORM `responses` relationship into a model requiring joined `competency_code`/`competency_name` → **HTTP 500 on every assessment read, including the response to `POST /api/assessments`** | Build from the flat parent model, then attach explicitly constructed responses |
| 4 | `framework.py` job-role serialisation | Same latent bug: `JobRoleOut.model_validate(role)` coerced `requirements` into `RoleRequirementOut`, which needs joined competency fields → **HTTP 500 on `/api/framework/job-roles/{id}`** | Added `_job_role_base()` for the flat columns; joined requirements attached by the caller |
| 5 | `schemas.DomainGapAggregate` | `average_deficit: float` / `learners_with_gap: int` were non-optional, but the k-anonymity rule sets them to `None` when fewer than 5 learners are affected → **HTTP 500 whenever suppression triggered** | Declared both `| None` with a comment explaining that `None` means *suppressed*, never *zero* |
| 6 | `schemas.AdminOverviewOut` vs `analytics.admin_overview` | Schema required `ai_configured`; the service never returned it → **HTTP 500 on `/api/admin/overview`** | Service now reports `settings.ai_configured` |
| 7 | `quiz.py` `start_attempt` | Mutated `attempt.option_order[str(question.id)] = indices` in place after `db.flush()` on a SQLAlchemy `JSONB` column without `MutableDict`, so SQLAlchemy did not detect the change and persisted `{}` → **shuffled quiz attempts were graded against unshuffled indices (`0,1,2,3`), mis-scoring learners** | Built `order_map` as a fresh dict and assigned `attempt.option_order = order_map` before commit |

---

## 5. Coverage honesty — what is tested vs what remains unverified

| Category | Status |
|---|---|
| Authentication | ✅ Tested (17 tests) |
| Authorization / RBAC | ✅ Tested (29 tests) |
| Cross-user / IDOR | ✅ Tested |
| Input validation | ✅ Schema-level rejection, secret non-echoing, and upload validation tested; no exhaustive grammar fuzzing |
| RAG authorization (SQL + pgvector) | ✅ Tested — both pre-retrieval ID check and SQL-level pgvector cosine-distance + keyword retrieval isolation across private, department, and organisation scopes |
| Citation verification | ✅ Tested — hallucinated `[S#]` stripping and refusal when zero valid citations remain |
| Prompt injection | ⚠️ **Partly** — regex detection (`scan_for_injection`), `prompt_injection_flagged` status, and `<<<UNTRUSTED_SOURCE_DATA>>>` fencing are tested; live adversarial LLM jailbreak evaluation against an external model is not automated |
| Malicious upload | ✅ Tested — magic-byte sniffing, binary masquerade, invalid UTF-8, corrupt PDF handling, 413 size cap, UUID filename sanitisation, and path-traversal guard |
| Quiz validation rules V1–V6 | ✅ Tested — all six rules and the full draft → publish → shuffled attempt → bounded competency feedback loop |
| API security / headers | ✅ Tested |
| Dependency checks | ❌ Not run — no `pip-audit`/`npm audit` executed in this environment |

### Not tested because the environment cannot test it

- **Docker Compose startup** — Docker is not installed in this sandbox. `docker-compose.yml`,
  both Dockerfiles and `deploy/init-db.sql` were written and the Compose file was
  YAML-parsed successfully, but **the stack has never been brought up via Docker**.
- **Live external LLM adversarial red-teaming** — unit tests mock `ai.embed` and `ai.chat`
  to deterministically test citation stripping and refusal logic without network calls.

---

## 6. Reproducing

```bash
# Prerequisites: PostgreSQL 17 with the vector and pg_trgm extensions available,
# and a database named pramana_test.

sudo -u postgres psql -d pramana_test -c "CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS pg_trgm;"

cd backend
PYTHONPATH=. ../.venv/bin/pytest tests/            # full suite (102 tests)
PYTHONPATH=. ../.venv/bin/pytest tests/ -q -v      # per-test names
```
