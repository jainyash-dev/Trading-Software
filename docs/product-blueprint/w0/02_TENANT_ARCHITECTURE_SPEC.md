# W0-02 - Tenant and Customer Architecture Specification

**Status:** Specification only. OD-BP-003 (seats) and OD-BP-008 (isolation strength) open.

## 1. Purpose

Define the isolation boundary for every private customer artefact and how shared market data is separated.

## 2. Entities

| Entity | Definition | Launch |
|---|---|---|
| User | Authenticated person | Yes |
| Tenant | Isolation workspace / billing customer | Yes; 1:1 with individual trader |
| Membership | User role on tenant (`owner`, later `member`/`admin`) | `owner` only at launch unless OD-BP-003 expands |
| Platform admin | Operator identity | Yes |
| Organization | Multi-seat container | Schema-extensible; **not implemented** at launch |

## 3. Lifecycle

1. Register -> create tenant `PENDING` -> verify email -> tenant `ACTIVE`.
2. Suspend: billing fail or abuse -> `SUSPENDED` (read-only or blocked per entitlement policy).
3. Close: delete workflow -> `CLOSED`; purge schedule per OD-BP-006.

Ownership: tenant `owner` user cannot leave without transferring ownership (future) or closing tenant.

## 4. Shared vs private data

| Class | Examples | `tenant_id` | Mutability |
|---|---|---|---|
| Shared market | instruments, membership, calendar, CA events, dataset versions, certification windows | NULL / absent | Platform operators only |
| Private customer | plans, journal, drawings, watchlists, settings, jobs, alerts, attachments, exports | NOT NULL | Tenant members only |
| Billing | subscriptions, entitlement snapshots | NOT NULL | System + owner |

Research engines read shared market inputs; they never write another tenant's private rows.

## 5. Authorization rules

1. Resolve session -> `(user_id, tenant_id, roles)`.
2. Repository layer requires `tenant_id = ctx.tenant_id` on private queries.
3. RLS enforces same predicate (defense in depth) - OD-BP-008 recommends shared DB + RLS.
4. Client-supplied `tenant_id` in body/query is ignored except admin tools.
5. Entitlements checked after authz (W0-08).

## 6. Concrete examples

### Allowed
- User A lists plans where `tenant_id = A`.
- User A downloads signed URL for `tenant/A/attachments/...` after authz.
- Shared `GET /candles?symbol=RELIANCE` returns market series (no private overlays from B).
- Worker for job owned by A sets tenant context A before journal write.

### Forbidden
- User A `GET /plans/{id}` where plan.tenant_id = B -> 404/403.
- User A guesses object key `tenant/B/...` -> signed URL mint denied; direct access denied.
- Cache key without tenant prefix serving B's plan to A.
- Scan job for A writing opportunity rows with tenant B.
- Admin reading journal without ticketed break-glass audit.
- Shared market endpoint accepting payload that mutates private settings.

## 7. Jobs, cache, object storage

| Surface | Isolation mechanism |
|---|---|
| Jobs | `jobs.tenant_id` NOT NULL for customer jobs; worker context binder |
| Redis | `t:{tenant_id}:...` vs `mkt:...` |
| Objects | `tenant/{tenant_id}/...` vs `market/...` |
| Notifications | Destination records tenant-scoped |

## 8. Future org extensibility (without building now)

Reserve nullable `organization_id` on tenants OR separate org table; do not implement invites/roles beyond owner at launch unless OD-BP-003 says otherwise.

## 9. Mapping to MS modules

MS-016 owns identity/tenant; all MS-005-015 private tables inherit tenant rules; MS-001-004 shared market.

## 10. Acceptance tests

Cross-tenant IDOR matrix for plans, journal, drawings, jobs, attachments, alerts, exports; RLS bypass attempts with app DB role must fail; shared market write from customer role denied.
