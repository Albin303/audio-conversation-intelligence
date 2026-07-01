import subprocess
import time
import sys
import os

print("Starting backend server in subprocess...")
env = os.environ.copy()
# Ensure unbuffered output so we get everything
env["PYTHONUNBUFFERED"] = "1"

proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "src.api.server:app", "--host", "127.0.0.1", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
    env=env,
    cwd=os.getcwd()
)

# Wait for startup
time.sleep(5)

# Start a thread to read stdout/stderr of the server and print it
import threading
def reader(stream, prefix):
    for line in stream:
        print(f"{prefix}: {line.strip()}", flush=True)

t1 = threading.Thread(target=reader, args=(proc.stdout, "[STDOUT]"))
t2 = threading.Thread(target=reader, args=(proc.stderr, "[STDERR]"))
t1.daemon = True
t2.daemon = True
t1.start()
t2.start()

print("Running integration test script...")
test_proc = subprocess.run(
    [sys.executable, "test_audio_upload.py"],
    capture_output=True,
    text=True
)

print("\n--- TEST SCRIPT STDOUT ---")
print(test_proc.stdout)
print("--- TEST SCRIPT STDERR ---")
print(test_proc.stderr)
print("--------------------------")

print("Waiting a bit to check if server is still alive...")
time.sleep(3)

ret = proc.poll()
if ret is not None:
    print(f"Server exited with return code: {ret}")
else:
    print("Server is still running. Terminating...")
    proc.terminate()
