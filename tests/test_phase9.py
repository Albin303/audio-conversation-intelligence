import unittest
from pathlib import Path
from scripts.benchmark_accuracy import (
    run_wer_benchmark,
    run_der_benchmark,
    run_role_classification_benchmark,
    run_lead_scoring_benchmark,
    run_sentiment_benchmark
)

class BenchmarkAccuracyTests(unittest.TestCase):
    def test_benchmark_functions(self):
        # 1. Test Word Error Rate (WER) proxy
        wer = run_wer_benchmark()
        self.assertIsInstance(wer, float)
        self.assertGreaterEqual(wer, 0.0)
        
        # 2. Test Diarization Error Rate (DER) proxy
        der = run_der_benchmark()
        self.assertIsInstance(der, float)
        self.assertGreaterEqual(der, 0.0)
        
        # 3. Test Role Classification accuracy
        role_acc = run_role_classification_benchmark()
        self.assertIsInstance(role_acc, float)
        self.assertTrue(0.0 <= role_acc <= 1.0)
        
        # 4. Test Lead Scoring accuracy
        lead_acc = run_lead_scoring_benchmark()
        self.assertIsInstance(lead_acc, float)
        self.assertTrue(0.0 <= lead_acc <= 1.0)
        
        # 5. Test Sentiment accuracy
        sentiment_acc = run_sentiment_benchmark()
        self.assertIsInstance(sentiment_acc, float)
        self.assertTrue(0.0 <= sentiment_acc <= 1.0)

if __name__ == "__main__":
    unittest.main()
