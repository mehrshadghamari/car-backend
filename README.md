# Car Deal Opportunity Detection Platform

Automated vehicle opportunity detection: crawls Divar listings, compares against Khodro45 / Hamrah Mechanic market prices, matches purchase requests, and sends SMS notifications with tracked gateway links.

## Requirements

- **Local mode:** Python 3.10+, `pip`
- **Docker mode:** Docker + Docker Compose
- **Optional:** Redis (for automatic scheduled crawls; manual “Run crawl now” works without Celery)

---

## Option A — Local (SQLite, no Postgres)

Best for quick PM testing on a laptop.

### First time (install + DB + seed)

```bash
git clone <repo-url>
cd car-backend
bash scripts/local-first-run.sh
```

### Run

```bash
bash scripts/local-up.sh
```

### Stop

```bash
bash scripts/local-down.sh
```

### URLs

| Page | URL |
|------|-----|
| Register / login (users) | http://127.0.0.1:8000/ |
| Staff admin (secret UUID path) | see `.env` `PORTAL_PATH_UUID_1/2` or local-first-run output |
| Crawl results (staff) | `/portal/{uuid1}/{uuid2}/results` |

پنل کاربر فارسی (RTL) — کد آزمایشی OTP: **11111** (see `user-portal/README.md`)

### PM test flow

1. Open **Landing** → select Peugeot 207 → register phone → check **Run crawl immediately**
2. Open **Crawl results** → click **Detail** → see diagnostics & opportunities
3. Click **Run crawl now** to re-run without waiting for scheduler
4. SMS links open `/g/{token}` → redirect to Divar

Logs: `.logs/api.log`, `.logs/celery-worker.log`, `.logs/celery-beat.log`

---

## Option B — Docker (Postgres + Redis + Celery)

Full stack, closer to production.

### First time (build + DB + seed)

```bash
git clone <repo-url>
cd car-backend
bash scripts/docker-first-run.sh
```

### Run

```bash
bash scripts/docker-up.sh
```

### Stop

```bash
bash scripts/docker-down.sh
```

Wipe database and start fresh:

```bash
RESET=1 bash scripts/docker-down.sh
bash scripts/docker-first-run.sh
bash scripts/docker-up.sh
```

### URLs

Same as local — http://127.0.0.1:8000/

View logs:

```bash
docker compose logs -f api
docker compose logs -f celery-worker celery-beat
```

---

## Script reference

| Script | Purpose |
|--------|---------|
| `scripts/local-first-run.sh` | Local: install deps, create DB, migrate, **seed catalog** |
| `scripts/local-up.sh` | Local: start API + Celery (if Redis available) |
| `scripts/local-down.sh` | Local: stop API + Celery |
| `scripts/docker-first-run.sh` | Docker: build, init Postgres, migrate, **seed catalog** |
| `scripts/docker-up.sh` | Docker: `docker compose up -d` |
| `scripts/docker-down.sh` | Docker: `docker compose down` |

---

## Configuration

| File | Use |
|------|-----|
| `.env.example` | Local SQLite (copied by `local-first-run.sh`) |
| `.env.docker.example` | Docker Postgres/Redis hostnames (copied by `docker-first-run.sh`) |

SMS is dry-run when `SMS_IR_API_KEY` is empty.

---

## Documentation

Full AI-generated docs: **[ai-gen-doc/](ai-gen-doc/)**

## Architecture

Clean/Hexagonal Architecture — FastAPI, SQLAlchemy 2.0 async, PostgreSQL/SQLite, Redis, Celery.
