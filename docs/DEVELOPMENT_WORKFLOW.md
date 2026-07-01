# Nexus AI Docker Development Workflow

## Production

Build the optimized production images:

```bash
docker compose -f docker-compose.v2.yml build
```

Start API and frontend:

```bash
docker compose -f docker-compose.v2.yml up
```

Start API, frontend, and both worker types:

```bash
docker compose -f docker-compose.v2.yml --profile workers up
```

The API container only accepts requests, persists uploads/jobs, serves health/status endpoints, and reads reports. Audio and ML inference run in worker containers using SQLite-backed job polling.

## Development

Start hot-reload development services:

```bash
docker compose -f docker-compose.dev.yml --profile workers up
```

Hot-reload mounts:

- `./src:/app/src`
- `./frontend:/app`
- `./uploads:/app/uploads`
- `./database:/app/database`
- `./logs:/app/logs`

Python changes reload through:

```bash
uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
```

Frontend changes reload through:

```bash
npm run dev
```

Only dependency changes should require image rebuilds. Python source, TypeScript, React, and CSS edits are bind-mounted.

## Queue Flow

Text analysis:

1. `POST /api/analyze` creates a `processing_jobs` row with `source_type=text`.
2. `ml-worker` claims pending text jobs.
3. The worker runs extraction, prediction, reports, and persistence.
4. Clients poll `GET /api/jobs/{job_id}` until `completed`.

Audio analysis:

1. `POST /api/upload` stores the audio file and creates a pending audio job.
2. `audio-worker` claims the job, transcribes, diarizes, and writes an `awaiting_ml` payload.
3. `ml-worker` claims the `awaiting_ml` job and completes analysis.
4. Clients poll `GET /api/jobs/{job_id}` until `completed`.

## Validation

Run local validation:

```bash
python -m unittest discover -s tests -v
python -m compileall src
docker compose -f docker-compose.v2.yml build
```

Then start production services and verify:

```bash
docker compose -f docker-compose.v2.yml --profile workers up
curl http://localhost:8000/health
curl http://localhost:8000/api/readiness
```
