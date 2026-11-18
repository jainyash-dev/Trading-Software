# MS-006  -  Charting & Technical Analysis

| Field | Value |
|---|---|
| Module ID | MS-006 |
| Name | Charting & Technical Analysis |
| Status | Initial specification (Assignment 00) |
| Implementation authorised | **No** |

## 1. Purpose and boundaries

Render M/W/D candles with engine zones, plan overlays, tenant drawings; no UI eligibility math.

**In scope:** behaviours listed below.  
**Out of scope:** broker order execution; UI reimplementation of Zone Engine / MTF / G0-G8; weakening D66; desktop-primary packaging.

## 2. Features and submodules

- Candle view
- Zone overlays
- Plan overlays
- Drawings
- Crosshair zoom pan

## 3. User workflows

1. Open symbol from scan
2. Inspect zones
3. Draw levels
4. Toggle plan geometry

## 4. Frontend screens

- Analysis / Chart

Responsive desktop / tablet / mobile required for customer-facing screens. Admin consoles may be desktop-first.

## 5. Backend services and APIs

Representative API surface (final paths must be OpenAPI-controlled):

- `GET /candles`
- `GET /symbols/{symbol}/bundle`
- `CRUD /drawings`

Authz: customer routes require tenant context (except public marketing). Admin routes require platform admin + audit.

## 6. Database entities and ownership

- `drawings (tenant)`
- `candle cache pointers (shared)`

Ownership: shared market entities have no customer `tenant_id` (or `tenant_id` NULL). Private entities require `tenant_id NOT NULL` and RLS.

## 7. Workers and schedules

- `candle-cache-worker`

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

Implemented with lightweight-charts; P2/P10 browser evidence on fixtures.

## 14. Missing capabilities

- Tenant isolation on drawings
- mobile gesture polish

## 15. Dependencies

- MS-001
- MS-007
- MS-010
- MS-016

## 16. Open questions

- None module-specific beyond global OD-BP register

## 17. Deployment notes

Ship behind feature flags when SaaS infra exists. Local loopback edition remains an engineering baseline under OD-BP-001. Commercial implementation requires separate build authorisation after W0 specs.
