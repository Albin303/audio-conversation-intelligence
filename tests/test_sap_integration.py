import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from src.integrations.sap_c4c.client import (
    SAPClient,
    SAPConfigurationError,
    SAPPayloadError,
    SAPRequestError,
)
from src.integrations.sap_c4c.config import SAPConfig
from src.integrations.sap_c4c.mapper import map_pipeline_result_to_sap
from src.services.sap_lead_service import SAPLeadService


def config(**overrides):
    values = {
        "enabled": True,
        "endpoint": "https://sap.example.com/leads",
        "username": "user",
        "password": "pwd",
        "timeout": 5.0,
        "lead_source": "Z3",
        "market_segment": "001",
    }
    values.update(overrides)
    return SAPConfig(**values)


def response(status_code, body=None, text=""):
    mock_response = AsyncMock()
    mock_response.status_code = status_code
    mock_response.text = text
    mock_response.json = lambda: body or {}
    return mock_response


VALID_SAP_PAYLOAD = {
    "name": "Lead Prospect - Alice Smith",
    "source": "Z3",
    "account": {
        "formattedName": "Alice Smith",
        "firstLineName": "Alice Smith",
        "address": {
            "region": {},
            "email": "alice@example.com",
            "mobileFormattedNumber": "+1-555-0199",
        },
    },
    "primaryContact": {
        "isPrimary": True,
        "givenName": "Alice",
        "familyName": "Smith",
    },
    "notes": [{"content": "Test notes"}],
    "extensions": {"Z_K_MarketSegment": "001"},
}


class SAPIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.sample_pipeline_result = {
            "privacy": {
                "grouped": {
                    "customer_name": ["Alice Smith"],
                    "email": ["alice@example.com"],
                    "customer_number": ["+1-555-0199"],
                }
            },
            "conversationSummary": {
                "overview": "Alice is very interested in the premium phone and asked about discounts."
            },
            "conversionScore": {
                "probability": 0.85,
                "label": "hot",
            },
            "summary": {
                "dominant": "positive",
            },
            "products": [
                {"name": "Galaxy S25"},
            ],
            "rawFeatures": [
                {"label": "PRODUCT", "value": "Galaxy S25"},
            ],
        }

    def test_config_loading(self):
        with patch.dict(os.environ, {
            "SAP_C4C_ENABLED": "true",
            "SAP_C4C_ENDPOINT": "https://sap.example.com/leads",
            "SAP_C4C_USERNAME": "testuser",
            "SAP_C4C_PASSWORD": "testpassword",
            "SAP_C4C_TIMEOUT_SEC": "5.0",
            "SAP_C4C_LEAD_SOURCE": "Z3",
            "SAP_C4C_MARKET_SEGMENT": "001",
        }):
            sap_config = SAPConfig.load_from_env()
            self.assertTrue(sap_config.enabled)
            self.assertEqual(sap_config.endpoint, "https://sap.example.com/leads")
            self.assertEqual(sap_config.username, "testuser")
            self.assertEqual(sap_config.password, "testpassword")
            self.assertEqual(sap_config.timeout, 5.0)
            self.assertEqual(sap_config.lead_source, "Z3")
            self.assertEqual(sap_config.market_segment, "001")

    def test_correct_payload_mapping(self):
        sap_payload = map_pipeline_result_to_sap(self.sample_pipeline_result)

        self.assertEqual(sap_payload["name"], "Lead Prospect - Alice Smith")
        self.assertEqual(sap_payload["source"], "Z3")
        self.assertEqual(sap_payload["account"]["formattedName"], "Alice Smith")
        self.assertEqual(sap_payload["account"]["firstLineName"], "Alice Smith")
        self.assertEqual(sap_payload["account"]["address"]["region"], {})
        self.assertEqual(sap_payload["account"]["address"]["email"], "alice@example.com")
        self.assertEqual(sap_payload["account"]["address"]["mobileFormattedNumber"], "+1-555-0199")
        self.assertEqual(sap_payload["primaryContact"]["isPrimary"], True)
        self.assertEqual(sap_payload["primaryContact"]["givenName"], "Alice")
        self.assertEqual(sap_payload["primaryContact"]["familyName"], "Smith")
        self.assertIn("Lead Score: 85", sap_payload["notes"][0]["content"])
        self.assertIn("Intent: Hot", sap_payload["notes"][0]["content"])
        self.assertIn("Sentiment: Positive", sap_payload["notes"][0]["content"])
        self.assertEqual(sap_payload["extensions"]["Z_K_MarketSegment"], "001")

    def test_dynamic_mapping_uses_ai_fields_and_rich_notes(self):
        result = {
            "privacy": {
                "grouped": {
                    "customer_name": ["Jane Doe"],
                    "company_name": ["Acme Corp"],
                    "email": ["jane@example.com"],
                    "customer_number": ["+1-555-0100"],
                }
            },
            "conversationSummary": {
                "overview": "Jane wants a demo for the CRM platform.",
                "nextAction": "Schedule a product demo next week.",
                "customerNeed": "Enterprise CRM rollout",
                "Risks": ["Budget approval is pending"],
                "keyPoints": ["Needs ERP integration", "Budget approval pending"],
            },
            "products": [{"name": "Nexus AI CRM"}],
            "rawFeatures": [
                {"label": "PRODUCT", "value": "Nexus AI CRM"},
                {"label": "BUDGET", "value": "50000"},
                {"label": "COMPETITOR", "value": "Salesforce"},
                {"label": "INTENT", "value": "High Interest"},
            ],
            "summary": {"dominant": "positive"},
            "conversionScore": {"probability": 0.92, "label": "hot"},
            "prediction": {"probability": 0.92, "label": "hot"},
        }

        sap_payload = map_pipeline_result_to_sap(result)

        self.assertEqual(sap_payload["account"]["formattedName"], "Jane Doe")
        self.assertEqual(sap_payload["account"]["address"]["email"], "jane@example.com")
        self.assertEqual(sap_payload["account"]["address"]["mobileFormattedNumber"], "+1-555-0100")
        self.assertIn("Customer: Jane Doe", sap_payload["notes"][0]["content"])
        self.assertIn("Company: Acme Corp", sap_payload["notes"][0]["content"])
        self.assertIn("Product Interest: Nexus AI CRM", sap_payload["notes"][0]["content"])
        self.assertIn("Lead Score: 92", sap_payload["notes"][0]["content"])
        self.assertIn("Intent: Hot", sap_payload["notes"][0]["content"])
        self.assertIn("Sentiment: Positive", sap_payload["notes"][0]["content"])
        self.assertIn("Recommendation: Schedule a product demo next week.", sap_payload["notes"][0]["content"])

    def test_missing_email_and_phone_still_create_payload(self):
        result = {
            "privacy": {"grouped": {"customer_name": ["No Contact"]}},
            "conversationSummary": {"overview": "No contact details were provided.", "nextAction": "Follow up by phone."},
            "products": [{"name": "Workflow Platform"}],
            "summary": {"dominant": "neutral"},
            "conversionScore": {"probability": 0.44, "label": "warm"},
        }

        sap_payload = map_pipeline_result_to_sap(result)

        self.assertEqual(sap_payload["account"]["formattedName"], "No Contact")
        self.assertEqual(sap_payload["account"]["address"]["email"], "")
        self.assertEqual(sap_payload["account"]["address"]["mobileFormattedNumber"], "")
        self.assertIn("Product Interest: Workflow Platform", sap_payload["notes"][0]["content"])
        self.assertIn("Lead Score: 44", sap_payload["notes"][0]["content"])

    def test_single_word_customer_name_uses_family_name_fallback(self):
        result = {
            "privacy": {"grouped": {"customer_name": ["Swetha"]}},
            "conversationSummary": {"overview": "Customer asked for phone recommendations."},
            "conversionScore": {"probability": 0.41, "label": "warm"},
        }

        sap_payload = map_pipeline_result_to_sap(result)

        self.assertEqual(sap_payload["primaryContact"]["givenName"], "Swetha")
        self.assertEqual(sap_payload["primaryContact"]["familyName"], "Lead")

    def test_only_product_interest_is_used_when_other_fields_are_missing(self):
        result = {
            "products": [{"name": "Analytics Suite"}],
            "rawFeatures": [{"label": "PRODUCT", "value": "Analytics Suite"}],
            "conversationSummary": {"overview": "Interested in analytics capabilities."},
        }

        sap_payload = map_pipeline_result_to_sap(result)

        self.assertEqual(sap_payload["account"]["formattedName"], "Prospect Lead")
        self.assertIn("Product Interest: Analytics Suite", sap_payload["notes"][0]["content"])
        self.assertIn("Lead Score: 0", sap_payload["notes"][0]["content"])

    def test_notes_use_sales_summary_sections_and_confidence(self):
        result = {
            "transcript": "Hi, my name is Jane Doe. I work at Acme Corp. My email is jane@acme.com and phone is +1-555-0100. My budget is 50000 and I need a CRM demo next week.",
            "conversationSummary": {
                "overview": "Jane wants a CRM demo next week.",
                "nextAction": "Schedule a product demo next week.",
                "Risks": ["Budget approval is pending"],
                "customerNeed": "Enterprise CRM rollout",
            },
            "rawFeatures": [{"label": "DECISION_MAKER", "value": "CEO"}],
            "summary": {"dominant": "positive"},
            "conversionScore": {"probability": 0.92, "label": "hot"},
        }

        sap_payload = map_pipeline_result_to_sap(result)
        content = sap_payload["notes"][0]["content"]

        self.assertIn("Customer Information", content)
        self.assertIn("Sales Insights", content)
        self.assertIn("Business Insights", content)
        self.assertIn("Recommendation", content)
        self.assertIn("Name: Jane Doe", content)
        self.assertIn("Company: Acme Corp", content)
        self.assertIn("Email: jane@acme.com", content)
        self.assertIn("Phone: +1-555-0100", content)
        self.assertIn("Decision Maker: CEO", content)
        self.assertIn("Budget: 50000", content)
        self.assertIn("Timeline: next week", content)
        self.assertIn("Confidence", content)

    def test_payload_mapping_fallbacks(self):
        sap_payload = map_pipeline_result_to_sap({})

        self.assertEqual(sap_payload["name"], "Lead Prospect - Prospect Lead")
        self.assertEqual(sap_payload["account"]["formattedName"], "Prospect Lead")
        self.assertEqual(sap_payload["account"]["address"]["email"], "")
        self.assertEqual(sap_payload["account"]["address"]["mobileFormattedNumber"], "")
        self.assertEqual(sap_payload["primaryContact"]["givenName"], "Prospect")
        self.assertEqual(sap_payload["primaryContact"]["familyName"], "Lead")
        self.assertIn("Product Interest: CRM Software", sap_payload["notes"][0]["content"])
        self.assertIn("Lead Score: 0", sap_payload["notes"][0]["content"])

    def test_wrong_pipeline_result_type(self):
        with self.assertRaises(ValueError):
            map_pipeline_result_to_sap(None)  # type: ignore[arg-type]

    async def test_client_disabled(self):
        client = SAPClient(config(enabled=False))
        result = await client.create_lead(VALID_SAP_PAYLOAD)

        self.assertEqual(result["status"], "disabled")
        self.assertFalse(result["lead_created"])

    async def test_wrong_payload(self):
        client = SAPClient(config())
        with self.assertRaises(SAPPayloadError):
            await client.create_lead({"Name": "Lead"})

    async def test_missing_credentials(self):
        client = SAPClient(config(username="", password=""))
        with self.assertRaises(SAPConfigurationError):
            await client.create_lead(VALID_SAP_PAYLOAD)

    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_client_success(self, mock_post):
        mock_post.return_value = response(201, {"value": {"id": "510e08a1-81af-11f1-923b-d37dc5bdb092", "displayId": "165"}})
        client = SAPClient(config())

        payload = map_pipeline_result_to_sap(self.sample_pipeline_result)
        result = await client.create_lead(payload)

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["lead_created"])
        self.assertEqual(result["lead_id"], "165")
        self.assertEqual(result["object_id"], "510e08a1-81af-11f1-923b-d37dc5bdb092")
        self.assertEqual(result["http_status"], 201)
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"]["Accept"], "application/json")
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertIsInstance(kwargs["auth"], httpx.BasicAuth)

    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_wrong_credentials_401_response(self, mock_post):
        mock_post.return_value = response(401, text="Unauthorized Access")
        client = SAPClient(config(username="bad_user"))

        with self.assertRaises(SAPRequestError) as cm:
            await client.create_lead(VALID_SAP_PAYLOAD)

        self.assertEqual(cm.exception.status_code, 401)
        self.assertIn("HTTP 401", str(cm.exception))

    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_400_response(self, mock_post):
        mock_post.return_value = response(400, text="Bad payload")
        client = SAPClient(config())

        with self.assertRaises(SAPRequestError) as cm:
            await client.create_lead(VALID_SAP_PAYLOAD)

        self.assertEqual(cm.exception.status_code, 400)
        self.assertEqual(mock_post.await_count, 1)

    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_500_response_does_not_retry_non_idempotent_post(self, mock_post):
        mock_post.return_value = response(500, text="SAP unavailable")
        client = SAPClient(config())

        with self.assertRaises(SAPRequestError) as cm:
            await client.create_lead(VALID_SAP_PAYLOAD)

        self.assertEqual(cm.exception.status_code, 500)
        self.assertEqual(mock_post.await_count, 1)

    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_timeout(self, mock_post):
        mock_post.side_effect = httpx.TimeoutException("Connection timed out")
        client = SAPClient(config())

        with self.assertRaises(SAPRequestError) as cm:
            await client.create_lead(VALID_SAP_PAYLOAD)

        self.assertIn("Connection timed out", str(cm.exception))
        self.assertEqual(mock_post.await_count, 1)

    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_connection_failure(self, mock_post):
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        client = SAPClient(config())

        with self.assertRaises(SAPRequestError) as cm:
            await client.create_lead(VALID_SAP_PAYLOAD)

        self.assertIn("Connection refused", str(cm.exception))
        self.assertEqual(mock_post.await_count, 1)

    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_network_loss(self, mock_post):
        mock_post.side_effect = httpx.NetworkError("Network is unreachable")
        client = SAPClient(config())

        with self.assertRaises(SAPRequestError) as cm:
            await client.create_lead(VALID_SAP_PAYLOAD)

        self.assertIn("Network is unreachable", str(cm.exception))
        self.assertEqual(mock_post.await_count, 1)

    async def test_ai_result_survives_sap_failure(self):
        failing_client = AsyncMock()
        failing_client.create_lead.side_effect = SAPRequestError(
            "SAP is down",
            status_code=500,
            response_body="Validation details",
        )
        service = SAPLeadService(client=failing_client)

        analysis_result = dict(self.sample_pipeline_result)
        analysis_result["transcript"] = "Customer conversation still exists"
        analysis_result["sapLead"] = await service.create_lead_from_analysis(analysis_result)

        self.assertEqual(analysis_result["transcript"], "Customer conversation still exists")
        self.assertFalse(analysis_result["sapLead"]["leadCreated"])
        self.assertEqual(analysis_result["sapLead"]["sapStatus"], "failed")
        self.assertEqual(analysis_result["sapLead"]["httpStatus"], 500)
        self.assertIn("Validation details", analysis_result["sapLead"]["error"])
        self.assertIsNotNone(analysis_result["sapLead"]["payload"])

    def test_phone_number_formats_and_aliases(self):
        phone_examples = [
            ("+91 98765 43210", "+91 98765 43210"),
            ("9876543210", "9876543210"),
            ("+91-98765-43210", "+91-98765-43210"),
            ("(987) 654-3210", "(987) 654-3210"),
        ]
        from src.aspect_sentiment.privacy import extract_and_redact_pii
        for raw_text, expected_phone in phone_examples:
            privacy = extract_and_redact_pii(f"My contact number is {raw_text}")
            result = {
                "privacy": {
                    "grouped": {
                        "customer_number": [entity.value for entity in privacy.entities if entity.type in ("customer_number", "phone")],
                        "customer_name": ["John Doe"],
                    }
                }
            }
            sap_payload = map_pipeline_result_to_sap(result)
            self.assertEqual(sap_payload["account"]["address"]["mobileFormattedNumber"], expected_phone)
            # primaryContact.mobile is not in the verified SAP C4C schema; only account.address.mobileFormattedNumber is confirmed.
            self.assertIn("mobileFormattedNumber", sap_payload["account"]["address"])

    @patch("src.services.analysis_service.process_text", new_callable=AsyncMock)
    @patch("src.services.analysis_service.summarize_conversation", new_callable=AsyncMock)
    async def test_full_contact_fields_end_to_end(self, mock_sum, mock_proc):
        mock_proc.return_value = {
            "raw_features": [{"label": "PRODUCT", "value": "CRM software"}],
            "sentiment_score": 0.5,
            "confidence_score": 0.8,
            "hesitation_score": 0,
            "delay_flag": 0,
            "brand_count": 0,
            "feature_count": 1,
            "interaction_length": 1,
            "extraction_provider": "mock",
        }
        mock_sum.return_value = {
            "overview": "John Doe wants CRM software.",
            "nextAction": "Follow up with John.",
            "confidence": 0.9,
        }
        from src.services.analysis_service import AnalysisService
        svc = AnalysisService()
        transcript = "Hello, my name is John Doe. My email is john.doe@example.com and my phone number is +91 98765 43210. I work at Acme Corp. I want CRM software."
        analysis_res = await svc.run_pipeline(transcript, source_name="test_call", source_type="text", started=0.0)
        sap_payload = map_pipeline_result_to_sap(analysis_res)

        self.assertEqual(sap_payload["account"]["formattedName"], "John Doe")
        self.assertEqual(sap_payload["primaryContact"]["givenName"], "John")
        self.assertEqual(sap_payload["primaryContact"]["familyName"], "Doe")
        self.assertEqual(sap_payload["account"]["address"]["email"], "john.doe@example.com")
        # primaryContact.email is not in the verified SAP C4C schema; pending OData $metadata confirmation.
        self.assertEqual(sap_payload["account"]["address"]["mobileFormattedNumber"], "+91 98765 43210")
        # primaryContact.mobile is not in the verified SAP C4C schema; pending OData $metadata confirmation.
        self.assertIn("Company: Acme Corp", sap_payload["notes"][0]["content"])
        self.assertIn("Phone: +91 98765 43210", sap_payload["notes"][0]["content"])
        self.assertIn("Email: john.doe@example.com", sap_payload["notes"][0]["content"])


if __name__ == "__main__":
    unittest.main()
