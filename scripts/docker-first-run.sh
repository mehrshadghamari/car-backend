#!/usr/bin/env bash
# First-time Docker setup: build images, init Postgres, migrate, seed catalog.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Car Backend — Docker first-run setup"

if [ ! -f .env ]; then
  cp .env.docker.example .env
  echo "    Created .env from .env.docker.example"
else
  echo "    Using existing .env (ensure DATABASE_URL uses host 'postgres' and Redis uses 'redis')"
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker + Docker Compose plugin."
  exit 1
fi

echo "==> Building images..."
docker compose build

echo "==> Starting Postgres + Redis..."
docker compose up -d postgres redis

echo "==> Waiting for Postgres..."
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U car -d car_backend >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "==> Initializing database..."
docker compose run --rm api python3 scripts/init_db.py

echo "==> Applying schema migrations..."
docker compose run --rm api python3 scripts/migrate_db.py

echo "==> Seeding car catalog..."
docker compose run --rm api python3 scripts/seed_catalog.py

echo "==> Seeding SMS providers and templates..."
docker compose run --rm api bash scripts/run_seed_sms_config.sh

echo ""
echo "Docker first-run complete."
echo ""
echo "Next:"
echo "  bash scripts/docker-up.sh"
echo "  bash scripts/docker-down.sh"
