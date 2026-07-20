"""Container worker entry point using SQLite as the shared job queue."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

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

from src.core.logging import configure_logging
from src.nexus_ai.core.paths import ensure_runtime_dirs
from src.nexus_ai.repositories.sqlite import JobRepository, init_sqlite


POLL_SECONDS = float(os.getenv("WORKER_POLL_SECONDS", "1.0"))
JOB_REPOSITORY = JobRepository()
_AUDIO_TRANSCRIBER: Any | None = None


def utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _update(job_id: str, **kwargs: Any) -> None:
    JOB_REPOSITORY.update(job_id, updated_at=utc_now(), **kwargs)


def _serialize_diarization(diarization: Any) -> dict[str, Any]:
    return {
        "turns": [asdict(turn) for turn in diarization.turns],
        "speaker_map": diarization.speaker_map,
        "provider": diarization.provider,
        "speaker_confidence": diarization.speaker_confidence,
        "warnings": diarization.warnings,
    }


def _deserialize_diarization(payload: Any) -> Any:
    from src.aspect_sentiment.diarization import DiarizationResult, TranscriptTurn

    if isinstance(payload, list):
        turns = []
        for turn in payload:
            if not isinstance(turn, dict):
                continue
            turns.append(TranscriptTurn(
                speaker=turn.get("speaker", "Unknown"),
                raw_speaker=turn.get("rawSpeaker") or turn.get("speaker", "Unknown"),
                text=turn.get("text", ""),
                start=turn.get("start"),
                end=turn.get("end"),
                confidence=turn.get("confidence", 1.0),
                overlap=turn.get("overlap", False),
                warnings=turn.get("warnings") or [],
            ))
        return DiarizationResult(
            turns=turns,
            speaker_map={},
            provider="frontend-provided",
            speaker_confidence={},
            warnings=[],
        )

    if isinstance(payload, dict):
        return DiarizationResult(
            turns=[TranscriptTurn(**turn) for turn in payload.get("turns", [])],
            speaker_map=payload.get("speaker_map") or {},
            provider=payload.get("provider") or "worker-payload",
            speaker_confidence=payload.get("speaker_confidence") or {},
            warnings=payload.get("warnings") or [],
        )
    return None


def _get_audio_transcriber() -> Any:
    global _AUDIO_TRANSCRIBER
    if _AUDIO_TRANSCRIBER is None:
        if os.getenv("USE_GROQ_WHISPER", "true").lower() == "true":
            from src.aspect_sentiment.groq_audio import GroqCloudTranscriber

            _AUDIO_TRANSCRIBER = GroqCloudTranscriber()
        else:
            from src.aspect_sentiment.audio import WhisperTranscriber

            _AUDIO_TRANSCRIBER = WhisperTranscriber()
    return _AUDIO_TRANSCRIBER


async def process_audio_job(job: dict[str, Any]) -> None:
    from src.aspect_sentiment.diarization import diarize_audio_segments

    job_id = str(job["id"])
    storage_path = Path(str(job["storage_path"]))
    payload = job.get("payload") or {}

    _update(job_id, status="processing", progress_stage="Transcribing", progress_percent=20)
    transcriber = _get_audio_transcriber()
    transcription = await asyncio.to_thread(transcriber.transcribe, storage_path)

    _update(job_id, status="processing", progress_stage="Speaker Diarization", progress_percent=45)
    diarization = await asyncio.to_thread(diarize_audio_segments, storage_path, transcription.segments)

    next_payload = {
        **payload,
        "text": transcription.text,
        "source_name": job.get("filename") or storage_path.name,
        "language": transcription.language,
        "transcription_confidence": transcription.confidence,
        "duration_seconds": transcription.duration_seconds,
        "whisper_model": getattr(transcriber, "model_size", None),
        "diarization": _serialize_diarization(diarization),
    }
    _update(
        job_id,
        status="awaiting_ml",
        payload=next_payload,
        progress_stage="Waiting for ML worker",
        progress_percent=70,
    )


async def process_ml_job(job: dict[str, Any]) -> None:
    from src.services.analysis_service import analysis_service

    job_id = str(job["id"])
    payload = job.get("payload") or {}
    source_type = str(job.get("source_type") or "text")
    source_name = str(payload.get("source_name") or job.get("filename") or f"{source_type}-{job_id}")
    text = str(payload.get("text") or "")
    if not text.strip():
        raise ValueError("Job payload is missing transcript text")

    _update(job_id, status="processing", progress_stage="Feature Extraction", progress_percent=75)
    started = float(payload.get("started_at") or time.perf_counter())
    diarization_payload = payload.get("diarization") or payload.get("diarizedTranscript")
    diarization = _deserialize_diarization(diarization_payload) if diarization_payload else None

    result = await analysis_service.run_pipeline(
        text,
        source_name=source_name,
        source_type=source_type,
        started=started,
        diarization=diarization,
        transcription_confidence=payload.get("transcription_confidence"),
        whisper_model=payload.get("whisper_model"),
        language=payload.get("language"),
    )
    from src.services.sap_lead_service import sap_lead_service

    result["sapLead"] = await sap_lead_service.create_lead_from_analysis(result)

    safe_text = analysis_service.privacy_safe_csv_text(result, text)
    analysis_service.append_transcript_csv(
        source_name=source_name,
        text=safe_text,
        result=result,
        language=result.get("metadata", {}).get("language"),
        duration_s=payload.get("duration_seconds"),
    )
    analysis_service.append_transcript_sqlite(
        source_name=source_name,
        source_type=source_type,
        text=safe_text,
        result=result,
        language=result.get("metadata", {}).get("language"),
        duration_s=payload.get("duration_seconds"),
    )

    _update(
        job_id,
        status="completed",
        result=result,
        completed_at=utc_now(),
        progress_stage="Completed",
        progress_percent=100,
    )


def claim_audio_job() -> dict[str, Any] | None:
    return JOB_REPOSITORY.claim_next(
        statuses=("pending",),
        source_types=("audio",),
        claimed_status="processing",
        updated_at=utc_now(),
        progress_stage="Transcribing",
        progress_percent=10,
    )


def claim_ml_job() -> dict[str, Any] | None:
    text_job = JOB_REPOSITORY.claim_next(
        statuses=("pending",),
        source_types=("text",),
        claimed_status="processing",
        updated_at=utc_now(),
        progress_stage="Feature Extraction",
        progress_percent=10,
    )
    if text_job:
        return text_job
    return JOB_REPOSITORY.claim_next(
        statuses=("awaiting_ml",),
        source_types=("audio",),
        claimed_status="processing",
        updated_at=utc_now(),
        progress_stage="Feature Extraction",
        progress_percent=75,
    )


async def run_forever(worker_type: str) -> None:
    print(f"Starting {worker_type} worker with SQLite queue polling.")
    while True:
        job = claim_audio_job() if worker_type == "audio" else claim_ml_job()
        if not job:
            await asyncio.sleep(POLL_SECONDS)
            continue

        job_id = str(job["id"])
        try:
            if worker_type == "audio":
                await process_audio_job(job)
            else:
                await process_ml_job(job)
        except Exception as exc:
            _update(
                job_id,
                status="failed",
                error=str(exc),
                completed_at=utc_now(),
                progress_stage="Failed",
            )


def main() -> None:
    configure_logging()
    ensure_runtime_dirs()
    init_sqlite()
    worker_type = os.getenv("WORKER_TYPE", "audio").lower()
    if worker_type not in {"audio", "ml"}:
        raise ValueError(f"Unsupported WORKER_TYPE: {worker_type}")
    asyncio.run(run_forever(worker_type))


if __name__ == "__main__":
    main()
