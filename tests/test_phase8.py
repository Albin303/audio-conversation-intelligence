import unittest
from unittest.mock import patch, MagicMock
from src.services.report_service import report_service

class EnterpriseReportTests(unittest.TestCase):
    def test_generate_report_none(self):
        # When job does not exist, return None
        res = report_service.generate_report("invalid-job-id")
        self.assertIsNone(res)

    @patch("src.services.report_service.ReportService.get_report")
    def test_generate_report_success(self, mock_get_report):
        mock_result = {
            "conversationSummary": {
                "overview": "Test call summary",
                "customerNeed": "laptop",
                "outcome": "pending",
                "nextAction": "follow up"
            },
            "conversionScore": {
                "explainability": {
                    "Lead Score": 85.0,
                    "Recommendation": "Call them back"
                },
                "decisionTrace": {
                    "contributions": {
                        "xgboost_contribution": 0.35,
                        "intent_contribution": 0.20,
                    },
                    "formula": "fusion formula"
                }
            },
            "rawFeatures": [
                {"value": "too costly", "label": "OBJECTION"}
            ],
            "conversationStages": [
                {"stage": "Opening", "startTime": 0.0, "endTime": 5.0, "confidence": 0.95}
            ],
            "sentimentTimeline": {
                "summary": {
                    "startLabel": "Neutral",
                    "endLabel": "Positive",
                    "trend": "Improving",
                    "curveConfidence": 0.85
                }
            },
            "analytics": {
                "followUpPriority": "High",
                "riskScore": 0.35
            },
            "privacy": {
                "grouped": {
                    "customer_name": ["Alice"],
                    "agent_name": ["Bob"],
                    "job_title": ["Engineer"],
                    "budget": ["60000"]
                }
            }
        }
        
        mock_get_report.return_value = mock_result
        
        report = report_service.generate_report("test-job-id")
        
        self.assertIsNotNone(report)
        self.assertEqual(report["jobId"], "test-job-id")
        self.assertEqual(report["profile"]["customerName"], "Alice")
        self.assertEqual(report["profile"]["agentName"], "Bob")
        self.assertEqual(report["profile"]["leadScore"], 85.0)
        self.assertEqual(report["objections"]["totalObjections"], 1)
        self.assertEqual(report["objections"]["list"], ["too costly"])
        self.assertEqual(len(report["stages"]), 1)
        self.assertEqual(report["stages"][0]["stage"], "Opening")
        self.assertIn("SPEECH INTELLIGENCE AND INTENT DETECTION CONVERSATION ANALYSIS REPORT", report["exportableText"])
        self.assertIn("Alice", report["exportableText"])

if __name__ == "__main__":
    unittest.main()
