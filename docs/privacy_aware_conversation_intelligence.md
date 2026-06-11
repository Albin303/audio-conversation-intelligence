# Privacy-Aware Real-Time Sales Conversation Intelligence

## Updated Architecture

Audio -> Whisper -> Speaker Diarization -> Structured Transcript -> Local PII Extraction -> PII Removal -> Customer Behavioral Transcript -> LLaMA Intelligence Extraction -> Hybrid Prediction Engine -> Dashboard

## Diarization Pipeline

- `src/aspect_sentiment/audio.py` now preserves Whisper segment timestamps.
- `src/aspect_sentiment/diarization.py` aligns Whisper segments to pyannote speaker turns when `HUGGINGFACE_TOKEN`, `HF_TOKEN`, or `PYANNOTE_AUTH_TOKEN` is configured.
- If pyannote is unavailable, the system falls back to lightweight speaker heuristics so live capture still works.
- Explicit typed transcripts such as `Customer: ... Agent: ...` are parsed directly.

Structured transcript response:

```json
[
  {"speaker": "Customer", "text": "I need a laptop under 70k"},
  {"speaker": "Agent", "text": "We have EMI offers"}
]
```

## Transcript Alignment Logic

For audio uploads, each Whisper segment is matched to the pyannote speaker interval with the largest time overlap. Consecutive turns from the same final role are merged to reduce UI noise and duplicate processing.

## Local NLP Extraction Pipeline

`src/aspect_sentiment/privacy.py` extracts sensitive details before LLaMA:

- phone numbers with regex
- emails with regex
- company and job-title phrases with conservative regex
- names, locations, and organizations with spaCy NER when an English model is installed

The cleaned customer transcript replaces each detected value with placeholders such as `[PHONE_REDACTED]`.

## Customer-Only LLaMA Flow

The backend sends only `customerBehavioralTranscript` to LLaMA. Agent text is retained for transcript display, but it is not used as the primary semantic input for conversion scoring.

## Prediction Improvements

`src/aspect_sentiment/probability_fusion.py` accepts `agent_transcript` and records a customer weighting metric. Behavioral, intent, emotion, and engagement scores are derived from cleaned customer speech.

## Dashboard Updates

The existing frontend architecture is preserved. The dashboard now renders:

- colored Customer and Agent transcript blocks in live capture results
- extracted local structured details
- redaction count and privacy-safe status
- customer behavioral summary metrics

## Dependency Installation

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

For pyannote diarization, set one of:

```bash
HUGGINGFACE_TOKEN=...
HF_TOKEN=...
PYANNOTE_AUTH_TOKEN=...
```

The default pyannote pipeline is `pyannote/speaker-diarization-3.1`; override with `PYANNOTE_PIPELINE` if needed.

## Performance Notes

- pyannote is loaded lazily and cached.
- spaCy is loaded lazily and cached.
- The LLaMA prompt receives only cleaned customer speech, reducing token usage.
- Speaker turns are merged before response serialization to avoid duplicate dashboard rendering.
- Regex extraction runs before spaCy and does not require network calls.

## Privacy Boundary

Raw transcript and structured PII remain local to the backend response. External LLaMA calls receive only the cleaned customer behavioral transcript, not phone numbers, emails, addresses, customer names, company names, or job titles detected locally.
