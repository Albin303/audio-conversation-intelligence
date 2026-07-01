# Nexus AI v2 Architecture Report

Nexus AI v2 is being refactored into a production-grade modular monolith with versioned APIs, SQLite operational storage, persistent Docker volumes, structured logging, and clear boundaries for future workers, PostgreSQL, object storage, authentication, and enterprise dashboards.

The current frontend and legacy API routes remain compatible.

## High-Level Architecture

```mermaid
flowchart TD
    UI[Next.js Dashboard] --> API[FastAPI API Service]
    API --> V1[/api/v1 Routers]
    API --> Legacy[/api Compatibility Routes]
    API --> Middleware[Request ID + JSON Logging]
    API --> Services[Service Layer]
    Services --> Repositories[Repository Layer]
    Repositories --> SQLite[(SQLite: database/nexus_ai.db)]
    Services --> Jobs[Background Job Boundary]
    Jobs --> Audio[Audio Worker Image]
    Jobs --> ML[ML Worker Image]
    Audio --> Uploads[uploads/audio Volume]
    Services --> Reports[uploads/reports Volume]
    API --> Logs[logs/nexus_ai.log Volume]
```

## Folder Structure

Current architecture rails:

```text
src/
  api/
    server.py
    worker.py
    v1/
  ai/
  config/
    settings.py
  core/
    logging.py
  database/
  middleware/
    request_context.py
  ml/
  nexus_ai/
    core/
      paths.py
    repositories/
      sqlite.py
  repositories/
  services/
    health_service.py
  utils/
  workers/
```

The older modules remain in place to preserve behavior while business logic is moved gradually out of `src/api/server.py`.

## API Architecture

Legacy routes remain available:

```text
/health
/api/health
/api/readiness
/api/upload
/api/jobs/{job_id}
/api/analyze
/api/follow-up-alerts
```

Versioned v2-compatible routes are now mounted:

```text
/api/v1/health
/api/v1/health/liveness
/api/v1/health/readiness
/api/v1/health/database
/api/v1/health/storage
/api/v1/health/worker
/api/v1/upload
/api/v1/jobs/{job_id}
/api/v1/analyze
/api/v1/followup
/api/v1/followup/{alert_id}
/api/v1/conversation/{job_id}
/api/v1/dashboard
/api/v1/settings
/api/v1/admin
/api/v1/report/{job_id}
```

Some dashboard/admin/report endpoints are scaffold aliases today. They exist so the future enterprise dashboard can adopt stable route families without breaking the current UI.

## Request Flow

Text analysis:

```text
Client
  -> /api/v1/analyze or /api/analyze
  -> FastAPI request middleware adds x-request-id
  -> Existing analysis pipeline runs
  -> Conversation metadata is written to SQLite
  -> Follow-up alerts are written to SQLite
  -> Existing response shape is returned
```

Audio upload:

```text
Client
  -> /api/v1/upload or /api/upload
  -> Audio file saved under uploads/audio
  -> Job row written to SQLite processing_jobs
  -> In-memory queue receives job for current worker
  -> Client polls /api/v1/jobs/{job_id}
```

## Background Worker Flow

Current worker path:

```text
Queued job
  -> status = processing in memory and SQLite
  -> transcription
  -> diarization
  -> feature extraction
  -> prediction
  -> status = completed/failed in memory and SQLite
  -> result_json stored in SQLite
```

Future queue migration path:

```text
asyncio.Queue
  -> Repository interface remains
  -> Redis/RabbitMQ/SQS queue adapter replaces queue transport
  -> API and frontend polling contract remains stable
```

## Database Architecture

SQLite remains the operational database for v2.

Tables currently initialized:

```text
conversations
follow_up_alerts
processing_jobs
```

No SQL is required inside API route handlers for these new storage paths. SQLite access is centralized in `src/nexus_ai/repositories/sqlite.py`.

## Storage Architecture

Persistent local storage:

```text
uploads/audio/
uploads/processed/
uploads/reports/
database/nexus_ai.db
logs/nexus_ai.log
```

Docker volume paths:

```text
/app/uploads
/app/database
/app/logs
```

Environment overrides:

```text
NEXUS_UPLOADS_DIR=/app/uploads
NEXUS_DATABASE_DIR=/app/database
NEXUS_LOGS_DIR=/app/logs
NEXUS_SQLITE_PATH=/app/database/nexus_ai.db
NEXUS_STORAGE_BACKEND=sqlite
```

## Docker Architecture

Deployment files:

```text
Dockerfile.api
Dockerfile.audio
Dockerfile.ml
Dockerfile.frontend
Dockerfile.backend  # compatibility alias-style backend build
docker-compose.v2.yml
```

Dependency files:

```text
requirements/base.txt
requirements/api.txt
requirements/audio.txt
requirements/ml.txt
requirements/dev.txt
requirements.txt  # legacy all-in-one file
```

`docker-compose.v2.yml` builds:

```text
api
frontend
audio-worker  # worker profile
ml-worker     # worker profile
```

The `.dockerignore` excludes local dependency folders, generated outputs, sample audio, `.git`, virtualenvs, and runtime data from image build context.

## Performance Improvements

Implemented:

- Docker build context is much smaller because `.venv`, `node_modules`, `.next`, `.git`, sample audio, and generated artifacts are ignored.
- Persistent runtime data is moved out of images and into mounted volumes.
- Requirements are split by concern so future API images do not need audio/ML packages.
- Request logging is structured JSON and written to `logs/nexus_ai.log`.
- Health checks now validate database, storage, and worker state separately.
- Heavy worker images are separated at Dockerfile level.

Current compatibility caveat:

The API process still imports and loads some ML/runtime objects from the legacy `server.py` path. For that reason `Dockerfile.api` currently installs `requirements/api.txt` plus `requirements/ml.txt`. The next phase should move model loading and scoring behind services/workers so the API image can drop `requirements/ml.txt` and target the requested sub-500 MB image size.

## Security Preparation

Authentication is not implemented yet, per requirement.

Prepared route families:

```text
/api/v1/settings
/api/v1/admin
```

Recommended next security layer:

```text
JWT auth middleware
RBAC dependency
Roles: Admin, Manager, Agent, Viewer
Audit event repository
Tenant ID propagation
```

## Future PostgreSQL Migration Plan

SQLite stays for v2.

To migrate later:

1. Define repository interfaces in `src/repositories`.
2. Add PostgreSQL implementation beside SQLite implementation.
3. Move table creation into migrations.
4. Switch implementation via `NEXUS_STORAGE_BACKEND=postgres`.
5. Keep API/services unchanged.

The goal is a database adapter swap, not a business-logic rewrite.

## Future Cloud Storage Migration Plan

Local volumes stay for v2.

To migrate later:

1. Add storage interface: `save_audio`, `get_audio`, `save_report`, `signed_url`.
2. Implement local filesystem backend.
3. Add S3/Azure Blob backend.
4. Store object URIs in SQLite/PostgreSQL.
5. Switch via `NEXUS_STORAGE_PROVIDER=s3|azure|local`.

## Deployment Workflow

Local v2 deployment:

```bash
docker compose -f docker-compose.v2.yml up --build api frontend
```

Build worker images:

```bash
docker compose -f docker-compose.v2.yml --profile workers build
```

Runtime volumes preserve:

```text
uploads
database
logs
```

## Major Changes Made

- Added clean architecture package skeleton under `src/`.
- Added centralized environment settings.
- Added JSON logging with request IDs.
- Added request context middleware.
- Added versioned `/api/v1` route family.
- Added liveness/readiness/database/storage/worker health checks.
- Added SQLite `processing_jobs` table and repository.
- Persisted audio job status and results to SQLite.
- Persisted uploaded audio under `uploads/audio`.
- Split requirements by runtime concern.
- Added API, audio, ML, and frontend Dockerfiles.
- Updated Docker Compose for API/frontend plus worker image profiles.

## Recommended Next Phase

1. Move `analyze_text_payload`, upload orchestration, and follow-up handling out of `server.py` into `src/services`.
2. Add a `JobQueue` interface with `InMemoryJobQueue` first, then Redis/RabbitMQ later.
3. Move XGBoost model loading into `src/ml` and lazy-load only in scoring workers.
4. Move Whisper/Pyannote/SpeechBrain imports into `src/ai` provider modules so API startup avoids heavy imports.
5. Add audit event table and auth/RBAC dependency scaffolding.
6. Add API contract tests for both legacy and `/api/v1` endpoints.
