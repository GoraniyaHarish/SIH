# Test report

**Scope:** automated checks on `pramana-judge-review-stabilization`.  
**Latest successful verification:** push run `42963296590` and pull-request run `42963304645`, both on commit `44ae715f51cc00dfe3e3d53b757d85159b125287`.

## Results

| Check | Result |
|---|---|
| Backend tests (PostgreSQL + pgvector) | 111 passed; 3 warnings |
| Frontend typecheck and production build | Passed |
| Backend and frontend Docker images | Built |
| Python dependency audit (`pip-audit`) | No known vulnerabilities reported |
| Production frontend audit (`npm audit --omit=dev`) | 0 vulnerabilities reported |
| React Router lockfile check | 7.18.5 |
| Clean production-mode Compose startup | Passed |
| Alembic migration on a fresh database | Passed |
| API, PostgreSQL and Redis health checks | Passed |
| Frontend route and API proxy checks | Passed |
| CI demonstration-data seed | Passed; generated password is masked and not printed |
| Playwright role journeys | Learner, manager, assessor and administrator passed |
| Authorization check | Non-admin users were denied admin-only routes |
| Browser page errors | None observed during the four role journeys |
| Government integration status | iGOT Karmayogi and NSSTA correctly reported as `not_configured` |

## Test environment

The backend suite ran against PostgreSQL with pgvector. The Compose job created a fresh production-mode stack with disposable database and upload volumes, applied the migration, checked service health, seeded a private CI-only demonstration cohort, then exercised each role in Chromium. The job removed the disposable volumes after the run.

## Limits

- Dependency audits describe the tested lockfiles and package versions; they do not guarantee that future advisories will not affect them.
- Browser journeys cover the listed workflows, not every interaction or device size.
- The citation tests verify that citation IDs refer to retrieved passages. They do not prove that every generated claim is semantically entailed by its citation.
- These checks do not replace manual testing, independent security review or deployment validation.

## Still unverified

- Independent penetration testing, parser fuzzing and broader manual exploratory testing.
- Production hosting, TLS/reverse-proxy configuration, secrets management, backup and restore drills, monitoring and operational runbooks.
- Validation of the provisional competency framework by MoSPI/NSSTA domain experts.
- Authorized, end-to-end iGOT Karmayogi or NSSTA integration.

These results are CI evidence for a prototype. They do not establish production readiness, regulatory compliance or government approval.
