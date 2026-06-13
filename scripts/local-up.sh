#!/usr/bin/env bash
# Start API locally (and Celery worker+beat when Redis is available).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=scripts/lib/port.sh
source "$ROOT/scripts/lib/port.sh"
PYTHON="${PYTHON:-python3}"
PID_DIR="$ROOT/.pids"
mkdir -p "$PID_DIR" data
LOG_DIR="$ROOT/.logs"
mkdir -p "$LOG_DIR"

if [ ! -f .env ]; then
  echo "Missing .env — run: bash scripts/local-first-run.sh"
  exit 1
fi

if [ ! -f data/car_backend.db ]; then
  echo "Database not found — run: bash scripts/local-first-run.sh"
  exit 1
fi

REQUESTED_PORT="${PORT:-8000}"
if ss -tln 2>/dev/null | grep -q ":${REQUESTED_PORT} "; then
  echo "==> Port ${REQUESTED_PORT} is in use — trying to stop old API..."
  PORT="$REQUESTED_PORT" bash "$ROOT/scripts/kill-api.sh" || true
fi

if [ -n "${PORT:-}" ]; then
  API_PORT="$PORT"
else
  API_PORT="$(find_free_port 8000 8001 8002 8003 8004 8005)" || {
    echo "No free port between 8000–8005."
    exit 1
  }
fi

if [ "$API_PORT" != "$REQUESTED_PORT" ] && ss -tln 2>/dev/null | grep -q ":${REQUESTED_PORT} "; then
  echo ""
  describe_port_blocker "$REQUESTED_PORT"
  echo ""
  echo "==> Starting API on port ${API_PORT} instead."
  echo ""
fi

echo "$API_PORT" >"$PID_DIR/api.port"

redis_ok=false
if command -v redis-cli >/dev/null 2>&1 && redis-cli ping >/dev/null 2>&1; then
  redis_ok=true
elif docker compose ps redis 2>/dev/null | grep -q "running\|Up"; then
  redis_ok=true
else
  echo "==> Redis not detected — starting Redis via Docker (optional)..."
  if command -v docker >/dev/null 2>&1; then
    docker compose up -d redis 2>/dev/null || true
    sleep 2
    if docker compose exec -T redis redis-cli ping >/dev/null 2>&1; then
      redis_ok=true
    fi
  fi
fi

start_bg() {
  local name="$1"
  shift
  local pidfile="$PID_DIR/$name.pid"
  if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "    restarting $name (pid $(cat "$pidfile"))"
    kill "$(cat "$pidfile")" 2>/dev/null || true
    sleep 1
    kill -9 "$(cat "$pidfile")" 2>/dev/null || true
    rm -f "$pidfile"
  fi
  PYTHONPATH="$ROOT" nohup "$@" >"$LOG_DIR/$name.log" 2>&1 &
  echo $! >"$pidfile"
  echo "    started $name (pid $(cat "$pidfile"), log: .logs/$name.log)"
}

echo "==> Starting local services on port ${API_PORT}..."

start_bg api $PYTHON -m uvicorn src.main:app --host 127.0.0.1 --port "$API_PORT" --reload

if $redis_ok; then
  start_bg celery-worker $PYTHON -m celery -A src.infrastructure.tasks.celery_app worker --loglevel=info
  start_bg celery-beat $PYTHON -m celery -A src.infrastructure.tasks.celery_app beat --loglevel=info
else
  echo "    Celery skipped (no Redis). Manual crawl still works: /results → Run crawl now"
fi

sleep 2
if curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null; then
  echo ""
  echo "Local stack is up."
else
  echo ""
  echo "API started but /health check failed — see .logs/api.log"
fi

echo "  Landing:       http://127.0.0.1:${API_PORT}/"
echo "  Crawl results: http://127.0.0.1:${API_PORT}/results"
echo "  Trim mapping:  http://127.0.0.1:${API_PORT}/trim-mapping"
echo "  Admin:         http://127.0.0.1:${API_PORT}/admin/  (admin / admin)"
echo ""
echo "Stop: bash scripts/local-down.sh"
