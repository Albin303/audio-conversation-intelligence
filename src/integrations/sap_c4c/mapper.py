from __future__ import annotations

from typing import Any


DEFAULT_CUSTOMER_NAME = "Prospect Lead"
DEFAULT_PRODUCT_INTEREST = "CRM Software"
DEFAULT_LEAD_SOURCE = "Z3"
DEFAULT_MARKET_SEGMENT = "001"


def _first_grouped_value(grouped: dict[str, Any], *keys: str) -> str:
    for key in keys:
        values = grouped.get(key)
        if isinstance(values, list):
            for value in values:
                cleaned = str(value or "").strip()
                if cleaned:
                    return cleaned
        elif isinstance(values, str) and values.strip():
            return values.strip()
    return ""


def _title(value: Any, fallback: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        return fallback
    return " ".join(part.capitalize() for part in cleaned.replace("_", " ").split())


def _lead_score(result: dict[str, Any]) -> int:
    conversion_score = result.get("conversionScore") if isinstance(result.get("conversionScore"), dict) else {}
    prediction = result.get("prediction") if isinstance(result.get("prediction"), dict) else {}
    probability = conversion_score.get("probability", prediction.get("probability", 0.0))
    try:
        score = float(probability)
    except (TypeError, ValueError):
        score = 0.0
    if score <= 1:
        score *= 100
    return max(0, min(100, round(score)))


def _conversation_summary(result: dict[str, Any]) -> str:
    summary = result.get("conversationSummary")
    if isinstance(summary, dict):
        for key in ("overview", "summary", "Conversation Summary", "outcome", "nextAction"):
            value = str(summary.get(key) or "").strip()
            if value:
                return value
    for key in ("customerBehavioralTranscript", "customerTranscript", "transcript"):
        value = str(result.get(key) or "").strip()
        if value:
            return value[:1000]
    return "Conversation analyzed by Nexus AI."


def _split_name(full_name: str) -> tuple[str, str]:
    clean = " ".join(full_name.split()) or DEFAULT_CUSTOMER_NAME
    parts = clean.split(" ", 1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def _product_interest(result: dict[str, Any]) -> str:
    products = result.get("products")
    if isinstance(products, list):
        for product in products:
            if isinstance(product, dict):
                value = str(product.get("name") or product.get("value") or "").strip()
                if value:
                    return value

    raw_features = result.get("rawFeatures")
    if isinstance(raw_features, list):
        for feature in raw_features:
            if not isinstance(feature, dict):
                continue
            label = str(feature.get("label") or "").upper()
            if label in {"PRODUCT", "BRAND", "FEATURE", "USE_CASE"}:
                value = str(feature.get("name") or feature.get("value") or "").strip()
                if value:
                    return value
    return DEFAULT_PRODUCT_INTEREST


def map_pipeline_result_to_sap(
    result: dict[str, Any],
    *,
    lead_source: str = DEFAULT_LEAD_SOURCE,
    market_segment: str = DEFAULT_MARKET_SEGMENT,
) -> dict[str, Any]:
    """
    Transform a Nexus AI pipeline result into the SAP C4C Lead payload.

    The field names and nesting mirror the SAP C4C lead-service POST payload.
    """
    if not isinstance(result, dict):
        raise ValueError("Pipeline result must be a dictionary")

    privacy = result.get("privacy") if isinstance(result.get("privacy"), dict) else {}
    grouped = privacy.get("grouped") if isinstance(privacy.get("grouped"), dict) else {}

    customer_name = _first_grouped_value(grouped, "customer_name", "name", "person") or DEFAULT_CUSTOMER_NAME
    email = _first_grouped_value(grouped, "email", "contact_email")
    phone = _first_grouped_value(grouped, "customer_number", "phone", "mobile", "contact_phone")
    product_interest = _product_interest(result)
    given_name, family_name = _split_name(customer_name)

    conversion_score = result.get("conversionScore") if isinstance(result.get("conversionScore"), dict) else {}
    prediction = result.get("prediction") if isinstance(result.get("prediction"), dict) else {}
    intent = _title(conversion_score.get("label", prediction.get("label")), "Cold")

    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    sentiment = _title(summary.get("dominant"), "Neutral")

    note = (
        f"{_conversation_summary(result)}\n\n"
        f"Product Interest: {product_interest}\n"
        f"Intent: {intent}\n"
        f"Lead Score: {_lead_score(result)}\n"
        f"Sentiment: {sentiment}"
    )

    return {
        "name": f"Lead Prospect - {customer_name}",
        "source": lead_source,
        "account": {
            "formattedName": customer_name,
            "firstLineName": customer_name,
            "address": {
                "region": {},
                "email": email,
                "mobileFormattedNumber": phone,
            },
        },
        "primaryContact": {
            "isPrimary": True,
            "givenName": given_name,
            "familyName": family_name,
        },
        "notes": [
            {
                "content": note,
            }
        ],
        "extensions": {
            "Z_K_MarketSegment": market_segment,
        },
    }
