from __future__ import annotations

import os
from dataclasses import dataclass


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True, slots=True)
class SAPConfig:
    enabled: bool
    endpoint: str
    username: str
    password: str
    timeout: float
    lead_source: str = "Z3"
    market_segment: str = "001"

    @classmethod
    def load_from_env(cls) -> "SAPConfig":
        return cls(
            enabled=_bool_env("SAP_C4C_ENABLED", False),
            endpoint=os.getenv("SAP_C4C_ENDPOINT", "").strip(),
            username=os.getenv("SAP_C4C_USERNAME", "").strip(),
            password=os.getenv("SAP_C4C_PASSWORD", "").strip(),
            timeout=_float_env("SAP_C4C_TIMEOUT_SEC", 10.0),
            lead_source=os.getenv("SAP_C4C_LEAD_SOURCE", "Z3").strip() or "Z3",
            market_segment=os.getenv("SAP_C4C_MARKET_SEGMENT", "001").strip() or "001",
        )

    def missing_required_fields(self) -> list[str]:
        missing: list[str] = []
        if not self.endpoint:
            missing.append("SAP_C4C_ENDPOINT")
        if not self.username:
            missing.append("SAP_C4C_USERNAME")
        if not self.password:
            missing.append("SAP_C4C_PASSWORD")
        return missing
