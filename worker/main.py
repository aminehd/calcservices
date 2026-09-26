import json
import os
import random
import socket
import time
import urllib.request

URL = os.environ.get("COORDINATOR_URL", "http://127.0.0.1:9001")
ME = os.environ.get("WORKER_ID", socket.gethostname())
DIM = 4


def get(path):
    with urllib.request.urlopen(URL + path, timeout=5) as r:
        return json.load(r)


def post(path, obj):
    req = urllib.request.Request(
        URL + path,
        data=json.dumps(obj).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.load(r)


print(f"{ME} up, coordinator at {URL}", flush=True)
while True:
    try:
        weights = get("/weights")
        time.sleep(0.2)
        grad = [random.gauss(0, 0.1) for _ in range(DIM)]
        reply = post("/report", {"worker": ME, "grad": grad, "step": weights["step"]})
        print(f"{ME} reported at step {weights['step']} waiting {reply['waiting']}", flush=True)
        time.sleep(1)
    except Exception as exc:
        print(f"{ME} retry after {type(exc).__name__}: {exc}", flush=True)
        time.sleep(2)
