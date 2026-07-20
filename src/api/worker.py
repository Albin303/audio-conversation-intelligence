import asyncio
from typing import Any, Dict
from pathlib import Path
from datetime import datetime, timezone

from src.nexus_ai.repositories.sqlite import JobRepository
from src.workers.job_queue import AudioJob, InMemoryJobQueue

# Global dictionary to hold job status and results
JOBS: Dict[str, Dict[str, Any]] = {}
queue = InMemoryJobQueue()
JOB_REPOSITORY = JobRepository()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

async def process_audio_job(job_id: str, tmp_path: str, filename: str, transcriber, diarize_fn, analyze_fn):
    JOBS[job_id]["status"] = "processing"
    JOBS[job_id]["progress_stage"] = "Transcribing"
    JOBS[job_id]["progress_percent"] = 20
    JOB_REPOSITORY.update(
        job_id,
        status="processing",
        updated_at=utc_now(),
        progress_stage="Transcribing",
        progress_percent=20,
    )
    try:
        transcriber_instance = transcriber() if callable(transcriber) else transcriber
        # We run the heavy tasks in a thread pool to avoid blocking the event loop
        transcription = await asyncio.to_thread(transcriber_instance.transcribe, tmp_path)
        JOBS[job_id]["progress_stage"] = "Speaker Diarization"
        JOBS[job_id]["progress_percent"] = 45
        JOB_REPOSITORY.update(
            job_id,
            status="processing",
            updated_at=utc_now(),
            progress_stage="Speaker Diarization",
            progress_percent=45,
        )
        diarization = await asyncio.to_thread(diarize_fn, tmp_path, transcription.segments)
        JOBS[job_id]["progress_stage"] = "Feature Extraction"
        JOBS[job_id]["progress_percent"] = 65
        JOB_REPOSITORY.update(
            job_id,
            status="processing",
            updated_at=utc_now(),
            progress_stage="Feature Extraction",
            progress_percent=65,
        )
        
        stages = [
            {"id": "upload", "title": "Audio uploaded", "description": filename, "status": "completed"},
            {"id": "transcription", "title": "Speech transcription", "description": "Audio converted to text", "status": "completed"},
            {"id": "diarization", "title": "Speaker diarization", "description": "Agent and customer turns aligned", "status": "completed"},
            {"id": "privacy", "title": "Local PII extraction", "description": "Sensitive details redacted before LLaMA", "status": "completed"},
            {"id": "analysis", "title": "Feature extraction", "description": "Sales features extracted", "status": "completed"},
            {"id": "prediction", "title": "Conversion scoring", "description": "Lead score calculated", "status": "completed"},
        ]
        
        result = await analyze_fn(
            transcription.text,
            source_name=filename,
            source_type="audio",
            language=transcription.language,
            transcription_confidence=transcription.confidence,
            whisper_model=transcriber_instance.model_size,
            diarization=diarization,
            started=JOBS[job_id]["started_at"],
        )
        from src.services.sap_lead_service import sap_lead_service

        result["sapLead"] = await sap_lead_service.create_lead_from_analysis(result)
        
        JOBS[job_id]["status"] = "completed"
        JOBS[job_id]["progress_stage"] = "Completed"
        JOBS[job_id]["progress_percent"] = 100
        JOBS[job_id]["result"] = result
        JOB_REPOSITORY.update(
            job_id,
            status="completed",
            result=result,
            updated_at=utc_now(),
            completed_at=utc_now(),
            progress_stage="Completed",
            progress_percent=100,
        )
        
    except Exception as e:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["progress_stage"] = "Failed"
        JOBS[job_id]["error"] = str(e)
        JOB_REPOSITORY.update(
            job_id,
            status="failed",
            error=str(e),
            updated_at=utc_now(),
            completed_at=utc_now(),
            progress_stage="Failed",
        )
    finally:
        if not JOBS[job_id].get("persistent_upload"):
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass

async def background_worker(transcriber, diarize_fn, analyze_fn):
    print("Background worker started.")
    while True:
        job: AudioJob = await queue.dequeue()
        job_id = job.job_id
        tmp_path = job.storage_path
        filename = job.filename
        
        try:
            await process_audio_job(job_id, tmp_path, filename, transcriber, diarize_fn, analyze_fn)
        except Exception as e:
            print(f"Worker error on job {job_id}: {e}")
        finally:
            queue.task_done()
