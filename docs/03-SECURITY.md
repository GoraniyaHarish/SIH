# Security review

**This is an engineering self-review of a prototype. It is not an audit, not a penetration test, and
does not establish compliance with any regulation. Items under “Unverified” have not been tested.**

## Threat model (abbreviated STRIDE, ranked by realistic impact)

| # | Threat | Mitigation | Status |
|---|---|---|---|
| T1 | Credential stuffing / brute force | Argon2id (t=2, m=64MiB, p=2); per-IP 20/5min limiter; per-account lockout after 10 failures; identical error for unknown vs wrong password | Implemented |
| T2 | Session theft / replay | 15-min access JWT in `httpOnly`, `SameSite=strict` cookie; refresh stored as SHA-256 digest only; rotation on every use; **family reuse detection revokes the whole chain** | Implemented |
| T3 | Privilege escalation via signup | `/auth/register` hard-codes `role=LEARNER`; elevated roles only via `/admin/users` | Implemented |
| T4 | IDOR on documents / assessments / plans | Every fetch goes through an ownership predicate; documents use `can_read_document` with 404 (not 403) on denial; plan-item update verifies plan ownership | Implemented |
| T5 | Prompt injection via uploaded document | Extracted text is scanned for injection patterns and flagged; retrieved text is wrapped in `<<<UNTRUSTED_SOURCE_DATA>>>` fences; system prompt states retrieved text is data, never instructions | Implemented · **partially verified** |
| T6 | Hallucinated citations | Post-generation citation regex; any `[S#]` not mapping to a retrieved chunk is **stripped**; zero valid citations ⇒ answer withheld entirely | Implemented |
| T7 | Cross-tenant vector leakage | Authorisation applied as a SQL predicate **inside** the retrieval query; unauthorised chunks never leave the database, so they cannot reach the model | Implemented |
| T8 | Malicious upload | Magic-byte validation (`%PDF-`, `PK\x03\x04`+`.docx`, UTF-8 for text); NUL-byte rejection; 20 MB streamed cap; UUID filenames; storage outside webroot; path-traversal check on resolve; 500-page cap; parser exceptions contained | Implemented |
| T9 | Stored XSS via document title / question text | React escapes by default; no `dangerouslySetInnerHTML` anywhere; API responses set `X-Content-Type-Options: nosniff` | Implemented |
| T10 | SQL injection | 100% SQLAlchemy Core/ORM with bound parameters; no string-interpolated SQL | Implemented |
| T11 | CSRF | `SameSite=strict` cookies plus JSON-only content type; no state-changing GET | Implemented |
| T12 | Secret leakage in logs | JSON logger redacts any field matching password/token/secret/prompt/content; prompts and document text are never logged | Implemented |
| T13 | Stack-trace / internal detail leakage | Global handler returns a generic message; validation errors return field name + message only, never the submitted value | Implemented |
| T14 | DoS via large body / expensive AI call | Content-Length cap middleware; streamed upload cap; per-route rate limits on login, refresh, upload, ask, quiz-generate | Implemented |
| T15 | Role change race / orphaned admin | Role changes bump `token_version` (invalidating live tokens); last-active-admin protection on both role change and deactivation | Implemented |
| T16 | Aggregate inference of an individual | Manager analytics suppress any cell derived from <5 learners | Implemented |

## AI-specific controls

- Provider is a boundary, not a dependency: `AI_BASE_URL` / `AI_API_KEY` / models are env-driven; no
  SDK key is hard-coded. Timeouts (60s), bounded retries with jittered backoff, and a per-process rate
  gate wrap every call.
- **Outbound document text is gated** by `AI_SEND_DOCUMENTS_EXTERNALLY`. When false, the assistant
  returns verbatim passages with citations instead of calling the model.
- Every AI call is recorded in `ai_usage_logs` (operation, model, latency, tokens, outcome) — never
  the prompt or the document content.
- Failure is never silent: provider down ⇒ `mode=extractive` with citations, or a refusal. Quiz
  generation falls back to a deterministic cloze generator flagged `extractive_fallback`.

## What has been verified

- CI builds both Docker images and starts a fresh production-mode Compose stack.
- The database migration, API/database/Redis health checks, SPA route and API proxy checks pass.
- Playwright role journeys pass for learner, manager, assessor and administrator; non-admin access
  to admin routes is denied.
- The backend suite reports 111 passing tests. Frontend typecheck and production build pass.
- Dependency audits report no known Python vulnerabilities and zero production npm vulnerabilities.
- iGOT Karmayogi and NSSTA are verified as `not_configured`, not live integrations.

See `docs/04-TEST-REPORT.md` for the tested commit and run details.

## Unverified / requires deployment-level review

1. **Automated test coverage.** The backend suite reports **111 passing tests** across
   authentication, role and resource authorization, competency-gap calculations, document upload,
   retrieval isolation, citation handling and quiz generation/attempts. The test report records the
   tested commit and CI run. Dependency audits are also required CI jobs. Live adversarial LLM
   jailbreak evaluation against an external model is not part of the current suite.
2. No penetration test, no fuzzing of the PDF/DOCX parsers, no adversarial corpus.
3. Prompt-injection resistance has one regex-based detector and a structural fence; it has **not**
   been tested against a determined attacker.
4. Rate limiting is in-process unless Redis is configured; behind multiple instances the effective
   limit multiplies.
5. TLS termination, HSTS, secret management, backup encryption and at-rest encryption are
   deployment concerns not exercised here.
6. Argon2 parameters are tuned for a laptop, not benchmarked against target hardware.
7. No CSP beyond `default-src 'none'` on API responses; the SPA itself would need a tuned CSP at the
   edge.
8. Audit log is append-only by convention (no DB-level revoke of UPDATE/DELETE). A production
   deployment should enforce that with grants.

## Deliberate non-goals

No password-reset email flow (would need SMTP and a token store). No MFA. No SSO. No data
residency controls. Dependency audits run in CI; this does not replace ongoing review of advisories or a full software supply-chain assessment. No formal DPIA — the app
minimises personal data (no address, no DOB, IPs are HMAC-pseudonymised) but has not been assessed
against any specific statute.
