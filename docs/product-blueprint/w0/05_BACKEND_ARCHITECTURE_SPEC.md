# W0-05 - Backend Application Architecture Specification

**Status:** Specification only. No API/schema changes authorised.

## 1. Purpose

Evolve `platform/gtf_platform` into a cloud-ready modular monolith without duplicating research engines.

## 2. Current map

| Area | Today |
|---|---|
| App entry | `platform/run_api.py`, `gtf_platform/app.py` |
| Routes | ~59 paths in `openapi.json` |
| Security | Loopback session |
| Jobs | In-process `jobs.py` |
| Research bridge | `integration/` calling `nse` |
| Instance lock | Single-process `instance.py` |

## 3. Application boundaries

```
platform/web (SPA)
    -> API gateway/edge
    -> gtf_platform modular monolith
         -> auth / tenancy / billing modules
         -> app domain modules (scans, plans, journal, ...)
         -> research_bridge -> nse.* (stdlib engines)
         -> enqueue -> workers
```

`nse/` must not import `platform/`. Network adapters stay outside `nse/`.

## 4. Domain module ownership

| Module package (proposed) | Owns | Must not own |
|---|---|---|
| `auth` | identity, sessions | eligibility |
| `tenancy` | tenants, memberships | market data |
| `billing` | entitlements | journal accounting |
| `market` | dataset catalogue reads | private drawings |
| `research_bridge` | calls scanner/qualification/backtest/risk/store adapters | reimplemented gates |
| `opportunity` | opportunities desk | zone detection |
| `planning` | trade plans | order routing |
| `journal_api` | journal HTTP | second portfolio ledger |
| `jobs_api` | job create/status | long compute inline |
| `ops` | health, meta, admin | customer journal reads without audit |

## 5. Middleware chain (SaaS mode)

1. TLS terminated at edge.
2. Request id / trace context.
3. Security headers.
4. Authn (session/JWT validation).
5. Tenant context binder + RLS SET LOCAL.
6. Entitlement gate (route class).
7. Rate limit.
8. Handler.
9. Audit emitter for mutating routes.

Local mode uses existing loopback middleware; SaaS mode rejects bootstrap.

## 6. API versioning and errors

- Stay on `/api/v1` until breaking change needs `/api/v2`.
- Stable error envelope: `{ "error": { "code": "...", "message": "...", "details": ... } }`.
- Preserve engine status strings; do not rename `candidate_status` / gate ids.
- `authorises_order` always false on plan responses.

## 7. Validation, rate limits, idempotency

- Pydantic/request models for all writes.
- Rate limits per IP and per tenant (W0-07).
- Idempotency-Key required for scan create, backtest create, plan approve retries.

## 8. Transactions and events

- One DB transaction per request where feasible.
- After commit, emit internal domain events to queue (job queued, plan approved, export requested).
- Do not dual-write journal to a second ledger.

## 9. Engine integration rules

| Rule | Detail |
|---|---|
| Eligibility | Only via scanner/qualification / MTF overlay path |
| Portfolio/caps | Journal authority (`portfolio_at`) |
| Plans | Risk checks via `nse.research.risk` |
| Backtest | `nse.research.backtest` + manifest |
| Explain | Deterministic explain; LLM optional later |

## 10. Backward compatibility

- OpenAPI diff required in CI for SaaS branch.
- Local OpenAPI paths remain for engineering baseline until explicitly retired.
- Contract disagreements with `docs/architecture/API_CONTRACTS.md` must be tracked as defects (existing rule).

## 11. Acceptance tests

Middleware order tests; tenant context missing fails closed; engine bridge unit tests still pass; no import of broker clients; OpenAPI snapshot for SaaS surface.
