# Nexus AI | Migration & Implementation Summary (v1 to v2)

This document provides a comprehensive overview of the architectural changes, refactors, and feature implementations made to migrate the system from its legacy version to the current production-grade **Nexus AI v2** enterprise platform.

---

## 1. Monolithic API to Distributed Worker Architecture
* **Legacy State**: The FastAPI server processed audio transcriptions, diarizations, and LLM extractions synchronously or locally in the request thread.
* **Implemented Change**: 
  - Centralized a background job queue using a SQLite-backed processing manager (`processing_jobs` table).
  - Split the processing lifecycle into decoupled background workers:
    - **Audio Transcription Worker**: Handles Whisper speech-to-text and Pyannote audio diarization.
    - **ML Analysis Worker**: Handles LLaMA feature extraction, XGBoost lead scoring, PII sanitization, and alert generation.
  - The API server now immediately logs a pending job ID and delegates work, allowing clients to poll `/api/jobs/{job_id}`.
* **RATIONALE**: Heavy machine learning models (Whisper/Pyannote) block the FastAPI single-threaded event loop and consume massive CPU/GPU resources, causing request timeouts. Offloading them to decoupled background workers keeps the API server extremely lightweight, responsive, and horizontally scalable.

---

## 2. Advanced Diarization & Role Classifier Pipeline
* **Legacy State**: Basic pyannote/acoustic segmentation with naive heuristics.
* **Implemented Change**:
  - **Silero VAD (Voice Activity Detection)**: Extracts precise voice segments.
  - **ECAPA-TDNN Embeddings**: Extracts speaker acoustic identities.
  - **Real-time Speaker Tracker**: Tracks speaker profiles dynamically across call turns.
  - **Hybrid Role Classifier**: Lexical rule-matching combined with MiniLM semantic embedding similarity to classify speaker turns into **Agent**, **Customer**, or **Guest**.
  - **Flow Order Validator**: Ensures conversation order rules (e.g., Agent starts, Customer follows).
  - **LLM Semantic Diarization Fallback**: Falls back to LLM semantic diarization on the transcript text if the acoustic pipeline fails or if a text-only analysis request is run, bypassing sentence-alternating bugs.
  - **Frontend Preserved Timeline**: Frontend passes down previous audio diarizations to avoid re-diarization collapse during text analysis.
* **RATIONALE**: Tabular XGBoost lead scoring and LLaMA feature extractions are highly dependent on *who* said what (e.g., a customer expressing budget limitations vs. an agent asking about budget). Incorrect turn assignment corrupts the ML feature vector, resulting in inaccurate conversion predictions.

---

## 3. Database Operational Storage & Repositories
* **Legacy State**: Flat CSV logging and memory-based structures.
* **Implemented Change**:
  - Implemented SQLite central storage (`database/nexus_ai.db`) with tables for `conversations`, `follow_up_alerts`, and `processing_jobs`.
  - Introduced the Repository Pattern:
    - [sqlite.py](file:///d:/Project%20-AI%20audio/src/nexus_ai/repositories/sqlite.py) containing `JobRepository`, `ConversationRepository`, and `FollowUpAlertRepository` to isolate SQL queries from business logic.
* **RATIONALE**: CSV logging is prone to lock contention under concurrent request volume, and in-memory variables wipe on container restart. Standardizing on SQLite with a repository layer provides transaction safety, persistent alerts, and a modular interface that can be easily swapped for PostgreSQL in the future.

---

## 4. Split-Concern Containerization (Docker)
* **Legacy State**: No container support, requiring manual local python setup.
* **Implemented Change**:
  - Created specialized Dockerfiles for individual services:
    - [Dockerfile.api](file:///d:/Project%20-AI%20audio/Dockerfile.api) for the lightweight endpoint server.
    - [Dockerfile.audio](file:///d:/Project%20-AI%20audio/Dockerfile.audio) packaging audio packages and `ffmpeg`.
    - [Dockerfile.ml](file:///d:/Project%20-AI%20audio/Dockerfile.ml) for XGBoost and LLaMA process handling.
    - [Dockerfile.frontend](file:///d:/Project%20-AI%20audio/Dockerfile.frontend) optimized for Next.js.
  - Created [docker-compose.v2.yml](file:///d:/Project%20-AI%20audio/docker-compose.v2.yml) to run production multi-service containers.
  - Created [.dockerignore](file:///d:/Project%20-AI%20audio/.dockerignore) to ignore local artifacts, directories, and virtual environments.
* **RATIONALE**: Bundling all audio transcription, ML libraries, and the frontend into one image results in massive, unmaintainable container images (5GB+). Splitting concerns cuts build times, isolates dependency vulnerabilities, and reduces production image size footprint.

---

## 5. Next.js Enterprise Dashboard (Premium Aesthetics)
* **Legacy State**: Simple HTML/JS interface.
* **Implemented Change**:
  - Engineered a premium dark-themed Next.js client with:
    - Glassmorphic HSL styling, glowing cursor effects, and subtle custom micro-animations.
    - Waveform visualizations showing active audio processing.
    - Live meeting capture (capturing both browser tab meeting audio and user microphone).
    - Graphical conversation stage tracking (Opening -> Discovery -> Pricing -> Negotiation -> Closing).
    - Integrated sentiment timelines and follow-up alert toggles.
* **RATIONALE**: High-fidelity dashboard visualizations provide stakeholders with actionable CRM telemetry (conversion probability, customer needs, follow-ups) at a glance, delivering a premium UX.
