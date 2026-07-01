from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AudioJob:
    job_id: str
    storage_path: str
    filename: str


class JobQueue(Protocol):
    async def enqueue(self, job: AudioJob) -> None:
        ...

    async def dequeue(self) -> AudioJob:
        ...

    def task_done(self) -> None:
        ...


class InMemoryJobQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[AudioJob] = asyncio.Queue()

    async def enqueue(self, job: AudioJob) -> None:
        await self._queue.put(job)

    async def dequeue(self) -> AudioJob:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()

