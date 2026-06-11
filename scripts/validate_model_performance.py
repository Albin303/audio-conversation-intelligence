from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = PROJECT_ROOT / "models" / "sales_conversion_metrics.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate saved conversion-model performance metrics.")
    parser.add_argument("--min-accuracy", type=float, default=0.73)
    parser.add_argument("--min-recall", type=float, default=0.80)
    parser.add_argument("--min-f1", type=float, default=0.74)
    args = parser.parse_args()

    if not METRICS_PATH.exists():
        print(json.dumps({"status": "failed", "failures": [f"{METRICS_PATH.name} not found"]}, indent=2))
        return 2

    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    failures = []
    if float(metrics.get("accuracy", 0)) < args.min_accuracy:
        failures.append(f"accuracy {metrics.get('accuracy')} is below {args.min_accuracy}")
    if float(metrics.get("recall", 0)) < args.min_recall:
        failures.append(f"recall {metrics.get('recall')} is below {args.min_recall}")
    if float(metrics.get("f1", 0)) < args.min_f1:
        failures.append(f"f1 {metrics.get('f1')} is below {args.min_f1}")

    print(
        json.dumps(
            {
                "status": "passed" if not failures else "failed",
                "model": metrics.get("model_name"),
                "accuracy": metrics.get("accuracy"),
                "precision": metrics.get("precision"),
                "recall": metrics.get("recall"),
                "f1": metrics.get("f1"),
                "roc_auc": metrics.get("roc_auc"),
                "threshold": metrics.get("classification_threshold"),
                "failures": failures,
            },
            indent=2,
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
