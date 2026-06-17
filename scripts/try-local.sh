#!/usr/bin/env bash
#
# Try the DarcOS desktop on THIS machine — no ISO, no VM. Runs the real agent
# daemon + the bridge as your user and opens the Windows-12 desktop in your
# browser. The agent actually works (acts as your user, policy-gated). Ctrl-C
# to stop everything.
#
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AF="${ROOT}/profiles/darcos/airootfs"
LIB="${AF}/usr/local/lib/darcos"
T="/tmp/darcos-try"
PORT="${DARCOS_BRIDGE_PORT:-8787}"

mkdir -p "${T}/run/darcos" "${T}/soul"
export XDG_RUNTIME_DIR="${T}/run"
export DARCOS_AGENT_CONF="${T}/agent.conf"
export DARCOS_PERSONA_DIR="${AF}/usr/share/darcos/personas"
export DARCOS_SOUL_DIR="${T}/soul"
printf 'ENGINE="rule"\nAUTONOMY="act"\nPERSONA="samantha"\n' > "${DARCOS_AGENT_CONF}"

SOCK="${T}/run/darcos/agentd.sock"

echo "[try-local] starting the DarcOS agent..."
python3 "${LIB}/agentd.py" serve >"${T}/agent.log" 2>&1 &
AGENT=$!
sleep 1

echo "[try-local] starting the desktop bridge on http://127.0.0.1:${PORT} ..."
DARCOS_AGENT_SOCK="${SOCK}" DARCOS_DESKTOP_DIR="${AF}/usr/share/darcos/desktop" \
    DARCOS_BRIDGE_PORT="${PORT}" python3 "${LIB}/bridge.py" >"${T}/bridge.log" 2>&1 &
BRIDGE=$!
sleep 1

cleanup(){ echo; echo "[try-local] stopping..."; kill "${AGENT}" "${BRIDGE}" 2>/dev/null; }
trap cleanup EXIT INT TERM

URL="http://127.0.0.1:${PORT}/index.html?theme=warm"
echo "[try-local] opening ${URL}"
( xdg-open "${URL}" >/dev/null 2>&1 || echo "Open this in your browser: ${URL}" ) &

cat <<EOF

  DarcOS desktop is live at:  ${URL}
  - Click the white agent in the taskbar → chat is REAL (runs via the agent).
  - Try:  "run echo hello"   or   "what is running"
  Press Ctrl-C here to stop.

EOF
wait "${BRIDGE}"
