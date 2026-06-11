# 🔧 Audio Upload Debug Guide

## What I Fixed ✅

### 1. **UI Page Ordering** ✅ FIXED
- **Issue**: All sections were showing in continuous scroll
- **Solution**: Implemented proper page-based navigation with 3 phases:
  - **Phase 1 (Upload)**: Audio upload interface
  - **Phase 2 (Processing)**: Pipeline visualization while processing
  - **Phase 3 (Results)**: Dashboard with NLP results
- **Location**: `frontend/src/App.tsx` - Added `uiPhase` state to control which sections render

### 2. **Audio Upload Error Handling** 🆕 IMPROVED
- Added detailed console logging to show exactly what's being sent to the backend
- Improved error messages to include HTTP status codes
- Added FormData debugging to track file handling
- Better error display in the UI

### 3. **Created Debugging Tools** 🆕

Created two comprehensive test tools to help diagnose the issue:

#### **Option A: HTML Debug Tool** (Easiest)
**File**: `frontend/audio-upload-debug.html`
- Open in browser: `file:///.../frontend/audio-upload-debug.html`
- Or run via dev server: `http://localhost:5173/audio-upload-debug.html`
- Has 3 tests:
  1. Health check (is backend running?)
  2. Text analysis (API communication working?)
  3. Audio upload (file upload working?)
- Shows real-time streaming responses from backend

#### **Option B: Python Debug Script** (More thorough)
**File**: `test_audio_upload.py`
```bash
# Make sure backend is running first in another terminal:
python -m uvicorn src.api.server:app --reload --port 8000

# Then run tests in a new terminal:
python test_audio_upload.py
```

---

## How to Debug Step-by-Step 🔍

### Step 1: Verify Backend is Running
```bash
# Open a terminal and run:
python -m uvicorn src.api.server:app --reload --port 8000
```
- Should see: `Uvicorn running on http://127.0.0.1:8000`
- CORS middleware initialized

### Step 2: Check Browser Console
1. Open your app in browser: `http://localhost:5173`
2. Open DevTools: **F12** or **Ctrl+Shift+I**
3. Go to **Console** tab
4. Try uploading an audio file
5. Look for logs like:
   ```
   📤 Sending to backend: {hasFile: true, fileName: "test.wav", fileSize: 12345, ...}
   📎 Added file to FormData: {name: "test.wav", size: "12.34 KB", type: "audio/wav"}
   ```

### Step 3: Use Debug Tool
- Open `frontend/audio-upload-debug.html` in browser
- Click "Check Backend" to verify connectivity
- Click "Analyze Text" to test basic API communication
- Click "Upload & Analyze Audio" to test file upload

### Step 4: Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "Request failed: HTTP 0" | Backend not running | Start backend: `uvicorn src.api.server:app --reload --port 8000` |
| "Request failed: HTTP 404" | Wrong endpoint or port | Check API_BASE_URL in frontend config |
| "Request failed: HTTP 400" | Missing required field | File or text must be provided |
| "Request failed: HTTP 422" | Empty audio transcript | Audio file too short or no speech detected |
| "Request failed: HTTP 500" | Backend error | Check backend console for error details |
| CORS error in browser | CORS not configured | Backend has CORS enabled for `http://localhost:5173` |

---

## What the Error Message Tells You 📊

The error message now includes:
- **HTTP Status Code** (200, 400, 404, 500, etc.)
- **Status Text** (OK, Bad Request, etc.)
- **Backend Error Detail** (if available)

Examples:
```
✅ Success: Status 200
❌ API Error: Missing 'text' or 'file' field
❌ Request failed: HTTP 422 Unprocessable Entity
❌ Request failed: HTTP 500 Internal Server Error
```

---

## Testing Workflow 🚀

### Quick Test (5 minutes)
1. Start backend: `uvicorn src.api.server:app --reload --port 8000`
2. Open debug tool: `frontend/audio-upload-debug.html`
3. Click "Check Backend" ✓
4. Click "Analyze Text" ✓
5. Select an audio file and click "Upload & Analyze Audio" ✓

### Full Test (10 minutes)
1. Run Python test script: `python test_audio_upload.py`
2. Open React app frontend
3. Try uploading a real audio file
4. Check browser console for detailed logs

---

## Expected Behavior After Fix

### Upload Phase (Page 1)
- Select/drag audio file
- See file details (name, size)
- Status shows "Audio queued for transcription"

### Processing Phase (Page 2) - After clicking "Run Intelligence Pipeline"
- See animated pipeline visualization
- Pipeline stages: Uploading → Speech-to-text → NLP extraction → Sentiment analysis
- See processing logs in real-time

### Results Phase (Page 3) - After processing completes
- Transcript section with highlighted sentiment words
- NLP tokens breakdown
- Entity recognition results
- Overall sentiment summary
- Download report as JSON or PDF

---

## Environment Checklist ✓

- [ ] Backend running on `http://localhost:8000`
- [ ] Vite dev server running on `http://localhost:5173`
- [ ] CORS middleware enabled in backend
- [ ] Audio file format supported (.wav, .mp3, .m4a, .flac, .ogg, .aac, .webm)
- [ ] Whisper model downloaded (~3GB for 'small' model)
- [ ] spaCy model downloaded (`en_core_web_sm`)

---

## File Changes Summary

**Modified Files:**
1. `frontend/src/App.tsx` - Added UI phase management
2. `frontend/src/lib/api.ts` - Improved error handling and logging

**New Files:**
1. `test_audio_upload.py` - Python test suite
2. `frontend/audio-upload-debug.html` - Browser-based debug tool

---

## Next Steps if Issue Persists

1. **Share console logs** from browser DevTools (F12)
2. **Check backend logs** - Any error messages printed?
3. **Verify file permissions** - Can Python write to temp upload dir?
4. **Test with demo sample** - Click "Use cinematic demo sample" (doesn't need audio upload)
5. **Check network tab** - See actual HTTP request/response details

---

## Support Info

**Backend Health Check:**
```bash
curl http://localhost:8000/health
```
Expected response:
```json
{
  "status": "ok",
  "spacy_model": "core_web_sm",
  "whisper_model": "small",
  "whisper_device": "cpu"
}
```

**Current Endpoints:**
- `GET /health` - System status
- `POST /api/analyze` - JSON response
- `POST /api/analyze-stream` - Server-Sent Events (streaming)

Both endpoints accept:
- `file` (multipart form-data) - Audio or text file
- `text` (form data) - Raw text input
- `language` (form data) - Optional language code

