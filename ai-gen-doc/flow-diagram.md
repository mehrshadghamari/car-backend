# End-to-End Flow

**Version:** 0.2.0

---

## Operator setup

```mermaid
flowchart LR
  A[Admin: Car Brand] --> B[Admin: Car Model]
  B --> C[divar_path + hamrah mapping]
```

Example model row:
- Divar: `car/peugeot/207i/manual-p`
- Hamrah: `peugeot/peugeot207/2749`

---

## User purchase request (v0.2.0)

```mermaid
flowchart TB
  U[User + filters] --> M[Car Model from DB]
  M --> D[Build Divar URL]
  M --> H[Build Hamrah preview URL]
  D --> CT[Create Crawl Target]
  U --> PR[Create Purchase Request]
  CT --> PR
```

---

## Crawl and opportunity detection

```mermaid
flowchart TB
  CT[Crawl Target] --> DV[Divar: list + detail]
  DV --> LS[Listing: price km year]
  LS --> HM[Hamrah: priceDown priceUp]
  HM --> EV{price <= floor?}
  EV -->|yes| OP[Opportunity]
  EV -->|no| SKIP[Skip]
```

---

## Notification and gateway

```mermaid
flowchart LR
  OP[Opportunity] --> MATCH[Match Purchase Requests]
  MATCH --> SMS[SMS.ir + gateway link]
  SMS --> USER[User phone]
  USER --> GW["GET /g/token"]
  GW --> CLICK[Record click]
  GW --> DIVAR[Redirect Divar listing]
```

---

## Landing page test scenario

1. Select brand → model  
2. Set year min + max km  
3. **Preview URLs** → see Divar + Hamrah links  
4. **Run scenario** → creates user + purchase request + crawl target  
5. Optional: **run crawl** → check opportunities
