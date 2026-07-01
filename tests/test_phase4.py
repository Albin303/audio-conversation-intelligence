import unittest
from src.aspect_sentiment.diarization import TranscriptTurn
from src.aspect_sentiment.sentiment_timeline import (
    compute_turn_sentiment,
    map_sentiment_label,
    compute_sentiment_timeline,
)

class SentimentTimelineTests(unittest.TestCase):
    def test_sentiment_label_mapping(self):
        # Ready To Buy
        t1 = "I am ready to buy this laptop right now. Confirm the order."
        score1 = compute_turn_sentiment(t1)
        self.assertEqual(map_sentiment_label(t1, score1), "Ready To Buy")
        
        # Interested
        t2 = "I am looking for a device with good battery and performance."
        score2 = compute_turn_sentiment(t2)
        self.assertEqual(map_sentiment_label(t2, score2), "Interested")
        
        # Frustrated
        t3 = "This is too expensive and I am disappointed with your delivery delay."
        score3 = compute_turn_sentiment(t3)
        self.assertEqual(map_sentiment_label(t3, score3), "Frustrated")
        
        # Positive
        t4 = "This is a great option. Thank you!"
        score4 = compute_turn_sentiment(t4)
        self.assertEqual(map_sentiment_label(t4, score4), "Positive")
        
        # Neutral
        t5 = "The laptop has 16GB RAM and 512GB SSD."
        score5 = compute_turn_sentiment(t5)
        self.assertEqual(map_sentiment_label(t5, score5), "Neutral")

    def test_sentiment_timeline_generation(self):
        turns = [
            TranscriptTurn(speaker="Agent", text="This is a test call for the system.", start=0.0, end=2.0),
            TranscriptTurn(speaker="Customer", text="I want to buy a gaming laptop but I am frustrated with prices.", start=2.5, end=6.0),
            TranscriptTurn(speaker="Agent", text="I understand. We can offer you EMI options and a 10% discount.", start=6.5, end=10.0),
            TranscriptTurn(speaker="Customer", text="Oh that is perfect, I am very interested now and ready to buy!", start=10.5, end=14.0),
        ]
        
        timeline = compute_sentiment_timeline(turns)
        
        # Verify turns length matches input
        self.assertEqual(len(timeline["turns"]), 4)
        
        # Check sentimentLabels
        self.assertEqual(timeline["turns"][0]["sentimentLabel"], "Neutral")
        self.assertEqual(timeline["turns"][1]["sentimentLabel"], "Frustrated")
        self.assertEqual(timeline["turns"][3]["sentimentLabel"], "Ready To Buy")
        
        # Check transitions: Frustrated to Ready To Buy etc.
        self.assertGreater(timeline["summary"]["transitionCount"], 0)
        self.assertEqual(timeline["summary"]["startLabel"], "Neutral")
        self.assertEqual(timeline["summary"]["endLabel"], "Ready To Buy")
        self.assertEqual(timeline["summary"]["trend"], "Improving")
        self.assertGreater(timeline["summary"]["curveConfidence"], 0.0)

if __name__ == "__main__":
    unittest.main()
