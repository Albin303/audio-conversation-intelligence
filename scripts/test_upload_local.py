import requests
import pathlib
import time
import sys

def main():
    p = pathlib.Path('audio/conv_001.wav')
    print('exists', p.exists(), 'path', p)
    if not p.exists():
        print('audio file missing', p)
        sys.exit(2)

    with p.open('rb') as f:
        r = requests.post('http://localhost:8000/api/upload', files={'audio': (p.name, f, 'audio/wav')}, timeout=60)
    print('upload', r.status_code)
    print(r.text)
    data = r.json() if r.status_code == 200 else {}
    job_id = data.get('job_id')
    print('job_id', job_id)
    if not job_id:
        sys.exit(3)

    for i in range(20):
        time.sleep(3)
        resp = requests.get(f'http://localhost:8000/api/jobs/{job_id}', timeout=30)
        print('poll', i, resp.status_code, resp.text)
        if resp.status_code == 200 and resp.json().get('status') in ('completed', 'failed'):
            break

if __name__ == '__main__':
    main()
