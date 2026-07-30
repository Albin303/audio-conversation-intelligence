#!/usr/bin/env python3
"""
Pipeline Diagnostic -- Nexus AI -> SAP C4C Contact Field Tracer
=============================================================
Run from the project root:

    python scripts/diagnose_sap_pipeline.py

Tests the exact transcript:
    "Hi, my name is John Anderson. My phone number is +91 98765 43210.
     My email is john.anderson@test.com."

Prints a PASS/FAIL table for every pipeline stage without calling SAP.
Set SAP_C4C_ENABLED=true and real credentials to also test the live API.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS_MARK = "PASS"
FAIL_MARK = "FAIL"

EXPECTED = {
    "first_name": "John",
    "last_name":  "Anderson",
    "full_name":  "John Anderson",
    "phone":      "+91 98765 43210",
    "email":      "john.anderson@test.com",
}

TRANSCRIPT = (
    "Hi, my name is John Anderson. "
    "My phone number is +91 98765 43210. "
    "My email is john.anderson@test.com."
)

failures: list[str] = []


def header(text: str) -> None:
    print(f"\n{'=' * 62}")
    print(f"  {text}")
    print(f"{'=' * 62}")


def check(label: str, actual: str, expected: str) -> bool:
    ok = actual.strip() == expected.strip()
    mark = PASS_MARK if ok else FAIL_MARK
    print(f"  [{mark}]  {label}")
    print(f"          expected : {expected}")
    if not ok:
        print(f"          got      : {actual!r}  <-- MISMATCH")
    else:
        print(f"          got      : {actual}")
    return ok


def record(label: str, actual: str, expected: str) -> None:
    if not check(label, actual, expected):
        failures.append(label)


def mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    user, domain = email.split("@", 1)
    return f"{'*' * len(user)}@{domain}"


def mask_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    return f"{'*' * max(0, len(digits) - 4)}{digits[-4:]}" if len(digits) > 4 else "****"


# ---------------------------------------------------------------------------
# Stage 1: Transcript
# ---------------------------------------------------------------------------
header("STAGE 1 -- Transcript")
print(f"\n  {TRANSCRIPT}\n")
all_present = (
    "John Anderson" in TRANSCRIPT
    and "+91 98765 43210" in TRANSCRIPT
    and "john.anderson@test.com" in TRANSCRIPT
)
print(f"  [{PASS_MARK if all_present else FAIL_MARK}]  All expected values present in transcript")
if not all_present:
    failures.append("Transcript -- missing expected values")


# ---------------------------------------------------------------------------
# Stage 2: PII Extraction
# ---------------------------------------------------------------------------
header("STAGE 2 -- PII Extraction (privacy.py + analysis_service.pii_payload)")

from src.aspect_sentiment.privacy import extract_and_redact_pii
from src.services.analysis_service import AnalysisService

pii_result = extract_and_redact_pii(TRANSCRIPT)

print(f"\n  Raw entities detected:")
for e in pii_result.entities:
    print(f"    type={e.type!r:22s}  value={e.value!r}")

# Use the same pii_payload helper the real pipeline uses
privacy_info = AnalysisService.pii_payload(pii_result)
grouped: dict = privacy_info.get("grouped", {})

print(f"\n  Grouped dict (post-normalisation):")
print(textwrap.indent(json.dumps(grouped, indent=4, default=str), "    "))

# Resolve values the same way the mapper does
name_candidates = grouped.get("customer_name", [])
extracted_name = name_candidates[0] if name_candidates else ""

phone_keys = ["customer_number", "phone", "mobile", "contact_phone", "contact_number", "phone_number", "mobile_number"]
extracted_phone = ""
for k in phone_keys:
    vals = grouped.get(k, [])
    if isinstance(vals, list) and vals:
        extracted_phone = str(vals[0]).strip()
        break
    elif isinstance(vals, str) and vals.strip():
        extracted_phone = vals.strip()
        break

email_candidates = grouped.get("email", [])
extracted_email = (
    email_candidates[0] if isinstance(email_candidates, list) and email_candidates
    else (email_candidates if isinstance(email_candidates, str) else "")
)

print()
record("customer_name extracted", extracted_name,  EXPECTED["full_name"])
record("phone extracted",         extracted_phone, EXPECTED["phone"])
record("email extracted",         extracted_email, EXPECTED["email"])


# ---------------------------------------------------------------------------
# Stage 3: Mapper _collect_ai_fields
# ---------------------------------------------------------------------------
header("STAGE 3 -- Mapper Input (_collect_ai_fields)")

pipeline_result: dict = {
    "privacy": {"grouped": grouped},
    "transcript": TRANSCRIPT,
}

from src.integrations.sap_c4c.mapper import _collect_ai_fields

ai_fields = _collect_ai_fields(pipeline_result)
print(f"\n  _collect_ai_fields output:")
print(textwrap.indent(json.dumps(ai_fields, indent=4, default=str), "    "))
print()

record("ai_fields.customer_name", ai_fields.get("customer_name", ""), EXPECTED["full_name"])
record("ai_fields.phone",         ai_fields.get("phone", ""),         EXPECTED["phone"])
record("ai_fields.email",         ai_fields.get("email", ""),         EXPECTED["email"])


# ---------------------------------------------------------------------------
# Stage 4: SAP Payload
# ---------------------------------------------------------------------------
header("STAGE 4 -- SAP Payload (map_pipeline_result_to_sap)")

from src.integrations.sap_c4c.mapper import map_pipeline_result_to_sap

sap_payload = map_pipeline_result_to_sap(pipeline_result)
print(f"\n  Full payload:")
print(textwrap.indent(json.dumps(sap_payload, indent=4, default=str), "    "))
print()

pc   = sap_payload.get("primaryContact", {})
addr = sap_payload.get("account", {}).get("address", {})

record("primaryContact.givenName",              pc.get("givenName", ""),               EXPECTED["first_name"])
record("primaryContact.familyName",             pc.get("familyName", ""),              EXPECTED["last_name"])
record("account.address.email",                 addr.get("email", ""),                 EXPECTED["email"])
record("account.address.mobileFormattedNumber", addr.get("mobileFormattedNumber", ""), EXPECTED["phone"])

print(f"\n  Masked payload log (what sap_lead_service emits before dispatch):")
masked = {
    "phone_masked": mask_phone(addr.get("mobileFormattedNumber", "")),
    "email_masked": mask_email(addr.get("email", "")),
    "givenName":    pc.get("givenName", ""),
    "familyName":   pc.get("familyName", ""),
}
print(textwrap.indent(json.dumps(masked, indent=4), "    "))


# ---------------------------------------------------------------------------
# Stage 5: Schema validation
# ---------------------------------------------------------------------------
header("STAGE 5 -- client._validate_payload (schema check)")

from src.integrations.sap_c4c.client import SAPClient, SAPPayloadError

try:
    SAPClient._validate_payload(sap_payload)
    print(f"\n  [{PASS_MARK}]  Payload passes SAP schema validation")
except SAPPayloadError as exc:
    print(f"\n  [{FAIL_MARK}]  Schema validation FAILED: {exc}")
    failures.append(f"Schema validation: {exc}")


# ---------------------------------------------------------------------------
# Stage 6: Live SAP API (optional)
# ---------------------------------------------------------------------------
header("STAGE 6 -- Live SAP API (SAP_C4C_ENABLED check)")

SAP_ENABLED = os.getenv("SAP_C4C_ENABLED", "false").lower() == "true"

if not SAP_ENABLED:
    print(f"\n  [SKIP]  SAP_C4C_ENABLED is not true.")
    print(f"          Set SAP_C4C_ENABLED=true + credentials and re-run to test the live API.")
else:
    from src.services.sap_lead_service import SAPLeadService

    async def _run_live() -> None:
        svc = SAPLeadService()
        result = await svc.create_lead_from_analysis(pipeline_result)
        print(f"\n  SAP response:")
        print(textwrap.indent(json.dumps(result, indent=4, default=str), "    "))
        if result.get("leadCreated"):
            print(f"\n  [{PASS_MARK}]  Lead created -- ID: {result.get('leadId')}")
            print(f"\n  Open SAP C4C UI and verify the Lead contains:")
            print(f"    First Name : {EXPECTED['first_name']}")
            print(f"    Last Name  : {EXPECTED['last_name']}")
            print(f"    Phone      : {EXPECTED['phone']}")
            print(f"    Email      : {EXPECTED['email']}")
        else:
            status = result.get("httpStatus")
            error  = result.get("error", "unknown")
            print(f"\n  [{FAIL_MARK}]  Lead creation failed (HTTP {status}): {error}")
            if status == 400:
                print("  --> HTTP 400: SAP rejected field names/values.")
                print("      Check the OData $metadata for exact field names.")
            elif status == 401:
                print("  --> HTTP 401: Bad credentials. Check SAP_C4C_USERNAME/PASSWORD.")
            failures.append(f"Live SAP API: HTTP {status} -- {error}")

    asyncio.run(_run_live())


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
header("SUMMARY")

if failures:
    print(f"\n  {len(failures)} check(s) FAILED:")
    for f in failures:
        print(f"    [FAIL]  {f}")
    print(f"\n  Fix the failing stage, then re-run this script.\n")
    sys.exit(1)
else:
    print(f"\n  All pipeline stages PASS.")
    print(f"  Phone, email, and name all flow correctly to the SAP payload.\n")
    if not SAP_ENABLED:
        print(f"  Next step:")
        print(f"    Set SAP_C4C_ENABLED=true and re-run to verify the live API (Stage 6).")
        print(f"    If Stage 6 passes but the SAP UI is missing fields, the issue is on")
        print(f"    the SAP side (OData field config) -- not in this application.\n")
    sys.exit(0)
