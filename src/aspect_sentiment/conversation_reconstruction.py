from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from src.aspect_sentiment.diarization import DiarizationResult, TranscriptTurn


ENDING_RX = re.compile(r"[.!?]$")
FRAGMENT_START_RX = re.compile(r"^(and|but|or|so|because|then|also|with|for|to)\b", re.IGNORECASE)


@dataclass(slots=True)
class ReconstructionMetadata:
    confidence: float
    warnings: list[str] = field(default_factory=list)
    fallback_used: bool = False
    model_used: str = "deterministic-reconstruction-v1"
    processing_time_ms: int = 0
    merged_fragments: int = 0
    overlap_turns: int = 0


@dataclass(slots=True)
class ReconstructionResult:
    turns: list[TranscriptTurn]
    metadata: ReconstructionMetadata

    @property
    def formatted(self) -> str:
        return "\n".join(f"{turn.speaker}: {turn.text}" for turn in self.turns if turn.text)


def _is_fragment(text: str) -> bool:
    words = text.split()
    if not words:
        return True
    if len(words) <= 3 and not ENDING_RX.search(text):
        return True
    return bool(FRAGMENT_START_RX.search(text)) and not text[:1].isupper()


def _merge_confidence(left: float | None, right: float | None) -> float | None:
    values = [value for value in (left, right) if value is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def reconstruct_conversation(diarization: DiarizationResult) -> ReconstructionResult:
    """Rebuild readable conversation turns from diarized transcript fragments."""
    started = time.perf_counter()
    warnings = list(diarization.warnings)
    merged_fragments = 0
    sorted_turns = sorted(
        [turn for turn in diarization.turns if turn.text.strip()],
        key=lambda turn: (
            float("inf") if turn.start is None else turn.start,
            float("inf") if turn.end is None else turn.end,
        ),
    )

    reconstructed: list[TranscriptTurn] = []
    for turn in sorted_turns:
        clean_text = " ".join(turn.text.split())
        if not clean_text:
            continue

        should_merge = False
        if reconstructed and reconstructed[-1].speaker == turn.speaker:
            should_merge = True
        elif reconstructed and _is_fragment(clean_text):
            should_merge = True

        if should_merge and reconstructed:
            previous = reconstructed[-1]
            previous.text = f"{previous.text} {clean_text}".strip()
            previous.end = turn.end if turn.end is not None else previous.end
            previous.confidence = _merge_confidence(previous.confidence, turn.confidence)
            previous.overlap = previous.overlap or turn.overlap
            previous.warnings = list(dict.fromkeys([*previous.warnings, *turn.warnings]))
            merged_fragments += 1
            continue

        reconstructed.append(
            TranscriptTurn(
                speaker=turn.speaker if turn.speaker in {"Agent", "Customer", "Unknown"} else "Unknown",
                raw_speaker=turn.raw_speaker,
                text=clean_text,
                start=turn.start,
                end=turn.end,
                confidence=turn.confidence,
                overlap=turn.overlap,
                warnings=list(turn.warnings),
            )
        )

    if any(turn.start is None or turn.end is None for turn in reconstructed):
        warnings.append("missing_timestamps")
    if any(turn.overlap for turn in reconstructed):
        warnings.append("overlapping_speech_preserved")
    if any(turn.speaker == "Unknown" for turn in reconstructed):
        warnings.append("unknown_speaker_present")

    confidence_values = [turn.confidence for turn in reconstructed if turn.confidence is not None]
    confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.5
    confidence = max(0.0, min(1.0, confidence - (0.03 * len(set(warnings)))))

    return ReconstructionResult(
        turns=reconstructed,
        metadata=ReconstructionMetadata(
            confidence=round(confidence, 4),
            warnings=list(dict.fromkeys(warnings)),
            fallback_used=False,
            processing_time_ms=int((time.perf_counter() - started) * 1000),
            merged_fragments=merged_fragments,
            overlap_turns=sum(1 for turn in reconstructed if turn.overlap),
        ),
    )
