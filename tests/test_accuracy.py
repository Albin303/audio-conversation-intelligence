from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from src.aspect_sentiment.audio import WhisperTranscriber
from src.aspect_sentiment.diarization import (
    DiarizationResult,
    TranscriptTurn,
    _refine_turn_roles,
    diarize_audio_segments,
    diarize_text,
)
from src.aspect_sentiment.conversation_reconstruction import reconstruct_conversation
from src.aspect_sentiment.llama_extraction import merge_rule_features
from src.aspect_sentiment.privacy import extract_and_redact_pii
from src.aspect_sentiment.role_classifier import classify_role_hybrid
from src.aspect_sentiment.tracking import SpeakerTracker
from src.api.server import local_structured_entities, readiness
from scripts.benchmark_diarization import compute_embedding_metrics, compute_reference_metrics


class PrivacyAccuracyTests(unittest.TestCase):
    def test_only_extracts_customer_name_with_direct_evidence(self):
        result = extract_and_redact_pii(
            "My name is Alice Johnson. I need a Samsung phone. John reviewed the proposal."
        )

        names = [entity.value for entity in result.entities if entity.type == "customer_name"]
        self.assertEqual(names, ["Alice Johnson"])
        self.assertNotIn("John", names)
        self.assertIn("[CUSTOMER_NAME_REDACTED]", result.cleaned_text)

    def test_does_not_treat_product_or_intent_as_a_name(self):
        result = extract_and_redact_pii("I am Looking for Samsung Galaxy under 50000.")
        names = [entity.value for entity in result.entities if entity.type == "customer_name"]
        self.assertEqual(names, [])

    def test_agent_and_customer_names_follow_speaker_evidence(self):
        diarization = DiarizationResult(
            turns=[
                TranscriptTurn("Agent", "Hello Ravi. My name is Sarah."),
                TranscriptTurn("Customer", "Hi Sarah. My name is Ravi."),
            ],
            provider="test",
        )

        entities = local_structured_entities(diarization.formatted, diarization)
        grouped = {
            entity_type: {item["value"] for item in entities if item["type"] == entity_type}
            for entity_type in ("customer_name", "agent_name")
        }

        self.assertEqual(grouped["customer_name"], {"Ravi"})
        self.assertEqual(grouped["agent_name"], {"Sarah"})

    def test_nested_labels_keep_agent_and_customer_names_separate(self):
        text = (
            "Customer: [Agent]: Good morning. My name is Jennifer. "
            "Customer: [Customer]: Hi Jennifer. My name is Michael Thomas. "
            "I'm looking for a laptop."
        )
        diarization = diarize_text(text)
        privacy = extract_and_redact_pii(diarization.customer_text)
        entities = local_structured_entities(text, diarization)
        privacy_names = {
            entity.value for entity in privacy.entities if entity.type == "customer_name"
        }
        grouped = {
            entity_type: {item["value"] for item in entities if item["type"] == entity_type}
            for entity_type in ("customer_name", "agent_name")
        }

        self.assertEqual(privacy_names, {"Michael Thomas"})
        self.assertEqual(grouped["customer_name"], {"Michael Thomas"})
        self.assertEqual(grouped["agent_name"], {"Jennifer"})

    def test_model_number_is_not_extracted_as_budget(self):
        text = (
            "Agent: The price of the MacBook Pro M4 with 16GB RAM and 512GB SSD "
            "is approximately ₹1,89,000. Customer: That's higher than my budget. "
            "I'm hoping to stay around ₹1,60,000."
        )
        entities = local_structured_entities(text, diarize_text(text))
        values = {(item["type"], item["value"]) for item in entities}

        self.assertNotIn(("budget", "4"), values)
        self.assertIn(("product_price", "189000"), values)
        self.assertIn(("budget", "160000"), values)


class DiarizationAccuracyTests(unittest.TestCase):
    def test_acoustic_speaker_is_not_flipped_by_sentence_words(self):
        turns = [
            TranscriptTurn(
                "Agent",
                "I need your account details. I can suggest a Dell laptop.",
                raw_speaker="SPEAKER_0",
            )
        ]

        refined = _refine_turn_roles(turns, preserve_speakers=True)
        self.assertTrue(refined)
        self.assertEqual({turn.speaker for turn in refined}, {"Agent"})

    def test_speaker_tracker_returns_match_confidence(self):
        tracker = SpeakerTracker(threshold=0.75, max_speakers=2)

        first = tracker.track_speaker_with_confidence(np.array([1.0, 0.0], dtype=np.float32))
        repeat = tracker.track_speaker_with_confidence(np.array([0.96, 0.04], dtype=np.float32))
        second = tracker.track_speaker_with_confidence(np.array([0.0, 1.0], dtype=np.float32))
        capped = tracker.track_speaker_with_confidence(np.array([0.7, 0.7], dtype=np.float32))

        self.assertEqual(first.speaker, "Speaker_A")
        self.assertEqual(repeat.speaker, "Speaker_A")
        self.assertGreaterEqual(repeat.confidence, 0.95)
        self.assertEqual(second.speaker, "Speaker_B")
        self.assertTrue(second.is_new)
        self.assertIn(capped.speaker, {"Speaker_A", "Speaker_B"})
        self.assertEqual(tracker.speaker_names, ["Speaker_A", "Speaker_B"])

    def test_vad_ecapa_pipeline_reports_overlap_and_confidence(self):
        whisper_segments = [
            {"start": 0.7, "end": 1.1, "text": "How can I help you today?"},
            {"start": 1.2, "end": 1.8, "text": "I need a laptop under 60000."},
        ]
        vad_segments = [
            {"start": 0.0, "end": 1.2},
            {"start": 0.8, "end": 2.0},
        ]
        embeddings = [
            np.array([1.0, 0.0], dtype=np.float32),
            np.array([0.0, 1.0], dtype=np.float32),
        ]

        def classify(speaker: str, text: str, **_: object) -> dict:
            return {
                "speaker": speaker,
                "role": "Agent" if speaker == "Speaker_A" else "Customer",
                "confidence": 0.96,
                "method": "test",
            }

        with (
            patch.dict("os.environ", {
                "ENABLE_SPEAKER_TRACKING": "true",
                "USE_LLM_DIARIZATION": "false",
                "USE_GROQ_WHISPER": "false",
            }),
            patch("src.aspect_sentiment.vad.get_speech_segments", return_value=vad_segments),
            patch("src.aspect_sentiment.embeddings.get_speaker_embedding", side_effect=embeddings),
            patch("src.aspect_sentiment.diarization._load_audio_mono", return_value=(np.zeros(32000), 16000)),
            patch("src.aspect_sentiment.role_classifier.classify_role_hybrid", side_effect=classify),
            patch("src.aspect_sentiment.flow_validator.validate_and_correct_roles", side_effect=lambda _, c, threshold=0.85: c),
        ):
            result = diarize_audio_segments(Path("sample.wav"), whisper_segments)

        self.assertEqual(result.provider, "vad-ecapa-tracking")
        self.assertEqual(result.speaker_map, {"Speaker_A": "Agent", "Speaker_B": "Customer"})
        self.assertIn("Speaker_A", result.speaker_confidence)
        self.assertTrue(result.turns[0].overlap)
        self.assertIn("overlapping_speech_detected", result.warnings)
        self.assertGreater(result.turns[0].confidence or 0.0, 0.5)

    def test_diarization_quality_metrics_with_reference(self):
        predicted = [
            {"start": 0.0, "end": 1.0, "speaker": "Speaker_A"},
            {"start": 1.0, "end": 2.0, "speaker": "Speaker_B"},
            {"start": 2.0, "end": 3.0, "speaker": "Speaker_A"},
        ]
        reference = {
            "segments": [
                {"start": 0.0, "end": 1.0, "speaker": "Agent"},
                {"start": 1.0, "end": 2.0, "speaker": "Customer"},
                {"start": 2.0, "end": 3.0, "speaker": "Agent"},
            ]
        }

        metrics = compute_reference_metrics(predicted, reference)

        self.assertEqual(metrics["diarizationErrorRatePct"], 0.0)
        self.assertEqual(metrics["speakerPurityPct"], 100.0)
        self.assertEqual(metrics["speakerConsistencyPct"], 100.0)
        self.assertEqual(metrics["speakerSwitchingErrors"], 0)

    def test_conversation_reconstruction_merges_fragments_and_preserves_overlap(self):
        diarization = DiarizationResult(
            turns=[
                TranscriptTurn("Customer", "under 60000", start=1.0, end=1.4, confidence=0.9),
                TranscriptTurn("Agent", "What is your budget?", start=0.0, end=0.8, confidence=0.8),
                TranscriptTurn("Customer", "I need a laptop", start=0.9, end=1.0, confidence=0.9),
                TranscriptTurn("Agent", "I can suggest Dell.", start=1.5, end=2.0, confidence=0.85, overlap=True),
            ],
            warnings=["test_warning"],
        )

        result = reconstruct_conversation(diarization)

        self.assertEqual(result.turns[0].speaker, "Agent")
        self.assertIn("I need a laptop under 60000", result.formatted)
        self.assertEqual(result.metadata.merged_fragments, 1)
        self.assertEqual(result.metadata.overlap_turns, 1)
        self.assertIn("overlapping_speech_preserved", result.metadata.warnings)

    def test_embedding_quality_metrics_report_false_speaker_creation(self):
        rows = [
            {"speaker": "Speaker_A", "embedding": np.array([1.0, 0.0], dtype=np.float32)},
            {"speaker": "Speaker_A", "embedding": np.array([0.9, 0.1], dtype=np.float32)},
            {"speaker": "Speaker_B", "embedding": np.array([0.0, 1.0], dtype=np.float32)},
            {"speaker": "Speaker_C", "embedding": np.array([0.1, 0.9], dtype=np.float32)},
        ]

        metrics = compute_embedding_metrics(rows, expected_speakers=2)

        self.assertEqual(metrics["falseSpeakerCreation"], 1)
        self.assertIn("avgIntraSpeaker", metrics["embeddingSimilarity"])


class ExtractionAccuracyTests(unittest.TestCase):
    def test_rejects_ungrounded_llama_features(self):
        features = merge_rule_features(
            [
                {"value": "Samsung", "label": "BRAND"},
                {"value": "RTX 4090", "label": "FEATURE"},
                {"value": "Ready to Purchase", "label": "INTENT"},
            ],
            "I need a Dell laptop under 60000, but I am not sure yet.",
        )

        values = {str(feature["value"]).lower() for feature in features}
        self.assertNotIn("samsung", values)
        self.assertNotIn("rtx 4090", values)
        self.assertIn("dell", values)
        self.assertIn("60000", values)


class RoleClassificationAccuracyTests(unittest.TestCase):
    def test_multi_signal_role_classifier_returns_probabilities(self):
        agent = classify_role_hybrid(
            "Speaker_A",
            "Good morning, this is Sarah calling from TechNova. May I know your budget and brand preference?",
            speaker_word_count=16,
            total_word_count=32,
        )
        customer = classify_role_hybrid(
            "Speaker_B",
            "I am looking for a laptop under 60000 but I am not sure if I should buy today.",
            speaker_word_count=17,
            total_word_count=32,
        )

        self.assertEqual(agent["role"], "Agent")
        self.assertEqual(customer["role"], "Customer")
        self.assertIn("probability", agent)
        self.assertIn("signals", agent)
        self.assertGreater(agent["probability"]["Agent"], customer["probability"]["Agent"])


class WhisperAccuracyTests(unittest.TestCase):
    def test_filters_low_confidence_hallucinations_and_repeats(self):
        segments = WhisperTranscriber._clean_segments(
            [
                {
                    "start": 0,
                    "end": 1,
                    "text": "Thanks for watching",
                    "avg_logprob": -1.2,
                    "no_speech_prob": 0.8,
                    "compression_ratio": 1.0,
                },
                {
                    "start": 1,
                    "end": 2,
                    "text": "I need a laptop",
                    "avg_logprob": -0.2,
                    "no_speech_prob": 0.05,
                    "compression_ratio": 1.1,
                },
                {
                    "start": 2,
                    "end": 3,
                    "text": "I need a laptop",
                    "avg_logprob": -0.2,
                    "no_speech_prob": 0.05,
                    "compression_ratio": 1.1,
                },
            ]
        )

        self.assertEqual([segment["text"] for segment in segments], ["I need a laptop"])

    def test_preserves_word_timestamps_and_removes_repeated_words(self):
        segments = WhisperTranscriber._clean_segments(
            [
                {
                    "start": 0,
                    "end": 1,
                    "text": "I I need need a laptop",
                    "avg_logprob": -0.1,
                    "no_speech_prob": 0.05,
                    "compression_ratio": 1.1,
                    "words": [{"word": "I", "start": 0.0, "end": 0.1}],
                }
            ]
        )

        self.assertEqual(segments[0]["text"], "I need a laptop")
        self.assertEqual(segments[0]["words"][0]["word"], "I")


class ApiHealthTests(unittest.TestCase):
    def test_readiness_returns_a_payload(self):
        payload = readiness()
        self.assertIn(payload["status"], {"ready", "degraded"})
        self.assertIn("checks", payload)


if __name__ == "__main__":
    unittest.main()
