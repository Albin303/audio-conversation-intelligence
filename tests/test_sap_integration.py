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
        failing_client.create_lead.side_effect = SAPRequestError("SAP is down", status_code=500)
        service = SAPLeadService(client=failing_client)

        analysis_result = dict(self.sample_pipeline_result)
        analysis_result["transcript"] = "Customer conversation still exists"
        analysis_result["sapLead"] = await service.create_lead_from_analysis(analysis_result)

        self.assertEqual(analysis_result["transcript"], "Customer conversation still exists")
        self.assertFalse(analysis_result["sapLead"]["leadCreated"])
        self.assertEqual(analysis_result["sapLead"]["sapStatus"], "failed")
        self.assertEqual(analysis_result["sapLead"]["httpStatus"], 500)


if __name__ == "__main__":
    unittest.main()
