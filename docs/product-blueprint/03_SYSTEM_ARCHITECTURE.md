# 03  -  System Architecture (Cloud Web SaaS)

**Pattern:** Modular monolith + independently scalable workers.  
**Primary interface:** Hosted browser application.  
**Not:** Tauri / Electron / desktop-primary DB.

## 1. Context

```
 Customer browsers
        |
     CDN + WAF + TLS
        |
  React/TS SPA (static)
        |
  Application API (FastAPI modular monolith)
        |-- PostgreSQL (shared market + tenant data)
        |-- Redis (cache, rate limits, queue coordination)
        |-- Object storage (raw EOD, CA archives, attachments, exports)
        |-- Workers (ingest, validate, CA, candles, scan, backtest, alerts, maintenance)
        |
  Deterministic engines (nse/ library imported in-process or via worker tasks)
```

## 2. Architecture principles

1. **Eligibility authority stays in engines.** UI and API never reimplement zones, freshness, or G0-G8.
2. **Shared market data, private customer data.** Clear ownership boundaries.
3. **Tenant context on every mutating and private read path.**
4. **Replaceable infrastructure.** Hosting/provider choices are config; business rules are not.
5. **Fail closed.** Unknown, incomplete, fixture and failed data never become PASS/CERTIFIED.
6. **No broker order path.** Providers that place orders are forbidden.
7. **`nse/` stdlib / offline boundary preserved.** Network adapters live outside `nse/`.

## 3. Logical modules inside the monolith

| Package area | Responsibility |
|---|---|
| `identity` | AuthN/AuthZ, tenants, sessions, admin audit |
| `billing` | Plans, entitlements, payment webhooks |
| `marketdata` | Dataset catalogue, readiness, shared queries |
| `research_bridge` | Calls into `nse` scanner/qualification/backtest/risk/store adapters |
| `opportunity` | Opportunities desk (evolve from platform) |
| `planning` | Trade plans |
| `portfolio` | Portfolio views over journal authority |
| `journal` | Customer journal API |
| `jobs` | Job submission and status |
| `notify` | Alerts/email/push dispatch interfaces |
| `ops` | Health, backup metadata, feature flags |

Workers execute long jobs; the API enqueues and authorises.

## 4. Frontend architecture

- React + TypeScript SPA.
- Responsive desktop / tablet / mobile layouts.
- Auth screens + customer workspace shell.
- Research terminal: overview, scanner, charts, plans, portfolio, journal, analytics (descriptive), settings.
- Real-time: prefer SSE or authenticated websocket for job progress and alert badges only where polling is insufficient.
- API client centralises auth, errors, freshness headers, and entitlement errors.

## 5. Backend API

- Versioned HTTPS JSON API (`/api/v1/...`).
- OpenAPI is the contract.
- Evolve from current `platform/gtf_platform` routes; replace loopback session with SaaS auth.
- Idempotency keys for scan/backtest/create-plan where retries are expected.
- Rate limits per tenant and per IP.

## 6. Database design (PostgreSQL)

### 6.1 Recommendation

PostgreSQL as primary production database.

### 6.2 Schema domains

| Domain | Isolation | Examples |
|---|---|---|
| `market_*` | Shared, read-mostly | instruments, membership intervals, calendar, CA events, candle pointers, dataset versions, certification windows |
| `tenant_*` / row `tenant_id` | Private | users, settings, watchlists, drawings, plans, opportunities, jobs metadata, alert rules |
| `journal_*` | Private (tenant_id) | orders, executions, charges, notes, reviews, attachment metadata |
| `billing_*` | Private + platform | subscriptions, invoices references, entitlements |
| `audit_*` | Private + platform admin | append-only audit |

**Isolation model (initial):** Shared database, shared schemas, mandatory `tenant_id` on private tables, enforced in repository layer + Postgres Row Level Security (RLS) as defense in depth. Schema-per-tenant deferred (OD-BP-008).

### 6.3 Redis

- Session/token denylist or session store (if used)
- Short-lived caches keyed by `tenant_id:` or `shared:`
- Queue coordination / locks for workers
- Rate-limit counters

Cache keys for private data must include tenant id. Shared market cache keys must not embed customer data.

### 6.4 Object storage

| Prefix | Contents | Access |
|---|---|---|
| `market/raw/...` | Immutable bhavcopies, CA source files | Workers + signed admin |
| `market/derived/...` | Derived artefacts with hashes | Workers/API read |
| `tenant/{tenant_id}/attachments/...` | Journal attachments | Tenant-scoped signed URLs |
| `tenant/{tenant_id}/exports/...` | Customer exports | Time-limited signed URLs |

## 7. Workers

| Worker | Trigger | Notes |
|---|---|---|
| Market data ingestion | Schedule / manual admin | Writes inbox/raw objects; no silent overwrite |
| Data validation | After ingest | Findings immutable |
| Corporate-action processing | After CA acquire | Does not invent completeness |
| Candle generation / parse cache | After validation | Cache keyed by archive hash + loader version |
| Scheduled scanning | Post-session calendar | Tenant jobs only for entitled tenants; shared scan artefact optional OD-BP-009 |
| Backtesting | On demand | Tenant-scoped; quota limited |
| Alert delivery | Event/schedule | Tenant isolation on channels |
| Maintenance | Schedule | Vacuum, partition, expired export cleanup |
| Recovery | On incident | Restore drills |

## 8. Cloud infrastructure

| Concern | Recommendation | Alternatives |
|---|---|---|
| Hosting | Managed container service or PaaS for API + workers | DIY VMs (higher ops) |
| CDN / WAF | CDN for SPA + WAF in front of API | Origin-only (rejected for public SaaS) |
| TLS | Managed certificates, HTTPS only |  -  |
| Managed PostgreSQL | Provider-managed with PITR | Self-managed (rejected initially) |
| Redis | Managed Redis |  -  |
| Object storage | S3-compatible |  -  |
| Secrets | Cloud secret manager | Env files on disk (dev only) |
| Observability | Metrics + structured logs + traces |  -  |
| CI/CD | Build, test, migrate, deploy pipelines | Manual SSH (rejected) |
| Backup / DR | DB PITR + object versioning + restore runbooks |  -  |

**No provider purchase or account creation is authorised by this document.** Region preference (proposed: India / ap-south for data residency) = OD-BP-010.

## 9. Mapping from current repository

| Today | SaaS target |
|---|---|
| `platform/web` React SPA | Customer SPA behind CDN |
| `platform/gtf_platform` FastAPI loopback | Public API monolith + auth |
| Dual SQLite | PostgreSQL (+ migration programme) |
| In-process job thread | Worker pool + Redis queue |
| Local files under `nse/data` | Object storage + controlled operator ingest |
| Loopback cookie session | SaaS identity module |
| Single instance lock | Horizontally scalable API; sticky not required if jobs externalised |

## 10. Explicit non-architecture

- Desktop installers and auto-updaters as primary distribution
- Local SQLite as production system of record for SaaS customers
- Broker execution microservices
- Letting the SPA compute eligibility

## 11. Acceptance for architecture

- Owner accepts modular monolith + workers (or records alternative).
- OD-BP-001 resolved for commercial production direction; production cloud **build** still requires separate authorisation after W0 specs.
- Security model in `08_CLOUD_SECURITY_AND_TENANCY.md` accepted for specification; implementation not authorised by OD-BP-001 alone.
