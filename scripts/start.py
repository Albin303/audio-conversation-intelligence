import subprocess
import os
import sys
import time
import signal

def main():
    print("=== Nexus AI - Hugging Face Spaces Supervisor ===")
    
    # Force output to be unbuffered so logs appear immediately
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    # Environment variables
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    # Create worker environments
    env_audio = env.copy()
    env_audio["WORKER_TYPE"] = "audio"
    
    env_ml = env.copy()
    env_ml["WORKER_TYPE"] = "ml"
    
    # Start processes
    processes = {}
    
    print("Starting Audio Worker process...")
    processes["audio_worker"] = subprocess.Popen(
        [sys.executable, "src/workers/run_worker.py"],
        env=env_audio
    )
    
    print("Starting ML Worker process...")
    processes["ml_worker"] = subprocess.Popen(
        [sys.executable, "src/workers/run_worker.py"],
        env=env_ml
    )
    
    # Start Uvicorn API server
    port = int(os.getenv("PORT", "7860"))
    print(f"Starting FastAPI server on port {port}...")
    processes["api_server"] = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", str(port)],
        env=env
    )
    
    def terminate_all(signum, frame):
        print(f"Received signal {signum}. Terminating all processes...")
        for name, proc in processes.items():
            if proc.poll() is None:
                print(f"Terminating {name}...")
                proc.terminate()
        sys.exit(0)
        
    signal.signal(signal.SIGTERM, terminate_all)
    signal.signal(signal.SIGINT, terminate_all)
    
    # Monitor loop
    try:
        while True:
            time.sleep(5)
            
            # Check API server
            if processes["api_server"].poll() is not None:
                ret = processes["api_server"].returncode
                print(f"CRITICAL: API server exited with code {ret}. Exiting supervisor.")
                terminate_all(signal.SIGTERM, None)
                sys.exit(ret)
                
            # Check Audio Worker
            if processes["audio_worker"].poll() is not None:
                print("WARNING: Audio worker died. Restarting...")
                processes["audio_worker"] = subprocess.Popen(
                    [sys.executable, "src/workers/run_worker.py"],
                    env=env_audio
                )
                
            # Check ML Worker
            if processes["ml_worker"].poll() is not None:
                print("WARNING: ML worker died. Restarting...")
                processes["ml_worker"] = subprocess.Popen(
                    [sys.executable, "src/workers/run_worker.py"],
                    env=env_ml
                )
    except Exception as e:
        print(f"Supervisor error: {e}")
        terminate_all(signal.SIGTERM, None)

if __name__ == "__main__":
    main()
