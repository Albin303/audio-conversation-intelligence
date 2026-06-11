#!/bin/bash
# Quick startup script for the entire system with debugging tools

echo "🚀 AI Audio Sentiment Analysis - Full Stack Startup"
echo "=================================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Backend
echo -e "${BLUE}1. Starting Backend API...${NC}"
echo "   Command: .venv/bin/python -m uvicorn src.api.server:app --reload --port 8000"
echo "   Expected: 'Uvicorn running on http://127.0.0.1:8000'"
echo ""
echo "   🔧 Run in terminal 1 (DO NOT CLOSE):"
echo "   cd d:/Project -AI audio"
echo "   .venv/bin/python -m uvicorn src.api.server:app --reload --port 8000"
echo ""

# Step 2: Frontend
echo -e "${BLUE}2. Starting Frontend Dev Server...${NC}"
echo "   Command: npm run dev"
echo "   Expected: 'http://localhost:3000'"
echo ""
echo "   🔧 Run in terminal 2 (DO NOT CLOSE):"
echo "   cd d:/Project -AI audio/frontend"
echo "   npm run dev"
echo ""

# Step 3: Debug Tools  
echo -e "${BLUE}3. Using Debug Tools...${NC}"
echo "   After both servers are running:"
echo ""
echo "   Option A - Browser Debug Tool (EASIEST):"
echo "   - Open: http://localhost:3000/audio-upload-debug.html"
echo "   - Or: file:///d:/Project%20-AI%20audio/frontend/public/audio-upload-debug.html"
echo "   - Tests: Health Check → Text Analysis → Audio Upload"
# Step 3: Debug Tools continued
echo ""
echo "   Option B - Python Test Suite:"
echo "   Run in terminal 3:"
echo "   cd d:/Project -AI audio"
echo "   .venv/bin/python test_audio_upload.py"
echo ""

# Step 4: Main App
echo -e "${GREEN}4. Access the Full App${NC}"
echo "   Open in browser: http://localhost:3000"
echo ""

echo -e "${YELLOW}⚠️  IMPORTANT:${NC}"
echo "   - Keep BOTH terminal 1 (backend) and 2 (frontend) OPEN"
echo "   - If you see 'request failed' error:"
echo "     1. Check backend console for actual error"
# Step 4 continued
echo "     2. Run debug tools to isolate the issue"
echo "     3. See DEBUG_AUDIO_UPLOAD.md for troubleshooting"
echo ""

echo -e "${GREEN}✨ System ready! Follow steps above to start.${NC}"
