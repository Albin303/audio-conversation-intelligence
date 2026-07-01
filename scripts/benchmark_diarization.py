import os
import sys
import time
import json
import argparse
import psutil
import numpy as np
from pathlib import Path
from typing import Any

# Add project root to python path
sys.path.insert(0, os.getcwd())

# Import components
from src.aspect_sentiment.diarization import _load_audio_mono, _segment_samples
from src.aspect_sentiment.vad import get_speech_segments
from src.aspect_sentiment.embeddings import get_speaker_embedding
from src.aspect_sentiment.tracking import SpeakerTracker
from src.aspect_sentiment.role_classifier import classify_role_hybrid
from src.aspect_sentiment.flow_validator import validate_and_correct_roles


DEFAULT_ROLE_CASES = [
    (
        "Agent",
        "Good morning. How can I help you today? We currently have EMI options and discounts available.",
    ),
    (
        "Customer",
        "I want to buy a laptop for programming under 50000 rupees. Is there any discount?",
    ),
    (
        "Agent",
        "May I know your budget and brand preference so I can suggest the right model?",
    ),
    (
        "Customer",
        "I am not sure if I should buy now. I will think about it and get back to you.",
    ),
]


def get_ram_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)

def get_cpu_percent():
    return psutil.cpu_percent(interval=0.1)


def cosine(v1: np.ndarray, v2: np.ndarray) -> float:
    norm = np.linalg.norm(v1) * np.linalg.norm(v2)
    return float(np.dot(v1, v2) / norm) if norm > 0 else 0.0


def load_reference(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload.get("segments"), list):
        raise ValueError("Reference JSON must include a 'segments' list.")
    return payload


def overlap_seconds(a: dict[str, Any], b: dict[str, Any]) -> float:
    return max(0.0, min(float(a["end"]), float(b["end"])) - max(float(a["start"]), float(b["start"])))


def build_speaker_mapping(predicted: list[dict[str, Any]], reference: list[dict[str, Any]]) -> dict[str, str]:
    votes: dict[str, dict[str, float]] = {}
    for pred in predicted:
        pred_speaker = str(pred["speaker"])
        for ref in reference:
            overlap = overlap_seconds(pred, ref)
            if overlap <= 0:
                continue
            ref_speaker = str(ref["speaker"])
            votes.setdefault(pred_speaker, {})
            votes[pred_speaker][ref_speaker] = votes[pred_speaker].get(ref_speaker, 0.0) + overlap
    return {
        speaker: max(ref_votes, key=ref_votes.get)
        for speaker, ref_votes in votes.items()
        if ref_votes
    }


def compute_reference_metrics(
    predicted: list[dict[str, Any]],
    reference: dict[str, Any] | None,
    *,
    frame_seconds: float = 0.1,
) -> dict[str, Any]:
    if not reference:
        return {
            "speakerConsistencyPct": None,
            "speakerSwitchingErrors": None,
            "diarizationErrorRatePct": None,
            "speakerPurityPct": None,
            "referenceRoleClassificationAccuracyPct": None,
            "referenceRequired": [
                "speakerConsistencyPct",
                "speakerSwitchingErrors",
                "diarizationErrorRatePct",
                "speakerPurityPct",
                "referenceRoleClassificationAccuracyPct",
            ],
        }

    ref_segments = reference["segments"]
    mapping = build_speaker_mapping(predicted, ref_segments)
    start = min(float(seg["start"]) for seg in [*predicted, *ref_segments])
    end = max(float(seg["end"]) for seg in [*predicted, *ref_segments])
    frames = np.arange(start, end, frame_seconds)
    total_ref_speech = 0
    diarization_errors = 0

    for frame_start in frames:
        frame_mid = float(frame_start + frame_seconds / 2)
        ref_active = [
            str(seg["speaker"])
            for seg in ref_segments
            if float(seg["start"]) <= frame_mid < float(seg["end"])
        ]
        pred_active = [
            mapping.get(str(seg["speaker"]), str(seg["speaker"]))
            for seg in predicted
            if float(seg["start"]) <= frame_mid < float(seg["end"])
        ]
        if ref_active:
            total_ref_speech += 1
            if not pred_active or pred_active[0] not in ref_active:
                diarization_errors += 1
        elif pred_active:
            diarization_errors += 1

    total_overlap_by_pred: dict[str, float] = {}
    correct_overlap_by_pred: dict[str, float] = {}
    for pred in predicted:
        pred_speaker = str(pred["speaker"])
        for ref in ref_segments:
            overlap = overlap_seconds(pred, ref)
            if overlap <= 0:
                continue
            total_overlap_by_pred[pred_speaker] = total_overlap_by_pred.get(pred_speaker, 0.0) + overlap
            if mapping.get(pred_speaker) == str(ref["speaker"]):
                correct_overlap_by_pred[pred_speaker] = correct_overlap_by_pred.get(pred_speaker, 0.0) + overlap

    purity_denominator = sum(total_overlap_by_pred.values())
    purity = (
        100.0 * sum(correct_overlap_by_pred.values()) / purity_denominator
        if purity_denominator > 0
        else None
    )

    switch_errors = 0
    comparable_switches = 0
    for prev_ref, next_ref in zip(ref_segments, ref_segments[1:]):
        ref_changed = prev_ref["speaker"] != next_ref["speaker"]
        prev_pred = max(predicted, key=lambda seg: overlap_seconds(seg, prev_ref), default=None)
        next_pred = max(predicted, key=lambda seg: overlap_seconds(seg, next_ref), default=None)
        if prev_pred is None or next_pred is None:
            continue
        comparable_switches += 1
        pred_changed = prev_pred["speaker"] != next_pred["speaker"]
        if pred_changed != ref_changed:
            switch_errors += 1

    consistency = 100.0 * (1.0 - (switch_errors / comparable_switches)) if comparable_switches else None

    reference_roles = reference.get("roles", {})
    role_total = 0
    role_correct = 0
    for predicted_speaker, ref_speaker in mapping.items():
        if ref_speaker not in reference_roles:
            continue
        role_total += 1
        if predicted_speaker == ref_speaker or reference_roles.get(ref_speaker) == reference_roles.get(predicted_speaker):
            role_correct += 1

    der = 100.0 * diarization_errors / total_ref_speech if total_ref_speech else None
    return {
        "speakerConsistencyPct": round(consistency, 2) if consistency is not None else None,
        "speakerSwitchingErrors": switch_errors,
        "diarizationErrorRatePct": round(der, 2) if der is not None else None,
        "speakerPurityPct": round(purity, 2) if purity is not None else None,
        "referenceRoleClassificationAccuracyPct": round(100.0 * role_correct / role_total, 2) if role_total else None,
        "speakerMapping": mapping,
        "referenceRequired": [],
    }


def compute_embedding_metrics(rows: list[dict[str, Any]], expected_speakers: int) -> dict[str, Any]:
    if not rows:
        return {
            "speakerDriftPct": None,
            "speakerPurityPctProxy": None,
            "falseSpeakerCreation": 0,
            "embeddingSimilarity": {},
        }

    by_speaker: dict[str, list[np.ndarray]] = {}
    for row in rows:
        by_speaker.setdefault(row["speaker"], []).append(row["embedding"])

    centroids = {
        speaker: np.mean(embeddings, axis=0)
        for speaker, embeddings in by_speaker.items()
        if embeddings
    }
    intra_similarities = [
        cosine(row["embedding"], centroids[row["speaker"]])
        for row in rows
        if row["speaker"] in centroids
    ]
    inter_similarities = [
        cosine(centroids[left], centroids[right])
        for index, left in enumerate(centroids)
        for right in list(centroids)[index + 1 :]
    ]
    avg_intra = float(np.mean(intra_similarities)) if intra_similarities else None
    avg_inter = float(np.mean(inter_similarities)) if inter_similarities else None

    speaker_drift = 100.0 * (1.0 - avg_intra) if avg_intra is not None else None
    separation = (avg_intra - avg_inter) if avg_intra is not None and avg_inter is not None else None
    purity_proxy = max(0.0, min(100.0, 100.0 * separation)) if separation is not None else None

    return {
        "speakerDriftPct": round(speaker_drift, 2) if speaker_drift is not None else None,
        "speakerPurityPctProxy": round(purity_proxy, 2) if purity_proxy is not None else None,
        "falseSpeakerCreation": max(0, len(by_speaker) - expected_speakers),
        "embeddingSimilarity": {
            "avgIntraSpeaker": round(avg_intra, 4) if avg_intra is not None else None,
            "avgInterSpeaker": round(avg_inter, 4) if avg_inter is not None else None,
            "minIntraSpeaker": round(float(np.min(intra_similarities)), 4) if intra_similarities else None,
            "maxInterSpeaker": round(float(np.max(inter_similarities)), 4) if inter_similarities else None,
        },
    }


def compute_role_case_accuracy() -> tuple[float, list[dict[str, Any]], float]:
    t0 = time.perf_counter()
    results = []
    correct = 0
    for expected, text in DEFAULT_ROLE_CASES:
        result = classify_role_hybrid(expected, text)
        is_correct = result["role"] == expected
        correct += int(is_correct)
        results.append({
            "expected": expected,
            "predicted": result["role"],
            "confidence": result["confidence"],
            "method": result["method"],
            "correct": is_correct,
        })
    latency = time.perf_counter() - t0
    return 100.0 * correct / len(DEFAULT_ROLE_CASES), results, latency


def run_benchmark(audio_path: Path, reference_path: Path | None, expected_speakers: int):
    print("==================================================")
    print("       Speech Intelligence and Intent Detection - Speaker Tracking Benchmark      ")
    print("==================================================")
    
    if not audio_path.exists():
        print(f"Error: Sample audio not found at {audio_path}")
        return
    reference = load_reference(reference_path)
        
    print(f"Sample File: {audio_path.name} ({audio_path.stat().st_size / (1024*1024):.2f} MB)")
    if reference_path:
        print(f"Reference File: {reference_path}")
    else:
        print("Reference File: not supplied; DER/purity/switching are reported as reference-required.")
    
    initial_ram = get_ram_usage()
    print(f"Initial RAM Usage: {initial_ram:.2f} MB")
    
    # 1. Benchmark VAD
    t0 = time.perf_counter()
    vad_segments = get_speech_segments(audio_path)
    vad_latency = time.perf_counter() - t0
    
    print("\n1. Silero VAD Performance:")
    print(f"  - Detected Segments: {len(vad_segments)}")
    print(f"  - Latency: {vad_latency:.4f} seconds")
    print(f"  - RAM Usage: {get_ram_usage():.2f} MB")
    
    # 2. Benchmark Embedding & Tracking
    samples, sample_rate = _load_audio_mono(audio_path)
    tracker = SpeakerTracker()
    
    t0 = time.perf_counter()
    embeddings_time = 0.0
    tracking_rows = []
    for seg in vad_segments:
        seg_samples = _segment_samples(samples, sample_rate, seg["start"], seg["end"])
        t_start = time.perf_counter()
        emb = get_speaker_embedding(seg_samples)
        embeddings_time += time.perf_counter() - t_start
        match = tracker.track_speaker_with_confidence(emb)
        tracking_rows.append({
            "start": seg["start"],
            "end": seg["end"],
            "speaker": match.speaker,
            "confidence": match.confidence,
            "embedding": emb,
        })
        
    tracking_latency = time.perf_counter() - t0
    runs = len(tracking_rows)
    embedding_metrics = compute_embedding_metrics(tracking_rows, expected_speakers)
    reference_metrics = compute_reference_metrics(tracking_rows, reference)

    print(f"\n2. SpeechBrain ECAPA Speaker Embedding & Tracking ({runs} segments):")
    print(f"  - Unique Speakers Tracked: {len(tracker.speaker_names)}")
    print(f"  - Speaker Consistency %: {reference_metrics['speakerConsistencyPct']}")
    print(f"  - Speaker Switching Errors: {reference_metrics['speakerSwitchingErrors']}")
    print(f"  - Speaker Drift %: {embedding_metrics['speakerDriftPct']}")
    print(f"  - DER %: {reference_metrics['diarizationErrorRatePct']}")
    print(f"  - Speaker Purity %: {reference_metrics['speakerPurityPct']}")
    print(f"  - Speaker Purity Proxy %: {embedding_metrics['speakerPurityPctProxy']}")
    print(f"  - False Speaker Creation: {embedding_metrics['falseSpeakerCreation']}")
    print(f"  - Embedding Similarity: {embedding_metrics['embeddingSimilarity']}")
    print(f"  - Total Embedding + Tracking Latency: {tracking_latency:.4f} seconds")
    if runs > 0:
        print(f"  - Avg Embedding Generation Latency: {embeddings_time/runs:.4f} seconds/segment")
    print(f"  - RAM Usage: {get_ram_usage():.2f} MB")
    
    # 3. Benchmark Role Classification
    role_accuracy, role_results, classification_latency = compute_role_case_accuracy()
    
    print("\n3. Hybrid Role Classification Performance:")
    print(f"  - Role Classification Accuracy %: {role_accuracy:.2f}")
    print(f"  - Reference Role Classification Accuracy %: {reference_metrics['referenceRoleClassificationAccuracyPct']}")
    for result in role_results:
        print(
            f"  - {result['expected']} Case: {result['predicted']} "
            f"(Confidence: {result['confidence']}, Method: {result['method']}, Correct: {result['correct']})"
        )
    print(f"  - Classification Latency ({len(role_results)} runs): {classification_latency:.4f} seconds")
    print(f"  - RAM Usage: {get_ram_usage():.2f} MB")
    
    # 4. Flow Validator test
    t0 = time.perf_counter()
    turns = [
        {"speaker": "Speaker_A", "text": "Hello, good morning!"},
        {"speaker": "Speaker_A", "text": "I am calling from Speech Intelligence and Intent Detection."},
        {"speaker": "Speaker_B", "text": "Hi, I am interested in buying a device."}
    ]
    classifications = {
        "Speaker_A": {"role": "Customer", "confidence": 0.50},
        "Speaker_B": {"role": "Customer", "confidence": 0.95}
    }
    corrected = validate_and_correct_roles(turns, classifications)
    validator_latency = time.perf_counter() - t0
    
    print("\n4. Flow Validator Performance:")
    print(f"  - Corrected Speaker_A: {corrected['Speaker_A']['role']} (Method: {corrected['Speaker_A'].get('method')})")
    print(f"  - Validator Latency: {validator_latency:.4f} seconds")
    
    # 5. Final memory footprint
    final_ram = get_ram_usage()
    print("\n5. Resource Summary:")
    print(f"  - RAM Overhead: {final_ram - initial_ram:.2f} MB")
    print(f"  - Peak CPU usage measured: {get_cpu_percent():.1f}%")
    print("\n6. Machine-Readable Metrics:")
    print(json.dumps({
        "uniqueSpeakers": len(tracker.speaker_names),
        "detectedSegments": len(vad_segments),
        "expectedSpeakers": expected_speakers,
        **embedding_metrics,
        **reference_metrics,
        "roleCaseClassificationAccuracyPct": role_accuracy,
        "latency": {
            "vadSeconds": round(vad_latency, 4),
            "embeddingTrackingSeconds": round(tracking_latency, 4),
            "avgEmbeddingSeconds": round(embeddings_time / runs, 4) if runs else None,
            "roleClassificationSeconds": round(classification_latency, 4),
        },
        "memory": {
            "initialMb": round(initial_ram, 2),
            "finalMb": round(final_ram, 2),
            "overheadMb": round(final_ram - initial_ram, 2),
        },
    }, indent=2))
    print("==================================================")
    print("Benchmark completed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark speaker diarization and role classification quality.")
    parser.add_argument("--audio", type=Path, default=Path("audio/conv_001.wav"))
    parser.add_argument("--reference", type=Path, default=None, help="Optional JSON with timestamped reference segments.")
    parser.add_argument("--expected-speakers", type=int, default=2)
    args = parser.parse_args()
    run_benchmark(args.audio, args.reference, args.expected_speakers)
