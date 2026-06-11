# Troubleshooting Audio Upload & Processing Failures

If you run into issues uploading or analyzing audio files, follow this step-by-step diagnostic guide to locate and fix the problem.

---

## Diagnostic Flowchart

1. **Frontend Upload Request**: The user uploads a WAV file at `http://localhost:5173`.
2. **FastAPI Route**: The frontend calls `POST /api/upload` and receives a `job_id`.
3. **Task Queue**: The job is pushed into the FastAPI async queue handled by `src/api/worker.py`.
4. **Whisper Transcription**: The worker calls Whisper, which decodes the file using `ffmpeg`.
5. **Diarization**: The worker calls Pyannote to separate speakers.
6. **LLM extraction & Scoring**: Results are parsed, features are derived, and lead predictions are fuzed.

---

## Common Error Cases & Fixes

### 1. File Upload Fails Immediately (CORS / Connection Error)
* **Symptom**: Clicking "Upload" in the browser results in a generic network failure or `Access-Control-Allow-Origin` CORS block in the browser console (F12).
* **Fix**:
  - Check if the API backend is running at `http://localhost:8000`. Run:
    ```bash
    curl http://localhost:8000/api/health
    ```
  - Verify that the frontend origin (`http://localhost:3000` or `http://localhost:3001` or `http://localhost:5173`) is declared in the `ALLOWED_ORIGINS` variable in `.env`.

### 2. Job Status Remains "pending" Indefinitely
* **Symptom**: The upload succeeds and returns a Job ID, but the dashboard remains stuck on "transcribing" or "processing" forever.
* **Fix**:
  - The background task worker failed to start or crashed. Ensure that `FastAPI` startup event creates the worker.
  - Check the terminal where you launched the backend API. If there is a Python traceback, look at the error log.
  - Restart the backend server.

### 3. Job Status Changes to "failed" with Error: `ffmpeg not found`
* **Symptom**: The polling endpoint returns `{"status": "failed", "error": "... ffmpeg is not found or not in PATH"}`.
* **Fix**:
  - OpenAI Whisper relies on `ffmpeg` to extract and decode audio sample formats.
  - Install `ffmpeg` via winget:
    ```powershell
    winget install Gyan.FFmpeg
    ```
  - Alternatively, download `ffmpeg` and place the folder `ffmpeg-xxx` in the project root, or add the `bin` folder path containing `ffmpeg.exe` to your Windows System Environment Variable `PATH`.

### 4. Diarization Fails (HuggingFace authentication issue)
* **Symptom**: The log shows `Hugging Face token is invalid` or crashes during Pyannote initialization.
* **Fix**:
  - If you configure `DIARIZATION_BACKEND=pyannote` in `.env`, you must provide a valid `HUGGINGFACE_TOKEN`.
  - Obtain a token from [huggingface.co](https://huggingface.co/settings/tokens).
  - You must also manually accept user agreements for the `pyannote/speaker-diarization-3.1` (or community) model on the Hugging Face hub web interface.
  - **Easiest Workaround**: Set `DIARIZATION_BACKEND=free-local` in `.env` to bypass Hugging Face requirements and use a fallback regex-based turn diarizer.

### 5. Extraction Fails (Groq API Rate Limits / Authentication)
* **Symptom**: The transcription completes but features are empty or fall back to local rule-based extractions.
* **Fix**:
  - Ensure your `LLAMA_API_KEY` is correctly set in `.env.local`.
  - Test connectivity to Groq using:
    ```bash
    curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer YOUR_API_KEY"
    ```
