# Setup Guide

**Version:** 0.2.0

---

## Quick start (SQLite — recommended for Iran / no Docker)

```bash
cd car-backend
bash scripts/dev_setup.sh
uvicorn src.main:app --reload
```

Uses `python3` and creates `./data/car_backend.db`.

| Page | URL |
|------|-----|
| Landing | http://127.0.0.1:8000/ |
| Admin | http://127.0.0.1:8000/admin/ (`admin` / `admin`) |
| API docs | http://127.0.0.1:8000/docs |

---

## Manual steps

```bash
cp .env.example .env
pip install -e ".[dev]"
python3 scripts/init_db.py
python3 scripts/seed_catalog.py
uvicorn src.main:app --reload
```

---

## PostgreSQL (production)

1. Create database and user matching `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://car:car@localhost:5432/car_backend
   ```

2. Start services (if Docker works):
   ```bash
   docker compose up -d postgres redis
   ```

3. Migrate:
   ```bash
   alembic upgrade head
   python3 scripts/seed_catalog.py
   ```

---

## Celery (background crawl)

Requires Redis:

```bash
celery -A src.infrastructure.tasks.celery_app worker --loglevel=info
celery -A src.infrastructure.tasks.celery_app beat --loglevel=info
```

---

## Common errors

| Error | Fix |
|-------|-----|
| `password authentication failed for user "car"` | Use SQLite in `.env` or fix Postgres credentials |
| `command not found: python` | Use `python3` |
| Docker `403 Forbidden` | Use SQLite; Docker Hub blocked in some regions |
| Empty car models on landing | Run `python3 scripts/seed_catalog.py` |
