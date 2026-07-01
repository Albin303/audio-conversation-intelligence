import unittest
from src.aspect_sentiment.analytics_engine import compute_conversation_analytics

class ConversationAnalyticsTests(unittest.TestCase):
    def test_analytics_computation(self):
        partial_result = {
            "diarizationMetrics": {
                "speaker_duration": {"Agent": 45.0, "Customer": 30.0},
                "silence_duration": 5.0,
                "total_duration": 80.0,
                "interruptions": {"Agent": 1, "Customer": 0}
            },
            "diarizedTranscript": [],
            "reconstructedTranscript": [
                {"speaker": "Agent", "start": 0.0, "end": 2.0},
                {"speaker": "Customer", "start": 3.0, "end": 6.0},
                {"speaker": "Agent", "start": 7.5, "end": 9.5}
            ],
            "conversationStages": [],
            "sentimentTimeline": {},
            "summary": {
                "averageScore": 0.35,
            },
            "conversionScore": {
                "probability": 0.82,
                "label": "hot",
                "confidence": 0.64,
            },
            "pipelineFeatures": {
                "hesitation_score": 1,
            },
            "conversationSummary": {
                "confidence": 0.85
            },
            "rawFeatures": [
                {"label": "OBJECTION"},
                {"label": "INTENT"}
            ],
            "metadata": {
                "speakerConfidence": {"Speaker_A": 0.9, "Speaker_B": 0.8}
            }
        }
        
        latencies = {
            "vad_diarization_ms": 150.0,
            "embeddings_ms": 90.0,
            "classifier_ms": 30.0,
            "llama_extraction_ms": 500.0,
            "xgboost_prediction_ms": 20.0
        }
        
        analytics = compute_conversation_analytics(partial_result, latencies)
        
        # Verify required keys are present
        self.assertIn("agentQuality", analytics)
        self.assertIn("customerEngagement", analytics)
        self.assertIn("speakingRatio", analytics)
        self.assertIn("averageResponseTime", analytics)
        self.assertIn("interruptions", analytics)
        self.assertIn("deadAir", analytics)
        self.assertIn("conversationDuration", analytics)
        self.assertIn("talkListenRatio", analytics)
        self.assertIn("objectionSignalsCount", analytics)
        self.assertIn("buyingSignalsCount", analytics)
        self.assertIn("riskScore", analytics)
        self.assertIn("followUpPriority", analytics)
        self.assertIn("conversationQualityScore", analytics)
        self.assertIn("profiling", analytics)
        self.assertIn("calibratedConfidence", analytics)
        
        # Check specific values
        self.assertEqual(analytics["objectionSignalsCount"], 1)
        self.assertEqual(analytics["buyingSignalsCount"], 1)
        self.assertEqual(analytics["speakingRatio"]["Agent"], 0.6)
        self.assertEqual(analytics["speakingRatio"]["Customer"], 0.4)
        self.assertEqual(analytics["talkListenRatio"], 1.5)
        self.assertEqual(analytics["followUpPriority"], "High")
        self.assertEqual(analytics["profiling"]["totalLatencyMs"], 790.0)
        self.assertGreater(analytics["calibratedConfidence"], 0.5)

if __name__ == "__main__":
    unittest.main()
