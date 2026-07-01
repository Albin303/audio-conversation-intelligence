import unittest
from src.aspect_sentiment.probability_fusion import fuse_probabilities

class LeadScoreExplainabilityTests(unittest.TestCase):
    def test_explainability_and_decision_trace(self):
        # Sample inputs
        xgboost_prob = 0.85
        transcript = "I want to buy a laptop. Price is good. Can I get a discount?"
        raw_features = [
            {"value": "laptop", "label": "PRODUCT"},
            {"value": "discount", "label": "PRICE_DISCUSSION"},
            {"value": "buy", "label": "INTENT"}
        ]
        sentiment_score = 0.4
        agent_transcript = "Sure, we have EMI options."
        
        result = fuse_probabilities(
            xgboost_prob=xgboost_prob,
            transcript=transcript,
            raw_features=raw_features,
            sentiment_score=sentiment_score,
            agent_transcript=agent_transcript,
        )
        
        # Verify backward-compatibility keys
        self.assertIn("prediction", result)
        self.assertIn("probability", result)
        self.assertIn("label", result)
        self.assertIn("reasons", result)
        
        # Verify Phase 5 new keys
        self.assertIn("explainability", result)
        self.assertIn("decisionTrace", result)
        
        exp = result["explainability"]
        self.assertIn("Lead Score", exp)
        self.assertIn("Positive Factors", exp)
        self.assertIn("Negative Factors", exp)
        self.assertIn("Most Influential Features", exp)
        self.assertIn("Confidence", exp)
        self.assertIn("Recommendation", exp)
        
        self.assertIsInstance(exp["Lead Score"], float)
        self.assertIsInstance(exp["Positive Factors"], list)
        self.assertIsInstance(exp["Negative Factors"], list)
        self.assertIsInstance(exp["Most Influential Features"], list)
        self.assertIsInstance(exp["Confidence"], float)
        self.assertIsInstance(exp["Recommendation"], str)
        
        trace = result["decisionTrace"]
        self.assertIn("inputs", trace)
        self.assertIn("contributions", trace)
        self.assertIn("formula", trace)
        
        # Verify contributions trace values are populated and positive
        contribs = trace["contributions"]
        self.assertGreater(contribs["xgboost_contribution"], 0.0)
        self.assertGreater(contribs["intent_contribution"], 0.0)
        self.assertEqual(trace["inputs"]["xgboost_base_probability"], xgboost_prob)

if __name__ == "__main__":
    unittest.main()
