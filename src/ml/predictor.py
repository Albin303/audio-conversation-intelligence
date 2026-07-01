from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from src.aspect_sentiment.probability_fusion import fuse_probabilities


REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = REPO_ROOT / "models"
CONVERSION_MODEL_PATH = MODEL_DIR / "sales_conversion_model.pkl"
MODEL_FEATURES_PATH = MODEL_DIR / "sales_conversion_features.pkl"
MODEL_METRICS_PATH = MODEL_DIR / "sales_conversion_metrics.json"

_MODEL_LOCK = threading.Lock()
_CONVERSION_MODEL: Any | None = None
_MODEL_FEATURES: list[str] | None = None


def load_model_metrics() -> dict[str, Any]:
    if not MODEL_METRICS_PATH.exists():
        return {}
    try:
        payload = json.loads(MODEL_METRICS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def get_model_features() -> list[str]:
    global _MODEL_FEATURES
    if _MODEL_FEATURES is None:
        with _MODEL_LOCK:
            if _MODEL_FEATURES is None:
                import joblib

                _MODEL_FEATURES = list(joblib.load(MODEL_FEATURES_PATH))
    return _MODEL_FEATURES


def get_conversion_model() -> Any:
    global _CONVERSION_MODEL
    if _CONVERSION_MODEL is None:
        with _MODEL_LOCK:
            if _CONVERSION_MODEL is None:
                import joblib

                _CONVERSION_MODEL = joblib.load(CONVERSION_MODEL_PATH)
    return _CONVERSION_MODEL


def build_conversion_row(extraction: dict[str, Any]) -> tuple[Any, Any]:
    import pandas as pd

    row: dict[str, Any] = {
        "budget": 0,
        "sentiment_score": extraction.get("sentiment_score", 0),
        "confidence_score": extraction.get("confidence_score", 0),
        "hesitation_score": extraction.get("hesitation_score", 0),
        "delay_flag": extraction.get("delay_flag", 0),
        "feature_count": extraction.get("feature_count", 0),
        "brand_count": extraction.get("brand_count", 0),
        "interaction_length": extraction.get("interaction_length", 0),
    }

    from src.aspect_sentiment.mapping_engine import process_extractions

    normalized = process_extractions(extraction.get("raw_features", []))
    for key, value in normalized.to_xgboost_dict().items():
        row[key] = value

    explanation_row = pd.DataFrame([row])
    model_row = explanation_row.copy()
    model_features = get_model_features()
    for column in model_features:
        if column not in model_row.columns:
            model_row[column] = 0

    return model_row[model_features], explanation_row


def predict_with_trained_model(extraction: dict[str, Any], text: str, agent_text: str = "") -> dict[str, Any]:
    model_row, _explanation_row = build_conversion_row(extraction)
    xgboost_prob = float(get_conversion_model().predict_proba(model_row)[0][1])

    raw_features = extraction.get("raw_features", [])
    sentiment_score = float(extraction.get("sentiment_score", 0))

    return fuse_probabilities(
        xgboost_prob=xgboost_prob,
        transcript=text,
        raw_features=raw_features,
        sentiment_score=sentiment_score,
        agent_transcript=agent_text,
    )
