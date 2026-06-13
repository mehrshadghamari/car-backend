# Implementation Documentation

**Version:** 0.3.0  
**Last updated:** 2026-06-05  
**Stack:** Python 3.10+, FastAPI, SQLAlchemy 2.0 async, SQLite (dev) / PostgreSQL (prod), Redis, Celery

---

## 1. Product Summary

The platform automatically:

1. User registers a **purchase request** (car model, optional year/km/color) — open for **48 hours** (configurable)
2. System crawls **listing platforms** (Divar) every **5 minutes**, first **10 listings** per check
3. Each listing is priced via a **pluggable pricing platform** (Khodro45 default, or Hamrah Mechanic)
4. Detects **opportunities** when listing price ≤ market floor (`price_down`)
5. Sends **SMS** with short link → **preview page** (IP view tracking) → **gateway click** → Divar listing

---

## 2. Architecture

```
src/
├── domain/              # Entities, value objects, domain services (no framework deps)
├── application/         # Use cases, ports, mappers
├── infrastructure/      # DB, Divar/Hamrah/SMS adapters, Celery
├── presentation/        # FastAPI routers, admin, schemas
└── main.py
```

**Pattern:** Clean / Hexagonal — inner layers never import FastAPI or SQLAlchemy in domain/application.

---

## 3. Database Model

| Table | Purpose |
|-------|---------|
| `car_brands` | Brand name + slug (e.g. پژو / peugeot) |
| `listing_platforms` | Listing sources (divar, …) |
| `pricing_platforms` | Price sources (khodro45, hamrah_mechanic, …) |
| `car_models` | Model metadata (threshold, pages) |
| `car_model_listing_mappings` | Car model ↔ Divar path |
| `car_model_pricing_mappings` | Car model ↔ Khodro45 slug / Hamrah IDs |
| `users` | Phone, name, source channel |
| `purchase_requests` | User interest + `expires_at`, `pricing_platform_id`, poll limits |
| `purchase_request_crawl_targets` | Many crawl targets per purchase |
| `crawl_targets` | Divar listing URL + `vehicle_context` JSON |
| `crawl_runs` | Per-crawl stats |
| `listings` | Crawled Divar posts (token, price, km, year, color) |
| `market_prices` | Pricing snapshot per listing (`reference_url`, `pricing_provider`) |
| `opportunities` | Qualified deals (discount %, score) |
| `opportunity_deliveries` | SMS sent + gateway token |
| `opportunity_page_views` | Preview page views (IP, unique flag) |
| `gateway_clicks` | Click-through tracking + time-to-click |

### Car model mappings (example: 207 Pana)

**Listing (Divar):** `car/peugeot/207i/manual-p`  
**Khodro45:** slug `cpe-peugeot-207pana-at`  
**Hamrah:** `peugeot/peugeot207/2749`

### Generated URLs

**Divar** (from user filters `year_min=1402`, `usage_max=80000`):

```
https://divar.ir/s/tehran/car/peugeot/207i/manual-p?production-year=1402-&usage=-80000
```

**Khodro45** (default pricing):

```
https://khodro45.com/carprice/cpe-peugeot-207pana-at/?year=1403&color_id=Black&kilometer=31000
```

Khodro45 urgent-sale prices come from API field `k45_price` (max / estimated_price / min), matching the website’s «قیمت فروش فوری» block. `market_price` (platform listings) is ignored. HTML parse is fallback only (page is client-rendered). Khodro45 opportunities require listing price between left and right (inclusive). Tag by nearest tier: near left → best, near middle → good, near right → normal.

**Hamrah Mechanic** (alternative):

```
https://www.hamrah-mechanic.com/carprice/peugeot/peugeot207/1403/2749/?kilometer=31000&clr=ColorWhite&bodycondition=WithoutColor
```

**Hamrah API** (internal):

```
/_next/data/{buildId}/carprice/peugeot/peugeot207/1403/2749.json?kilometer=31000&clr=ColorWhite&bodycondition=WithoutColor
```

---

## 4. Core Flows

### 4.1 Purchase flow (v0.2.0)

```
User selects car_model + year/km filters
    → build_divar_search_url()
    → create CrawlTarget (listing_url + vehicle_context from car_model)
    → create PurchaseRequest (links user, model, crawl_target)
```

### 4.2 Crawl + evaluate

```
Celery or POST /crawl-targets/{id}/crawl-now
    → Divar SSR page 1 (+ API pagination if headers allow)
    → For each listing: GET posts-v2/web/{token} (year, km, color)
    → Hamrah price fetch (cached in Redis)
    → evaluate_opportunity(listing_price vs priceDown)
    → persist Opportunity if qualified
```

### 4.3 Notify + gateway

```
Match active purchase_requests for crawl_target
    → SMS.ir with gateway URL: {APP_HOST}/g/{token}
    → User clicks → record GatewayClick → 302 to Divar listing
```

---

## 5. External Integrations

### Divar

| Method | Endpoint / approach |
|--------|---------------------|
| List (page 1) | GET listing URL → parse `window.__PRELOADED_STATE__` |
| List (page 2+) | POST `api.divar.ir/v8/web-search/...` (may return `BLOCKING_VIEW` without extra headers) |
| Detail | GET `api.divar.ir/v8/posts-v2/web/{token}` |

### Hamrah Mechanic

| Step | `_next/data/{buildId}/...` |
|------|---------------------------|
| Brands | `carprice.json` |
| Models | `carprice/{brand}.json` |
| Years | `carprice/{brand}/{model}.json` |
| Types | `carprice/{brand}/{model}/{year}.json` |
| Price | `carprice/.../{typeId}.json?kilometer&clr&bodycondition` |

`buildId` cached in Redis; daily Celery refresh.

### SMS.ir

Env: `SMS_IR_API_KEY`, `SMS_IR_LINE_NUMBER`, `SMS_IR_TEMPLATE_ID`  
Dry-run mode when API key is empty (returns `dry-run-{phone}`).

---

## 6. UI & Admin

| URL | Description |
|-----|-------------|
| `/` | Landing page — test scenario (static HTML/JS) |
| `/admin/` | Starlette Admin — `admin` / `admin` |
| `/docs` | OpenAPI (Swagger) |
| `/g/{token}` | Gateway redirect |

---

## 7. Configuration (`.env`)

| Key | Default (dev) |
|-----|----------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/car_backend.db` |
| `APP_HOST` | `http://localhost:8000` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `DEFAULT_NEAR_THRESHOLD_PCT` | `0.02` |

---

## 8. Scripts

| Script | Purpose |
|--------|---------|
| `scripts/dev_setup.sh` | Init DB + seed catalog (one command) |
| `scripts/init_db.py` | `create_all` tables (SQLite or Postgres) |
| `scripts/seed_catalog.py` | Seed Peugeot + 207 Pana |

---

## 9. Opportunity Rule

```python
is_below_floor = listing_price <= price_down
is_near_floor = listing_price <= price_down * (1 + near_threshold_pct)  # default 2%
is_opportunity = is_below_floor or is_near_floor
```

---

## 10. Tests

```bash
python3 -m pytest tests/unit -q
```

Covers: Persian number parsing, opportunity scorer, Divar SSR parser (sample HTML), URL builder, Hamrah `__NEXT_DATA__` parser.

---

## 11. Known Limitations (v0.2.0)

- Divar API pagination may block without `DIVAR_EXTRA_HEADERS_JSON` in `.env`
- Docker Hub blocked in some regions — use SQLite for local dev
- Redis optional for basic API; required for Hamrah price cache and Celery
- `alembic upgrade head` requires working PostgreSQL credentials
