"""Thin FastAPI routing layer — delegates all business logic to services."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi import APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.nexus_ai.core.paths import AUDIO_UPLOADS_DIR, SQLITE_DB_PATH, ensure_runtime_dirs
from src.nexus_ai.repositories.sqlite import init_sqlite
from src.nexus_ai.repositories.sqlite import JobRepository
from src.core.logging import configure_logging
from src.middleware.request_context import request_context_middleware
from src.services.health_service import database_check, storage_check, worker_check
from src.services.upload_service import upload_service
from src.services.job_service import job_service
from src.services.follow_up_service import follow_up_service
from src.services.dashboard_service import dashboard_service
from src.services.report_service import report_service

# Backward-compatible re-exports for existing tests and internal callers
readiness = dashboard_service.readiness
import uuid
from datetime import datetime, timezone


REPO_ROOT = Path(__file__).resolve().parents[2]
JOB_REPOSITORY = JobRepository()


def local_structured_entities(text: str, diarization: Any) -> list[dict[str, Any]]:
    from src.services.analysis_service import analysis_service

    return analysis_service.local_structured_entities(text, diarization)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file(REPO_ROOT / ".env.local")
load_env_file(REPO_ROOT / ".env")
configure_logging()


app = FastAPI(title="AI Audio Analysis API", version="1.0.0")
app.middleware("http")(request_context_middleware)

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", ",".join(DEFAULT_ALLOWED_ORIGINS)).split(",")
    if origin.strip()
]


@app.on_event("startup")
async def startup_event():
    existing = os.environ.get("PATH", "").split(os.pathsep)
    for ffmpeg_dir in REPO_ROOT.glob("ffmpeg-*"):
        candidate = ffmpeg_dir / "bin"
        if candidate.exists() and str(candidate) not in existing:
            os.environ["PATH"] = str(candidate) + os.pathsep + os.environ.get("PATH", "")
            break
    ensure_runtime_dirs()
    init_sqlite()



app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ #
# Request Models
# ------------------------------------------------------------------ #

class DiarizedTurn(BaseModel):
    speaker: str
    text: str
    start: float | None = None
    end: float | None = None
    rawSpeaker: str | None = None


class TextAnalysisRequest(BaseModel):
    text: str
    sourceName: str = "typed-conversation"
    diarizedTranscript: list[DiarizedTurn] | None = None


class FollowUpStatusRequest(BaseModel):
    status: str


# ------------------------------------------------------------------ #
# Routes — thin wrappers around services
# ------------------------------------------------------------------ #

@app.get("/health")
@app.get("/api/health")
def health() -> dict[str, Any]:
    return dashboard_service.health()


@app.get("/api/readiness")
def readiness() -> dict[str, Any]:
    return dashboard_service.readiness()


@app.get("/live")
@app.get("/api/live")
def liveness() -> dict[str, Any]:
    return {"status": "alive"}


@app.get("/ready")
@app.get("/api/ready")
def ready() -> dict[str, Any]:
    return dashboard_service.readiness()


@app.get("/api/health/database")
def health_database() -> dict[str, Any]:
    return database_check()


@app.get("/api/health/storage")
def health_storage() -> dict[str, Any]:
    return storage_check()


@app.get("/api/health/worker")
def health_worker() -> dict[str, Any]:
    return worker_check()


@app.get("/api/follow-up-alerts")
def get_follow_up_alerts(
    priority: str | None = None,
    status: str | None = None,
    customer_name: str | None = None,
) -> dict[str, Any]:
    return follow_up_service.list_alerts(
        priority=priority,
        status=status,
        customer_name=customer_name,
    )


@app.patch("/api/follow-up-alerts/{alert_id}")
def patch_follow_up_alert(alert_id: str, request: FollowUpStatusRequest) -> dict[str, Any]:
    try:
        return follow_up_service.update_status(alert_id, request.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/analyze")
async def analyze_text(request: TextAnalysisRequest) -> dict[str, Any]:
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Conversation text is required.")

    job_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    JOB_REPOSITORY.create(
        job_id=job_id,
        status="pending",
        filename=request.sourceName,
        storage_path="",
        source_type="text",
        payload={
            "text": request.text,
            "source_name": request.sourceName,
            "diarizedTranscript": [turn.model_dump() for turn in request.diarizedTranscript] if request.diarizedTranscript else None,
        },
        created_at=created_at,
    )
    return {"job_id": job_id, "status": "pending"}


@app.post("/api/upload")
async def upload_audio(audio: UploadFile = File(...)) -> dict[str, Any]:
    data = await audio.read()
    return await upload_service.upload_audio(audio.filename or "", data)


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str) -> dict[str, Any]:
    job = job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.websocket("/api/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    buffer = b""
    try:
        while True:
            data = await websocket.receive_bytes()
            buffer += data
            await websocket.send_json({"status": "receiving", "bytes_received": len(buffer)})
    except WebSocketDisconnect:
        pass


# ------------------------------------------------------------------ #
# Versioned API router (legacy compatibility)
# ------------------------------------------------------------------ #

v1_router = APIRouter(prefix="/api/v1")
v1_router.add_api_route("/health", health, methods=["GET"])
v1_router.add_api_route("/health/liveness", liveness, methods=["GET"])
v1_router.add_api_route("/health/readiness", readiness, methods=["GET"])
v1_router.add_api_route("/health/database", health_database, methods=["GET"])
v1_router.add_api_route("/health/storage", health_storage, methods=["GET"])
v1_router.add_api_route("/health/worker", health_worker, methods=["GET"])
v1_router.add_api_route("/analyze", analyze_text, methods=["POST"])
v1_router.add_api_route("/upload", upload_audio, methods=["POST"])
v1_router.add_api_route("/jobs/{job_id}", get_job_status, methods=["GET"])
v1_router.add_api_route("/followup", get_follow_up_alerts, methods=["GET"])
v1_router.add_api_route("/followup/{alert_id}", patch_follow_up_alert, methods=["PATCH"])
v1_router.add_api_route("/conversation/{job_id}", get_job_status, methods=["GET"])
v1_router.add_api_route("/dashboard", readiness, methods=["GET"])
v1_router.add_api_route("/settings", health, methods=["GET"])
v1_router.add_api_route("/admin", readiness, methods=["GET"])
v1_router.add_api_route("/report/{job_id}", get_job_status, methods=["GET"])
app.include_router(v1_router)


# Serve static files from Next.js export directory
from fastapi.staticfiles import StaticFiles
frontend_out = REPO_ROOT / "frontend" / "out"
if frontend_out.exists():
    app.mount("/", StaticFiles(directory=str(frontend_out), html=True), name="frontend")
else:
    import logging
    logging.getLogger("uvicorn").warning(f"Frontend static directory not found at {frontend_out}. Static files will not be served.")
