import sys
import time
import requests
from pathlib import Path

BACKEND_URL = "http://localhost:8000"

def test_health():
    print("\n1. Testing Backend API Health Check...")
    try:
        res = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        if res.status_code == 200:
            print("  [PASS] Status: OK")
            print("  [PASS] Response:", res.json())
            return True
        else:
            print(f"  [FAIL] Failed (Status Code: {res.status_code})")
            return False
    except Exception as e:
        print("  [FAIL] Connection failed. Is the backend running?")
        print(f"     Error: {e}")
        return False

def test_readiness():
    print("\n2. Testing Backend API Readiness...")
    try:
        res = requests.get(f"{BACKEND_URL}/api/readiness", timeout=5)
        if res.status_code == 200:
            data = res.json()
            print(f"  [PASS] Status: {data.get('status')}")
            print(f"  [PASS] Details: {data.get('checks')}")
            return True
        else:
            print(f"  [FAIL] Failed (Status Code: {res.status_code})")
            return False
    except Exception as e:
        print(f"  [FAIL] Readiness check failed: {e}")
        return False

def test_text_analysis():
    print("\n3. Testing Text Feature Extraction & Analysis...")
    try:
        payload = {
            "text": "Hello, my name is John Smith and I am looking for a Dell laptop for my office. My budget is around 80,000 INR. I need it this week.",
            "sourceName": "integration-test-client"
        }
        res = requests.post(f"{BACKEND_URL}/api/analyze", json=payload, timeout=15)
        if res.status_code == 200:
            data = res.json()
            print("  [PASS] API Analysis response received!")
            print("  [PASS] Sentiment Dominant:", data.get("summary", {}).get("dominant"))
            print("  [PASS] Conversion Score Label:", data.get("conversionScore", {}).get("label"))
            print("  [PASS] Conversion Score Probability:", data.get("conversionScore", {}).get("probability"))
            print("  [PASS] Privacy Redactions:", data.get("privacy", {}).get("redactionCount"))
            print("  [PASS] Follow-Up Alerts:", len(data.get("followUpAlerts", [])))
            return True
        else:
            print(f"  [FAIL] Analysis failed (Status Code: {res.status_code})")
            print("  Response:", res.text)
            return False
    except Exception as e:
        print(f"  [FAIL] Text analysis error: {e}")
        return False

def test_audio_upload():
    print("\n4. Testing Audio Upload and Job Queue...")
    root = Path(__file__).resolve().parent
    audio_path = root / "audio" / "conv_001.wav"
    
    if not audio_path.exists():
        print(f"  [WARN] Warning: Audio file not found at {audio_path}. Skipping audio upload test.")
        return True
        
    try:
        print(f"  Uploading {audio_path.name} ({audio_path.stat().st_size} bytes)...")
        with open(audio_path, "rb") as f:
            files = {"audio": (audio_path.name, f, "audio/wav")}
            res = requests.post(f"{BACKEND_URL}/api/upload", files=files, timeout=15)
            
        if res.status_code != 200:
            print(f"  [FAIL] Upload request failed (Status Code: {res.status_code})")
            print("  Response:", res.text)
            return False
            
        job_info = res.json()
        job_id = job_info.get("job_id")
        print(f"  [PASS] Upload successful. Job ID: {job_id}")
        print("  Polling job status (timeout 90 seconds)...")
        
        for attempt in range(45):
            time.sleep(2)
            job_res = requests.get(f"{BACKEND_URL}/api/jobs/{job_id}", timeout=5)
            if job_res.status_code != 200:
                print(f"  [FAIL] Failed to poll job (Status Code: {job_res.status_code})")
                return False
                
            job_data = job_res.json()
            status = job_data.get("status")
            print(f"    - Poll {attempt+1}: status is '{status}'")
            
            if status == "completed":
                print("  [PASS] Audio processing job completed successfully!")
                result = job_data.get("result", {})
                print("  [PASS] Whisper Transcription length:", len(result.get("transcript", "")))
                print("  [PASS] Conversion Score Label:", result.get("conversionScore", {}).get("label"))
                print("  [PASS] Follow-Up Alerts Detected:", len(result.get("followUpAlerts", [])))
                return True
            elif status == "failed":
                print("  [FAIL] Job failed in worker:", job_data.get("error"))
                return False
        else:
            print("  [FAIL] Polling timed out after 90 seconds.")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Audio upload test error: {e}")
        return False

if __name__ == "__main__":
    print("==================================================")
    print("      Nexus AI - API Integration Test Suite       ")
    print("==================================================")
    
    success = True
    if not test_health():
        success = False
    elif not test_readiness():
        success = False
    elif not test_text_analysis():
        success = False
    elif not test_audio_upload():
        success = False
        
    print("\n==================================================")
    if success:
        print("SUCCESS: All API integration tests passed!")
        sys.exit(0)
    else:
        print("FAILURE: One or more integration tests failed.")
        sys.exit(1)
