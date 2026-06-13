#!/usr/bin/env bash
# Start full Docker stack (API + Celery + Postgres + Redis).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  echo "Missing .env — run: bash scripts/docker-first-run.sh"
  exit 1
fi

echo "==> Starting Docker stack..."
docker compose up -d

echo ""
echo "Docker stack is up."
echo "  Landing:       http://127.0.0.1:8000/"
echo "  Crawl results: http://127.0.0.1:8000/results"
echo "  Admin:         http://127.0.0.1:8000/admin/  (admin / admin)"
echo "  API docs:      http://127.0.0.1:8000/docs"
echo ""
echo "Logs:  docker compose logs -f api"
echo "Stop:  bash scripts/docker-down.sh"
