#!/usr/bin/env bash
# Free port 8000 and stop uvicorn for this project.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=scripts/lib/port.sh
source "$ROOT/scripts/lib/port.sh"
PORT="${PORT:-8000}"
PID_DIR="$ROOT/.pids"

echo "==> Stopping car-backend API on port $PORT..."

stop_pidfile() {
  local name="$1"
  local pidfile="$PID_DIR/$name.pid"
  [ -f "$pidfile" ] || return 0
  local pid
  pid="$(cat "$pidfile")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    sleep 1
    kill -9 "$pid" 2>/dev/null || true
    echo "    stopped $name (pid $pid from .pids/$name.pid)"
  fi
  rm -f "$pidfile"
}

stop_pidfile celery-beat
stop_pidfile celery-worker
stop_pidfile api
rm -f "$PID_DIR/api.port"

if pkill -f "uvicorn src.main:app --host 127.0.0.1 --port ${PORT}" 2>/dev/null; then
  echo "    sent stop to uvicorn on :${PORT}"
  sleep 1
fi

if command -v lsof >/dev/null 2>&1; then
  PIDS="$(lsof -t -iTCP:"${PORT}" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "${PIDS}" ]; then
    echo "    trying to kill listener(s) on :${PORT}: ${PIDS}"
    # shellcheck disable=SC2086
    kill ${PIDS} 2>/dev/null || true
    sleep 1
    # shellcheck disable=SC2086
    kill -9 ${PIDS} 2>/dev/null || true
  fi
fi

if ss -tln 2>/dev/null | grep -q ":${PORT} "; then
  echo ""
  describe_port_blocker "$PORT"
  echo ""
  exit 1
fi

echo "Port ${PORT} is free."
