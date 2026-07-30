from __future__ import annotations

import re
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


def _coerce_text(value: Any) -> str:
    cleaned = str(value or "").strip()
    return cleaned


def _extract_confidence(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _confidence_label(confidence: float | None) -> str:
    if confidence is None:
        return ""
    if confidence >= 0.9:
        return "High"
    if confidence >= 0.7:
        return "Medium"
    return "Low"


def _extract_from_transcript(text: str) -> dict[str, str]:
    extracted: dict[str, str] = {}
    if not text:
        return extracted

    name_match = None
    for pattern in [
        r"\b(?:my name is|this is|i am|i'm)\s+([A-Za-z]+(?:\s+[A-Za-z]+)+)",
        r"\bname is\s+([A-Za-z]+(?:\s+[A-Za-z]+)+)",
    ]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name_match = match.group(1)
            break
    if name_match:
        extracted["customer_name"] = name_match.strip()

    company_match = None
    for pattern in [
        r"\b(?:work(?:ing)?\s+(?:at|for)|from\s+(?:the\s+)?company)\s+([A-Za-z0-9&]+(?:\s+[A-Za-z0-9&]+){0,4})(?=\b|[.,!?])",
        r"\b(?:company|org|organization|team)\s+(?:is|named|called)?\s*([A-Za-z0-9&]+(?:\s+[A-Za-z0-9&]+){0,4})(?=\b|[.,!?])",
    ]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            company_match = match.group(1).strip(" ,.")
            break
    if company_match:
        extracted["company_name"] = company_match.strip()

    email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
    if email_match:
        extracted["email"] = email_match.group(0)

    phone_match = re.search(
        r"\b(?:my\s+)?(?:phone|mobile|cell|contact|whatsapp|telephone|tel)?(?:\s+(?:number|no\.?|num))?\s*(?:is|:|=|at|on)?\s*((?:\+?\d{1,4}[\s.-]?)?(?:\(\d{1,5}\)[\s.-]?)?\d{2,5}(?:[\s.-]?\d{2,5}){1,4})\b",
        text,
        re.IGNORECASE,
    )
    if not phone_match:
        phone_match = re.search(r"\b(?:\+?\d{1,4}[\s.-]?)?(?:\(\d{1,5}\)[\s.-]?)?\d{2,5}(?:[\s.-]?\d{2,5}){1,4}\b", text)

    if phone_match:
        extracted["phone"] = phone_match.group(1 if phone_match.lastindex else 0).strip()

    budget_match = re.search(r"\b(?:budget|price|cost)(?:\s+(?:is|of|around|under|up to))?\s*(?:₹|rs\.?|inr)?\s*([0-9][0-9,\.kKlL]*)", text, re.IGNORECASE)
    if budget_match:
        extracted["budget"] = budget_match.group(1).strip()

    timeline_match = None
    for pattern in [r"\bnext week\b", r"\btomorrow\b", r"\bthis month\b", r"\bwithin\s+\d+\s+days\b", r"\bwithin\s+\d+\s+weeks\b", r"\bsoon\b", r"\blater\b"]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            timeline_match = match.group(0)
            break
    if timeline_match:
        extracted["timeline"] = timeline_match.strip()

    decision_maker_match = re.search(r"\b(?:decision maker|approved by|via|contacted by|my (?:ceo|cto|manager|director|vp|president))\b", text, re.IGNORECASE)
    if decision_maker_match:
        extracted["decision_maker"] = decision_maker_match.group(0).strip()

    return extracted


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
        return parts[0], "Lead"
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


def _collect_ai_fields(result: dict[str, Any]) -> dict[str, Any]:
    privacy = result.get("privacy") if isinstance(result.get("privacy"), dict) else {}
    grouped = privacy.get("grouped") if isinstance(privacy.get("grouped"), dict) else {}

    conversation_summary = result.get("conversationSummary") if isinstance(result.get("conversationSummary"), dict) else {}
    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    conversion_score = result.get("conversionScore") if isinstance(result.get("conversionScore"), dict) else {}
    prediction = result.get("prediction") if isinstance(result.get("prediction"), dict) else {}

    transcript_text = _coerce_text(result.get("transcript") or result.get("customerTranscript") or result.get("customerBehavioralTranscript") or "")
    inferred_fields = _extract_from_transcript(transcript_text)
    raw_features = result.get("rawFeatures") if isinstance(result.get("rawFeatures"), list) else []
    for feature in raw_features:
        if isinstance(feature, dict):
            label = str(feature.get("label") or "").upper()
            value = _coerce_text(feature.get("value") or feature.get("name") or "")
            if label == "DECISION_MAKER" and value:
                inferred_fields["decision_maker"] = value

    customer_name = _coerce_text(_first_grouped_value(grouped, "customer_name", "name", "person")) or inferred_fields.get("customer_name") or DEFAULT_CUSTOMER_NAME
    company_name = _coerce_text(_first_grouped_value(grouped, "company_name", "company", "organization")) or inferred_fields.get("company_name")
    email = _coerce_text(_first_grouped_value(grouped, "email", "contact_email")) or inferred_fields.get("email")
    phone = _coerce_text(_first_grouped_value(grouped, "customer_number", "phone", "mobile", "contact_phone", "contact_number", "phone_number", "mobile_number", "contact")) or inferred_fields.get("phone")
    product_interest = _product_interest(result)
    intent = _title(conversion_score.get("label", prediction.get("label")), "Cold")
    sentiment = _title(summary.get("dominant"), "Neutral")
    lead_score = _lead_score(result)
    conversation_summary_text = _coerce_text(_conversation_summary(result))
    next_best_action = _coerce_text(conversation_summary.get("nextAction") or "")
    if not next_best_action and isinstance(conversation_summary.get("Action Items"), list):
        action_items = [str(item).strip() for item in conversation_summary.get("Action Items", []) if str(item).strip()]
        next_best_action = ", ".join(action_items)
    budget = _coerce_text(_first_grouped_value(grouped, "budget")) or inferred_fields.get("budget")
    timeline = _coerce_text(_first_grouped_value(grouped, "timeline")) or inferred_fields.get("timeline")
    pain_points = _coerce_text(
        ", ".join(
            [str(item).strip() for item in conversation_summary.get("Risks", []) if str(item).strip()]
        )
    )
    competitor = _coerce_text(_first_grouped_value(grouped, "competitor"))
    customer_intent = _coerce_text(conversation_summary.get("customerNeed") or conversation_summary.get("outcome") or "")
    decision_maker = _coerce_text(_first_grouped_value(grouped, "decision_maker", "decisionMaker")) or inferred_fields.get("decision_maker")

    field_confidence = {
        "customer_name": _extract_confidence(grouped.get("customer_name_confidence")) if isinstance(grouped, dict) else None,
        "company_name": _extract_confidence(grouped.get("company_name_confidence")) if isinstance(grouped, dict) else None,
        "email": _extract_confidence(grouped.get("email_confidence")) if isinstance(grouped, dict) else None,
        "phone": _extract_confidence(grouped.get("customer_number_confidence") or grouped.get("phone_confidence")) if isinstance(grouped, dict) else None,
        "budget": _extract_confidence(grouped.get("budget_confidence")) if isinstance(grouped, dict) else None,
        "timeline": _extract_confidence(grouped.get("timeline_confidence")) if isinstance(grouped, dict) else None,
        "product_interest": None,
        "decision_maker": _extract_confidence(grouped.get("decision_maker_confidence")) if isinstance(grouped, dict) else None,
    }

    return {
        "customer_name": customer_name,
        "company_name": company_name,
        "email": email,
        "phone": phone,
        "product_interest": product_interest,
        "conversation_summary": conversation_summary_text,
        "lead_score": lead_score,
        "sentiment": sentiment,
        "intent": intent,
        "customer_intent": customer_intent or intent,
        "budget": budget,
        "timeline": timeline,
        "pain_points": pain_points,
        "competitor": competitor,
        "next_best_action": next_best_action,
        "decision_maker": decision_maker,
        "field_confidence": field_confidence,
    }


def _build_notes(ai_values: dict[str, Any]) -> str:
    lines = [
        "Customer Information",
        "---------------------",
        f"Customer: {ai_values['customer_name']}",
        f"Name: {ai_values['customer_name']}",
    ]
    if ai_values.get("company_name"):
        lines.append(f"Company: {ai_values['company_name']}")
    if ai_values.get("email"):
        lines.append(f"Email: {ai_values['email']}")
    if ai_values.get("phone"):
        lines.append(f"Phone: {ai_values['phone']}")

    lines.extend(["", "Sales Insights", "--------------"])
    if ai_values.get("product_interest"):
        lines.append(f"Product Interest: {ai_values['product_interest']}")
    if ai_values.get("intent"):
        lines.append(f"Intent: {ai_values['intent']}")
    elif ai_values.get("customer_intent"):
        lines.append(f"Intent: {ai_values['customer_intent']}")
    if ai_values.get("lead_score") is not None:
        lines.append(f"Lead Score: {ai_values['lead_score']}")
    if ai_values.get("sentiment"):
        lines.append(f"Sentiment: {ai_values['sentiment']}")
    if ai_values.get("decision_maker"):
        lines.append(f"Decision Maker: {ai_values['decision_maker']}")

    lines.extend(["", "Business Insights", "-----------------"])
    if ai_values.get("budget"):
        lines.append(f"Budget: {ai_values['budget']}")
    if ai_values.get("timeline"):
        lines.append(f"Timeline: {ai_values['timeline']}")
    if ai_values.get("pain_points"):
        lines.append(f"Pain Points: {ai_values['pain_points']}")
    if ai_values.get("competitor"):
        lines.append(f"Competitor: {ai_values['competitor']}")

    lines.extend(["", "Recommendation", "--------------"])
    if ai_values.get("next_best_action"):
        lines.append(f"Recommendation: {ai_values['next_best_action']}")
    else:
        lines.append("Recommendation: Follow up with the customer and address the main requirement or objection.")

    confidence = ai_values.get("field_confidence") or {}
    if confidence:
        lines.extend(["", "Confidence", "----------"])
        for field_name, value in confidence.items():
            if value is not None:
                lines.append(f"{field_name}: {_confidence_label(value)} ({round(float(value) * 100)}%)")

    if ai_values.get("conversation_summary"):
        lines.extend(["", "Conversation Summary", "-------------------", ai_values['conversation_summary']])
    return "\n".join(lines)


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

    ai_values = _collect_ai_fields(result)
    customer_name = ai_values["customer_name"]
    email = ai_values["email"]
    phone = ai_values["phone"]
    product_interest = ai_values["product_interest"]
    given_name, family_name = _split_name(customer_name)

    note = _build_notes(ai_values)

    payload = {
        "name": f"Lead Prospect - {customer_name}",
        "source": lead_source,
        "account": {
            "formattedName": customer_name,
            "firstLineName": customer_name,
            "address": {
                "region": {},
                "email": email or "",
                "mobileFormattedNumber": phone or "",
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

    if email:
        payload["account"]["address"]["email"] = email
    if phone:
        payload["account"]["address"]["mobileFormattedNumber"] = phone
    if product_interest:
        payload["notes"][0]["content"] = note

    return payload
