from __future__ import annotations

import logging
from typing import Any

import httpx

from src.integrations.sap_c4c.config import SAPConfig


logger = logging.getLogger("nexus.integrations.sap_c4c")


class SAPC4CError(Exception):
    """Base exception for SAP C4C lead creation failures."""


class SAPConfigurationError(SAPC4CError):
    """Raised when SAP integration is enabled but required config is missing."""


class SAPPayloadError(SAPC4CError):
    """Raised when the SAP payload is not valid for submission."""


class SAPRequestError(SAPC4CError):
    def __init__(self, message: str, *, status_code: int | None = None, response_body: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


def _extract_identifiers(payload: Any) -> tuple[str | None, str | None]:
    if not isinstance(payload, dict):
        return None, None

    value = payload.get("value")
    if isinstance(value, dict):
        lead_number = value.get("displayId") or value.get("displayID") or value.get("LeadID")
        object_id = value.get("id") or value.get("ID") or value.get("ObjectID")
        if lead_number or object_id:
            return str(lead_number) if lead_number else None, str(object_id) if object_id else None

    for key in ("displayId", "displayID", "LeadID", "LeadId", "leadId", "ID", "Id", "ObjectID", "ObjectId"):
        value = payload.get(key)
        if value:
            object_id = payload.get("id") or payload.get("ObjectID")
            return str(value), str(object_id) if object_id else None

    nested = payload.get("d")
    if isinstance(nested, dict):
        nested_id, nested_object_id = _extract_identifiers(nested)
        if nested_id:
            return nested_id, nested_object_id
        results = nested.get("results")
        if isinstance(results, list) and results:
            return _extract_identifiers(results[0])

    return None, None


class SAPClient:
    def __init__(self, config: SAPConfig | None = None) -> None:
        self.config = config or SAPConfig.load_from_env()

    def _validate_config(self) -> None:
        missing = self.config.missing_required_fields()
        if missing:
            raise SAPConfigurationError(
                "SAP C4C integration is missing required environment variables: "
                + ", ".join(missing)
            )

    @staticmethod
    def _validate_payload(payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict) or not payload:
            raise SAPPayloadError("SAP lead payload must be a non-empty dictionary")
        required_top_level = ("name", "source", "account", "primaryContact", "notes", "extensions")
        missing = [field for field in required_top_level if field not in payload]
        if missing:
            raise SAPPayloadError("SAP lead payload is missing required fields: " + ", ".join(missing))
        if not isinstance(payload.get("name"), str):
            raise SAPPayloadError("SAP lead payload field name must be a string")
        if not isinstance(payload.get("source"), str):
            raise SAPPayloadError("SAP lead payload field source must be a string")

        account = payload.get("account")
        if not isinstance(account, dict):
            raise SAPPayloadError("SAP lead payload field account must be an object")
        for field in ("formattedName", "firstLineName", "address"):
            if field not in account:
                raise SAPPayloadError(f"SAP lead payload field account.{field} is required")
        if not isinstance(account.get("formattedName"), str):
            raise SAPPayloadError("SAP lead payload field account.formattedName must be a string")
        if not isinstance(account.get("firstLineName"), str):
            raise SAPPayloadError("SAP lead payload field account.firstLineName must be a string")

        address = account.get("address")
        if not isinstance(address, dict):
            raise SAPPayloadError("SAP lead payload field account.address must be an object")
        for field in ("region", "email", "mobileFormattedNumber"):
            if field not in address:
                raise SAPPayloadError(f"SAP lead payload field account.address.{field} is required")
        if not isinstance(address.get("region"), dict):
            raise SAPPayloadError("SAP lead payload field account.address.region must be an object")
        if not isinstance(address.get("email"), str):
            raise SAPPayloadError("SAP lead payload field account.address.email must be a string")
        if not isinstance(address.get("mobileFormattedNumber"), str):
            raise SAPPayloadError("SAP lead payload field account.address.mobileFormattedNumber must be a string")

        primary_contact = payload.get("primaryContact")
        if not isinstance(primary_contact, dict):
            raise SAPPayloadError("SAP lead payload field primaryContact must be an object")
        for field in ("isPrimary", "givenName", "familyName"):
            if field not in primary_contact:
                raise SAPPayloadError(f"SAP lead payload field primaryContact.{field} is required")
        if not isinstance(primary_contact.get("isPrimary"), bool):
            raise SAPPayloadError("SAP lead payload field primaryContact.isPrimary must be a boolean")
        if not isinstance(primary_contact.get("givenName"), str):
            raise SAPPayloadError("SAP lead payload field primaryContact.givenName must be a string")
        if not isinstance(primary_contact.get("familyName"), str):
            raise SAPPayloadError("SAP lead payload field primaryContact.familyName must be a string")

        notes = payload.get("notes")
        if not isinstance(notes, list) or not notes:
            raise SAPPayloadError("SAP lead payload field notes must be a non-empty list")
        if not isinstance(notes[0], dict) or not isinstance(notes[0].get("content"), str):
            raise SAPPayloadError("SAP lead payload field notes[0].content must be a string")

        extensions = payload.get("extensions")
        if not isinstance(extensions, dict):
            raise SAPPayloadError("SAP lead payload field extensions must be an object")
        if not isinstance(extensions.get("Z_K_MarketSegment"), str):
            raise SAPPayloadError("SAP lead payload field extensions.Z_K_MarketSegment must be a string")

    async def create_lead(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.config.enabled:
            logger.info("sap_c4c_disabled")
            return {
                "status": "disabled",
                "lead_created": False,
                "lead_id": None,
                "object_id": None,
                "http_status": None,
                "error": None,
            }

        self._validate_config()
        self._validate_payload(payload)

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        auth = httpx.BasicAuth(self.config.username, self.config.password)

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    self.config.endpoint,
                    json=payload,
                    headers=headers,
                    auth=auth,
                )
        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError, httpx.TransportError) as exc:
            logger.warning("sap_c4c_request_failed_no_retry", extra={"sap_status": "request_error"})
            raise SAPRequestError(f"SAP C4C request failed: {exc}") from exc

        if 200 <= response.status_code < 300:
            try:
                body: Any = response.json()
            except ValueError:
                body = {}
            lead_id, object_id = _extract_identifiers(body)
            logger.info(
                "sap_c4c_lead_created",
                extra={
                    "sap_status": "success",
                    "sap_http_status": response.status_code,
                    "sap_lead_id": lead_id,
                },
            )
            return {
                "status": "success",
                "lead_created": True,
                "lead_id": lead_id,
                "object_id": object_id,
                "http_status": response.status_code,
                "error": None,
            }

        error = SAPRequestError(
            f"SAP C4C returned HTTP {response.status_code}",
            status_code=response.status_code,
            response_body=response.text[:1000],
        )
        logger.error(
            "sap_c4c_lead_create_failed",
            extra={
                "sap_status": "failed",
                "sap_http_status": response.status_code,
            },
        )
        raise error
