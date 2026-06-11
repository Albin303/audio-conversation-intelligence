# Lead-Scoring Pipeline Overview

This doc explains what each piece does, where it is used, and how data flows end to end.

## High-level flow
1) **Transcription → text files/CSV**  
   - `src/extraction/transcribe.py` (or manual input) produces raw transcript text.
2) **Feature extraction (no preprocessing yet)**  
   - `src/extraction/feature_extraction.py`: turns one transcript string into a feature dict.  
   - `src/extraction/feature_batch.py`: batches over many transcripts and writes `data/processed/features.csv` (or similar). **Only extracts; does not scale/encode.**
3) **Preprocessing for modeling**  
   - `src/utils/preprocessing.py`: takes the feature CSV into memory, drops raw text/file cols, fills missing values, one-hot encodes categoricals, scales numerics, and returns `(X, y, scaler)`. It does **not** rewrite the CSV—used at training/eval time.
4) **Training**  
   - `src/models/train_model.py`: CLI wrapper around preprocessing + model fit (RandomForest/XGBoost) + save payload (`model`, `scaler`, `feature_columns`, `target_col`).  
   - Notebook `src/models/lead_scoring_pipeline.ipynb` follows the same steps interactively and also uses `prepare_features` from `predict.py` for a sample prediction.
5) **Evaluation**  
   - `src/models/evaluate.py`: loads saved model payload, preprocesses a validation CSV with the same `feature_columns`/`scaler`, prints confusion matrix and classification report.
6) **Inference**  
   - `src/models/predict.py`: `prepare_features` aligns a single feature dict to training columns, applies the saved scaler, and `predict` outputs class/probability.
7) **Validation checks (optional but recommended)**  
   - `src/utils/validation.py`: sanity-check a CSV for missing values, invalid numerics, budget outliers, and invalid categorical values before training/eval.

## File-by-file purpose
- `src/extraction/feature_extraction.py`: rule-based NLP features per transcript.
- `src/extraction/feature_batch.py`: loops over many transcripts, writes feature CSV.
- `src/utils/preprocessing.py`: in-memory encoding/scaling for modeling; used by training/eval.
- `src/utils/validation.py`: data-quality report.
- `src/models/train_model.py`: headless training CLI; saves model payload.
- `src/models/evaluate.py`: headless evaluation CLI on a CSV.
- `src/models/predict.py`: single-sample inference utilities and CLI.
- `src/models/lead_scoring_pipeline.ipynb`: interactive notebook combining validation, preprocessing, training, saving, and a sample prediction.

## Typical commands (from repo root)
```bash
# 1) Batch extract features from transcripts directory (writes CSV)
python -m src.extraction.feature_batch

# 2) Optional: validate the CSV before modeling
python -m src.utils.validation --input data/processed/features.csv

# 3) Train a model
python -m src.models.train_model --data data/processed/features.csv --model data/processed/lead_scoring_model.joblib

# 4) Evaluate the saved model on a holdout CSV
python -m src.models.evaluate --model data/processed/lead_scoring_model.joblib --data data/processed/features.csv

# 5) Predict for one sample (JSON inline)
python -m src.models.predict --model data/processed/lead_scoring_model.joblib --json '{"product":"laptop","budget":60000,"brand_count":1,"use_case_count":2,"preference":"dell","intent_strength":"medium","decision_stage":"consideration","sentiment":"positive","hesitation":0,"follow_up_needed":1,"offer_given":0,"emi_option":1,"product_suggested":1,"word_count":120,"sentence_count":8}'
```

## Key clarifications
- The feature CSV is written directly by `feature_batch.py`; preprocessing happens later, in memory, when you train/eval/predict.
- Consistency comes from reusing the saved `feature_columns` and `scaler` (stored in the joblib payload) inside `evaluate.py` and `predict.py`.
- If you add new feature columns, you must regenerate the CSV and retrain so `feature_columns` matches.
