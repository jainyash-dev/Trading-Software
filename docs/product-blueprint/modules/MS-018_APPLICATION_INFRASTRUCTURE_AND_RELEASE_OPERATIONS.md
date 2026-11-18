# MS-018  -  Application, Infrastructure & Release Operations

| Field | Value |
|---|---|
| Module ID | MS-018 |
| Name | Application, Infrastructure & Release Operations |
| Status | Initial specification (Assignment 00) |
| Implementation authorised | **No** |

## 1. Purpose and boundaries

Hosting, CDN/WAF, TLS, managed DB, workers, secrets, observability, CI/CD, backup/DR.

**In scope:** behaviours listed below.  
**Out of scope:** broker order execution; UI reimplementation of Zone Engine / MTF / G0-G8; weakening D66; desktop-primary packaging.

## 2. Features and submodules

- Environments
- Deploy pipeline
- Secrets
- Monitoring
- Backup/restore drills

## 3. User workflows

1. Deploy → migrate → health → observe

## 4. Frontend screens

- Ops status (public status page later)

Responsive desktop / tablet / mobile required for customer-facing screens. Admin consoles may be desktop-first.

## 5. Backend services and APIs

Representative API surface (final paths must be OpenAPI-controlled):

- `/health`
- `/meta`
- `admin ops APIs`

Authz: customer routes require tenant context (except public marketing). Admin routes require platform admin + audit.

## 6. Database entities and ownership

- `ops metadata not customer data`

Ownership: shared market entities have no customer `tenant_id` (or `tenant_id` NULL). Private entities require `tenant_id NOT NULL` and RLS.

## 7. Workers and schedules

- `all workers`
- `restore-worker`

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

Local run_api only; no SaaS infra in repo.

## 14. Missing capabilities

- Entire cloud topology
- CI
- DR

## 15. Dependencies

- None beyond platform baseline

## 16. Open questions

- OD-BP-007
- OD-BP-010

## 17. Deployment notes

Ship behind feature flags when SaaS infra exists. Local loopback edition remains an engineering baseline under OD-BP-001. Commercial implementation requires separate build authorisation after W0 specs.
## 18. Engineering annex  -  reference topology

```
Internet → CDN (SPA) → WAF → API service (N replicas)
                           → Worker service (M replicas)
                           → Managed PostgreSQL (PITR)
                           → Managed Redis
                           → Object storage
                           → Secret manager
                           → Logs/metrics/traces
CI: lint → unit → integration → migrate (prod approve) → deploy → smoke
```

### 18.1 Environments

| Env | Data | Purpose |
|---|---|---|
| local | SQLite/files optional | Owner/dev research |
| staging | Synthetic + scrubbed | SaaS integration |
| production | Licensed market + customers | Commercial |

### 18.2 Backup / DR acceptance

- Monthly restore drill documented.
- RPO/RTO measured against OD-BP-007.
- Object versioning enabled on raw market bucket.

### 18.3 Security baseline checklist

- TLS everywhere
- Secrets not in images
- Dependency scanning in CI
- SBOM retained per release
- No public DB ports

