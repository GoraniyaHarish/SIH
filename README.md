# PRAMANA

Competency assessment and evidence-based learning for India's Official Statistical System.

PRAMANA is the team's prototype for **SIH 26101**, under the Ministry of Statistics and Programme Implementation (MoSPI). The platform connects role requirements, competency assessment, skill-gap analysis, learning recommendations and reassessment in one workflow.

## How it works

1. A learner is associated with a statistical job role.
2. The learner's current competencies are assessed.
3. The gap engine compares current levels with role requirements and explains each priority.
4. The recommendation service matches gaps to relevant courses and creates a learning plan.
5. Learners study course material and can ask questions against uploaded documents.
6. Quizzes can be generated from learning material, reviewed and attempted.
7. Assessment and quiz evidence updates the learner's competency profile.

The framework and seeded catalogue are prototype data. They are not an approved MoSPI competency standard or a live government course catalogue.

## Technology

| Area | Technology |
|---|---|
| Web application | React, TypeScript, Vite |
| API | Python, FastAPI, Pydantic |
| Persistence | PostgreSQL 17, SQLAlchemy, Alembic |
| Document retrieval | pgvector |
| Background services | Redis and an ingestion worker |
| Deployment | Docker Compose |
| Tests | pytest, Playwright browser journeys |

The backend is organised as a modular monolith. Business rules and access checks live in the API; the frontend presents API results.

## Run locally with Docker Compose

Requirements: Docker Engine and the Docker Compose plugin.

```bash
cp .env.example .env
```

Edit `.env` and set unique values for `POSTGRES_PASSWORD` and `JWT_SECRET`. Do not commit this file.

Start the application:

```bash
docker compose up --build -d
docker compose ps
```

Open **http://localhost:3000**. API documentation is available at **http://localhost:3000/api/docs**.

To create local demonstration accounts, set a private password and explicitly enable the seed operation:

```bash
docker compose exec -e ALLOW_DEMO_SEED=1 -e DEMO_PASSWORD='use-a-unique-password-here' api python seed.py
```

The seed command creates demonstration records. Do not use these accounts or data as real employee records. To stop the application:

```bash
docker compose down
```

To remove the local database and uploaded files as well, use `docker compose down --volumes`. This permanently deletes local application data.

## Configuration and data handling

- External AI processing is **off by default**. Document and query text is not sent to an external provider unless `AI_SEND_DOCUMENTS_EXTERNALLY=true` is deliberately configured.
- AI provider settings are optional. Without an enabled provider, the assistant uses local keyword retrieval and extractive passages.
- iGOT Karmayogi and NSSTA settings are empty by default. The application reports them as not configured; no live integration is claimed.
- Never place API keys, tokens, passwords or real employee information in source control or demonstration data.

See `.env.example` for the available settings.

## Project structure

```text
backend/
  app/
    api/routers/       HTTP endpoints and request handling
    core/              configuration, authentication and database setup
    integrations/      external-service adapter boundaries
    models/            database models
    services/          competency, learning, document and quiz logic
  alembic/             database migrations
  tests/               backend tests
frontend/
  src/
    components/        shared interface components
    lib/               API client and authentication state
    pages/             application screens
    styles/            application styles
  e2e/                 browser role journeys
docs/
  01-RESEARCH-AND-REQUIREMENTS.md
  02-ARCHITECTURE.md
  03-SECURITY.md
  04-TEST-REPORT.md
  evaluation/
  research/
```

## Engineering notes

### Competency gap calculation

The gap service calculates a deficit between the required and current proficiency levels, then adjusts its priority using competency importance, criticality and confidence. The formula and thresholds are documented in the service and surfaced in the interface. The result is a decision-support aid, not a formal employee-performance rating.

### Document-grounded answers

Document access is checked before retrieval. Answers are built from authorised passages, and citations are restricted to retrieved chunks. Citation-ID validation confirms that a citation points to a retrieved source; it does not independently prove that every generated statement is entailed by that source. Review important answers against the original material.

### Evidence labels

Framework items, courses and documents distinguish official, provisional and demonstration material. The competency mappings in this prototype are provisional and require review by MoSPI/NSSTA subject-matter experts.

## Current status

The review branch has automated backend, frontend, dependency-audit, Docker-build and Compose/browser checks. The latest documented CI run is recorded in [the test report](docs/04-TEST-REPORT.md).

This is a prototype, not a production government service. It has not undergone an independent penetration test, formal compliance assessment or operational deployment review. Live iGOT/NSSTA integration, government SSO, approved competency-framework data and production hosting remain outside the verified scope.

## Documentation

- [Research and requirements](docs/01-RESEARCH-AND-REQUIREMENTS.md)
- [Architecture](docs/02-ARCHITECTURE.md)
- [Security review](docs/03-SECURITY.md)
- [Test report](docs/04-TEST-REPORT.md)
- [Independent SIH review](docs/evaluation/2026-11-independent-review.md)
- [Government ecosystem evidence](docs/research/government-learning-ecosystem-evidence.md)
