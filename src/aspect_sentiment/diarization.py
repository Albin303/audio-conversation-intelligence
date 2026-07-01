from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
import wave
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLE_RATE = 16000

SPEAKER_LABEL_RX = re.compile(
    r"(?i)(?<![A-Za-z])\[?\s*(customer|agent|speaker\s*[ab]|speaker_[ab])\s*\]?\s*:"
)
SENTENCE_SPLIT_RX = re.compile(r"(?<=[.!?])\s+")
AGENT_TERMS = {
    "good morning sir",
    "good afternoon sir",
    "how are you",
    "what about your name",
    "what about your job",
    "features you need",
    "good to know",
    "we have",
    "i can suggest",
    "i will share",
    "emi offer",
    "offer available",
    "available",
    "recommend",
    "let me",
    "our",
}
CUSTOMER_TERMS = {
    "my name",
    "my budget",
    "i am earning",
    "i am a",
    "i need",
    "i want",
    "my budget",
    "i mostly",
    "i may",
    "i think",
    "not sure",
    "under",
    "looking for",
    "can you",
}


@dataclass(slots=True)
class TranscriptTurn:
    speaker: str
    text: str
    start: float | None = None
    end: float | None = None
    raw_speaker: str | None = None
    confidence: float | None = None
    overlap: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DiarizationResult:
    turns: list[TranscriptTurn]
    speaker_map: dict[str, str] = field(default_factory=dict)
    provider: str = "heuristic"
    speaker_confidence: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def formatted(self) -> str:
        return "\n".join(f"{turn.speaker}: {turn.text}" for turn in self.turns if turn.text)

    @property
    def customer_text(self) -> str:
        return " ".join(turn.text for turn in self.turns if turn.speaker in {"Customer", "Guest"}).strip()

    @property
    def guest_text(self) -> str:
        return " ".join(turn.text for turn in self.turns if turn.speaker == "Guest").strip()

    @property
    def agent_text(self) -> str:
        return " ".join(turn.text for turn in self.turns if turn.speaker == "Agent").strip()

    @property
    def speaker_confidence_resolved(self) -> dict[str, float]:
        resolved = {}
        for spk, conf in self.speaker_confidence.items():
            resolved_spk = self.speaker_map.get(spk, spk)
            resolved[resolved_spk] = conf
        for turn in self.turns:
            if turn.speaker and turn.confidence is not None:
                if turn.speaker not in resolved:
                    resolved[turn.speaker] = turn.confidence
                else:
                    # average it if already present
                    resolved[turn.speaker] = (resolved[turn.speaker] + turn.confidence) / 2
        return {k: round(v, 4) for k, v in resolved.items()}

    @property
    def speaker_duration(self) -> dict[str, float]:
        durations = {}
        for turn in self.turns:
            if not turn.speaker:
                continue
            if turn.start is not None and turn.end is not None:
                dur = max(0.0, turn.end - turn.start)
            else:
                dur = len(turn.text.split()) / 2.5
            durations[turn.speaker] = durations.get(turn.speaker, 0.0) + dur
        return {spk: round(dur, 4) for spk, dur in durations.items()}

    @property
    def speaking_ratio(self) -> dict[str, float]:
        durations = self.speaker_duration
        total_duration = sum(durations.values())
        if total_duration <= 0:
            return {spk: 0.0 for spk in durations}
        return {spk: round(dur / total_duration, 4) for spk, dur in durations.items()}

    @property
    def silence_duration(self) -> float:
        timed_turns = sorted(
            [t for t in self.turns if t.start is not None and t.end is not None],
            key=lambda t: t.start
        )
        if not timed_turns:
            return 0.0
        
        silence = 0.0
        max_end = timed_turns[0].end
        for turn in timed_turns[1:]:
            if turn.start > max_end:
                silence += turn.start - max_end
            max_end = max(max_end, turn.end)
        return round(silence, 4)

    @property
    def interruptions(self) -> dict[str, int]:
        counts = {spk: 0 for spk in set(t.speaker for t in self.turns if t.speaker)}
        timed_turns = sorted(
            [t for t in self.turns if t.start is not None and t.end is not None and t.speaker],
            key=lambda t: t.start
        )
        for i in range(1, len(timed_turns)):
            prev_turn = timed_turns[i - 1]
            curr_turn = timed_turns[i]
            if curr_turn.speaker != prev_turn.speaker:
                if curr_turn.start < prev_turn.end - 0.05:
                    counts[curr_turn.speaker] = counts.get(curr_turn.speaker, 0) + 1
        return counts

    @property
    def average_turn_length(self) -> dict[str, float]:
        durations = {}
        counts = {}
        for turn in self.turns:
            if not turn.speaker:
                continue
            if turn.start is not None and turn.end is not None:
                dur = max(0.0, turn.end - turn.start)
            else:
                dur = len(turn.text.split()) / 2.5
            durations[turn.speaker] = durations.get(turn.speaker, 0.0) + dur
            counts[turn.speaker] = counts.get(turn.speaker, 0) + 1
        return {spk: round(durations[spk] / counts[spk], 4) if counts[spk] > 0 else 0.0 for spk in durations}

    @property
    def consecutive_turns(self) -> dict[str, int]:
        consecutive = {}
        prev_speaker = None
        for turn in self.turns:
            if not turn.speaker:
                continue
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", turn.text) if s.strip()]
            for _ in sentences:
                if turn.speaker == prev_speaker:
                    consecutive[turn.speaker] = consecutive.get(turn.speaker, 0) + 1
                prev_speaker = turn.speaker
        return consecutive

    @property
    def metrics(self) -> dict[str, Any]:
        return {
            "speaker_confidence": self.speaker_confidence_resolved,
            "speaker_duration": self.speaker_duration,
            "speaking_ratio": self.speaking_ratio,
            "interruptions": self.interruptions,
            "average_turn_length": self.average_turn_length,
            "silence_duration": self.silence_duration,
            "consecutive_turns": self.consecutive_turns,
        }


def _normalize_role(label: str) -> str:
    compact = label.strip().lower().replace("_", " ")
    if compact == "customer":
        return "Customer"
    if compact == "agent":
        return "Agent"
    if compact == "guest":
        return "Guest"
    if compact in {"speaker a", "speaker a"}:
        return "Customer"
    if compact in {"speaker b", "speaker b"}:
        return "Agent"
    return label.strip().title()


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def _turn_overlap_count(
    start: float,
    end: float,
    intervals: list[tuple[float, float, str]],
) -> int:
    speakers = {
        speaker
        for interval_start, interval_end, speaker in intervals
        if _overlap_seconds(start, end, interval_start, interval_end) > 0.05
    }
    return len(speakers)


def _role_from_classification(result: dict[str, Any]) -> str:
    role = str(result.get("role") or "Unknown").title()
    if role not in {"Agent", "Customer", "Guest"}:
        return "Unknown"
    confidence = float(result.get("confidence", 0.0) or 0.0)
    threshold = float(os.getenv("ROLE_CONFIDENCE_THRESHOLD", "0.85"))
    return role if confidence >= threshold else "Unknown"


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _guess_speaker_from_text(text: str, index: int, fallback: str | None = None) -> str:
    lower = text.lower()
    customer_score = sum(1 for term in CUSTOMER_TERMS if term in lower)
    agent_score = sum(1 for term in AGENT_TERMS if term in lower)
    if "?" in text and any(term in lower for term in ["your name", "your job", "you need", "can i help", "what about", "use it for", "brand preference"]):
        agent_score += 2
    if any(term in lower for term in ["i can suggest", "we currently", "we have", "i will share", "i'll share", "both are good", "available"]):
        agent_score += 2
    if any(term in lower for term in ["i want", "i need", "not really", "not sure", "i'll think", "i will think", "get back to you"]):
        customer_score += 2
    if customer_score > agent_score:
        return "Customer"
    if agent_score > customer_score:
        return "Agent"
    if fallback in {"Agent", "Customer"}:
        return fallback
    return "Customer" if index % 2 == 0 else "Agent"


def _sentence_parts(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_SPLIT_RX.split(text.strip()) if part.strip()]


def _split_turn_by_sentence(
    turn: TranscriptTurn,
    start_index: int,
    *,
    preserve_speaker: bool = False,
) -> list[TranscriptTurn]:
    parts = _sentence_parts(turn.text)
    resolved_speaker = (
        _guess_speaker_from_text(turn.text, start_index, turn.speaker)
        if preserve_speaker
        else None
    )
    if len(parts) <= 1:
        guessed = resolved_speaker or _guess_speaker_from_text(turn.text, start_index, turn.speaker)
        return [
            TranscriptTurn(
                speaker=guessed,
                raw_speaker=turn.raw_speaker,
                text=turn.text,
                start=turn.start,
                end=turn.end,
                confidence=turn.confidence,
                overlap=turn.overlap,
                warnings=list(turn.warnings),
            )
        ]

    duration = None
    if turn.start is not None and turn.end is not None and turn.end > turn.start:
        duration = turn.end - turn.start
    total_chars = max(1, sum(len(part) for part in parts))
    cursor = turn.start

    split_turns: list[TranscriptTurn] = []
    for offset, part in enumerate(parts):
        part_start = cursor
        part_end = None
        if duration is not None and cursor is not None:
            part_duration = duration * (len(part) / total_chars)
            part_end = min(turn.end, cursor + part_duration) if turn.end is not None else cursor + part_duration
            cursor = part_end

        split_turns.append(
            TranscriptTurn(
                speaker=resolved_speaker
                or _guess_speaker_from_text(part, start_index + offset, turn.speaker),
                raw_speaker=turn.raw_speaker,
                text=part,
                start=part_start,
                end=part_end,
                confidence=turn.confidence,
                overlap=turn.overlap,
                warnings=list(turn.warnings),
            )
        )

    return split_turns


def _refine_turn_roles(turns: list[TranscriptTurn], *, preserve_speakers: bool = False) -> list[TranscriptTurn]:
    refined: list[TranscriptTurn] = []
    sentence_index = 0
    for turn in turns:
        split_turns = _split_turn_by_sentence(turn, sentence_index, preserve_speaker=preserve_speakers)
        refined.extend(split_turns)
        sentence_index += len(split_turns)
    return _merge_turns(refined)


def _merge_turns(turns: list[TranscriptTurn]) -> list[TranscriptTurn]:
    merged: list[TranscriptTurn] = []
    for turn in turns:
        if not turn.text.strip():
            continue
        if merged and merged[-1].speaker == turn.speaker:
            merged[-1].text = f"{merged[-1].text} {turn.text}".strip()
            merged[-1].end = turn.end if turn.end is not None else merged[-1].end
            if merged[-1].confidence is not None or turn.confidence is not None:
                confidence_values = [
                    value
                    for value in (merged[-1].confidence, turn.confidence)
                    if value is not None
                ]
                merged[-1].confidence = _mean(confidence_values)
            merged[-1].overlap = merged[-1].overlap or turn.overlap
            merged[-1].warnings = list(dict.fromkeys([*merged[-1].warnings, *turn.warnings]))
        else:
            merged.append(turn)
    return merged


def _ffmpeg_executable() -> str:
    for ffmpeg_dir in REPO_ROOT.glob("ffmpeg-*"):
        candidate = ffmpeg_dir / "bin" / "ffmpeg.exe"
        if candidate.exists():
            return str(candidate)
    return "ffmpeg"


def _load_audio_mono(audio_path: Path, sample_rate: int = DEFAULT_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        wav_path = Path(tmp.name)

    command = [
        _ffmpeg_executable(),
        "-y",
        "-i",
        str(audio_path),
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "wav",
        str(wav_path),
    ]

    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with wave.open(str(wav_path), "rb") as handle:
            rate = handle.getframerate()
            frames = handle.readframes(handle.getnframes())
            samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    finally:
        wav_path.unlink(missing_ok=True)

    return samples, rate


def _segment_samples(samples: np.ndarray, sample_rate: int, start: float, end: float) -> np.ndarray:
    start_index = max(0, int(start * sample_rate))
    end_index = min(len(samples), int(max(end, start + 0.2) * sample_rate))
    return samples[start_index:end_index]


def _frame_audio(samples: np.ndarray, frame_size: int, hop_size: int) -> np.ndarray:
    if len(samples) < frame_size:
        padded = np.pad(samples, (0, frame_size - len(samples)))
        return padded.reshape(1, frame_size)
    frame_count = 1 + (len(samples) - frame_size) // hop_size
    shape = (frame_count, frame_size)
    strides = (samples.strides[0] * hop_size, samples.strides[0])
    return np.lib.stride_tricks.as_strided(samples, shape=shape, strides=strides).copy()


def _acoustic_features(samples: np.ndarray, sample_rate: int) -> list[float]:
    if len(samples) == 0:
        return [0.0] * 10

    frame_size = int(sample_rate * 0.025)
    hop_size = int(sample_rate * 0.010)
    frames = _frame_audio(samples, frame_size, hop_size)
    window = np.hanning(frame_size).astype(np.float32)
    windowed = frames * window

    rms = np.sqrt(np.mean(np.square(frames), axis=1) + 1e-9)
    zcr = np.mean(np.abs(np.diff(np.signbit(frames), axis=1)), axis=1)
    spectrum = np.abs(np.fft.rfft(windowed, axis=1)) + 1e-9
    freqs = np.fft.rfftfreq(frame_size, d=1.0 / sample_rate)
    spectral_sum = np.sum(spectrum, axis=1)
    centroid = np.sum(spectrum * freqs, axis=1) / spectral_sum
    bandwidth = np.sqrt(np.sum(spectrum * np.square(freqs - centroid[:, None]), axis=1) / spectral_sum)
    peak_freq = freqs[np.argmax(spectrum, axis=1)]

    return [
        float(np.mean(rms)),
        float(np.std(rms)),
        float(np.percentile(rms, 90)),
        float(np.mean(zcr)),
        float(np.std(zcr)),
        float(np.mean(centroid)),
        float(np.std(centroid)),
        float(np.mean(bandwidth)),
        float(np.std(bandwidth)),
        float(np.mean(peak_freq)),
    ]


def _role_map_from_cluster_text(cluster_texts: dict[int, list[str]]) -> dict[int, str]:
    scores: dict[int, int] = {}
    for cluster_id, texts in cluster_texts.items():
        joined = " ".join(texts).lower()
        customer_score = sum(1 for term in CUSTOMER_TERMS if term in joined)
        agent_score = sum(1 for term in AGENT_TERMS if term in joined)
        scores[cluster_id] = customer_score - agent_score

    if not scores:
        return {}

    if len(scores) == 1:
        only_cluster = next(iter(scores))
        return {only_cluster: "Customer" if scores[only_cluster] >= 0 else "Agent"}

    customer_cluster = max(scores, key=lambda cluster_id: scores[cluster_id])
    return {cluster_id: ("Customer" if cluster_id == customer_cluster else "Agent") for cluster_id in scores}


def _heuristic_audio_diarization(whisper_segments: list[dict[str, Any]], provider: str = "heuristic") -> DiarizationResult:
    turns = [
        TranscriptTurn(
            speaker=_guess_speaker_from_text(str(segment.get("text", "")), index),
            raw_speaker=f"SPEAKER_{index % 2}",
            text=str(segment.get("text", "")).strip(),
            start=float(segment.get("start", 0.0) or 0.0),
            end=float(segment.get("end", 0.0) or 0.0),
            confidence=0.45,
            warnings=["heuristic_speaker_assignment"],
        )
        for index, segment in enumerate(whisper_segments)
    ]
    return DiarizationResult(
        turns=_refine_turn_roles(turns),
        speaker_map={"SPEAKER_0": "Customer", "SPEAKER_1": "Agent"},
        provider=provider,
        speaker_confidence={"SPEAKER_0": 0.45, "SPEAKER_1": 0.45},
        warnings=["heuristic_speaker_assignment"],
    )


def _free_local_diarization(audio_path: Path, whisper_segments: list[dict[str, Any]]) -> DiarizationResult | None:
    usable_segments = [
        segment
        for segment in whisper_segments
        if str(segment.get("text", "")).strip()
        and float(segment.get("end", 0.0) or 0.0) > float(segment.get("start", 0.0) or 0.0)
    ]
    if len(usable_segments) < 2:
        return None

    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        samples, sample_rate = _load_audio_mono(audio_path)
        feature_rows = [
            _acoustic_features(
                _segment_samples(
                    samples,
                    sample_rate,
                    float(segment.get("start", 0.0) or 0.0),
                    float(segment.get("end", 0.0) or 0.0),
                ),
                sample_rate,
            )
            for segment in usable_segments
        ]
        scaled = StandardScaler().fit_transform(np.asarray(feature_rows, dtype=np.float32))
        labels = KMeans(n_clusters=2, random_state=42, n_init=10).fit_predict(scaled)
    except Exception as exc:
        logger.warning("Free local diarization failed, falling back to text heuristics: %s", exc)
        return None

    cluster_texts: dict[int, list[str]] = {}
    for label, segment in zip(labels, usable_segments):
        cluster_texts.setdefault(int(label), []).append(str(segment.get("text", "")).strip())

    role_map = _role_map_from_cluster_text(cluster_texts)
    turns = [
        TranscriptTurn(
            speaker=role_map.get(int(label), _guess_speaker_from_text(str(segment.get("text", "")), index)),
            raw_speaker=f"SPEAKER_{int(label)}",
            text=str(segment.get("text", "")).strip(),
            start=float(segment.get("start", 0.0) or 0.0),
            end=float(segment.get("end", 0.0) or 0.0),
            confidence=0.65,
        )
        for index, (label, segment) in enumerate(zip(labels, usable_segments))
    ]
    speaker_map = {f"SPEAKER_{cluster_id}": role for cluster_id, role in role_map.items()}
    return DiarizationResult(
        turns=_refine_turn_roles(turns, preserve_speakers=True),
        speaker_map=speaker_map,
        provider="free-local-kmeans+stable-roles",
        speaker_confidence={speaker: 0.65 for speaker in speaker_map},
    )


@lru_cache(maxsize=1)
def _load_pyannote_pipeline():
    token = os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN") or os.getenv("PYANNOTE_AUTH_TOKEN")
    if not token:
        logger.info("Pyannote disabled because no Hugging Face token is configured.")
        return None

    try:
        from pyannote.audio import Pipeline

        pipeline_name = os.getenv("PYANNOTE_PIPELINE", "pyannote/speaker-diarization-community-1")
        try:
            return Pipeline.from_pretrained(pipeline_name, token=token)
        except TypeError:
            return Pipeline.from_pretrained(pipeline_name, use_auth_token=token)
    except Exception as exc:
        logger.warning("Could not load pyannote diarization pipeline: %s", exc)
        return None


def _extract_json(text: str) -> dict[str, Any]:
    text_stripped = text.strip()
    try:
        import json
        return json.loads(text_stripped)
    except json.JSONDecodeError:
        pass

    # Try finding markdown code block
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text_stripped, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding the first '{' and last '}'
    first_brace = text_stripped.find("{")
    last_brace = text_stripped.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text_stripped[first_brace:last_brace+1])
        except json.JSONDecodeError:
            pass

    raise ValueError("Could not extract valid JSON from LLM response.")


def _llm_based_diarization(whisper_segments: list[dict[str, Any]]) -> DiarizationResult | None:
    provider = os.getenv("DIARIZATION_LLM_PROVIDER")
    minimax_key = os.getenv("MINIMAX_API_KEY")
    groq_key = os.getenv("LLAMA_API_KEY") or os.getenv("GROQ_API_KEY")

    if not provider:
        if minimax_key and not minimax_key.startswith("test-"):
            provider = "minimax"
        else:
            provider = "groq"
    provider = provider.lower()

    if provider == "minimax" and (not minimax_key or minimax_key.startswith("test-")):
        logger.info("MiniMax API key is missing or a placeholder. Falling back to Groq.")
        provider = "groq"

    import json
    usable_segments = [seg for seg in whisper_segments if str(seg.get("text", "")).strip()]
    if not usable_segments:
        return None

    def execute_call(active_provider: str) -> DiarizationResult | None:
        if active_provider == "minimax":
            api_key = minimax_key
            if not api_key or api_key.startswith("test-"):
                raise ValueError("Invalid/Placeholder MiniMax key")
            base_url = os.getenv("MINIMAX_API_URL", "https://api.minimax.io/v1")
            model = os.getenv("MINIMAX_MODEL", "MiniMax-M3")
        else:
            api_key = groq_key
            if not api_key:
                raise ValueError("Groq/LLaMA API key not configured for diarization.")
            base_url = os.getenv("LLAMA_API_URL", "https://api.groq.com/openai/v1")
            base_url = base_url.removesuffix("/chat/completions").rstrip("/")
            model = os.getenv("LLAMA_MODEL", "llama3-8b-8192")

        logger.info(f"Running LLM-based Diarization via {active_provider.upper()} ({model})...")
        
        segments_json = [
            {"id": i, "text": str(seg.get("text", "")).strip()}
            for i, seg in enumerate(usable_segments)
        ]

        prompt = f"""You are an expert transcriber. Review the following audio segments and assign a speaker to each based on the conversation context.

Speakers can be:
- "Agent" - the sales representative, support agent, or meeting host
- "Customer" - the primary customer or client being spoken to
- "Guest" - any additional participant

Return a JSON object with a single key "turns" containing an array of objects.
Each object must have "id" (integer matching the segment id) and "speaker" (either "Agent", "Customer", or "Guest").
Do not include any markdown or extra text.

Segments:
{json.dumps(segments_json, indent=2)}"""

        import httpx
        
        chat_completions_url = f"{base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }
        if active_provider != "minimax":
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        response = httpx.post(
            chat_completions_url,
            headers=headers,
            json=payload,
            timeout=60.0
        )
        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        parsed = _extract_json(content)

        raw_turns = parsed.get("turns", [])
        speaker_mapping = {rt.get("id"): rt.get("speaker") for rt in raw_turns if "id" in rt}
        
        turns = []
        for i, seg in enumerate(usable_segments):
            speaker_label = speaker_mapping.get(i) or _guess_speaker_from_text(str(seg.get("text", "")), i)
            turns.append(TranscriptTurn(
                speaker=speaker_label,
                raw_speaker="SPEAKER_LLM",
                text=str(seg.get("text", "")).strip(),
                start=float(seg.get("start", 0.0) or 0.0),
                end=float(seg.get("end", 0.0) or 0.0),
            ))

        return DiarizationResult(
            turns=_merge_turns(turns),
            speaker_map={"SPEAKER_LLM": "Agent/Customer"},
            provider=f"llm-{active_provider}-{model}",
        )

    try:
        return execute_call(provider)
    except Exception as exc:
        logger.warning(f"LLM Diarization via {provider.upper()} failed: {exc}")
        if provider == "minimax" and groq_key:
            logger.info("Falling back to Groq for LLM Diarization...")
            try:
                return execute_call("groq")
            except Exception as groq_exc:
                logger.warning(f"Fallback LLM Diarization via GROQ failed: {groq_exc}")
        return None


def diarize_audio_segments(audio_path: Path, whisper_segments: list[dict[str, Any]]) -> DiarizationResult:
    if not whisper_segments:
        return DiarizationResult(turns=[], provider="empty")

    enable_tracking = os.getenv("ENABLE_SPEAKER_TRACKING", "true").lower() == "true"
    if enable_tracking:
        try:
            logger.info("Running real-time VAD & Speaker Tracking pipeline...")
            from src.aspect_sentiment.vad import get_speech_segments
            from src.aspect_sentiment.embeddings import get_speaker_embedding
            from src.aspect_sentiment.tracking import SpeakerTracker
            from src.aspect_sentiment.role_classifier import classify_role_hybrid
            from src.aspect_sentiment.flow_validator import validate_and_correct_roles
            
            # 1. Silero VAD: Get speech segments
            vad_segments = get_speech_segments(audio_path)
            if not vad_segments:
                logger.warning("VAD returned no speech segments. Falling back to whisper segments.")
                vad_segments = [{"start": float(s.get("start", 0.0)), "end": float(s.get("end", 0.0))} for s in whisper_segments]
                
            # 2. Extract ECAPA embeddings and Track speakers
            samples, sample_rate = _load_audio_mono(audio_path)
            tracker = SpeakerTracker()
            
            segment_speaker_map = []
            tracker_confidence: dict[str, list[float]] = {}
            for seg in vad_segments:
                start = seg["start"]
                end = seg["end"]
                seg_samples = _segment_samples(samples, sample_rate, start, end)
                emb = get_speaker_embedding(seg_samples)
                match = tracker.track_speaker_with_confidence(emb)
                speaker_id = match.speaker
                tracker_confidence.setdefault(speaker_id, []).append(match.confidence)
                segment_speaker_map.append({
                    "start": start,
                    "end": end,
                    "speaker": speaker_id,
                    "confidence": match.confidence,
                    "is_new": match.is_new,
                })
                
            # 3. Align Whisper transcript segments with VAD speakers
            raw_turns = []
            for index, segment in enumerate(whisper_segments):
                w_start = float(segment.get("start", 0.0) or 0.0)
                w_end = float(segment.get("end", w_start) or w_start)
                w_text = str(segment.get("text", "")).strip()
                
                overlaps = {}
                overlap_confidences: dict[str, list[float]] = {}
                for vs in segment_speaker_map:
                    overlap = _overlap_seconds(w_start, w_end, vs["start"], vs["end"])
                    if overlap > 0:
                        overlaps[vs["speaker"]] = overlaps.get(vs["speaker"], 0.0) + overlap
                        overlap_confidences.setdefault(vs["speaker"], []).append(float(vs.get("confidence", 0.0)))
                        
                if overlaps:
                    assigned_speaker = max(overlaps, key=overlaps.get)
                    total_overlap = sum(overlaps.values())
                    alignment_confidence = overlaps[assigned_speaker] / total_overlap if total_overlap else 0.0
                    embedding_confidence = _mean(overlap_confidences.get(assigned_speaker, []))
                    turn_confidence = _mean([alignment_confidence, embedding_confidence])
                else:
                    assigned_speaker = "Speaker_A" if index % 2 == 0 else "Speaker_B"
                    turn_confidence = 0.35

                is_overlap = sum(1 for value in overlaps.values() if value > 0.05) > 1
                warnings = []
                if not overlaps:
                    warnings.append("speaker_alignment_fallback")
                if is_overlap:
                    warnings.append("overlapping_speech_detected")
                    
                raw_turns.append(TranscriptTurn(
                    speaker=assigned_speaker,
                    raw_speaker=assigned_speaker,
                    text=w_text,
                    start=w_start,
                    end=w_end,
                    confidence=round(turn_confidence, 4),
                    overlap=is_overlap,
                    warnings=warnings,
                ))
                
            # 4. Role Classification (Primary: Rules, Fallback: MiniLM)
            speaker_texts = {}
            for turn in raw_turns:
                speaker_texts[turn.speaker] = speaker_texts.get(turn.speaker, "") + " " + turn.text
            total_role_words = sum(len(text.split()) for text in speaker_texts.values())
                
            classifications = {}
            for spk, text in speaker_texts.items():
                cleaned_text = text.strip()
                classifications[spk] = classify_role_hybrid(
                    spk,
                    cleaned_text,
                    speaker_word_count=len(cleaned_text.split()),
                    total_word_count=total_role_words,
                )
                
            # 5. Conversation Flow Order Validation & Correction
            validator_turns = [{"speaker": t.speaker, "text": t.text} for t in raw_turns]
            corrected_classifications = validate_and_correct_roles(
                validator_turns, 
                classifications,
                threshold=float(os.getenv("ROLE_CONFIDENCE_THRESHOLD", "0.85"))
            )
            
            # Resolve roles using sorting by Agent probability to prevent collisions and support Guest
            sorted_by_agent = sorted(
                corrected_classifications.items(),
                key=lambda item: float(
                    item[1].get("probability", {}).get("Agent", 1.0 if item[1].get("role") == "Agent" else 0.0)
                )
            )
            
            speaker_map = {}
            speaker_confidence = {}
            
            if len(sorted_by_agent) >= 3:
                # 3 or more speakers: map extremes to Customer/Agent, middle ones to Guest
                customer_spk = sorted_by_agent[0][0]
                agent_spk = sorted_by_agent[-1][0]
                speaker_map[customer_spk] = "Customer"
                speaker_map[agent_spk] = "Agent"
                for spk, _ in sorted_by_agent[1:-1]:
                    speaker_map[spk] = "Guest"
            elif len(sorted_by_agent) == 2:
                # 2 speakers: map to Customer and Agent
                customer_spk = sorted_by_agent[0][0]
                agent_spk = sorted_by_agent[1][0]
                speaker_map[customer_spk] = "Customer"
                speaker_map[agent_spk] = "Agent"
            elif len(sorted_by_agent) == 1:
                # 1 speaker: use fallback
                spk, result = sorted_by_agent[0]
                speaker_map[spk] = _role_from_classification(result)
                
            for spk, result in corrected_classifications.items():
                if spk not in speaker_map:
                    speaker_map[spk] = _role_from_classification(result)
                role_confidence = float(result.get("confidence", 0.0) or 0.0)
                embedding_confidence = _mean(tracker_confidence.get(spk, []))
                confidence_values = [value for value in [role_confidence, embedding_confidence] if value > 0]
                speaker_confidence[spk] = _mean(confidence_values)
                
            final_turns = []
            pipeline_warnings = []
            for turn in raw_turns:
                final_role = speaker_map.get(turn.speaker, "Unknown")
                turn_confidence_values = [
                    value for value in [turn.confidence, speaker_confidence.get(turn.speaker)] if value is not None
                ]
                turn_warnings = list(turn.warnings)
                if final_role == "Unknown":
                    turn_warnings.append("low_role_confidence")
                pipeline_warnings.extend(turn_warnings)
                final_turns.append(TranscriptTurn(
                    speaker=final_role,
                    raw_speaker=turn.speaker,
                    text=turn.text,
                    start=turn.start,
                    end=turn.end,
                    confidence=_mean(turn_confidence_values),
                    overlap=turn.overlap,
                    warnings=turn_warnings,
                ))
                
            merged_turns = _merge_turns(final_turns)
            
            # If the acoustic pipeline grouped everything into 1 speaker, fall back to LLM semantic diarization
            use_llm = os.getenv("USE_LLM_DIARIZATION", os.getenv("USE_GROQ_WHISPER", "true")).lower() == "true"
            if len(speaker_map) <= 1 and use_llm:
                logger.info("Acoustic pipeline detected only 1 speaker. Falling back to LLM semantic diarization.")
                llm_result = _llm_based_diarization(whisper_segments)
                if llm_result:
                    return llm_result

            return DiarizationResult(
                turns=merged_turns,
                speaker_map=speaker_map,
                provider="vad-ecapa-tracking",
                speaker_confidence=speaker_confidence,
                warnings=list(dict.fromkeys(pipeline_warnings)),
            )
        except Exception as e:
            logger.error(f"Real-time speaker tracking pipeline failed: {e}. Falling back to previous implementations.", exc_info=True)

    # Fallback to previous implementations
    use_llm = os.getenv("USE_LLM_DIARIZATION", os.getenv("USE_GROQ_WHISPER", "true")).lower() == "true"
    if use_llm:
        logger.info("LLM-based Diarization is active. Bypassing Pyannote.")
        result = _llm_based_diarization(whisper_segments)
        if result is not None:
            return result
        # Fallback if LLM fails
        return _heuristic_audio_diarization(whisper_segments, provider="heuristic-llm-fallback")

    backend = os.getenv("DIARIZATION_BACKEND", "free-local").strip().lower()
    if backend in {"free", "free-local", "local", "kmeans"}:
        result = _free_local_diarization(audio_path, whisper_segments)
        if result is not None:
            return result
        return _heuristic_audio_diarization(whisper_segments, provider="heuristic-free-local-fallback")

    pipeline = _load_pyannote_pipeline()
    if pipeline is None:
        result = _free_local_diarization(audio_path, whisper_segments)
        if result is not None:
            return result
        return _heuristic_audio_diarization(whisper_segments, provider="heuristic-free-local-fallback")

    try:
        diarization = pipeline(str(audio_path), num_speakers=2)
    except Exception as exc:
        logger.warning("Pyannote diarization failed, falling back to heuristic speakers: %s", exc)
        result = _free_local_diarization(audio_path, whisper_segments)
        if result is not None:
            return result
        return _heuristic_audio_diarization(whisper_segments, provider="heuristic-pyannote-fallback")

    speaker_intervals: list[tuple[float, float, str]] = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        speaker_intervals.append((float(turn.start), float(turn.end), str(speaker)))

    raw_turns: list[TranscriptTurn] = []
    raw_speaker_order: list[str] = []
    for index, segment in enumerate(whisper_segments):
        start = float(segment.get("start", 0.0) or 0.0)
        end = float(segment.get("end", start) or start)
        text = str(segment.get("text", "")).strip()
        overlaps: dict[str, float] = {}
        for interval_start, interval_end, speaker in speaker_intervals:
            overlap = _overlap_seconds(start, end, interval_start, interval_end)
            if overlap > 0:
                overlaps[speaker] = overlaps.get(speaker, 0.0) + overlap
        raw_speaker = max(overlaps, key=overlaps.get) if overlaps else f"SPEAKER_{index % 2}"
        total_overlap = sum(overlaps.values())
        confidence = overlaps[raw_speaker] / total_overlap if total_overlap else 0.4
        overlap_detected = sum(1 for value in overlaps.values() if value > 0.05) > 1
        warnings = []
        if not overlaps:
            warnings.append("speaker_alignment_fallback")
        if overlap_detected:
            warnings.append("overlapping_speech_detected")
        if raw_speaker not in raw_speaker_order:
            raw_speaker_order.append(raw_speaker)
        raw_turns.append(
            TranscriptTurn(
                speaker=raw_speaker,
                raw_speaker=raw_speaker,
                text=text,
                start=start,
                end=end,
                confidence=round(confidence, 4),
                overlap=overlap_detected,
                warnings=warnings,
            )
        )

    speaker_scores: dict[str, dict[str, int]] = {speaker: {"customer": 0, "agent": 0} for speaker in raw_speaker_order}
    for turn in raw_turns:
        lower = turn.text.lower()
        speaker_scores.setdefault(turn.speaker, {"customer": 0, "agent": 0})
        speaker_scores[turn.speaker]["customer"] += sum(1 for term in CUSTOMER_TERMS if term in lower)
        speaker_scores[turn.speaker]["agent"] += sum(1 for term in AGENT_TERMS if term in lower)

    speaker_map: dict[str, str] = {}
    if raw_speaker_order:
        customer_raw = max(raw_speaker_order, key=lambda s: (speaker_scores[s]["customer"] - speaker_scores[s]["agent"], -raw_speaker_order.index(s)))
        speaker_map[customer_raw] = "Customer"
        for raw in raw_speaker_order:
            speaker_map.setdefault(raw, "Agent")

    turns = [
        TranscriptTurn(
            speaker=speaker_map.get(turn.speaker, _guess_speaker_from_text(turn.text, index)),
            raw_speaker=turn.raw_speaker,
            text=turn.text,
            start=turn.start,
            end=turn.end,
            confidence=turn.confidence,
            overlap=turn.overlap,
            warnings=list(turn.warnings),
        )
        for index, turn in enumerate(raw_turns)
    ]
    speaker_confidence = {
        speaker: _mean([turn.confidence or 0.0 for turn in raw_turns if turn.raw_speaker == speaker])
        for speaker in speaker_map
    }
    warnings = list(dict.fromkeys(warning for turn in turns for warning in turn.warnings))
    return DiarizationResult(
        turns=_refine_turn_roles(turns, preserve_speakers=True),
        speaker_map=speaker_map,
        provider="pyannote.audio+stable-roles",
        speaker_confidence=speaker_confidence,
        warnings=warnings,
    )


def diarize_text(text: str) -> DiarizationResult:
    matches = list(SPEAKER_LABEL_RX.finditer(text))
    if matches:
        turns: list[TranscriptTurn] = []
        for index, match in enumerate(matches):
            next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            turn_text = text[match.end() : next_start].strip()
            if turn_text:
                turns.append(TranscriptTurn(speaker=_normalize_role(match.group(1)), raw_speaker=match.group(1), text=turn_text))
        return DiarizationResult(turns=_merge_turns(turns), provider="explicit-labels")

    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]
    if not sentences:
        sentences = [text.strip()] if text.strip() else []

    use_llm = os.getenv("USE_LLM_DIARIZATION", os.getenv("USE_GROQ_WHISPER", "true")).lower() == "true"
    if use_llm:
        logger.info("Using LLM-based Diarization for raw text...")
        fake_segments = [{"text": s, "start": float(i * 10), "end": float((i + 1) * 10)} for i, s in enumerate(sentences)]
        llm_result = _llm_based_diarization(fake_segments)
        if llm_result:
            return llm_result
        
    # Heuristic text split: alternate Speaker_A and Speaker_B
    raw_turns = []
    for index, sentence in enumerate(sentences):
        spk = "Speaker_A" if index % 2 == 0 else "Speaker_B"
        raw_turns.append(TranscriptTurn(speaker=spk, raw_speaker=spk, text=sentence))
        
    # Classify speaker roles using hybrid classifier
    from src.aspect_sentiment.role_classifier import classify_role_hybrid
    from src.aspect_sentiment.flow_validator import validate_and_correct_roles
    
    speaker_texts = {}
    for turn in raw_turns:
        speaker_texts[turn.speaker] = speaker_texts.get(turn.speaker, "") + " " + turn.text
    total_role_words = sum(len(text.split()) for text in speaker_texts.values())
        
    classifications = {}
    for spk, txt in speaker_texts.items():
        cleaned_text = txt.strip()
        classifications[spk] = classify_role_hybrid(
            spk,
            cleaned_text,
            speaker_word_count=len(cleaned_text.split()),
            total_word_count=total_role_words,
        )
        
    validator_turns = [{"speaker": t.speaker, "text": t.text} for t in raw_turns]
    corrected = validate_and_correct_roles(validator_turns, classifications)
    
    speaker_map = {}
    for spk, result in corrected.items():
        speaker_map[spk] = result["role"]
        
    final_turns = []
    for turn in raw_turns:
        final_role = speaker_map.get(turn.speaker, "Customer")
        final_turns.append(TranscriptTurn(
            speaker=final_role,
            raw_speaker=turn.speaker,
            text=turn.text
        ))
        
    return DiarizationResult(
        turns=_merge_turns(final_turns),
        speaker_map=speaker_map,
        provider="hybrid-text-classifier"
    )
