import os
import logging
import requests
from pathlib import Path
from typing import Any
from src.aspect_sentiment.audio import TranscriptionResult, WhisperTranscriber

logger = logging.getLogger(__name__)

class GroqCloudTranscriber:
    def __init__(self, model_size: str | None = None, device: str | None = None) -> None:
        # Match WhisperTranscriber interface
        self.model_size = model_size or os.getenv("WHISPER_MODEL", "whisper-large-v3")
        self.device = device or "cpu"

    def transcribe(self, audio_path: Path, language_hint: str | None = None) -> TranscriptionResult:
        logger.info("Transcribing audio via Groq Whisper API: %s", audio_path)
        
        api_key = os.getenv("LLAMA_API_KEY")
        if not api_key:
            raise ValueError("LLAMA_API_KEY environment variable is not set")
            
        base_url = os.getenv("LLAMA_API_URL", "https://api.groq.com/openai/v1")
        # Strip trailing slash or path suffix if it has /chat/completions
        base_url = base_url.removesuffix("/chat/completions").rstrip("/")
        url = f"{base_url}/audio/transcriptions"
        
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        # Read file bytes
        with open(audio_path, "rb") as f:
            files = {
                "file": (Path(audio_path).name, f, "audio/wav")
            }
            # Request both segment and word timestamps to enable downstream diarization
            data = [
                ("model", self.model_size),
                ("response_format", "verbose_json"),
                ("timestamp_granularities[]", "segment"),
                ("timestamp_granularities[]", "word"),
            ]
            if language_hint:
                data.append(("language", language_hint))
                
            response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            
        # Extract fields
        text = (result.get("text") or "").strip()
        raw_segments = result.get("segments") or []
        
        # Clean segments and estimate metrics using static methods in WhisperTranscriber
        cleaned_segments = WhisperTranscriber._clean_segments(raw_segments)
        confidence = WhisperTranscriber._estimate_confidence(result)
        duration = WhisperTranscriber._estimate_duration(result)
        language = result.get("language")
        
        return TranscriptionResult(
            text=text,
            segments=cleaned_segments,
            language=language,
            confidence=confidence,
            duration_seconds=duration
        )
