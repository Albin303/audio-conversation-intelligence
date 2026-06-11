from __future__ import annotations

import argparse
import json
import sys
import time
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.server import analyze_text_payload
from src.aspect_sentiment.audio import WhisperTranscriber
from src.aspect_sentiment.behavioral_signals import detect_signals
from src.aspect_sentiment.diarization import diarize_audio_segments


REQUIRED_TERMS = ["laptop", "60000", "dell", "lenovo"]


def validate_audio(audio_path: Path, min_confidence: float, min_turns: int) -> tuple[dict, list[str]]:
    transcriber = WhisperTranscriber()
    transcription = transcriber.transcribe(audio_path)
    diarization = diarize_audio_segments(audio_path, transcription.segments)
    result = asyncio.run(analyze_text_payload(
        transcription.text,
        source_name=audio_path.name,
        source_type="audio",
        language=transcription.language,
        transcription_confidence=transcription.confidence,
        whisper_model=transcriber.model_size,
        diarization=diarization,
        start_time=time.perf_counter(),
    ))

    customer_text = result.get("customerTranscript", "")
    agent_text = result.get("agentTranscript", "")
    transcript_lower = transcription.text.lower().replace(",", "")
    signals = detect_signals(customer_text, result.get("rawFeatures", []))

    failures: list[str] = []
    if transcription.confidence is None or transcription.confidence < min_confidence:
        failures.append(f"transcription confidence below threshold: {transcription.confidence}")
    if len(diarization.turns) < min_turns:
        failures.append(f"too few diarized turns: {len(diarization.turns)}")
    if not customer_text.strip():
        failures.append("missing customer transcript")
    if not agent_text.strip():
        failures.append("missing agent transcript")
    for term in REQUIRED_TERMS:
        if term not in transcript_lower:
            failures.append(f"required transcript term missing: {term}")
    if "asked_for_whatsapp" in signals.get("detected_positive", []):
        failures.append("false WhatsApp behavioral signal detected")
    if result.get("conversionScore", {}).get("label") not in {"warm", "hot", "cold"}:
        failures.append("conversion label is invalid")

    summary = {
        "audio": str(audio_path),
        "whisperModel": transcriber.model_size,
        "language": transcription.language,
        "confidence": transcription.confidence,
        "durationSeconds": transcription.duration_seconds,
        "segmentCount": len(transcription.segments),
        "diarizationProvider": diarization.provider,
        "turnCount": len(diarization.turns),
        "customerWordCount": len(customer_text.split()),
        "agentWordCount": len(agent_text.split()),
        "conversion": result.get("conversionScore", {}),
        "behavioralSignals": signals,
        "failures": failures,
    }
    return summary, failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a production smoke test for the audio pipeline.")
    parser.add_argument("--audio", type=Path, default=Path("audio/conv_001.wav"))
    parser.add_argument("--min-confidence", type=float, default=0.60)
    parser.add_argument("--min-turns", type=int, default=8)
    args = parser.parse_args()

    if not args.audio.exists():
        print(json.dumps({"failures": [f"audio file not found: {args.audio}"]}, indent=2))
        return 2

    summary, failures = validate_audio(args.audio, args.min_confidence, args.min_turns)
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
