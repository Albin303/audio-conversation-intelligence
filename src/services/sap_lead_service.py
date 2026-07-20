from __future__ import annotations

import logging
from typing import Any

from src.integrations.sap_c4c.client import (
    SAPC4CError,
    SAPClient,
    SAPRequestError,
)
from src.integrations.sap_c4c.mapper import map_pipeline_result_to_sap


logger = logging.getLogger("nexus.services.sap_lead")


class SAPLeadService:
    def __init__(self, client: SAPClient | None = None) -> None:
        self.client = client or SAPClient()

    async def create_lead_from_analysis(self, analysis_result: dict[str, Any]) -> dict[str, Any]:
        try:
            payload = map_pipeline_result_to_sap(
                analysis_result,
                lead_source=self.client.config.lead_source,
                market_segment=self.client.config.market_segment,
            )
            client_result = await self.client.create_lead(payload)
            sap_result = {
                "leadCreated": bool(client_result.get("lead_created")),
                "leadId": client_result.get("lead_id"),
                "objectId": client_result.get("object_id"),
                "sapStatus": client_result.get("status", "unknown"),
                "httpStatus": client_result.get("http_status"),
                "error": client_result.get("error"),
                "payload": payload,
            }
            logger.info(
                "sap_lead_sync_completed",
                extra={
                    "sap_status": sap_result["sapStatus"],
                    "sap_http_status": sap_result["httpStatus"],
                    "sap_lead_id": sap_result["leadId"],
                },
            )
            return sap_result
        except SAPRequestError as exc:
            logger.warning(
                "sap_lead_sync_failed",
                extra={
                    "sap_status": "failed",
                    "sap_http_status": exc.status_code,
                },
            )
            return {
                "leadCreated": False,
                "leadId": None,
                "objectId": None,
                "sapStatus": "failed",
                "httpStatus": exc.status_code,
                "error": str(exc),
                "payload": None,
            }
        except SAPC4CError as exc:
            logger.warning("sap_lead_sync_unavailable", extra={"sap_status": "failed"})
            return {
                "leadCreated": False,
                "leadId": None,
                "objectId": None,
                "sapStatus": "failed",
                "httpStatus": None,
                "error": str(exc),
                "payload": None,
            }
        except Exception as exc:
            logger.exception("sap_lead_sync_unexpected_error", extra={"sap_status": "failed"})
            return {
                "leadCreated": False,
                "leadId": None,
                "objectId": None,
                "sapStatus": "failed",
                "httpStatus": None,
                "error": f"Unexpected SAP integration error: {exc}",
                "payload": None,
            }


sap_lead_service = SAPLeadService()
