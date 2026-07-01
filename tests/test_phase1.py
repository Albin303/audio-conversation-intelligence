import unittest
import numpy as np
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from src.aspect_sentiment.diarization import DiarizationResult, TranscriptTurn, diarize_text
from src.aspect_sentiment.tracking import SpeakerTracker
from src.services.analysis_service import analysis_service

class SpeakerIntelligenceTests(unittest.TestCase):
    def test_metrics_calculation(self):
        # Create a mock DiarizationResult
        turns = [
            TranscriptTurn(speaker="Agent", text="Hello. How can I help?", start=0.0, end=2.0, confidence=0.9),
            TranscriptTurn(speaker="Customer", text="Hi, I need a laptop.", start=2.5, end=4.5, confidence=0.8),
            TranscriptTurn(speaker="Agent", text="What is your budget?", start=4.0, end=5.5, confidence=0.85), # Overlaps with customer by 0.5s (interruption by Agent)
            TranscriptTurn(speaker="Agent", text="Any brand preference?", start=5.5, end=7.0, confidence=0.9), # Consecutive turn
        ]
        
        result = DiarizationResult(
            turns=turns,
            speaker_map={"SPEAKER_0": "Agent", "SPEAKER_1": "Customer"},
            provider="test",
            speaker_confidence={"SPEAKER_0": 0.9, "SPEAKER_1": 0.8}
        )
        
        metrics = result.metrics
        
        # Test silence duration: 2.0 to 2.5 is 0.5s of silence
        self.assertAlmostEqual(metrics["silence_duration"], 0.5)
        
        # Test interruptions: Agent starts at 4.0, which is before Customer ends at 4.5.
        # So Agent interrupts Customer.
        self.assertEqual(metrics["interruptions"]["Agent"], 1)
        self.assertEqual(metrics["interruptions"].get("Customer", 0), 0)
        
        # Test speaker duration
        self.assertAlmostEqual(metrics["speaker_duration"]["Agent"], 2.0 + 1.5 + 1.5) # 5.0s
        self.assertAlmostEqual(metrics["speaker_duration"]["Customer"], 2.0) # 2.0s
        
        # Test speaking ratio (Agent is 5.0 / 7.0 = 0.7143)
        self.assertAlmostEqual(metrics["speaking_ratio"]["Agent"], 5.0 / 7.0, places=3)
        
        # Test average turn length
        self.assertAlmostEqual(metrics["average_turn_length"]["Agent"], 5.0 / 3, places=3)
        self.assertAlmostEqual(metrics["average_turn_length"]["Customer"], 2.0)
        
        # Test consecutive turns: Agent has consecutive sentence parts.
        self.assertEqual(metrics["consecutive_turns"].get("Agent", 0), 2)

    @patch("src.services.analysis_service.extract_and_redact_pii")
    @patch("src.services.analysis_service.process_text", new_callable=AsyncMock)
    @patch("src.services.analysis_service.summarize_conversation", new_callable=AsyncMock)
    @patch("src.services.analysis_service.predict_with_trained_model")
    def test_pipeline_exposes_metrics(self, mock_predict, mock_summarize, mock_process, mock_pii):
        # Mock privacyResult to avoid loading spacy/torch
        from src.aspect_sentiment.privacy import PrivacyResult
        mock_pii.return_value = PrivacyResult(
            cleaned_text="Hi there.",
            entities=[],
            redaction_count=0,
            provider="mock"
        )

        mock_process.return_value = {
            "raw_features": [],
            "sentiment_score": 0.0,
            "confidence_score": 0.5,
            "hesitation_score": 0,
            "delay_flag": 0,
            "brand_count": 0,
            "feature_count": 0,
            "interaction_length": 1,
            "extraction_provider": "test"
        }
        
        mock_summarize.return_value = {
            "overview": "test summary",
            "customerNeed": "test need",
            "keyPoints": [],
            "outcome": "test outcome",
            "nextAction": "test action",
            "confidence": 0.9,
            "provider": "test"
        }
        
        mock_predict.return_value = {
            "prediction": 0,
            "probability": 0.1,
            "label": "cold",
            "reasons": []
        }
        
        text = "Agent: Hello. Customer: Hi there."
        res = asyncio.run(analysis_service.run_pipeline(
            text=text,
            source_name="test",
            source_type="text",
            started=0.0
        ))
        
        self.assertIn("diarizationMetrics", res)
        metrics = res["diarizationMetrics"]
        self.assertIn("speaker_duration", metrics)
        self.assertIn("speaking_ratio", metrics)
        self.assertIn("silence_duration", metrics)
        self.assertIn("interruptions", metrics)

    def test_speaker_tracker_drift_correction(self):
        # Using a threshold that allows creating a new speaker
        tracker = SpeakerTracker(threshold=0.75)
        
        # 192 dimensional embeddings (SpeechBrain style)
        emb_a1 = np.zeros(192, dtype=np.float32)
        emb_a1[0] = 1.0
        
        emb_b1 = np.zeros(192, dtype=np.float32)
        emb_b1[1] = 1.0
        
        match1 = tracker.track_speaker_with_confidence(emb_a1)
        self.assertEqual(match1.speaker, "Speaker_A")
        
        match2 = tracker.track_speaker_with_confidence(emb_b1)
        self.assertEqual(match2.speaker, "Speaker_B")
        
        # Slightly drifted A embedding
        emb_a2 = np.zeros(192, dtype=np.float32)
        emb_a2[0] = 0.9
        emb_a2[2] = 0.435
        # normalize
        emb_a2 = emb_a2 / np.linalg.norm(emb_a2)
        
        match3 = tracker.track_speaker_with_confidence(emb_a2)
        # Should be classified as Speaker_A due to proximity
        self.assertEqual(match3.speaker, "Speaker_A")
        self.assertFalse(match3.is_new)

if __name__ == "__main__":
    unittest.main()
