# Feature Extraction Walkthrough (copy-paste ready for a quick demo)

Use this page when showing the team lead how the transcript-to-features flow works. Everything runs locally with the existing code.

## 1) What happens, in order
- `spaCy parse` — `doc = nlp(text)` in `src/extraction/feature_extraction.py:270`.
- `Product/brand/use-case matchers` — phrase matchers built from synonym tables (`:27-84`, used at `:276-282`).
- `Product guess fallback` — noun span after verbs like “want/buy” (`guess_product` at `:229-267`).
- `Budget` — regex first, then spaCy MONEY/CARDINAL entities (`:284-291`, regex defined `:98-123`).
- `Intent & hesitation` — keyword lists (`INTENT_HIGH/LOW`, `HESITATION` at `:130-153`) drive intent strength and decision stage (`:293-314`).
- `Offer / EMI flags` — keyword cues (`:315-316`).
- `Suggestions` — only sentences with suggest cues; collects brands/products (`detect_product_suggestions` at `:209-226`, used `:318-321`).
- `Sentiment` — VADER compound score (`:323-332`).
- `Final feature dict` — assembled and returned (`:333-362`).

## 2) Quick CLI demo (no code changes needed)
```bash
# From repo root
python -m src.extraction.feature_extraction --text "Hi, I want a laptop under 60k for programming and gaming. Maybe later, but any offer today? I suggest a Dell Inspiron."
```
Add `--log-level INFO` to show the logged steps:
```bash
python -m src.extraction.feature_extraction --text "sample text here" --log-level INFO
```

## 3) “Paste-and-see” minimal UI (optional, fast)
Run this one-liner to open a temporary Streamlit app with a textarea and live feature output (uses your existing functions):
```bash
python - <<'PY'
import streamlit as st
from src.extraction.feature_extraction import extract_features

st.title("Transcript Feature Extractor (demo)")
text = st.text_area("Paste transcript text", height=200, value="I want a laptop under 60k for programming and gaming. Maybe later, but any offer today? I suggest a Dell Inspiron.")
if st.button("Extract features"):
    st.json(extract_features(text))
PY
```
Then open the printed local URL (default http://localhost:8501) and demo the flow: paste text → click Extract → show JSON features.

## 4) Talking script for the meeting
1. Paste the transcript into the box.  
2. Explain spaCy parses once (tokens, POS, entities).  
3. Show product/brand/use-case matches; mention verb-based fallback guess.  
4. Point out budget regex + MONEY entity backup.  
5. Highlight intent/hesitation keywords → decision stage.  
6. Show offer/EMI flags and suggestion detection.  
7. Show sentiment (VADER) and basic counts.  
8. The JSON output is what downstream steps consume.

## 5) Where to look in code
- Main pipeline: `src/extraction/feature_extraction.py` (see line references above).  
- Batch runner that reads CSVs or directories: `src/extraction/feature_batch.py` (uses the same `extract_features`).  
- Synonym vocab lists: same file, top section (`PRODUCT_SYNONYMS`, `BRAND_SYNONYMS`, `USE_CASE_SYNONYMS`).  
- Regex & keyword lists: same file (`BUDGET_RX`, `INTENT_*`, `HESITATION`, `OFFER_CUES`, `EMI_CUES`, `SUGGEST_CUES`).  
