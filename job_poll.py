import time, http.client, json
job_id = "c83d6c9b-afa5-4b00-8854-6f205a6c661a"
for i in range(10):
    conn = http.client.HTTPConnection("localhost", 8000)
    conn.request("GET", f"/api/jobs/{job_id}")
    resp = conn.getresponse()
    data = resp.read().decode("utf-8")
    print(i, resp.status, data)
    if resp.status == 200:
        obj = json.loads(data)
        if obj.get("status") not in ("pending",):
            break
    time.sleep(3)
