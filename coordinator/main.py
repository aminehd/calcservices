import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8081"))
WORKERS = int(os.environ.get("WORKERS", "3"))
DIM = 4

lock = threading.Lock()
state = {"step": 0, "weights": [0.0] * DIM, "reports": {}}


def current_weights():
    return {"step": state["step"], "weights": state["weights"]}


def record(worker, grad):
    """TODO: store this worker's grad. When all WORKERS have reported,
    average the grads, add them to state["weights"], bump state["step"],
    and clear the reports. Return how many are still missing."""
    return WORKERS


class Handler(BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send({"ok": True})
            return
        with lock:
            self._send(current_weights())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        msg = json.loads(self.rfile.read(length) or b"{}")
        with lock:
            waiting = record(msg.get("worker", "?"), msg.get("grad", [0.0] * DIM))
            self._send({"step": state["step"], "waiting": waiting})

    def log_message(self, *args):
        pass


print(f"coordinator up on {PORT}, barrier of {WORKERS}", flush=True)
ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
