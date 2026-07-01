import os
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class SpeakerMatch:
    """Result of assigning an embedding to a tracked speaker profile."""

    speaker: str
    confidence: float
    is_new: bool


def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """Compute cosine similarity between two 1D vectors."""
    dot = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    return float(dot / (norm1 * norm2)) if norm1 > 0 and norm2 > 0 else 0.0

class SpeakerTracker:
    def __init__(self, threshold: float = None, max_speakers: int = None):
        if threshold is None:
            threshold = float(os.getenv("SPEAKER_TRACKING_THRESHOLD", "0.80"))
        self.threshold = threshold
        if max_speakers is None:
            max_speakers = int(os.getenv("SPEAKER_MAX_PROFILES", "2"))
        self.max_speakers = max(1, max_speakers)
        self.speakers = {}  # speaker_label -> list of embeddings
        self.running_averages = {}  # speaker_label -> mean embedding
        self.speaker_names = []  # List of unique speaker labels assigned (e.g. Speaker_A)

    def _next_speaker_label(self) -> str:
        letter = chr(65 + len(self.speaker_names))  # A, B, C...
        label = f"Speaker_{letter}"
        self.speaker_names.append(label)
        return label

    def track_speaker_with_confidence(self, embedding: np.ndarray) -> SpeakerMatch:
        """
        Match a new embedding against known speaker profiles.
        Returns the speaker label plus the matching confidence.
        """
        embedding = np.asarray(embedding, dtype=np.float32).reshape(-1)
        if embedding.size == 0:
            embedding = np.zeros(192, dtype=np.float32)
        if not np.any(embedding):
            label = self.speaker_names[-1] if self.speaker_names else self._next_speaker_label()
            self.speakers.setdefault(label, [])
            self.running_averages.setdefault(label, embedding)
            return SpeakerMatch(speaker=label, confidence=0.0, is_new=not self.speakers[label])

        if not self.running_averages:
            label = self._next_speaker_label()
            self.speakers[label] = [embedding]
            self.running_averages[label] = embedding
            return SpeakerMatch(speaker=label, confidence=1.0, is_new=True)

        best_label = None
        best_score = -1.0
        for label, embeddings in self.speakers.items():
            avg_emb = self.running_averages[label]
            sim_avg = cosine_similarity(embedding, avg_emb)
            
            # Match against the last 15 embeddings to handle drift and capture local voice features
            recent_embs = embeddings[-15:]
            sim_indivs = [cosine_similarity(embedding, past_emb) for past_emb in recent_embs]
            sim_max_indiv = max(sim_indivs) if sim_indivs else sim_avg
            
            # Hybrid similarity calculation (40% average profile, 60% nearest neighbor)
            sim = 0.4 * sim_avg + 0.6 * sim_max_indiv
            if sim > best_score:
                best_score = sim
                best_label = label

        if best_score >= self.threshold:
            # Match found! Append and update running average
            self.speakers[best_label].append(embedding)
            self.running_averages[best_label] = np.mean(self.speakers[best_label], axis=0)
            return SpeakerMatch(speaker=best_label, confidence=round(max(0.0, min(1.0, best_score)), 4), is_new=False)

        if len(self.speaker_names) >= self.max_speakers:
            self.speakers[best_label].append(embedding)
            self.running_averages[best_label] = np.mean(self.speakers[best_label], axis=0)
            capped_confidence = max(0.0, min(1.0, best_score))
            return SpeakerMatch(speaker=best_label, confidence=round(capped_confidence, 4), is_new=False)

        # Create a new speaker profile. Confidence reflects distance from the
        # closest known speaker, which is useful for downstream warnings.
        label = self._next_speaker_label()
        self.speakers[label] = [embedding]
        self.running_averages[label] = embedding
        new_confidence = 1.0 - max(0.0, min(1.0, best_score))
        return SpeakerMatch(speaker=label, confidence=round(new_confidence, 4), is_new=True)

    def track_speaker(self, embedding: np.ndarray) -> str:
        """Backward-compatible speaker tracking API."""
        return self.track_speaker_with_confidence(embedding).speaker
