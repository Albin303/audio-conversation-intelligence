# 🏗️ SYSTEM ARCHITECTURE VISUAL

## High-Level System Diagram

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                        💼 USER INTERFACE (React)                         ┃
┃                                                                           ┃
┃  ┌─────────────────────────────────────────────────────────────────┐   ┃
┃  │ 📝 Upload Section          │ 🎯 Processing Pipeline            │   ┃
┃  │ - Text Input               │ ✓ Uploading                      │   ┃
┃  │ - Audio Drag&Drop          │ ✓ Speech-to-Text                 │   ┃
┃  │ - File Browser             │ ✓ NLP Extraction                 │   ┃
┃  │ - Language Select          │ ✓ Sentiment Analysis             │   ┃
┃  │                            │                                   │   ┃
┃  ├──────────────────────────────────────────────────────────────────┤   ┃
┃  │ 📊 Dashboard               │ 💾 Results Export                │   ┃
┃  │ - Sentiment Gauge          │ - Download JSON                   │   ┃
┃  │ - Product Table            │ - Export PDF                      │   ┃
┃  │ - Highlights               │ - View Raw Response               │   ┃
┃  │ - Insights                 │                                   │   ┃
┃  └─────────────────────────────────────────────────────────────────┘   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                    ↕️ HTTP/SSE
                    ┌──────────────────────────────────────┐
                    │    Port 5173 ↔ Port 8000            │
                    └──────────────────────────────────────┘
                                    ↕️
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                      🔧 BACKEND API (FastAPI)                            ┃
┃                                                                           ┃
┃  ┌──────────────────────────────────────────────────────────────────┐   ┃
┃  │ 📡 REST Endpoints                                               │   ┃
┃  │ ├─ GET  /health              → System status check             │   ┃
┃  │ ├─ POST /api/analyze         → JSON response (standard)        │   ┃
┃  │ └─ POST /api/analyze-stream  → SSE real-time events           │   ┃
┃  └──────────────────────────────────────────────────────────────────┘   ┃
┃                                                                           ┃
┃  ┌──────────────────────────────────────────────────────────────────┐   ┃
┃  │ 🎙️ Audio Processor                                             │   ┃
┃  │                                                                  │   ┃
┃  │ WhisperTranscriber                                              │   ┃
┃  │ ├─ Audio Input → .wav, .mp3, .m4a, .flac, etc                │   ┃
┃  │ ├─ Whisper Model (small, base, medium, large)                 │   ┃
┃  │ ├─ Language Detection                                          │   ┃
┃  │ ├─ Confidence Scoring                                          │   ┃
┃  │ └─ Text Output → Transcript                                   │   ┃
┃  └──────────────────────────────────────────────────────────────────┘   ┃
┃                                    ↓                                      ┃
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                      🧠 NLP PROCESSING PIPELINE                          ┃
┃                                                                           ┃
┃  ┌─────────────────────────────────────────────────────────────────┐   ┃
┃  │ STEP 1: Text Normalization                                     │   ┃
┃  │ Input:  "  Hello   WORLD   with   spaces  "                   │   ┃
┃  │ Output: "Hello WORLD with spaces"                              │   ┃
┃  └─────────────────────────────────────────────────────────────────┘   ┃
┃                                ↓                                         ┃
┃  ┌─────────────────────────────────────────────────────────────────┐   ┃
┃  │ STEP 2: spaCy Tokenization & POS Tagging                       │   ┃
┃  │ - Sentence boundary detection                                  │   ┃
┃  │ - Token segmentation                                           │   ┃
┃  │ - Part-of-speech tagging (NOUN, VERB, ADJ, etc)               │   ┃
┃  │ - Lemmatization & normalization                               │   ┃
┃  │ - Dependency parsing                                          │   ┃
┃  └─────────────────────────────────────────────────────────────────┘   ┃
┃                                ↓                                         ┃
┃  ┌─────────────────────────────────────────────────────────────────┐   ┃
┃  │ STEP 3: Noun/Product Extraction                               │   ┃
┃  │ Input:  [tokens with POS tags]                                │   ┃
┃  │ Filter: pos_ in ["NOUN", "PROPN", compound phrases]           │   ┃
┃  │ Output: [camera, battery, performance, ...]                   │   ┃
┃  │                                                                │   ┃
┃  │ Filtering Rules Applied:                                       │   ┃
┃  │ ✗ Remove generic terms (app, thing, stuff, product, etc)      │   ┃
┃  │ ✗ Remove stopwords (the, a, and, etc)                         │   ┃
┃  │ ✗ Keep only 1-4 word phrases                                   │   ┃
┃  │ ✓ Normalize duplicates (camera quality ← quality of camera)   │   ┃
┃  │ ✓ Lemmatize terms (batteries ← battery)                       │   ┃
┃  └─────────────────────────────────────────────────────────────────┘   ┃
┃                                ↓                                         ┃
┃  ┌─────────────────────────────────────────────────────────────────┐   ┃
┃  │ STEP 4: Context Window Selection                              │   ┃
┃  │ For each product mention:                                      │   ┃
┃  │ - Find containing sentence                                    │   ┃
┃  │ - Detect clause boundaries (but, however, though, and, or)    │   ┃
┃  │ - Isolate context window (~50-100 chars around mention)       │   ┃
┃  │                                                                │   ┃
┃  │ Example:                                                       │   ┃
┃  │ Text:    "The camera is stunning. Battery drains fast."       │   ┃
┃  │           ←────────────────────── camera ────────────────→    │   ┃
┃  │           ←──────────────── battery ─────────────────→        │   ┃
┃  └─────────────────────────────────────────────────────────────────┘   ┃
┃                                ↓                                         ┃
┃  ┌─────────────────────────────────────────────────────────────────┐   ┃
┃  │ STEP 5: VADER Sentiment Analysis                              │   ┃
┃  │ For each context:                                              │   ┃
┃  │ - Tokenize context string                                     │   ┃
┃  │ - Look up sentiment lexicon (custom + VADER default)          │   ┃
┃  │ - Calculate polarity (neg, neutral, pos, compound)            │   ┃
┃  │ - Normalize score to [-1, +1] range                           │   ┃
┃  │                                                                │   ┃
┃  │ Scoring:                                                       │   ┃
┃  │   compound > 0.05   → POSITIVE (😊)                           │   ┃
┃  │   -0.05 ≤ compound ≤ 0.05 → NEUTRAL (😐)                      │   ┃
┃  │   compound < -0.05  → NEGATIVE (😟)                           │   ┃
┃  │                                                                │   ┃
┃  │ Custom Lexicon Additions:                                      │   ┃
┃  │   overheat: -2.7, crisp: 2.1, sluggish: -2.4, ...            │   ┃
┃  └─────────────────────────────────────────────────────────────────┘   ┃
┃                                ↓                                         ┃
┃  ┌─────────────────────────────────────────────────────────────────┐   ┃
┃  │ STEP 6: Results Aggregation                                   │   ┃
┃  │ - Group by product name (deduplication)                       │   ┃
┃  │ - Average scores for multi-mention products                   │   ┃
┃  │ - Calculate confidence scores                                 │   ┃
┃  │ - Generate summary statistics                                 │   ┃
┃  │ - Count sentiment distribution (pos%, neg%, neutral%)         │   ┃
┃  │                                                                │   ┃
┃  │ Output: ProductSentiment[]                                    │   ┃
┃  │ ├─ name: "camera"                                            │   ┃
┃  │ ├─ sentiment: "positive"                                     │   ┃
┃  │ ├─ score: 0.872                                              │   ┃
┃  │ ├─ confidence: 0.82                                          │   ┃
┃  │ ├─ mentions: 1                                               │   ┃
┃  │ ├─ context: "The camera is stunning..."                      │   ┃
┃  │ └─ highlights: [{...}]  ← Character positions in text        │   ┃
┃  └─────────────────────────────────────────────────────────────────┘   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                    ↓
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                         📊 ANALYSIS RESPONSE (JSON)                      ┃
┃                                                                           ┃
┃  {                                                                       ┃
┃    "transcript": "The camera is stunning...",                           ┃
┃    "products": [                                                        ┃
┃      {                                                                  ┃
┃        "name": "camera",                                               ┃
┃        "sentiment": "positive",                                        ┃
┃        "score": 0.872,        ← Range: -1 (very negative) to +1       ┃
┃        "confidence": 0.82,    ← Range: 0 to 1                         ┃
┃        "mentions": 1,                                                  ┃
┃        "context": "The camera is stunning.",                           ┃
┃        "highlights": [{"start": 4, "end": 10}]                       ┃
┃      },                                                                 ┃
┃      { ... more products ... }                                          ┃
┃    ],                                                                   ┃
┃    "summary": {                                                         ┃
┃      "positive": 67,         ← Percentage                              ┃
┃      "neutral": 0,                                                     ┃
┃      "negative": 33,                                                   ┃
┃      "averageScore": 0.405,  ← Mean sentiment                          ┃
┃      "totalProducts": 3,                                               ┃
┃      "dominant": "positive"                                            ┃
┃    },                                                                   ┃
┃    "metadata": {                                                        ┃
┃      "sourceType": "text|audio",                                       ┃
┃      "sourceName": "filename",                                         ┃
┃      "language": "en",                                                 ┃
┃      "processingMs": 245,    ← Total pipeline time                     ┃
┃      "wordCount": 58,                                                  ┃
┃      "sentenceCount": 6,                                               ┃
┃      "createdAt": "2026-04-13T...",                                   ┃
┃      "transcriptionConfidence": 0.95  ← Whisper confidence             ┃
┃    },                                                                   ┃
┃    "pipeline": [                                                        ┃
┃      { "id": "uploading", "status": "completed", ... },               ┃
┃      { "id": "speech_to_text", "status": "completed", ... },          ┃
┃      { "id": "nlp_extraction", "status": "completed", ... },          ┃
┃      { "id": "sentiment_analysis", "status": "completed", ... }       ┃
┃    ]                                                                    ┃
┃  }                                                                       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                    ↓
                    Returned to Frontend for Display
                                    ↓
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                      👀 VISUALIZATION (React UI)                         ┃
┃                                                                           ┃
┃  ┌─────────────────────────────────────────────────────────────────┐   ┃
┃  │ 📈 Sentiment Gauge            │  📊 Breakdown                  │   ┃
┃  │                               │                               │   ┃
┃  │     😊 67%                    │  ??? 67% [========>    ]       │   ┃
┃  │     Positive                  │  😐 0%  [                ]       │   ┃
┃  │                               │  😟 33% [======>         ]      │   ┃
┃  ├─────────────────────────────────────────────────────────────────┤   ┃
┃  │ 📦 Products Table                                              │   ┃
┃  │                                                                │   ┃
┃  │ Product      │ Sentiment  │ Score │ Confidence │ Context       │   ┃
┃  │──────────────┼───────────┼───────┼───────────┼──────────────│   ┃
┃  │ camera       │ 😊 Pos    │ 0.87  │ 82%       │ "stunning"   │   ┃
┃  │ battery      │ 😟 Neg    │ -0.56 │ 68%       │ "drain fast" │   ┃
┃  │ performance  │ 😊 Pos    │ 0.90  │ 83%       │ "excellent"  │   ┃
┃  └─────────────────────────────────────────────────────────────────┘   ┃
┃                                                                           ┃
┃  Highlighted Transcript:                                                 ┃
┃  "The [camera] is amazing but [battery] drains quickly. [Performance]    ┃
┃   is excellent."                                                         ┃
┃                   ↑            ↑              ↑                         ┃
┃          (product mentions are highlighted)                             ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

---

## Data Flow Summary

```
USER INPUT
    ↓
[Validation] ← Check file format, text length
    ↓
[Audio → Text] ← If audio: Whisper transcription
    ↓
[Normalization] ← Clean whitespace, case handling
    ↓
[Tokenization] ← spaCy pipeline: segment, POS tag
    ↓
[Noun Extraction] ← Filter NOUN/PROPN, remove generics
    ↓
[Context Isolation] ← Find sentences & clause boundaries
    ↓
[VADER Scoring] ← Sentiment lexicon lookup & calculation
    ↓
[Aggregation] ← Dedup products, average scores
    ↓
[Response Building] ← Pack into JSON schema
    ↓
[Streaming] ← Send via SSE or return JSON
    ↓
FRONTEND DISPLAY
    ↓
USER SEES RESULTS
```

---

## Technology Stack Map

```
Frontend Layer
├── React 18 (UI framework)
├── TypeScript (type safety)
├── Tailwind CSS (styling)
├── Framer Motion (animations)
├── Chart.js (visualizations)
└── Vite (build tool & dev server)

↕ HTTP/SSE

Backend Layer
├── FastAPI (API framework)
├── Uvicorn (ASGI server)
├── Pydantic (data validation)
├── asyncio (async processing)
└── CORS middleware

↓

Core Processing
├── spaCy (NLP - tokenization, POS, lemmatization)
├── VADER (sentiment scoring)
├── Whisper (audio transcription)
├── FFmpeg (audio format handling)
├── joblib (model persistence)
└── pandas (data manipulation)
```

---

**Diagram Generated:** April 13, 2026
**Status:** PRODUCTION READY
