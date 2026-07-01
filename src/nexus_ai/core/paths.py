from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def runtime_path(env_name: str, default_relative: str) -> Path:
    configured = os.getenv(env_name)
    if configured:
        return Path(configured).expanduser().resolve()
    return REPO_ROOT / default_relative


UPLOADS_DIR = runtime_path("NEXUS_UPLOADS_DIR", "uploads")
AUDIO_UPLOADS_DIR = UPLOADS_DIR / "audio"
PROCESSED_UPLOADS_DIR = UPLOADS_DIR / "processed"
REPORTS_DIR = UPLOADS_DIR / "reports"
DATABASE_DIR = runtime_path("NEXUS_DATABASE_DIR", "database")
LOGS_DIR = runtime_path("NEXUS_LOGS_DIR", "logs")
SQLITE_DB_PATH = Path(os.getenv("NEXUS_SQLITE_PATH", str(DATABASE_DIR / "nexus_ai.db"))).expanduser().resolve()


def ensure_runtime_dirs() -> None:
    for path in (
        UPLOADS_DIR,
        AUDIO_UPLOADS_DIR,
        PROCESSED_UPLOADS_DIR,
        REPORTS_DIR,
        DATABASE_DIR,
        LOGS_DIR,
        SQLITE_DB_PATH.parent,
    ):
        path.mkdir(parents=True, exist_ok=True)

