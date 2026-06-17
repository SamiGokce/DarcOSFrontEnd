#!/usr/bin/env python3
"""DarcOS desktop bridge — makes the web desktop function like a NATIVE one.

Serves the web desktop over http://127.0.0.1:PORT and exposes the real system
to it through darcos-agentd. The browser JS calls these endpoints, so a "real"
action in the UI runs a real action on the machine:

  POST /api/agent  {text}      → run a request through the agent (real tools)
  GET  /api/fs?path=…          → list a real directory
  GET  /api/open?path=…        → open a path with the system handler

Without this bridge the desktop still renders, but its apps are a simulation.
With it, the web desktop is a real shell over darcos-agentd (which runs as root).
"""
from __future__ import annotations
import http.server, socketserver, json, socket, os, urllib.parse, subprocess

DESKTOP_DIR = os.environ.get("DARCOS_DESKTOP_DIR", "/usr/share/darcos/desktop")
SOCK = os.environ.get("DARCOS_AGENT_SOCK", "/run/darcos/agentd.sock")
PORT = int(os.environ.get("DARCOS_BRIDGE_PORT", "8787"))


def agent_call(text: str) -> list:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(SOCK)
    s.sendall(json.dumps({"type": "prompt", "text": text}).encode())
    buf = b""
    while True:
        c = s.recv(65536)
        if not c:
            break
        buf += c
    s.close()
    return [json.loads(l) for l in buf.decode().splitlines() if l.strip()]


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=DESKTOP_DIR, **k)

    def _json(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path == "/api/agent":
            n = int(self.headers.get("content-length", 0))
            body = json.loads(self.rfile.read(n) or "{}")
            try:
                self._json({"events": agent_call(body.get("text", ""))})
            except Exception as exc:  # noqa: BLE001
                self._json({"events": [{"type": "error", "error": str(exc)}]})
        else:
            self.send_error(404)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/api/fs":
            path = os.path.expanduser(q.get("path", ["~"])[0])
            try:
                items = [{"name": e.name, "dir": e.is_dir()}
                         for e in sorted(os.scandir(path), key=lambda x: (not x.is_dir(), x.name))]
                self._json({"path": path, "items": items[:200]})
            except Exception as exc:  # noqa: BLE001
                self._json({"error": str(exc)}, 400)
        elif u.path == "/api/open":
            path = os.path.expanduser(q.get("path", [""])[0])
            subprocess.Popen(["xdg-open", path])  # real system open
            self._json({"opened": path})
        else:
            super().do_GET()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    print(f"[darcos-bridge] http://127.0.0.1:{PORT} → agent {SOCK}", flush=True)
    socketserver.TCPServer(("127.0.0.1", PORT), Handler).serve_forever()
