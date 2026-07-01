from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

from src.workers.job_queue import AudioJob, JobQueue

logger = logging.getLogger("nexus.worker")


class WorkerManager:
    def __init__(
        self,
        queue: JobQueue,
        process_audio_job: Callable[[str, str, str, Any, Any, Any], Awaitable[None]],
        transcriber_factory: Callable[[], Any],
        diarize_fn: Any,
        analyze_fn: Any,
    ) -> None:
        self.queue = queue
        self.process_audio_job = process_audio_job
        self.transcriber_factory = transcriber_factory
        self.diarize_fn = diarize_fn
        self.analyze_fn = analyze_fn

    async def run_forever(self) -> None:
        logger.info("worker manager started")
        while True:
            job: AudioJob = await self.queue.dequeue()
            try:
                await self.process_audio_job(
                    job.job_id,
                    job.storage_path,
                    job.filename,
                    self.transcriber_factory,
                    self.diarize_fn,
                    self.analyze_fn,
                )
            except Exception:
                logger.exception("worker manager failed job", extra={"job_id": job.job_id})
            finally:
                self.queue.task_done()

    def start_background_task(self) -> asyncio.Task[None]:
        return asyncio.create_task(self.run_forever())
