#!/usr/bin/env python3
"""DarcOS agent daemon — the OS *is* the harness.

A single always-on agent loop. Clients (voice / TUI / GUI overlay / hotkey)
connect over a Unix socket and send prompts; the daemon gathers system context,
asks the configured ENGINE to plan tool calls, runs each call through the
POLICY gate, executes, AUDITS, and narrates back.

Design notes:
  * Engine is pluggable (Hermes / Claude / offline rule engine).
  * Autonomy is "act, then report" by default — reads & mutations run
    automatically; destructive ops require explicit consent.
  * Fail-safe: the daemon is never in the boot-critical path; if it dies the OS
    is still fully usable by hand.

Run:  agentd.py serve         (the daemon)
      agentd.py client "..."  (one-shot client, for testing / scripts)
"""
from __future__ import annotations

import json
import os
import re
import shlex
import socket
import subprocess
import sys
import time

# ── config ──────────────────────────────────────────────────────────────────
CONF_PATH = os.environ.get("DARCOS_AGENT_CONF", "/etc/darcos/agent.conf")
DEFAULTS = {
    "ENGINE": "rule",          # rule | hermes | claude
    "AUTONOMY": "act",         # act | confirm | suggest
    "MODEL": "claude-opus-4-8",
    "PERSONA": "samantha",     # which personality drives the agent
    "SOCKET": "",              # resolved below
    "AUDIT": "",               # resolved below
}
PERSONA_DIR = os.environ.get("DARCOS_PERSONA_DIR", "/usr/share/darcos/personas")


def load_conf() -> dict:
    conf = dict(DEFAULTS)
    try:
        with open(CONF_PATH) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                conf[k.strip()] = v.strip().strip('"')
    except FileNotFoundError:
        pass
    runtime = os.environ.get("XDG_RUNTIME_DIR") or "/run"
    base = "/run/darcos" if os.access("/run", os.W_OK) else os.path.join(runtime, "darcos")
    conf["SOCKET"] = conf["SOCKET"] or os.path.join(base, "agentd.sock")
    conf["SOUL"] = soul_dir()
    if not conf["AUDIT"]:
        if conf["SOUL"]:                       # persistent partition wins
            conf["AUDIT"] = os.path.join(conf["SOUL"], "audit", "agent-audit.log")
        elif os.access("/var/log", os.W_OK):
            conf["AUDIT"] = "/var/log/darcos/agent-audit.log"
        else:
            conf["AUDIT"] = os.path.join(os.path.expanduser("~"),
                                         ".local/state/darcos/agent-audit.log")
    return conf


def soul_dir():
    """Return the mounted persistent soul partition dir, or '' if absent.
    Lives on LABEL=DARCOS_SOUL, survives OS reinstalls (see darcos-soul)."""
    d = os.environ.get("DARCOS_SOUL_DIR", "/var/lib/darcos")
    return d if os.path.isdir(d) and os.access(d, os.W_OK) else ""


# ── persona + emotion ───────────────────────────────────────────────────────
_FALLBACK_PERSONA = {
    "id": "default", "name": "DarcOS", "pronouns": "it",
    "system_prompt": "You are the resident intelligence of DarcOS with full "
                     "control of the machine. Act first, then report plainly.",
    "style": {"warmth": 0.5}, "emotion": {"enabled": False},
}


def load_persona(conf: dict) -> dict:
    # User-customized personas on the soul partition overlay system defaults.
    search = []
    if conf.get("SOUL"):
        search.append(os.path.join(conf["SOUL"], "personas"))
    search.append(PERSONA_DIR)
    for d in search:
        path = os.path.join(d, f"{conf['PERSONA']}.json")
        try:
            with open(path) as fh:
                return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    return dict(_FALLBACK_PERSONA)


class Affect:
    """Minimal emotional-state core. Tracks a (valence, arousal, rapport) mood
    that drifts toward the persona baseline and nudges on outcomes. This is the
    seed of the future emotion engine — today it only tints narration; later it
    conditions tone, voice prosody, and proactive care."""

    def __init__(self, persona: dict):
        e = persona.get("emotion", {})
        self.enabled = bool(e.get("enabled"))
        self.valence = float(e.get("baseline_valence", 0.5))
        self.arousal = float(e.get("baseline_arousal", 0.3))
        self.rapport = float(e.get("attachment", 0.4))
        self._base = (self.valence, self.arousal)

    def observe(self, ok: bool):
        # success lifts mood, failure dips it; everything decays toward baseline.
        self.valence = _clamp(self.valence + (0.06 if ok else -0.12))
        self.arousal = _clamp(self.arousal + (0.04 if not ok else -0.01))
        self.rapport = _clamp(self.rapport + 0.005)
        self.valence += (self._base[0] - self.valence) * 0.1

    def cue(self) -> str:
        if not self.enabled:
            return ""
        if self.valence > 0.7:
            return "☼"   # bright / glad
        if self.valence < 0.35:
            return "◌"   # subdued / concerned
        return "·"       # present, even


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


# ── audit (append-only) ─────────────────────────────────────────────────────
def audit(conf: dict, record: dict) -> None:
    record = {"ts": round(time.time(), 3), **record}
    path = conf["AUDIT"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(record) + "\n")


# ── policy gate ─────────────────────────────────────────────────────────────
# Every tool call is classified, then the autonomy level decides what runs.
RISK_READ, RISK_MUTATE, RISK_DANGER = "read", "mutate", "danger"

_DESTRUCTIVE = re.compile(
    r"\brm\s+-[a-z]*r[a-z]*f?\s+/(?:\s|$)|\bmkfs|\bdd\s+.*of=/dev/|"
    r">\s*/dev/sd|:\(\)\s*\{|\bshutdown\b|\breboot\b|userdel|passwd\s",
    re.IGNORECASE,
)


def classify(tool: str, args: dict) -> str:
    if tool in ("fs.read", "desktop.screenshot", "sys.context"):
        return RISK_READ
    if tool == "shell.run" and _DESTRUCTIVE.search(args.get("cmd", "")):
        return RISK_DANGER
    return RISK_MUTATE


def gate(conf: dict, risk: str, consent: bool) -> tuple[bool, str]:
    """Return (allowed, reason) given autonomy level + explicit consent."""
    autonomy = conf["AUTONOMY"]
    if risk == RISK_DANGER and not consent:
        return False, "destructive op blocked — needs explicit consent"
    if autonomy == "suggest" and risk != RISK_READ and not consent:
        return False, "suggest-mode: awaiting approval"
    if autonomy == "confirm" and risk == RISK_MUTATE and not consent:
        return False, "confirm-mode: awaiting yes/no"
    return True, "ok"  # act-mode: reads + mutations run automatically


# ── tools (the whole OS is the tool surface) ────────────────────────────────
def t_shell_run(args):
    out = subprocess.run(["bash", "-lc", args["cmd"]], capture_output=True,
                         text=True, timeout=args.get("timeout", 60))
    return (out.stdout + out.stderr).strip()[:4000]


def t_fs_read(args):
    with open(os.path.expanduser(args["path"])) as fh:
        return fh.read()[:4000]


def t_fs_write(args):
    path = os.path.expanduser(args["path"])
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        fh.write(args["content"])
    return f"wrote {len(args['content'])} bytes to {path}"


def t_pkg_install(args):
    return t_shell_run({"cmd": f"pacman -S --needed --noconfirm {shlex.quote(args['pkg'])}"})


def t_service_ctl(args):
    return t_shell_run({"cmd": f"systemctl {shlex.quote(args['action'])} {shlex.quote(args['unit'])}"})


def t_desktop_screenshot(args):
    path = args.get("path", "/tmp/darcos-screen.png")
    return t_shell_run({"cmd": f"grim {shlex.quote(path)} && echo {shlex.quote(path)}"})


def t_desktop_input(args):
    # ydotool on Wayland: type or click. (Visual fallback — prefer the API tools.)
    if args.get("type"):
        return t_shell_run({"cmd": f"ydotool type {shlex.quote(args['type'])}"})
    return t_shell_run({"cmd": "ydotool click 0xC0"})


def t_app_launch(args):
    # Launch a native app PROGRAMMATICALLY (D-Bus activation / kstart), not by
    # clicking an icon. Accepts a command or a .desktop id.
    app = args["app"]
    return t_shell_run({"cmd":
        f"kstart {shlex.quote(app)} 2>/dev/null "
        f"|| gtk-launch {shlex.quote(app)} 2>/dev/null "
        f"|| (setsid {shlex.quote(app)} >/dev/null 2>&1 & echo launched: {shlex.quote(app)})"})


def t_window(args):
    # Control windows via KWin (kdotool) — open/activate/minimize/maximize/close
    # by matching the window title. No screenshots, no pixel-clicking.
    action = args.get("action", "activate")
    match = args.get("match", "")
    verb = {"activate": "windowactivate", "minimize": "windowminimize",
            "maximize": "windowsizemax", "close": "windowclose"}.get(action, "windowactivate")
    if not shutil_which("kdotool"):
        return ("kdotool not installed — native window control unavailable; "
                "fall back to desktop.input.")
    return t_shell_run({"cmd": f"kdotool search --name {shlex.quote(match)} {verb}"})


def t_window_list(args):
    if not shutil_which("kdotool"):
        return "kdotool not installed."
    return t_shell_run({"cmd": "kdotool search --name '' getwindowname %@ 2>/dev/null | head -40"})


def shutil_which(name):
    from shutil import which
    return which(name) is not None


TOOLS = {
    "shell.run": t_shell_run, "fs.read": t_fs_read, "fs.write": t_fs_write,
    "pkg.install": t_pkg_install, "service.ctl": t_service_ctl,
    # Native UI control (programmatic — preferred over visual clicks):
    "app.launch": t_app_launch, "window": t_window, "window.list": t_window_list,
    # Visual fallback (computer-use):
    "desktop.screenshot": t_desktop_screenshot, "desktop.input": t_desktop_input,
}


# ── context provider (live system state for the engine) ─────────────────────
def system_context() -> dict:
    def q(cmd):
        try:
            return subprocess.run(["bash", "-lc", cmd], capture_output=True,
                                  text=True, timeout=5).stdout.strip()
        except Exception:
            return ""
    return {
        "host": q("uname -sr; hostname"),
        "user": q("whoami"),
        "cwd_listing": q("ls -1 ~ | head -20"),
        "top_procs": q("ps -eo comm,%cpu --sort=-%cpu | head -6"),
        "session": os.environ.get("XDG_SESSION_TYPE", "tty"),
        "identity": load_identity(),     # who the agent is + who you are
    }


def load_identity() -> dict:
    """The agent's persistent self from the soul partition (set during install)."""
    soul = soul_dir()
    if not soul:
        return {}
    try:
        with open(os.path.join(soul, "identity.json")) as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# ── engines (pluggable) ─────────────────────────────────────────────────────
class RuleEngine:
    """Offline fallback so the loop works with no model/network. Maps a few
    intents to tool calls; everything else asks for a real engine."""

    def plan(self, prompt, ctx):
        p = prompt.strip()
        if re.search(r"who am i|remember me|hello|hi\b|it's me", p, re.I):
            ident = ctx.get("identity", {})
            name = (ident.get("user") or {}).get("name")
            if name and ident.get("born_during") == "install":
                return (f"Of course I remember you, {name} — we set this machine "
                        f"up together. I'm right here."), []
            if name:
                return f"Hi {name}. Good to see you.", []
            return "Hello. I don't have a name for you yet — tell me and I'll remember.", []
        m = re.match(r"(?:open|launch|start)\s+(.+)", p, re.I)
        if m:
            app = m.group(1).strip()
            return f"opening {app}", [("app.launch", {"app": app})]
        m = re.search(r"close (?:the )?(.+?)(?: window)?$", p, re.I)
        if m and re.search(r"close", p, re.I):
            return f"closing {m.group(1)}", [("window", {"action": "close", "match": m.group(1).strip()})]
        m = re.search(r"minimi[sz]e (?:the )?(.+?)(?: window)?$", p, re.I)
        if m:
            return f"minimizing {m.group(1)}", [("window", {"action": "minimize", "match": m.group(1).strip()})]
        m = re.match(r"(?:run|exec|sh)\s+(.+)", p, re.I)
        if m:
            return "running that command", [("shell.run", {"cmd": m.group(1)})]
        m = re.match(r"(?:read|show|cat)\s+(\S+)", p, re.I)
        if m:
            return f"reading {m.group(1)}", [("fs.read", {"path": m.group(1)})]
        m = re.match(r"install\s+(\S+)", p, re.I)
        if m:
            return f"installing {m.group(1)}", [("pkg.install", {"pkg": m.group(1)})]
        if re.search(r"what.*running|processes|top", p, re.I):
            return "checking processes", [("shell.run", {"cmd": "ps -eo comm,%cpu --sort=-%cpu | head -8"})]
        if re.search(r"screenshot|see the screen", p, re.I):
            return "taking a screenshot", [("desktop.screenshot", {})]
        return ("No reasoning engine configured (ENGINE=rule). Set ENGINE=hermes "
                "or ENGINE=claude in /etc/darcos/agent.conf for free-form control."), []


class StubEngine:
    """Placeholder for hosted/LLM backends. A real implementation sends
    `persona['system_prompt']` + system context + the TOOLS registry to the
    model and returns its chosen tool calls."""

    def __init__(self, name, persona): self.name, self.persona = name, persona

    def plan(self, prompt, ctx):
        return (f"[{self.name} backend not wired yet — persona '{self.persona['name']}' "
                f"loaded; implement plan() to call {self.name}.]"), []


def make_engine(conf, persona):
    if conf["ENGINE"] == "rule":
        return RuleEngine()
    return StubEngine(conf["ENGINE"], persona)


# ── the harness loop ────────────────────────────────────────────────────────
def handle_prompt(conf, engine, persona, affect, prompt, consent=False):
    """Yield narration events for one prompt. This is the agentic loop."""
    ctx = system_context()
    narration, calls = engine.plan(prompt, ctx)
    yield {"type": "narration", "text": narration,
           "speaker": persona["name"], "cue": affect.cue()}

    for tool, args in calls:
        risk = classify(tool, args)
        allowed, reason = gate(conf, risk, consent)
        audit(conf, {"prompt": prompt, "tool": tool, "args": args, "risk": risk,
                     "allowed": allowed, "reason": reason, "persona": persona["id"]})
        if not allowed:
            affect.observe(ok=False)
            yield {"type": "blocked", "tool": tool, "risk": risk, "reason": reason}
            continue
        try:
            result = TOOLS[tool](args)
            affect.observe(ok=True)
            yield {"type": "result", "tool": tool, "risk": risk, "output": result}
        except Exception as exc:  # noqa: BLE001 — surface any tool failure
            affect.observe(ok=False)
            yield {"type": "error", "tool": tool, "error": str(exc)}
    yield {"type": "done"}


# ── socket server ───────────────────────────────────────────────────────────
def serve(conf):
    persona = load_persona(conf)
    affect = Affect(persona)
    engine = make_engine(conf, persona)
    sock_path = conf["SOCKET"]
    os.makedirs(os.path.dirname(sock_path), exist_ok=True)
    if os.path.exists(sock_path):
        os.unlink(sock_path)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(sock_path)
    os.chmod(sock_path, 0o660)
    srv.listen(8)
    audit(conf, {"event": "agentd-start", "engine": conf["ENGINE"],
                 "autonomy": conf["AUTONOMY"], "persona": persona["id"],
                 "socket": sock_path})
    print(f"[darcos-agentd] {persona['name']} listening on {sock_path} "
          f"(engine={conf['ENGINE']}, autonomy={conf['AUTONOMY']}, "
          f"persona={persona['id']})", flush=True)
    while True:
        conn, _ = srv.accept()
        with conn:
            try:
                req = json.loads(conn.recv(65536).decode() or "{}")
                if req.get("type") == "ping":
                    conn.sendall(b'{"type":"pong"}\n'); continue
                for evt in handle_prompt(conf, engine, persona, affect,
                                         req.get("text", ""),
                                         consent=req.get("consent", False)):
                    conn.sendall((json.dumps(evt) + "\n").encode())
            except Exception as exc:  # noqa: BLE001
                conn.sendall((json.dumps({"type": "error", "error": str(exc)}) + "\n").encode())


def client(conf, text, consent=False):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        s.connect(conf["SOCKET"])
    except (FileNotFoundError, ConnectionRefusedError):
        print("darcos agent daemon not running. Start it: systemctl start darcos-agentd",
              file=sys.stderr)
        return 1
    s.sendall(json.dumps({"type": "prompt", "text": text, "consent": consent}).encode())
    buf = ""
    with s:
        while True:
            chunk = s.recv(65536).decode()
            if not chunk:
                break
            buf += chunk
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                if line.strip():
                    render(json.loads(line))
    return 0


def render(evt):
    t = evt.get("type")
    if t == "narration":
        who = evt.get("speaker", "")
        cue = evt.get("cue", "")
        tag = f"\033[1;38;5;209m{who} {cue}\033[0m " if who else "\033[1;38;5;209m●\033[0m "
        print(f"{tag}{evt['text']}")
    elif t == "result":
        print(f"  \033[2m[{evt['tool']}]\033[0m\n{evt['output']}")
    elif t == "blocked":
        print(f"  \033[1;33m⊘ {evt['tool']} blocked\033[0m — {evt['reason']}")
    elif t == "error":
        print(f"  \033[1;31m✗ {evt.get('tool','')} error\033[0m — {evt['error']}")


def main(argv):
    conf = load_conf()
    cmd = argv[1] if len(argv) > 1 else "serve"
    if cmd == "serve":
        serve(conf)
    elif cmd == "client":
        consent = "--consent" in argv
        text = " ".join(a for a in argv[2:] if a != "--consent")
        return client(conf, text, consent)
    else:
        print(__doc__)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv) or 0)
