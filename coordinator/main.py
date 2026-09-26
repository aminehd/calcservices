import json
import os
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8081"))
CALC_URL = os.environ.get("CALC_URL", "http://127.0.0.1:9001")
CONTROL_PLANE_URL = os.environ.get("CONTROL_PLANE_URL", "http://controlplane:18000")

lock = threading.Lock()
state = {"done": 0, "per_op": {}}


def post(path, body):
    req = urllib.request.Request(
        CALC_URL + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.load(r)


def load_routes():
    with urllib.request.urlopen(CONTROL_PLANE_URL + "/snapshot", timeout=3) as r:
        ops = json.load(r)["ops"]
    print(f"routes from control plane: {ops}", flush=True)
    return ops


def show_my_envoy(attempts=10):
    for n in range(attempts):
        try:
            with urllib.request.urlopen("http://127.0.0.1:9901/config_dump", timeout=3) as r:
                dump = json.load(r)
        except Exception as exc:
            print(f"sidecar admin not up yet ({type(exc).__name__}), retrying", flush=True)
            time.sleep(1)
            continue

        listeners, clusters = [], []
        for cfg in dump.get("configs", []):
            for item in cfg.get("static_listeners", []) + cfg.get("dynamic_listeners", []):
                addr = item.get("listener", {}).get("address", {}).get("socket_address", {})
                if addr:
                    listeners.append(f"{addr.get('address')}:{addr.get('port_value')}")
            for item in cfg.get("static_clusters", []) + cfg.get("dynamic_active_clusters", []):
                c = item.get("cluster", {})
                ep = c.get("load_assignment", {}).get("endpoints", [{}])[0].get("lb_endpoints", [{}])[0]
                sock = ep.get("endpoint", {}).get("address", {}).get("socket_address", {})
                clusters.append(f"{c.get('name')}->{sock.get('address')}:{sock.get('port_value')}")

        if listeners or clusters:
            print(f"my envoy listens on {', '.join(listeners)}", flush=True)
            print(f"my envoy knows {', '.join(clusters)}", flush=True)
            return
        print(f"sidecar config still empty (try {n + 1})", flush=True)
        time.sleep(1)
    print("gave up reading my sidecar config", flush=True)


ROUTES = load_routes()
show_my_envoy()


def calculate(req):
    """TODO: req is {"op": "add", "a": 6, "b": 7}.
    1. look up ROUTES[req["op"]] to get the path
    2. post({"a": ..., "b": ...}) to it
    3. return the reply"""
    path = ROUTES[req["op"]]
    return post(path, {"a": req["a"], "b": req["b"]})


def tally(op):
    state["done"] += 1
    state["per_op"][op] = state["per_op"].get(op, 0) + 1


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
        else:
            with lock:
                self._send(dict(state))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(length) or b"{}")
        try:
            reply = calculate(req)
        except Exception as exc:
            self._send({"error": f"{type(exc).__name__}: {exc}"}, 502)
            return
        with lock:
            tally(req.get("op", "?"))
        self._send(reply)

    def log_message(self, *args):
        pass


print(f"coordinator up on {PORT}, calculators via {CALC_URL}", flush=True)
ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
