import json
import os
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


def step():
    """TODO: one training step.
    1. weights = get("/weights")
    2. sleep a little, this is the 'compute'
    3. grad = DIM random numbers
    4. post("/report", {"worker": ME, "grad": grad, "step": weights["step"]})
    5. print what happened"""
    get("/health")


print(f"{ME} up, coordinator at {URL}", flush=True)
while True:
    try:
        step()
        print(f"{ME} ok", flush=True)
    except Exception as exc:
        print(f"{ME} retry after {type(exc).__name__}: {exc}", flush=True)
    time.sleep(1)
