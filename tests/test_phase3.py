import unittest
import asyncio
from unittest.mock import patch, AsyncMock
from src.aspect_sentiment.diarization import TranscriptTurn
from src.aspect_sentiment.llama_extraction import detect_conversation_stages, summarize_conversation, _fallback_summary

class StageDetectionAndIntelligenceTests(unittest.TestCase):
    def test_detect_conversation_stages(self):
        turns = [
            TranscriptTurn(speaker="Agent", text="Hello and welcome to TechNova! My name is Sarah. How can I help you today?", start=0.0, end=4.0, confidence=0.9),
            TranscriptTurn(speaker="Customer", text="Hi Sarah, I am looking for a gaming laptop. I need something with a good GPU, like an RTX 4060, for programming and gaming.", start=4.5, end=9.5, confidence=0.88),
            TranscriptTurn(speaker="Agent", text="Great, we have the Dell G15 and HP Victus in stock. What is your budget?", start=10.0, end=14.0, confidence=0.92),
            TranscriptTurn(speaker="Customer", text="My budget is under 70000 rupees. Do you have any discounts or EMI options available?", start=14.5, end=19.5, confidence=0.85),
            TranscriptTurn(speaker="Agent", text="We have a 5% discount on credit card payments and no-cost EMI up to 6 months.", start=20.0, end=25.0, confidence=0.9),
            TranscriptTurn(speaker="Customer", text="That sounds okay, but I am not sure, it seems a bit expensive compared to other stores. Let me think about it and get back to you later.", start=25.5, end=31.5, confidence=0.8),
            TranscriptTurn(speaker="Agent", text="No problem. I will share the details over WhatsApp and follow up tomorrow. Thank you for calling!", start=32.0, end=37.0, confidence=0.95),
            TranscriptTurn(speaker="Customer", text="Thanks, goodbye.", start=37.5, end=39.5, confidence=0.9),
        ]
        
        stages = detect_conversation_stages(turns)
        
        # Verify stages list is not empty
        self.assertGreater(len(stages), 0)
        
        # Check that we have key stages represented
        stage_names = [s["stage"] for s in stages]
        self.assertIn("Opening", stage_names)
        self.assertIn("Discovery", stage_names)
        self.assertIn("Pricing", stage_names)
        self.assertIn("Negotiation", stage_names)
        self.assertIn("Closing", stage_names)
        
        # Verify indices and times are structured correctly
        for segment in stages:
            self.assertIn("stage", segment)
            self.assertIn("startIndex", segment)
            self.assertIn("endIndex", segment)
            self.assertIn("startTime", segment)
            self.assertIn("endTime", segment)
            self.assertIn("confidence", segment)
            self.assertGreaterEqual(segment["endIndex"], segment["startIndex"])
            self.assertGreaterEqual(segment["endTime"], segment["startTime"])

    def test_summary_keys_backward_compatibility(self):
        # Test fallback summary directly first
        res = _fallback_summary("Hi, I want a laptop under 60000. Price is expensive, get back later.")
        
        # Check old keys
        self.assertIn("overview", res)
        self.assertIn("customerNeed", res)
        self.assertIn("keyPoints", res)
        self.assertIn("outcome", res)
        self.assertIn("nextAction", res)
        self.assertIn("confidence", res)
        
        # Check new keys
        self.assertIn("Conversation Summary", res)
        self.assertIn("Key Moments", res)
        self.assertIn("Important Quotes", res)
        self.assertIn("Action Items", res)
        self.assertIn("Risks", res)
        self.assertIn("Recommendations", res)
        
        # Verify types
        self.assertIsInstance(res["Key Moments"], list)
        self.assertIsInstance(res["Important Quotes"], list)
        self.assertIsInstance(res["Action Items"], list)
        self.assertIsInstance(res["Risks"], list)
        self.assertIsInstance(res["Recommendations"], list)

    @patch("src.aspect_sentiment.llama_extraction.call_llama", new_callable=AsyncMock)
    def test_summarize_conversation_api_keys(self, mock_call):
        # Mock LLaMA returning the new structure
        mock_call.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"Conversation Summary": "Customer is exploring laptops under 60k.", "Key Moments": ["Customer asked for laptop", "Budget discussed"], "Important Quotes": ["\\u201cI want a laptop under 60000\\u201d"], "Action Items": ["Follow up with details"], "Risks": ["None"], "Recommendations": ["Offer Dell models"], "overview": "overview sentence", "customerNeed": "laptop", "keyPoints": ["point 1"], "outcome": "pending", "nextAction": "follow up", "confidence": 0.85}'
                    }
                }
            ]
        }
        
        res = asyncio.run(summarize_conversation("some transcript"))
        
        # Verify all keys are present
        self.assertEqual(res["Conversation Summary"], "Customer is exploring laptops under 60k.")
        self.assertEqual(res["Important Quotes"], ["“I want a laptop under 60000”"])
        self.assertEqual(res["overview"], "overview sentence")
        self.assertEqual(res["customerNeed"], "laptop")
        self.assertEqual(res["confidence"], 0.85)

if __name__ == "__main__":
    unittest.main()
