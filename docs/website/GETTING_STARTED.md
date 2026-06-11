# ✅ GETTING STARTED CHECKLIST

Use this checklist to ensure everything is working properly.

---

## 🟢 PHASE 1: Environment Setup (5 minutes)

### Step 1: Verify Python Installation
- [ ] Open PowerShell in project root
- [ ] Run: `.venv\Scripts\python.exe --version`
- [ ] Expected: Python 3.11+ (e.g., Python 3.11.0)
- [ ] If fails: Install Python or activate venv

### Step 2: Check Dependencies
- [ ] Run: `python test_system.py`
- [ ] Look for: ✅ "ALL TESTS COMPLETED SUCCESSFULLY!"
- [ ] Check: spaCy model loaded
- [ ] Check: Whisper model loaded
- [ ] If fails: Run `pip install -r requirements.txt` then `python -m spacy download en_core_web_sm`

### Step 3: Verify Node.js (for Frontend)
- [ ] Open new PowerShell window
- [ ] Run: `node --version`
- [ ] Expected: v18+ (e.g., v22.11.0)
- [ ] Run: `npm --version`
- [ ] Expected: 10+ (e.g., 10.9.0)
- [ ] If fails: Download from https://nodejs.org/

### Step 4: Check Frontend Dependencies
- [ ] Navigate: `cd frontend`
- [ ] Run: `npm install` (only if node_modules missing)
- [ ] Should complete within 2 minutes
- [ ] If fails: Check npm/node installation

---

## 🟡 PHASE 2: Start Services (3 minutes)

### Option A: Automated Startup (Easiest)
- [ ] In project root, double-click: `START.bat`
- [ ] Watch three windows open
- [ ] Wait 10-15 seconds for models to load
- [ ] All three should show "running" or "ready"

### Option B: Manual Startup (Full Control)

#### Window 1 - Backend API
- [ ] Open PowerShell in project root
- [ ] Run: `.venv\Scripts\python.exe -m uvicorn src.api.server:app --reload --port 8000`
- [ ] Wait for: **"Application startup complete"**
- [ ] Keep window open

#### Window 2 - Frontend Dev Server
- [ ] Open new PowerShell
- [ ] Navigate: `cd frontend`
- [ ] Run: `npm run dev`
- [ ] Wait for: **"Local: http://localhost:5173"**
- [ ] Keep window open

#### Window 3 - Browser
- [ ] Open Web Browser
- [ ] Navigate to: `http://localhost:5173`
- [ ] You should see the sentiment analysis UI

---

## 🟢 PHASE 3: Verify Backend (2 minutes)

### Test 1: Health Check
- [ ] Open browser and go to: `http://localhost:8000/health`
- [ ] Expected response:
  ```json
  {"status": "ok", "spacy_model": "...", "whisper_model": "small", "whisper_device": "cpu"}
  ```
- [ ] ✅ If you see this, backend is working

### Test 2: Simple Text Analysis
- [ ] Open New PowerShell Window
- [ ] Run:
  ```powershell
  $body = @{text="The camera is great but battery is bad"}
  Invoke-RestMethod -Uri "http://localhost:8000/api/analyze" -Method Post -Body $body
  ```
- [ ] Expected: JSON response with "products" array
- [ ] Check: Products include "camera" and "battery"
- [ ] ✅ If successful, API is working

### Test 3: Using Test Client
- [ ] Open: `test_client.html` (in project root)
- [ ] In browser: Type text in textarea
- [ ] Click: "Analyze" button
- [ ] Watch: Real-time results panel
- [ ] Expected: Products extracted with sentiment scores
- [ ] ✅ If working, API integration is good

---

## 🔵 PHASE 4: Test Frontend UI (5 minutes)

### Test 1: Text Input
- [ ] Frontend should be open at `http://localhost:5173`
- [ ] Click: Text area in "Input" section
- [ ] Type: `"The product is excellent but shipping took forever"`
- [ ] Click: "Analyze" button
- [ ] Wait: For processing to complete
- [ ] Expected: 
  - [ ] Results show in right panel
  - [ ] "product" sentiment appears correct
  - [ ] "shipping" sentiment appears negative
- [ ] ✅ Text input working

### Test 2: Pipeline Visualization
- [ ] Check the pipeline shows steps:
  - [ ] ✓ Uploading
  - [ ] ✓ Speech-to-text (skipped for text)
  - [ ] ✓ NLP extraction
  - [ ] ✓ Sentiment analysis
- [ ] Each should show "completed" status
- [ ] ✅ Pipeline display working

### Test 3: Results Display
- [ ] Results panel should show:
  - [ ] Sentiment gauge (circular)
  - [ ] Positive/Neutral/Negative breakdown
  - [ ] Product table with items
- [ ] Click: On a product item
- [ ] Expected: Highlights to appear in transcript
- [ ] ✅ Results display working

### Test 4: Audio Input (Optional)
- [ ] Click: "Input Type" dropdown
- [ ] Select: "Audio File"
- [ ] File selector appears
- [ ] Choose: Any .wav or .mp3 file
- [ ] Click: "Analyze"
- [ ] Wait: 3-10 seconds (longer for audio)
- [ ] Expected: Same results as text
- [ ] ✅ Audio processing working

---

## 🟢 PHASE 5: Verify Results Accuracy (3 minutes)

### Sample Test Case 1
```
Input: "The camera quality is stunning with sharp details. 
        Battery drains quickly though. Performance is excellent."

Expected Results:
- camera: POSITIVE (score > 0.7)
- battery: NEGATIVE (score < -0.5)
- performance: POSITIVE (score > 0.7)
- Positive%: 67%
- Negative%: 33%
```

### Sample Test Case 2
```
Input: "Excellent customer service but product is fragile"

Expected Results:
- customer service: POSITIVE
- product: NEGATIVE (due to "fragile")
- Positive%: 50%
- Negative%: 50%
```

### Sample Test Case 3
```
Input: "The device works fine"

Expected Results:
- device: NEUTRAL or slightly POSITIVE
- Mostly NEUTRAL or balanced sentiment
```

---

## 🔴 PHASE 6: Troubleshooting (If Something Fails)

### Problem: "API Connection Refused"
**Solution:**
1. Check backend window is running
2. Verify no other app uses port 8000
3. Restart backend:
   ```powershell
   .venv\Scripts\python.exe -m uvicorn src.api.server:app --reload --port 8000
   ```
4. Try health check: `http://localhost:8000/health`

### Problem: "Frontend Won't Load"
**Solution:**
1. Check frontend window is running
2. Verify no other app uses port 5173
3. Look for errors in terminal
4. Restart frontend:
   ```powershell
   cd frontend && npm run dev
   ```

### Problem: "spaCy Model Not Found"
**Solution:**
```powershell
python -m spacy download en_core_web_sm
```

### Problem: "Whisper Model Download Stuck"
**Solution:**
1. Press Ctrl+C to cancel
2. Ensure internet connection works
3. Try again:
   ```powershell
   python -c "import whisper; whisper.load_model('small')"
   ```

### Problem: "No Products Extracted"
**Try:**
- Longer input text (5+ sentences)
- More descriptive text (mention actual products)
- Use English language
- Example: "The phone camera is good and display is bright"

### Problem: "Sentiment Scores Seem Wrong"
**Check:**
1. Are the products actually mentioned? (algorithm extracts nouns)
2. Is there adjective context? ("amazing camera" vs just "camera")
3. Try more obvious sentiment: "Absolutely terrible" vs "not great"
4. Context window might be isolating different phrase

---

## 🟢 FINAL VERIFICATION CHECKLIST

When everything is working:

- [ ] Backend console shows no error messages
- [ ] Frontend console (F12) shows no red errors
- [ ] `http://localhost:8000/health` returns 200 OK
- [ ] `http://localhost:5173` loads the UI
- [ ] Test input produces sentiment scores
- [ ] Products are correctly extracted
- [ ] Sentiment labels match your expectations
- [ ] Export buttons work (JSON/PDF)
- [ ] No crashes or freezing

---

## 🎯 Quick Restart (If Something Breaks)

### Complete Restart
1. Close all PowerShell windows
2. Close browser tabs
3. Run `START.bat` again
4. Or manually restart both terminals

### Clean Test Run
```powershell
# In project root
python test_system.py  # Should pass all tests
```

### Verify Again
```powershell
# Check health
curl http://localhost:8000/health

# Try test API request
$body = @{text="Test input"}
Invoke-RestMethod -Uri "http://localhost:8000/api/analyze" -Method Post -Body $body
```

---

## 🎉 Success Indicators

You'll know everything is working when:

1. ✅ Browser shows the sentiment analysis dashboard
2. ✅ You can type text and see results in < 1 second
3. ✅ Products are extracted from your input
4. ✅ Sentiment is labeled (positive/negative/neutral)
5. ✅ Confidence scores appear (0-1 range)
6. ✅ No error messages in any console
7. ✅ Tests pass when you run `python test_system.py`

---

## 📚 Using the System

### Basic Workflow
1. **Paste Text** or **Upload Audio** in the input section
2. **Click Analyze** button
3. **Watch** the real-time pipeline
4. **View Results** in the dashboard
5. **Export** as JSON or PDF if needed

### Advanced Features
- Multi-language support (select language before upload)
- Audio transcription (Whisper)
- Confidence scoring
- Context highlighting
- Product deduplication
- Trend analysis

---

## 📈 Next Steps

### Short-term
- [ ] Test with your own data
- [ ] Try different languages
- [ ] Test with audio files
- [ ] Export results

### Medium-term
- [ ] Add more test cases
- [ ] Customize product categories
- [ ] Adjust sentiment thresholds
- [ ] Build integrations

### Long-term
- [ ] Deploy to production
- [ ] Add database for history
- [ ] Build API clients (Python, JavaScript, etc.)
- [ ] Create dashboard for analytics

---

## 📞 Support

**If you get stuck:**

1. Read the SYSTEM_GUIDE.md
2. Check API_DOCUMENTATION.md
3. Run: `python test_system.py`
4. Review terminal output for error messages
5. Check test_client.html for manual API testing

---

## ✅ Verification Summary

```
Phase 1 (Environment):  ⏳ → ✅
Phase 2 (Services):     ⏳ → ✅
Phase 3 (Backend):      ⏳ → ✅
Phase 4 (Frontend):     ⏳ → ✅
Phase 5 (Accuracy):     ⏳ → ✅
Phase 6 (Crisis):       N/A (hopefully!)

Overall Status: 🟢 READY
```

---

**Checklist Version:** 1.0
**Last Updated:** April 13, 2026
**Status:** Production Ready
