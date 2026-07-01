"""Dashboard service — aggregates health and readiness data."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from src.nexus_ai.core.paths import AUDIO_UPLOADS_DIR, SQLITE_DB_PATH
from src.services.health_service import (
    database_check,
    readiness_payload,
    storage_check,
    worker_check,
)


class DashboardService:
    """Aggregates dashboard/readiness payloads."""

    def health(self) -> dict[str, Any]:
        minimax_key = os.getenv("MINIMAX_API_KEY")
        diarization_provider = os.getenv("DIARIZATION_LLM_PROVIDER")
        if not diarization_provider:
            diarization_provider = "minimax" if minimax_key else "groq"

        return {
            "status": "ok",
            "llamaConfigured": bool(os.getenv("LLAMA_API_KEY")),
            "minimaxConfigured": bool(minimax_key),
            "leadModelLoaded": (Path("data") / "processed" / "lead_scoring_model.joblib").exists(),
            "whisperModel": os.getenv("WHISPER_MODEL", os.getenv("WHISPER_MODEL_SIZE", "whisper-large-v3")),
            "diarizationBackend": os.getenv("DIARIZATION_BACKEND", "free-local"),
            "diarizationLlmProvider": diarization_provider,
            "enableSpeakerTracking": os.getenv("ENABLE_SPEAKER_TRACKING", "true").lower() == "true",
            "roleBackend": os.getenv("ROLE_BACKEND", "hybrid"),
            "enableVAD": os.getenv("ENABLE_VAD", "true").lower() == "true",
            "roleConfidenceThreshold": float(os.getenv("ROLE_CONFIDENCE_THRESHOLD", "0.85")),
            "storageBackend": os.getenv("NEXUS_STORAGE_BACKEND", "sqlite"),
            "sqlitePath": str(SQLITE_DB_PATH),
            "uploadsDir": str(AUDIO_UPLOADS_DIR.parent),
        }

    def readiness(self) -> dict[str, Any]:
        minimax_key = os.getenv("MINIMAX_API_KEY")
        diarization_provider = os.getenv("DIARIZATION_LLM_PROVIDER")
        if not diarization_provider:
            diarization_provider = "minimax" if minimax_key else "groq"
        diarization_provider = diarization_provider.lower()

        use_llm = os.getenv("USE_LLM_DIARIZATION", os.getenv("USE_GROQ_WHISPER", "true")).lower() == "true"

        checks = {
            "conversionModel": (Path("models") / "sales_conversion_model.pkl").exists(),
            "modelFeatures": (Path("models") / "sales_conversion_features.pkl").exists(),
            "modelMetrics": (Path("models") / "sales_conversion_metrics.json").exists(),
            "leadModel": (Path("data") / "processed" / "lead_scoring_model.joblib").exists(),
            "ffmpeg": self._ffmpeg_available(),
            "llamaConfigured": bool(os.getenv("LLAMA_API_KEY")),
            "allowedOriginsConfigured": bool(
                [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
            ),
        }

        if use_llm and diarization_provider == "minimax":
            checks["minimaxConfigured"] = bool(minimax_key)

        return readiness_payload({
            "status": "ready" if all(checks.values()) else "degraded",
            "checks": checks,
            "whisperModel": os.getenv("WHISPER_MODEL", os.getenv("WHISPER_MODEL_SIZE", "whisper-large-v3")),
            "whisperDevice": os.getenv("WHISPER_DEVICE", "provider-managed" if os.getenv("USE_GROQ_WHISPER", "true").lower() == "true" else "cpu"),
            "diarizationBackend": os.getenv("DIARIZATION_BACKEND", "free-local"),
            "diarizationLlmProvider": diarization_provider,
            "enableSpeakerTracking": os.getenv("ENABLE_SPEAKER_TRACKING", "true").lower() == "true",
            "roleBackend": os.getenv("ROLE_BACKEND", "hybrid"),
            "enableVAD": os.getenv("ENABLE_VAD", "true").lower() == "true",
            "roleConfidenceThreshold": float(os.getenv("ROLE_CONFIDENCE_THRESHOLD", "0.85")),
            "storageBackend": os.getenv("NEXUS_STORAGE_BACKEND", "sqlite"),
            "sqlitePath": str(SQLITE_DB_PATH),
            "uploadsDir": str(AUDIO_UPLOADS_DIR.parent),
        })

    @staticmethod
    def _ffmpeg_available() -> bool:
        import shutil
        return shutil.which("ffmpeg") is not None


dashboard_service = DashboardService()