from __future__ import annotations

import json
import os
import re
import statistics
import sys
import time
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.aspect_sentiment import AspectSentimentEngine


WORD_RX = re.compile(r"[a-z0-9]+")
DEFAULT_DATASET = ROOT / "data" / "raw" / "features.csv"
DEFAULT_TEXT_DIR = ROOT / "data" / "raw"
GOLD_FIELDS = ("product", "brands", "use_case", "product_suggested", "budget")


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


@st.cache_resource(show_spinner="Loading NLP and sentiment models...")
def get_engine() -> AspectSentimentEngine:
    load_local_env()
    return AspectSentimentEngine()


def norm(value: object) -> str:
    return " ".join(WORD_RX.findall(str(value or "").lower()))


def split_terms(value: object) -> list[str]:
    return [term for term in (norm(part) for part in str(value or "").split(",")) if term]


def expected_terms_from_row(row: pd.Series, gold_columns: list[str]) -> set[str]:
    terms: set[str] = set()
    for field in gold_columns:
        if field not in row:
            continue
        if field == "budget":
            budget = norm(row.get(field, ""))
            if budget and budget not in {"none", "na", "n a"}:
                terms.add(budget)
        else:
            terms.update(split_terms(row.get(field, "")))
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


def read_uploaded_dataset(uploaded_file: Any) -> pd.DataFrame:
    suffix = Path(uploaded_file.name).suffix.lower()
    raw = uploaded_file.getvalue()
    if suffix == ".json":
        payload = json.loads(raw.decode("utf-8-sig"))
        if isinstance(payload, dict):
            for key in ("data", "rows", "conversations", "items"):
                if isinstance(payload.get(key), list):
                    payload = payload[key]
                    break
        return pd.DataFrame(payload)
    return pd.read_csv(StringIO(raw.decode("utf-8-sig")))


def load_builtin_dataset() -> pd.DataFrame:
    if DEFAULT_DATASET.exists():
        return pd.read_csv(DEFAULT_DATASET, encoding="utf-8-sig")

    rows = []
    for text_path in sorted(DEFAULT_TEXT_DIR.glob("conv_*.txt")):
        rows.append({"file": text_path.name, "text": text_path.read_text(encoding="utf-8", errors="replace")})
    return pd.DataFrame(rows)


def run_analysis(text: str, source_name: str, engine: AspectSentimentEngine) -> dict[str, Any]:
    started = time.perf_counter()
    response = engine.analyze_text(
        text,
        source_name=source_name,
        source_type="text",
        language="en",
        transcription_confidence=None,
        whisper_model=None,
        pipeline=[],
        processing_ms=0,
    )
    latency = time.perf_counter() - started
    return {"response": response, "latency": latency}


def evaluate_dataset(
    frame: pd.DataFrame,
    text_column: str,
    id_column: str | None,
    gold_columns: list[str],
    max_rows: int,
    engine: AspectSentimentEngine,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    total_expected = 0
    total_matched = 0
    total_predicted = 0
    rows_with_any_match = 0
    errors = 0

    for index, row in frame.head(max_rows).iterrows():
        source_name = str(row[id_column]) if id_column else f"row-{index + 1}"
        text = str(row.get(text_column, "") or "").strip()
        gold = expected_terms_from_row(row, gold_columns)
        result_row: dict[str, Any] = {
            "source": source_name,
            "expected": ", ".join(sorted(gold)),
            "expected_count": len(gold),
        }

        if not text:
            errors += 1
            result_row.update({"status": "error", "error": "Empty text", "latency_s": 0.0})
            rows.append(result_row)
            continue

        try:
            result = run_analysis(text, source_name, engine)
            response = result["response"]
            latency = result["latency"]
            latencies.append(latency)
            predicted = {norm(product.name) for product in response.products if norm(product.name)}
            matched = {term for term in gold if term_matches(term, predicted)}

            rows_with_any_match += int(bool(matched))
            total_expected += len(gold)
            total_matched += len(matched)
            total_predicted += len(predicted)

            result_row.update(
                {
                    "status": "ok",
                    "latency_s": round(latency, 2),
                    "predicted": ", ".join(sorted(predicted)),
                    "predicted_count": len(predicted),
                    "matched": ", ".join(sorted(matched)),
                    "matched_count": len(matched),
                    "missed": ", ".join(sorted(gold - matched)),
                    "precision": round(len(matched) / len(predicted), 3) if predicted else 0.0,
                    "recall": round(len(matched) / len(gold), 3) if gold else 0.0,
                    "sentiment": response.summary.dominant,
                    "entities": response.summary.totalProducts,
                    "conversion": response.conversionScore.label if response.conversionScore else "n/a",
                }
            )
        except Exception as exc:
            errors += 1
            result_row.update({"status": "error", "error": str(exc), "latency_s": 0.0})

        rows.append(result_row)

    metrics = {
        "rows": len(rows),
        "errors": errors,
        "recall": total_matched / total_expected if total_expected else 0.0,
        "precision": total_matched / total_predicted if total_predicted else 0.0,
        "matched": total_matched,
        "expected": total_expected,
        "predicted": total_predicted,
        "rows_with_any_match": rows_with_any_match,
        "latency_avg": statistics.mean(latencies) if latencies else 0.0,
        "latency_median": statistics.median(latencies) if latencies else 0.0,
        "latency_min": min(latencies) if latencies else 0.0,
        "latency_max": max(latencies) if latencies else 0.0,
    }
    return pd.DataFrame(rows), metrics


def render_single_conversation(engine: AspectSentimentEngine) -> None:
    st.subheader("Single Conversation")
    default_text = ""
    sample_files = sorted(DEFAULT_TEXT_DIR.glob("conv_*.txt"))
    sample_names = ["Paste text"] + [path.name for path in sample_files]
    selected_sample = st.selectbox("Source", sample_names)
    if selected_sample != "Paste text":
        selected_path = DEFAULT_TEXT_DIR / selected_sample
        default_text = selected_path.read_text(encoding="utf-8", errors="replace")

    text = st.text_area("Conversation text", value=default_text, height=260)
    if st.button("Run Llama 3 analysis", type="primary", use_container_width=True):
        if not text.strip():
            st.warning("Add a conversation transcript first.")
            return

        with st.spinner("Calling Llama 3 and scoring the conversation..."):
            result = run_analysis(text, selected_sample, engine)
        response = result["response"]

        cols = st.columns(4)
        cols[0].metric("Latency", f"{result['latency']:.2f}s")
        cols[1].metric("Entities", response.summary.totalProducts)
        cols[2].metric("Dominant sentiment", response.summary.dominant.title())
        cols[3].metric("Conversion", response.conversionScore.label.title() if response.conversionScore else "N/A")

        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "name": product.name,
                        "type": product.entityType,
                        "sentiment": product.sentiment,
                        "score": product.score,
                        "confidence": product.confidence,
                        "mentions": product.mentions,
                        "context": product.context,
                    }
                    for product in response.products
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

        with st.expander("Raw analysis JSON"):
            st.json(response.model_dump())


def render_batch_evaluation(engine: AspectSentimentEngine) -> None:
    st.subheader("Dataset Performance")
    uploaded = st.file_uploader("Upload conversation dataset", type=["csv", "json"])
    frame = read_uploaded_dataset(uploaded) if uploaded else load_builtin_dataset()

    if frame.empty:
        st.info("No dataset rows found.")
        return

    columns = list(frame.columns)
    text_guess = "text" if "text" in columns else columns[0]
    text_column = st.selectbox("Text column", columns, index=columns.index(text_guess))
    id_options = ["None"] + columns
    id_guess = "file" if "file" in columns else "None"
    id_column_choice = st.selectbox("Conversation ID column", id_options, index=id_options.index(id_guess))
    id_column = None if id_column_choice == "None" else id_column_choice
    default_gold = [field for field in GOLD_FIELDS if field in columns]
    gold_columns = st.multiselect("Expected answer columns", columns, default=default_gold)
    max_rows = st.slider("Rows to evaluate", min_value=1, max_value=int(len(frame)), value=min(10, int(len(frame))))

    st.caption(f"Loaded {len(frame)} rows. Model: {engine.llama_model}")
    with st.expander("Preview dataset"):
        st.dataframe(frame.head(20), use_container_width=True)

    if st.button("Run batch evaluation", type="primary", use_container_width=True):
        with st.spinner("Evaluating conversations with Llama 3..."):
            result_frame, metrics = evaluate_dataset(frame, text_column, id_column, gold_columns, max_rows, engine)

        cols = st.columns(5)
        cols[0].metric(
            "Recall",
            f"{metrics['recall']:.3f}",
            help="Matched expected terms divided by all expected terms.",
        )
        cols[1].metric(
            "Precision",
            f"{metrics['precision']:.3f}",
            help="Matched expected terms divided by predicted terms.",
        )
        cols[2].metric("Avg latency", f"{metrics['latency_avg']:.2f}s")
        cols[3].metric("Rows matched", f"{metrics['rows_with_any_match']}/{metrics['rows']}")
        cols[4].metric("Errors", str(metrics["errors"]))

        latency_cols = st.columns(3)
        latency_cols[0].metric("Median latency", f"{metrics['latency_median']:.2f}s")
        latency_cols[1].metric("Min latency", f"{metrics['latency_min']:.2f}s")
        latency_cols[2].metric("Max latency", f"{metrics['latency_max']:.2f}s")

        st.dataframe(result_frame, use_container_width=True, hide_index=True)
        st.download_button(
            "Download results CSV",
            result_frame.to_csv(index=False).encode("utf-8"),
            "llama3_performance_results.csv",
            "text/csv",
            use_container_width=True,
        )


def main() -> None:
    st.set_page_config(page_title="Llama 3 Performance Lab", page_icon=":bar_chart:", layout="wide")
    st.title("Llama 3 Performance Lab")
    st.write("Test CRM feature extraction on new sales conversation text and compare predictions with expected dataset labels.")

    try:
        engine = get_engine()
    except Exception as exc:
        st.error(f"Could not initialize the analysis engine: {exc}")
        return

    if not engine.llama_api_key:
        st.warning("LLAMA_API_KEY or GROQ_API_KEY is not set. Add it to `.env.local` before running Llama 3 extraction.")

    with st.sidebar:
        st.header("Runtime")
        st.write(f"Provider: llama")
        st.write(f"Model: {engine.llama_model}")
        st.write(f"API URL: {engine.llama_api_url}")
        st.write(f"spaCy: {engine.spacy_model_name}")

    single_tab, batch_tab = st.tabs(["Single test", "Batch evaluation"])
    with single_tab:
        render_single_conversation(engine)
    with batch_tab:
        render_batch_evaluation(engine)


if __name__ == "__main__":
    main()
