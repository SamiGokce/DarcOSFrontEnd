#!/usr/bin/env bash
# DarcOS launcher
#   ./run.sh          Production: build frontend, Django serves app + API
#   ./run.sh dev      Development: Django API + Vite dev server (proxies /api)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
DJANGO_HOST="${DJANGO_HOST:-127.0.0.1}"
DJANGO_PORT="${DJANGO_PORT:-8000}"
VITE_PORT="${VITE_PORT:-5173}"

ensure_venv() {
  if [[ ! -d "$BACKEND/.venv" ]]; then
    python3 -m venv "$BACKEND/.venv"
    "$BACKEND/.venv/bin/pip" install -r "$BACKEND/requirements.txt"
  fi
}

ensure_npm() {
  if [[ ! -d "$FRONTEND/node_modules" ]]; then
    (cd "$FRONTEND" && npm install)
  fi
}

run_migrate() {
  ensure_venv
  "$BACKEND/.venv/bin/python" "$BACKEND/manage.py" migrate --noinput
}

run_production() {
  echo "==> DarcOS production (Django on ${DJANGO_HOST}:${DJANGO_PORT})"
  ensure_npm
  (cd "$FRONTEND" && npm run build)

  ensure_venv
  run_migrate

  export DJANGO_DEBUG="${DJANGO_DEBUG:-false}"
  cd "$BACKEND"
  exec .venv/bin/python manage.py runserver "${DJANGO_HOST}:${DJANGO_PORT}" "$@"
}

run_development() {
  echo "==> DarcOS development"
  echo "    Vite:   http://${DJANGO_HOST}:${VITE_PORT}"
  echo "    Django: http://${DJANGO_HOST}:${DJANGO_PORT} (API only; proxied at /api)"
  ensure_npm
  ensure_venv
  run_migrate

  API_TARGET="http://${DJANGO_HOST}:${DJANGO_PORT}"
  cd "$BACKEND"
  .venv/bin/python manage.py runserver "${DJANGO_HOST}:${DJANGO_PORT}" &
  DJANGO_PID=$!

  cleanup() {
    kill "$DJANGO_PID" 2>/dev/null || true
  }
  trap cleanup EXIT INT TERM

  cd "$FRONTEND"
  export VITE_API_PROXY_TARGET="$API_TARGET"
  export VITE_PORT="$VITE_PORT"
  npm run dev -- --host "$DJANGO_HOST" --port "$VITE_PORT"
}

case "${1:-prod}" in
  dev|development)
    shift
    run_development "$@"
    ;;
  prod|production|"")
    [[ "${1:-}" == "prod" || "${1:-}" == "production" ]] && shift
    run_production "$@"
    ;;
  -h|--help|help)
    cat <<EOF
Usage: ./run.sh [MODE] [runserver args...]

Modes:
  prod, production   (default) Build frontend and run Django
  dev, development  Vite dev server with /api proxied to Django

Environment:
  DJANGO_HOST   (default: 127.0.0.1)
  DJANGO_PORT   (default: 8000)
  VITE_PORT     (default: 5173)
  DJANGO_DEBUG  (default: false in production)
EOF
    ;;
  *)
    echo "Unknown mode: $1 (use: prod | dev | help)" >&2
    exit 1
    ;;
esac
