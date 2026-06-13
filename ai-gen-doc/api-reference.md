# API Reference

**Version:** 0.2.0  
Base URL: `http://localhost:8000/api/v1`

---

## Users

| Method | Path | Description |
|--------|------|-------------|
| POST | `/users` | Create user |
| GET | `/users` | List users |
| GET | `/users/{id}` | Get user |
| PATCH | `/users/{id}` | Update user |
| DELETE | `/users/{id}` | Delete user |

## Car catalog

| Method | Path | Description |
|--------|------|-------------|
| GET | `/car-brands` | List brands (`?active_only=true`) |
| GET | `/car-models` | List models (`?brand_id=`) |
| POST | `/preview-urls` | Preview Divar + Hamrah URLs from model + filters |

### Preview URLs body

```json
{
  "car_model_id": "uuid",
  "city": "tehran",
  "production_year_min": 1402,
  "usage_max": 80000,
  "sample_production_year": 1403,
  "sample_kilometer": 31000
}
```

## Purchase flow

| Method | Path | Description |
|--------|------|-------------|
| POST | `/users/{user_id}/purchase-requests` | Create request + auto crawl target |
| POST | `/users/{user_id}/purchase-flow` | Same as above (alias) |
| GET | `/users/{user_id}/purchase-requests` | List user requests |
| PATCH | `/purchase-requests/{id}` | Update active/threshold |

### Purchase request body

```json
{
  "car_model_id": "uuid",
  "city": "tehran",
  "production_year_min": 1402,
  "production_year_max": null,
  "usage_min": null,
  "usage_max": 80000
}
```

## Scenario (test)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/flow/scenario` | Create user + purchase flow + optional crawl |

```json
{
  "car_model_id": "uuid",
  "phone": "09121234567",
  "production_year_min": 1402,
  "usage_max": 80000,
  "run_crawl": true
}
```

## Crawl targets

| Method | Path | Description |
|--------|------|-------------|
| POST | `/crawl-targets` | Create crawl target |
| GET | `/crawl-targets` | List |
| GET | `/crawl-targets/{id}` | Get |
| PATCH | `/crawl-targets/{id}` | Update |
| DELETE | `/crawl-targets/{id}` | Delete |
| POST | `/crawl-targets/{id}/crawl-now` | Trigger crawl (async) |
| GET | `/crawl-targets/{id}/runs` | Crawl run history |

## Opportunities & metrics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/opportunities` | List (`?crawl_target_id=&status=`) |
| GET | `/metrics/summary` | Detected, delivered, click rate |

## Gateway (no prefix)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/g/{token}` | Track click → redirect to Divar |

## Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | `{"status": "ok"}` |
