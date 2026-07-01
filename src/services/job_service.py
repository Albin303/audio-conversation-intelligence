"""Job service — manages job status retrieval queries."""

from __future__ import annotations

from typing import Any

from src.nexus_ai.repositories.sqlite import JobRepository


class JobService:
    """Retrieves job status from in-memory dict and SQLite."""

    def __init__(self) -> None:
        self.job_repository = JobRepository()

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Look up a job, first from in-memory dict, then SQLite."""
        persisted = self.job_repository.get(job_id)
        if persisted:
            return {
                "job_id": persisted["id"],
                "status": persisted["status"],
                "filename": persisted["filename"],
                "storage_path": persisted["storage_path"],
                "progress_stage": persisted.get("progress_stage"),
                "progress_percent": persisted.get("progress_percent"),
                "error": persisted.get("error"),
                "result": persisted.get("result"),
            }
        return None


job_service = JobService()
