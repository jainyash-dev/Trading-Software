# MS-007  -  Opportunity Scanner

| Field | Value |
|---|---|
| Module ID | MS-007 |
| Name | Opportunity Scanner |
| Status | Initial specification (Assignment 00) |
| Implementation authorised | **No** |

## 1. Purpose and boundaries

Run MIT scans via canonical pipeline; present candidates, opportunities, watchlists, history.

**In scope:** behaviours listed below.  
**Out of scope:** broker order execution; UI reimplementation of Zone Engine / MTF / G0-G8; weakening D66; desktop-primary packaging.

## 2. Features and submodules

- Manual/scheduled/historical scan
- Candidate table
- Opportunities desk
- Watchlists
- Scan configs

## 3. User workflows

1. Start scan
2. Review gates
3. Save watchlist
4. Open opportunity

## 4. Frontend screens

- Scanner
- Opportunities
- Watchlists
- History

Responsive desktop / tablet / mobile required for customer-facing screens. Admin consoles may be desktop-first.

## 5. Backend services and APIs

Representative API surface (final paths must be OpenAPI-controlled):

- `POST/GET /scans`
- `/opportunities*`
- `/watchlists*`
- `/scan-configs`

Authz: customer routes require tenant context (except public marketing). Admin routes require platform admin + audit.

## 6. Database entities and ownership

- `scans_meta`
- `opportunities`
- `watchlists`
- `scan_configs`
- `jobs`

Ownership: shared market entities have no customer `tenant_id` (or `tenant_id` NULL). Private entities require `tenant_id NOT NULL` and RLS.

## 7. Workers and schedules

- `scan-worker`
- `schedule-trigger`

Failure handling: retries with idempotency keys; poison-queue; never mark CERTIFIED on partial failure.

## 8. External integrations

Only owner-authorised adapters. No network inside `nse/`. PSP/email/LLM/data vendors gated by OD register.

## 9. Security and tenant rules

- Private resources tenant-scoped.
- Signed URLs for objects.
- Cross-tenant negative tests mandatory where private data exists.
- Admin break-glass audited.

## 10. Data quality and provenance

- Dataset/result responses include dataset version / hash when research-affecting.
- States: MISSING/STALE/PROVISIONAL/FIXTURE/INCOMPLETE/FAILED/CERTIFIED.
- D66 applies to CA completeness (MS-003/004).

## 11. Business rules and calculations

- Eligibility calculations only via `nse` qualification pathway when this module displays candidates.
- `authorises_order` remains false in any plan/order-related surface.
- Unknown never becomes PASS.

## 12. Testing and acceptance criteria

1. Unit tests for domain rules touched.
2. API contract tests including authz denial.
3. Cross-tenant IDOR tests if private data.
4. Integration test with engines where results shown.
5. Browser acceptance for customer screens on labelled fixture data.
6. No certification claim without D66 evidence.

Measurable: CI green for module test group; security suite includes at least one cross-tenant denial per private entity type.

## 13. Current implementation

Strong local implementation; jobs partial list UI.

## 14. Missing capabilities

- Per-tenant quotas
- optional shared scan artefact OD-BP-009

## 15. Dependencies

- MS-004
- MS-016
- MS-017

## 16. Open questions

- OD-BP-009

## 17. Deployment notes

Ship behind feature flags when SaaS infra exists. Local loopback edition remains an engineering baseline under OD-BP-001. Commercial implementation requires separate build authorisation after W0 specs.
## 18. Engineering annex  -  eligibility bridge

### 18.1 Invariants (tests must keep)

1. Candidates only from `MtfSnapshot.eligible_after_overlay` / `manual_review_after_overlay`.
2. One qualification pathway via `qualification` / `scanner`.
3. WIT-75/WIT-125 → BLOCKED.
4. Status via `derive_status`; MANUAL_REVIEW/BLOCKED/DATA_INSUFFICIENT never actionable.
5. `authorises_order` never true.

### 18.2 Job payload (tenant)

```json
{
  "tenant_id": "uuid",
  "mode": "manual|scheduled|historical",
  "as_of": "YYYY-MM-DD|null",
  "universe": "nifty100|adhoc",
  "symbols": ["..."],
  "dataset_version": "...",
  "idempotency_key": "..."
}
```

Worker loads shared canonical market data, runs `pipeline.run` (or equivalent), stores envelope keyed by tenant + scan_key, emits job completion.

### 18.3 SaaS delta vs current OpenAPI

- Add tenant auth.
- Add `GET /api/v1/jobs` list (missing today).
- Enforce quotas (MS-017).
- Persist scan artefacts in Postgres/object storage instead of local folders only.

