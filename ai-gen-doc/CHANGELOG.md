# Changelog

All notable implementation changes are documented here.  
Current version: **0.3.2** (see [VERSION](VERSION))

---

## [0.3.2] — 2026-06-09

### Added
- **12-hour pricing cache per trim** — `PRICING_CACHE_TTL_HOURS=12` reuses Khodro45/Hamrah prices for the same trim without re-fetching
- **Trim production year in Divar search** — shared pools and API/crawl URLs include the trim's Jalali year (4-layer catalog)
- Shared pool dedup key now includes `pool_production_year` (separate pools per year)

### Changed
- Purchase create defaults `production_year_min/max` from trim year when not sent by portal
- Divar Open API finder receives `production_year` filters from vehicle context

---

## [0.3.1] — 2026-06-09

### Fixed
- **Portal detail 500** — `get_detail_for_user()` returned wrong key (`car` vs `car_model`)
- **Lazy-load on purchase lists** — use `trim.year.model` chain matching SQLAlchemy joinedload
- **Shared pool crawl** — scheduler uses `listing_mapping_id` for shared targets

### Added
- **4-layer catalog** — brand → model → year → trim with Khodro45 import script
- **Auto listing/pricing mappings** — purchase create no longer fails when mappings missing
- **Divar Open API ingest** — API-first crawl mode avoids SSR 429 errors
- **Monitoring status** — `pending` before first crawl, `active` after completed run (portal + admin results)
- Unit tests for monitoring status, crawl scheduler, listing fetch, ensure mappings

### Changed
- User portal badges reflect crawl progress, not only `is_active`
- Admin crawl results table shows `monitoring_status` with year/trim in subtitle

---

## [0.3.0] — 2026-06-05

### Added
- **Pluggable platforms** — `listing_platforms` (Divar) and `pricing_platforms` (Hamrah Mechanic, Khodro45)
- **Car model mappings** — `car_model_listing_mappings`, `car_model_pricing_mappings` (separate listing vs pricing)
- **Khodro45 pricing adapter** — HTML parser for up/mid/down prices from car price page
- **Purchase TTL** — `expires_at` default 48h (`PURCHASE_TTL_HOURS` env)
- **Configurable polling** — `poll_interval_sec` (default 300), `max_listings_per_check` (default 10)
- **Multi crawl targets** — `purchase_request_crawl_targets` junction table
- **Gateway preview** — `/g/{token}` shows opportunity page + IP view tracking; `/g/{token}/go` redirects to Divar
- **Opportunity page views** — total views + unique views per IP
- API: `/api/v1/listing-platforms`, `/api/v1/pricing-platforms`
- Landing page: pricing platform selector (Khodro45 / Hamrah Mechanic)

### Changed
- Default pricing provider: **Khodro45** (`DEFAULT_PRICING_PLATFORM=khodro45`)
- `CrawlAndEvaluateUseCase` uses `PricingServiceFactory` (not hardcoded Hamrah)
- Celery `schedule_active_crawls` schedules from active non-expired purchase requests
- `MarketReferencePrice.reference_url` replaces `hamrah_url` (alias kept)

### Env vars
- `PURCHASE_TTL_HOURS=48`
- `CRAWL_LISTINGS_PER_CHECK=10`
- `DEFAULT_PRICING_PLATFORM=khodro45`
- `KHODRO45_BASE_URL=https://khodro45.com`

---

## [0.2.0] — 2026-06-05

### Added
- **Car catalog** (`car_brands`, `car_models`) with Divar + Hamrah Mechanic mappings
- **URL builder** — generates Divar search URL and Hamrah price URL from model + user filters (year, km)
- **Purchase flow** — auto-creates crawl target when user submits purchase request
- **Starlette Admin** at `/admin/` (login: `admin` / `admin`)
- **Landing page** at `/` — HTML/CSS/JS test UI for full scenario
- **SQLite local dev** — `scripts/init_db.py`, `scripts/dev_setup.sh` (no Docker required)
- **Seed script** — Peugeot + 207 Pana (`scripts/seed_catalog.py`)
- API: `/api/v1/car-brands`, `/api/v1/car-models`, `/api/v1/preview-urls`, `/api/v1/flow/scenario`

### Changed
- `purchase_requests` now links to `car_model_id` + filter fields (`production_year_min`, `usage_max`, etc.)
- `VehicleContext` includes `divar_brand_model` for Divar API schema
- Models use portable `Uuid` + `JSON` types (SQLite + PostgreSQL)
- Default `.env` uses SQLite: `sqlite+aiosqlite:///./data/car_backend.db`

### Fixed
- Python 3.10 compatibility (`StrEnum`, `UTC` via `domain/compat.py`)
- Setup scripts use `python3` (not `python`)
- Seed/init scripts fix `sys.path` for imports

---

## [0.1.0] — 2026-06-05

### Added
- Initial **Car Deal Opportunity Detection Platform**
- Clean Architecture: domain, application, infrastructure, presentation
- **Divar crawler** — SSR `__PRELOADED_STATE__` parser, post detail API, API pagination adapter
- **Hamrah Mechanic** — `_next/data` price API, Redis cache, buildId refresh
- **Opportunity engine** — compare listing price vs `priceDown` (+ near-threshold)
- **Users**, **purchase requests**, **crawl targets** CRUD
- **SMS.ir** adapter + **gateway** click tracking (`/g/{token}`)
- **Celery** tasks: crawl scheduler, match-and-notify, Hamrah buildId refresh
- **Alembic** migrations `001`, `002`
- Unit tests (Persian numbers, opportunity scorer, Divar SSR parser, URL builder)
