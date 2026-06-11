@echo off
REM =============================================================================
REM AI-Powered Sentiment Analysis System - Complete Startup Script
REM =============================================================================

setlocal enabledelayedexpansion

cls
echo.
echo ╔═════════════════════════════════════════════════════════════════════════════╗
echo ║        AI-Powered Aspect-Based Sentiment Analysis System                   ║
echo ║                    🎯 Complete Startup Script 🎯                           ║
echo ╚═════════════════════════════════════════════════════════════════════════════╝
echo.

REM Set project root
set PROJECT_ROOT=%~dp0
cd /d "%PROJECT_ROOT%"

echo [1/6] Checking environment...
if not exist ".venv" (
    echo ❌ ERROR: Virtual environment not found at .venv
    echo Run: python -m venv .venv
    pause
    exit /b 1
)
echo ✅ Virtual environment found

echo.
echo [2/6] Checking Python dependencies...
call .venv\Scripts\python.exe -c "import fastapi, spacy, whisper" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Installing dependencies...
    call .venv\Scripts\pip.exe install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Failed to install dependencies
        pause
        exit /b 1
    )
) else (
    echo ✅ All Python dependencies installed
)

echo.
echo [3/6] Checking spaCy models...
call .venv\Scripts\python.exe -c "import spacy; spacy.load('en_core_web_sm')" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Downloading spaCy English model...
    call .venv\Scripts\python.exe -m spacy download en_core_web_sm
    if errorlevel 1 (
        echo ❌ Failed to download spaCy model
        pause
        exit /b 1
    )
) else (
    echo ✅ spaCy model available
)

echo.
echo [4/6] Checking Node.js for frontend...
where node >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js not found. Install from: https://nodejs.org/
    pause
    exit /b 1
)
echo ✅ Node.js found
where npm >nul 2>&1
if errorlevel 1 (
    echo ❌ npm not found
    pause
    exit /b 1
)
echo ✅ npm found

echo.
echo [5/6] Checking frontend dependencies...
if not exist "frontend\node_modules" (
    echo ⚠️  Installing frontend dependencies...
    cd frontend
    call npm install --legacy-peer-deps
    if errorlevel 1 (
        echo ❌ Failed to install frontend dependencies
        pause
        exit /b 1
    )
    cd ..
) else (
    echo ✅ Frontend dependencies installed
)

echo.
echo [6/6] Running system tests...
call .venv\Scripts\python.exe test_system.py >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Some tests failed, but system may still work
) else (
    echo ✅ All system tests passed
)

echo.
echo ╔═════════════════════════════════════════════════════════════════════════════╗
echo ║                      ✅ SYSTEM READY TO START                              ║
echo ╚═════════════════════════════════════════════════════════════════════════════╝
echo.
echo 🚀 STARTING SERVICES...
echo.
echo Opening 3 windows:
echo   1. Backend API (http://localhost:8000)
echo   2. Frontend Dev Server (http://localhost:3000)
echo   3. Test Client (open in browser when ready)
echo.
timeout /t 2

REM Start backend in new window
echo Starting Backend API...
start "Backend API" cmd /k "cd /d "%PROJECT_ROOT%" && .venv\Scripts\python.exe -m uvicorn src.api.server:app --reload --port 8000"

timeout /t 3

REM Start frontend in new window
echo Starting Frontend Dev Server...
start "Frontend Dev" cmd /k "cd /d "%PROJECT_ROOT%\frontend" && npm run dev"

timeout /t 3

REM Open test client in browser
echo Opening test client in browser...
start test_client.html

echo.
echo ╔═════════════════════════════════════════════════════════════════════════════╗
echo ║                      🎉 STARTUP COMPLETE                                   ║
echo ╚═════════════════════════════════════════════════════════════════════════════╝
echo.
echo 📍 Access points:
echo.
echo   Frontend Dashboard:     http://localhost:3000
echo   API Health Check:       http://localhost:8000/health
echo   API Documentation:      http://localhost:8000/docs
echo   Raw Test Client:        file:///%PROJECT_ROOT%test_client.html
echo.
echo.
echo ⏹️  To stop the services:
echo   - Close the Backend API window (Ctrl+C)
echo   - Close the Frontend window (Ctrl+C)
echo.
echo 📚 Documentation:
echo   - SYSTEM_GUIDE.md - Comprehensive documentation
echo   - README.md - Project overview
echo.
pause
