# W0-04 - Database and Storage Architecture Specification

**Status:** Specification only. OD-BP-008 open. Dual-write migration not authorised without consistency design below.

## 1. Primary transactional database

**Recommendation:** Managed PostgreSQL 15+ as SaaS system of record.

Schemas (logical):

| Schema | Ownership |
|---|---|
| `auth` | users, sessions, mfa |
| `tenancy` | tenants, memberships |
| `billing` | plans, subscriptions, entitlements, billing_events |
| `market` | instruments, membership, calendar, ca_*, datasets, findings |
| `app` | watchlists, drawings, opportunities, plans, settings, jobs |
| `journal` | orders, executions, charges, notes, reviews, attachments metadata |
| `ops` | admin_audit, feature_flags |

Private tables: `tenant_id UUID NOT NULL` + FK + index `(tenant_id, id)`.

## 2. Row-Level Security

- Enable RLS on all private tables.
- Policy example: `tenant_id = current_setting('gtf.tenant_id')::uuid`.
- App sets `SET LOCAL gtf.tenant_id = ...` per request/transaction.
- App role has no BYPASSRLS; migration role separate.

## 3. Indexes and query patterns

- Plans/journal by `(tenant_id, updated_at DESC)`.
- Jobs by `(tenant_id, status, created_at)`.
- Market candles accessors by symbol + date (shared).
- Avoid sequential scans across tenants.

## 4. Connection pooling

PgBouncer / managed pooler in transaction mode; short transactions; no session-state beyond `SET LOCAL`.

## 5. Redis

| Use | Key pattern | TTL |
|---|---|---|
| Session store (optional) | `t:{tid}:sess:{sid}` | session TTL |
| Rate limits | `rl:{scope}:{key}` | window |
| Job locks | `lock:job:{id}` | short |
| Market cache | `mkt:candle:{sym}:{tf}:{hash}` | short |
| Queue coordination | queue lists / streams | n/a |

## 6. Object storage

| Prefix | Contents | Versioning |
|---|---|---|
| `market/raw/` | Immutable bhavcopy/CA sources | On |
| `market/derived/` | Derived artefacts + hashes | On |
| `tenant/{tid}/attachments/` | Journal attachments | On |
| `tenant/{tid}/exports/` | Customer exports | On + expire |

## 7. Retention / archival

- Market raw: retain indefinitely while licensed (OD-BP-014).
- Tenant attachments: while account active + OD-BP-006.
- Audit: OD-BP-011.
- Soft-deleted private rows: purge after cooling-off.

## 8. Backup / recovery

Delegated detail to W0-10; DB PITR required for production recommendation.

## 9. SQLite compatibility (engineering baseline)

Local mode continues dual SQLite (`platform` + research `store.py`) under OD-BP-001 baseline. SaaS code paths must not require SQLite in production.

Feature flag: `GTF_PERSISTENCE=sqlite|postgres`.

## 10. Migration strategy from SQLite (design only; not authorised to execute)

### Principles
- No silent dual-write without reconciliation.
- Expand/contract migrations.
- Tenant_id assignment for single-owner local export = new tenant UUID.

### Phases (spec)
1. **Export:** deterministic dump of local SQLite + file attachments + dataset hashes.
2. **Transform:** map to Postgres schemas; validate constraints offline.
3. **Load:** idempotent upsert by natural keys where possible.
4. **Reconcile:** row counts, checksums of journal ledgers, plan ids.
5. **Cutover:** only after owner authorises; read-only freeze window.
6. **Rollback:** keep SQLite snapshot immutable; Postgres load is additive until cutover flag flips.

### Dual-write (optional later)
Only if a written reconciliation job compares both stores every N minutes and pages on drift. **Not default.** Do not enable dual-write without owner approval of this consistency design.

## 11. Acceptance tests

RLS denial; migration dry-run checksum fixture; pooler SET LOCAL isolation between requests; object key tenancy.
