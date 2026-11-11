# Test report

**Scope:** automated checks on the `pramana-judge-review-stabilization` branch.  
**Latest recorded successful run:** GitHub Actions run `42959472304` and pull-request run `42959477405`, on commit `14349f8f1cca80e4fcd4c34eb615eed82a8598fd`.

## Results

| Check | Result |
|---|---|
| Backend tests (PostgreSQL + pgvector) | 109 passed; 3 warnings |
| Frontend typecheck and production build | Passed |
| Backend Docker image | Built |
| Frontend Docker image | Built |
| Python dependency audit (`pip-audit`) | No known vulnerabilities reported |
| Production frontend dependency audit (`npm audit --omit=dev`) | 0 vulnerabilities reported |
| React Router lockfile check | 7.18.5 |
| Clean production-mode Compose startup | Passed |
| Database migration and health checks | Passed |
| API documentation and frontend route checks | Passed |
| Playwright role journeys | Learner, manager, assessor and administrator passed |
| Authorization check | Non-admin roles were denied admin routes |
| Browser console | No uncaught page exceptions observed |
| Government integration status | iGOT Karmayogi and NSSTA correctly reported as `not_configured` |

## What these checks establish

The backend suite ran against PostgreSQL with pgvector. The Compose job started a fresh stack with disposable database and upload volumes, checked the migration and service health, then exercised the application through a browser for each role.

The dependency audit results describe the dependencies and lockfiles at the tested commit. They are not a guarantee against every vulnerability or future advisory.

## What remains unverified

- Independent penetration testing, fuzzing and broader manual exploratory testing.
- Production hosting, TLS/reverse-proxy configuration, secrets management, backups and restore drills.
- Semantic verification that each generated answer claim is fully supported by its cited passage.
- Validation of the provisional competency framework by MoSPI/NSSTA domain experts.
- Authorized, end-to-end iGOT Karmayogi or NSSTA integration.

These results are CI evidence for a prototype. They do not establish production readiness, regulatory compliance or government approval.
