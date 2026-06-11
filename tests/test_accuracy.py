from __future__ import annotations

import unittest

from src.aspect_sentiment.audio import WhisperTranscriber
from src.aspect_sentiment.diarization import (
    DiarizationResult,
    TranscriptTurn,
    _refine_turn_roles,
    diarize_text,
)
from src.aspect_sentiment.llama_extraction import merge_rule_features
from src.aspect_sentiment.privacy import extract_and_redact_pii
from src.api.server import local_structured_entities, readiness


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


class ApiHealthTests(unittest.TestCase):
    def test_readiness_returns_a_payload(self):
        payload = readiness()
        self.assertIn(payload["status"], {"ready", "degraded"})
        self.assertIn("checks", payload)


if __name__ == "__main__":
    unittest.main()
