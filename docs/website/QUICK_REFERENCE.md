# 🎯 QUICK REFERENCE GUIDE

## ⚡ One-Minute Setup

### Fastest Way to Start
```powershell
cd "d:\Project -AI audio"
START.bat
```
This will:
- ✅ Check environment
- ✅ Install dependencies  
- ✅ Start Backend API (port 8000)
- ✅ Start Frontend (port 5173)
- ✅ Open test client

Then open browser: **http://localhost:5173**

---

## 🔧 Manual Startup (If START.bat doesn't work)

### Terminal 1 - Backend
```powershell
cd "d:\Project -AI audio"
.venv\Scripts\python.exe -m uvicorn src.api.server:app --reload --port 8000
```

### Terminal 2 - Frontend
```powershell
cd "d:\Project -AI audio\frontend"
npm run dev
```

### Then Open Browser
```
http://localhost:5173
```

---

## 📍 Access Points

| Service | URL | Status |
|---------|-----|--------|
| Frontend Dashboard | http://localhost:5173 | Main UI |
| Backend API | http://localhost:8000 | JSON responses |
| API Health | http://localhost:8000/health | System status |
| API Docs (Swagger) | http://localhost:8000/docs | Interactive |
| API Docs (ReDoc) | http://localhost:8000/redoc | Alternative |
| Test Client | http://localhost/test_client.html | Offline testing |

---

## 🚀 Testing Without UI

### Test via Command Line
```powershell
# Check API is running
curl http://localhost:8000/health

# Test with text
curl -X POST "http://localhost:8000/api/analyze" `
  -F "text=The camera is amazing but battery drains fast"

# Test with audio file
curl -X POST "http://localhost:8000/api/analyze" `
  -F "file=@audio.wav" `
  -F "language=en"
```

### Test via Python
```python
import requests

response = requests.post(
    'http://localhost:8000/api/analyze',
    data={'text': 'Great product but expensive'}
)
print(response.json())
```

### Test via Browser
Open: `test_client.html` (in project root)
- No backend needed to load
- Test API when backend is running
- See results in real-time

---

## 📊 Input Examples

### Text Inputs
```
"The camera quality is stunning. Battery drains too quickly."
→ camera: positive, battery: negative

"Excellent customer service and fast shipping"
→ customer service: positive, shipping: positive

"Good value for money but feels cheap"
→ value: positive, build quality: negative
```

### Audio Inputs
- .wav files (recommended)
- .mp3, .m4a, .flac, .ogg, .aac, .webm
- 1+ seconds recommended
- Clear audio works best

---

## 💡 Example Workflow

1. **Upload**
   - Paste text or drag audio file
   - Select language (default: English)

2. **Processing**
   - Watch real-time pipeline:
     - Uploading ✓
     - Transcription (if audio)
     - NLP extraction
     - Sentiment analysis

3. **Results**
   - View sentiment gauge
   - See products extracted
   - Read confidence scores
   - Check context quotes

4. **Export**
   - Download as JSON
   - Export as PDF report

---

## 🐛 Troubleshooting

### Backend Won't Start
```
Error: ModuleNotFoundError
Fix: pip install -r requirements.txt

Error: spaCy model not found
Fix: python -m spacy download en_core_web_sm
```

### Frontend Won't Load
```
Error: Port 5173 in use
Fix: npm run dev (will use different port)

Error: Dependencies missing
Fix: cd frontend && npm install
```

### API Connection Issues
```
Ensure backend is running:
.venv\Scripts\python.exe -m uvicorn src.api.server:app --reload

Check it's accessible:
curl http://localhost:8000/health
```

### Audio Not Transcribed
```
Try a different format (.wav recommended)
Check audio is not corrupted
Ensure audio is 1+ seconds long
Clear audio works better
```

---

## 📚 Find More Help

| Topic | Location |
|-------|----------|
| Complete Guide | SYSTEM_GUIDE.md |
| API Reference | API_DOCUMENTATION.md |
| Build Info | BUILD_SUMMARY.md |
| Run Tests | python test_system.py |
| Architecture | API_DOCUMENTATION.md |

---

## ⌛ Performance Tips

### Faster Results
- Use text instead of audio
- Shorter inputs (< 1 min)
- English language
- Modern hardware with GPU

### Better Accuracy
- Clear audio (if using)
- Complete sentences
- Natural language (not fragmented)
- Longer context for complex subjects

---

## 🔑 Key System Info

### Backend Components
- **Framework**: FastAPI
- **NLP Library**: spaCy
- **Sentiment**: VADER
- **Audio**: Whisper (OpenAI)
- **Language**: Python 3.11+

### Frontend Components  
- **Framework**: React 18
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Animations**: Framer Motion
- **Charts**: Chart.js

### Supported Languages
- ✅ English
- ✅ Spanish
- ✅ French
- ✅ German
- ✅ Chinese
- ✅ And 20+ more...

---

## 🎯 Common Tasks

### Add Custom Product Dictionary
Edit: `src/aspect_sentiment/engine.py`
Update: `PRODUCT_SYNONYMS` & `BRAND_SYNONYMS`

### Change Whisper Model Size
Set environment variable:
```
WHISPER_MODEL_SIZE=medium
```
Or edit: `src/aspect_sentiment/audio.py`

### Use GPU for Faster Processing
```
WHISPER_DEVICE=cuda
```
Requires: NVIDIA GPU with CUDA

### Deploy to Production
1. Use production ASGI server (gunicorn)
2. Set up HTTPS (nginx + SSL)
3. Add rate limiting & monitoring
4. Use docker for containerization

---

## 📞 Quick Links

- **GitHub Repo**: (if available)
- **API Docs**: http://localhost:8000/docs
- **Status**: http://localhost:8000/health
- **Test UI**: Open test_client.html

---

## ✅ Healthy System Checklist

When you run the system, verify:
- [ ] Backend console shows "Application startup complete"
- [ ] Frontend console shows no red errors
- [ ] Health endpoint returns 200 OK  
- [ ] Text input produces sentiment scores
- [ ] Results display within 1 second
- [ ] Products are correctly extracted
- [ ] Sentiment labels make sense

---

**Built:** April 13, 2026
**Status:** 🟢 Production Ready
**Version:** 1.0.0
