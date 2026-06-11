@echo off
REM Quick startup guide for Windows

echo.
echo ========================================
echo.
echo  🚀 AI Audio Sentiment Analysis Startup
echo.
echo ========================================
echo.

echo Step 1: START BACKEND API
echo ========================
echo.
echo Open a NEW terminal/command prompt and run:
echo.
echo   cd d:\Project -AI audio
echo   python -m uvicorn src.api.server:app --reload --port 8000
echo.
echo Expected output:
echo   Uvicorn running on http://127.0.0.1:8000
echo.
echo Keep this terminal OPEN!
echo.

pause

echo Step 2: START FRONTEND DEV SERVER
echo ==================================
echo.
echo Open ANOTHER NEW terminal/command prompt and run:
echo.
echo   cd d:\Project -AI audio\frontend
echo   npm run dev
echo.
echo Expected output:
echo   http://localhost:5173
echo.
echo Keep this terminal OPEN!
echo.

pause

echo Step 3: DEBUG TOOLS
echo ==================
echo.
echo Now both backends are running. Test with:
echo.
echo OPTION A - Easy Browser Test (Recommended):
echo   1. Open browser to: http://localhost:5173/audio-upload-debug.html
echo   2. Click each test button in order:
echo      - "Check Backend" (tests connection)
echo      - "Analyze Text" (tests text API)
echo      - Select audio file then "Upload & Analyze Audio" (tests file upload)
echo.
echo OPTION B - Python Test Suite (Advanced):
echo   1. Open a 3rd terminal
echo   2. Run: cd d:\Project -AI audio
echo   3. Run: python test_audio_upload.py
echo.

pause

echo Step 4: MAIN APP
echo ================
echo.
echo Open your browser and go to: http://localhost:5173
echo.
echo Try uploading an audio file. Messages in browser console (F12) will show:
echo   📤 Sending to backend...
echo   📎 Added file to FormData...
echo.
echo If you see a "request failed" error, use the DEBUG TOOLS from Step 3
echo to identify the exact problem!
echo.

pause

echo.
echo ✨ SETUP COMPLETE
echo ================
echo.
echo If audio upload is still failing:
echo   1. Check backend console for error messages
echo   2. Read: DEBUG_AUDIO_UPLOAD.md
echo   3. Use the browser debug tool to trace the issue
echo.

pause
