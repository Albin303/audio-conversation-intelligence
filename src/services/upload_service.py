"""Upload service — manages audio upload and job creation."""

from __future__ import annotations

import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.nexus_ai.core.paths import AUDIO_UPLOADS_DIR, ensure_runtime_dirs
from src.nexus_ai.repositories.sqlite import JobRepository


class UploadService:
    """Orchestrates audio file upload, persistence, and job queueing."""

    def __init__(self) -> None:
        self.job_repository = JobRepository()

    async def upload_audio(self, filename: str, data: bytes) -> dict[str, Any]:
        """Save an audio file, create a processing job, enqueue it."""
        if not filename:
            raise ValueError("Audio filename is required.")

        job_id = str(uuid.uuid4())
        started = time.perf_counter()

        ensure_runtime_dirs()
        safe_filename = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(filename).name).strip("._") or "audio"
        tmp_path = AUDIO_UPLOADS_DIR / f"{job_id}_{safe_filename}"
        tmp_path.write_bytes(data)

        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self.job_repository.create(
            job_id=job_id,
            status="pending",
            filename=filename,
            storage_path=str(tmp_path),
            created_at=created_at,
            source_type="audio",
            payload={"started_at": started},
        )

        return {"job_id": job_id, "status": "pending"}


upload_service = UploadService()
