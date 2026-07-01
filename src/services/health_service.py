from __future__ import annotations

from pathlib import Path
from typing import Any

from src.nexus_ai.core.paths import AUDIO_UPLOADS_DIR, SQLITE_DB_PATH, ensure_runtime_dirs
from src.nexus_ai.repositories.sqlite import JobRepository, connect


def database_check() -> dict[str, Any]:
    try:
        with connect(SQLITE_DB_PATH) as connection:
            connection.execute("SELECT 1").fetchone()
        return {"status": "ok", "path": str(SQLITE_DB_PATH)}
    except Exception as exc:
        return {"status": "error", "path": str(SQLITE_DB_PATH), "error": str(exc)}


def storage_check() -> dict[str, Any]:
    try:
        ensure_runtime_dirs()
        probe = Path(AUDIO_UPLOADS_DIR) / ".storage_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return {"status": "ok", "uploadsDir": str(AUDIO_UPLOADS_DIR.parent)}
    except Exception as exc:
        return {"status": "error", "uploadsDir": str(AUDIO_UPLOADS_DIR.parent), "error": str(exc)}


def worker_check() -> dict[str, Any]:
    jobs = JobRepository().list_recent(limit=100)
    active_jobs = sum(1 for job in jobs if job.get("status") in {"pending", "processing", "awaiting_ml"})
    failed_jobs = sum(1 for job in jobs if job.get("status") == "failed")
    return {"status": "ok", "activeJobs": active_jobs, "failedJobs": failed_jobs}


def readiness_payload(base_payload: dict[str, Any]) -> dict[str, Any]:
    checks = {
        **base_payload.get("checks", {}),
        "database": database_check()["status"] == "ok",
        "storage": storage_check()["status"] == "ok",
        "worker": worker_check()["status"] == "ok",
    }
    return {
        **base_payload,
        "status": "ready" if all(checks.values()) else "degraded",
        "checks": checks,
        "runtime": {
            "database": database_check(),
            "storage": storage_check(),
            "worker": worker_check(),
        },
    }
