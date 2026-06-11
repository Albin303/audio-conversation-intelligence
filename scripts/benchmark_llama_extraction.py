from __future__ import annotations

import csv
import os
import re
import statistics
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.aspect_sentiment import AspectSentimentEngine

GOLD_CSV = ROOT / "data" / "raw" / "features.csv"
WORD_RX = re.compile(r"[a-z0-9]+")


def load_local_env() -> None:
    for env_path in (ROOT / ".env.local", ROOT / ".env"):
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def norm(value: object) -> str:
    return " ".join(WORD_RX.findall(str(value or "").lower()))


def split_terms(value: object) -> list[str]:
    return [term for term in (norm(part) for part in str(value or "").split(",")) if term]


def expected_terms(row: dict[str, str]) -> set[str]:
    terms: set[str] = set()
    for field in ("product", "brands", "use_case", "product_suggested"):
        terms.update(split_terms(row.get(field, "")))
    budget = norm(row.get("budget", ""))
    if budget and budget != "none":
        terms.add(budget)
    return {term for term in terms if term not in {"none", "na", "n a"}}


def term_matches(expected: str, predicted_terms: set[str]) -> bool:
    expected_tokens = set(expected.split())
    for predicted in predicted_terms:
        if expected == predicted or expected in predicted or predicted in expected:
            return True
        predicted_tokens = set(predicted.split())
        if expected_tokens and expected_tokens <= predicted_tokens:
            return True
    return False


def main() -> None:
    load_local_env()

    engine = AspectSentimentEngine()
    latencies: list[float] = []
    total_expected = 0
    total_matched = 0
    total_predicted = 0
    rows_with_any_match = 0
    errors: list[str] = []

    with GOLD_CSV.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    print(f"Provider: llama:{engine.llama_model}")
    print(f"Rows: {len(rows)}")
    print()

    for index, row in enumerate(rows, start=1):
        text = row.get("text", "")
        gold = expected_terms(row)
        started = time.perf_counter()
        try:
            result = engine.extract_mentions_with_provider(text)
            elapsed = time.perf_counter() - started
            latencies.append(elapsed)
            predicted = {norm(mention.name) for mention in result.mentions if norm(mention.name)}
            matched = {term for term in gold if term_matches(term, predicted)}
            rows_with_any_match += int(bool(matched))
            total_expected += len(gold)
            total_matched += len(matched)
            total_predicted += len(predicted)
            print(
                f"{index:02d} {row.get('file','')}: "
                f"{elapsed:.2f}s expected={len(gold)} predicted={len(predicted)} matched={len(matched)}"
            )
            if gold - matched:
                print(f"   missed: {', '.join(sorted(gold - matched))}")
            if predicted:
                print(f"   predicted: {', '.join(sorted(predicted))}")
        except Exception as exc:
            elapsed = time.perf_counter() - started
            errors.append(f"{row.get('file', index)}: {exc}")
            print(f"{index:02d} {row.get('file','')}: ERROR after {elapsed:.2f}s - {exc}")

    print()
    print("Summary")
    recall = total_matched / total_expected if total_expected else 0.0
    approx_precision = total_matched / total_predicted if total_predicted else 0.0
    print(f"Expected term recall: {recall:.3f} ({total_matched}/{total_expected})")
    print(f"Approx term precision: {approx_precision:.3f} ({total_matched}/{total_predicted})")
    print(f"Rows with any expected match: {rows_with_any_match}/{len(rows)}")
    if latencies:
        print(f"Latency avg: {statistics.mean(latencies):.2f}s")
        print(f"Latency median: {statistics.median(latencies):.2f}s")
        print(f"Latency min/max: {min(latencies):.2f}s / {max(latencies):.2f}s")
    if errors:
        print("Errors:")
        for error in errors:
            print(f"- {error}")


if __name__ == "__main__":
    main()
