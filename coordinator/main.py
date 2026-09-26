import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

WORKERS = int(os.environ.get("WORKERS", "3"))
DIM = 4

lock = threading.Lock()
state = {"step": 0, "weights": [0.0] * DIM, "reports": {}}


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
            self._send({"step": state["step"], "weights": state["weights"]})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        msg = json.loads(self.rfile.read(length) or b"{}")
        with lock:
            state["reports"][msg.get("worker", "?")] = msg.get("grad", [0.0] * DIM)
            waiting = WORKERS - len(state["reports"])
            if waiting <= 0:
                grads = list(state["reports"].values())
                state["weights"] = [
                    w + sum(g[i] for g in grads) / len(grads)
                    for i, w in enumerate(state["weights"])
                ]
                state["step"] += 1
                state["reports"] = {}
                print(
                    f"step {state['step']} weights {[round(w, 3) for w in state['weights']]}",
                    flush=True,
                )
            self._send({"step": state["step"], "waiting": max(waiting, 0)})

    def log_message(self, *args):
        pass


print(f"coordinator up, barrier of {WORKERS}", flush=True)
ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
