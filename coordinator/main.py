import json
import os
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8081"))
CALC_URL = os.environ.get("CALC_URL", "http://127.0.0.1:9001")
ADMIN_URL = os.environ.get("ADMIN_URL", "http://127.0.0.1:9901")

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


def show_my_envoy(attempts=10):
    for n in range(attempts):
        try:
            with urllib.request.urlopen(ADMIN_URL + "/config_dump", timeout=3) as r:
                configs = json.load(r).get("configs", [])
        except Exception as exc:
            print(f"sidecar admin not up yet ({type(exc).__name__}), retrying", flush=True)
            time.sleep(1)
            continue

        clusters, version = [], ""
        for cfg in configs:
            version = cfg.get("version_info", version)
            for item in cfg.get("dynamic_active_clusters", []):
                c = item.get("cluster", {})
                ep = c["load_assignment"]["endpoints"][0]["lb_endpoints"][0]
                sock = ep["endpoint"]["address"]["socket_address"]
                clusters.append(f"{c['name']}->{sock['address']}:{sock['port_value']}")

        if clusters:
            print(f"my envoy config is dynamic (xds) version {version or '-'}", flush=True)
            print(f"my envoy knows {', '.join(clusters)}", flush=True)
            return
        print(f"sidecar config still empty (try {n + 1})", flush=True)
        time.sleep(1)
    print("gave up reading my sidecar config", flush=True)


def calculate(req):
    return post("/calc", req)


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


if __name__ == "__main__":
    show_my_envoy()
    print(f"coordinator up on {PORT}, calculators via {CALC_URL}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
