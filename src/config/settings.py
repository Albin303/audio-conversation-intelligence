from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = os.getenv("NEXUS_APP_NAME", "Speech Intelligence and Intent Detection")
    app_env: str = os.getenv("NEXUS_ENV", "development")
    api_prefix: str = os.getenv("NEXUS_API_PREFIX", "/api/v1")
    storage_backend: str = os.getenv("NEXUS_STORAGE_BACKEND", "sqlite")
    uploads_dir: Path = Path(os.getenv("NEXUS_UPLOADS_DIR", "uploads")).expanduser()
    database_dir: Path = Path(os.getenv("NEXUS_DATABASE_DIR", "database")).expanduser()
    logs_dir: Path = Path(os.getenv("NEXUS_LOGS_DIR", "logs")).expanduser()
    sqlite_path: Path = Path(os.getenv("NEXUS_SQLITE_PATH", "database/nexus_ai.db")).expanduser()
    use_groq_whisper: bool = _bool_env("USE_GROQ_WHISPER", True)
    enable_request_logging: bool = _bool_env("NEXUS_ENABLE_REQUEST_LOGGING", True)


settings = Settings()

