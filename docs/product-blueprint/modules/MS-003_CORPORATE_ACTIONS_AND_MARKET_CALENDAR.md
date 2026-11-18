# MS-003  -  Corporate Actions & Market Calendar

| Field | Value |
|---|---|
| Module ID | MS-003 |
| Name | Corporate Actions & Market Calendar |
| Status | Initial specification (Assignment 00) |
| Implementation authorised | **No** |

## 1. Purpose and boundaries

Store CA events separately from prices; maintain verified trading calendar; enforce D66 completeness windows.

**In scope:** behaviours listed below.  
**Out of scope:** broker order execution; UI reimplementation of Zone Engine / MTF / G0-G8; weakening D66; desktop-primary packaging.

## 2. Features and submodules

- CA event register
- Source dual archive
- Reconciliation
- Calendar sessions
- Special sessions

## 3. User workflows

1. Ingest CA source
2. Reconcile two sources
3. Owner approves completeness window
4. Classify session date

## 4. Frontend screens

- Calendar
- CA event detail (admin)
- Completeness windows

Responsive desktop / tablet / mobile required for customer-facing screens. Admin consoles may be desktop-first.

## 5. Backend services and APIs

Representative API surface (final paths must be OpenAPI-controlled):

- `GET /calendar`
- `GET /corporate-actions`
- `POST /admin/ca/completeness`

Authz: customer routes require tenant context (except public marketing). Admin routes require platform admin + audit.

## 6. Database entities and ownership

- `ca_events`
- `ca_sources`
- `ca_reconciliations`
- `ca_completeness_windows`
- `calendar_days`

Ownership: shared market entities have no customer `tenant_id` (or `tenant_id` NULL). Private entities require `tenant_id NOT NULL` and RLS.

## 7. Workers and schedules

- `ca-ingest`
- `ca-reconcile`
- `calendar-build`

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

Calendar strong (D58). CA partial; D66 windows absent (0).

## 14. Missing capabilities

- Second official source acquisition
- completeness.csv owner approvals

## 15. Dependencies

- MS-001
- MS-004

## 16. Open questions

- D66 source path; no purchase without auth

## 17. Deployment notes

Ship behind feature flags when SaaS infra exists. Local loopback edition remains an engineering baseline under OD-BP-001. Commercial implementation requires separate build authorisation after W0 specs.
## 18. Engineering annex  -  D66 completeness window record

A completeness approval row must store at minimum:

| Field | Rule |
|---|---|
| symbol / instrument id | Required |
| window_start / window_end | Required |
| source_a_hash | SHA-256 verified |
| source_b_hash | SHA-256 verified |
| independence_note | Provenance/independence |
| reconciliation_id | Event-by-event record |
| owner_approver | Human identity |
| approved_at | Timestamp |
| status | APPROVED / REJECTED |

Single-source rows may exist as evidence but **cannot** set completeness APPROVED.

