import unittest
from src.aspect_sentiment.role_classifier import classify_role_hybrid

class RoleClassificationTests(unittest.TestCase):
    def test_agent_classification_reasons(self):
        result = classify_role_hybrid(
            "Speaker_A",
            "Good morning, this is Sarah calling from TechNova. I can suggest some great EMI options and discounts available. May I know your budget and brand preference?",
            speaker_word_count=28,
            total_word_count=40,
        )
        
        self.assertEqual(result["role"], "Agent")
        self.assertGreater(result["confidence"], 0.7)
        self.assertIn("reason", result)
        self.assertIsInstance(result["reason"], list)
        self.assertGreater(len(result["reason"]), 0)
        
        # Reasons should explain why it is classified as Agent
        self.assertTrue(any(r in result["reason"] for r in ["Greeting", "Sales Vocabulary", "Question Pattern", "Speaking Ratio"]))

    def test_customer_classification_reasons(self):
        result = classify_role_hybrid(
            "Speaker_B",
            "I want to buy a laptop for gaming. My budget is under 50000 rupees. But I am not sure, it seems too expensive. I'll think about it and get back to you later.",
            speaker_word_count=35,
            total_word_count=50,
        )
        
        self.assertEqual(result["role"], "Customer")
        self.assertGreater(result["confidence"], 0.7)
        self.assertIn("reason", result)
        self.assertIsInstance(result["reason"], list)
        self.assertGreater(len(result["reason"]), 0)
        
        # Reasons should explain why it is classified as Customer
        self.assertTrue(any(r in result["reason"] for r in ["Objection Language", "Buying Language", "Closing Behavior", "Speaking Ratio"]))

if __name__ == "__main__":
    unittest.main()
