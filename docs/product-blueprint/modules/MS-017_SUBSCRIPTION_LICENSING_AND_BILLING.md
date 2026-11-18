# MS-017  -  Subscription, Licensing & Billing

| Field | Value |
|---|---|
| Module ID | MS-017 |
| Name | Subscription, Licensing & Billing |
| Status | Initial specification (Assignment 00) |
| Implementation authorised | **No** |

## 1. Purpose and boundaries

Plans, entitlements, PSP webhooks, invoices references.

**In scope:** behaviours listed below.  
**Out of scope:** broker order execution; UI reimplementation of Zone Engine / MTF / G0-G8; weakening D66; desktop-primary packaging.

## 2. Features and submodules

- Plan catalogue
- Checkout
- Webhooks
- Entitlement enforcement
- Customer billing portal

## 3. User workflows

1. Choose plan → pay → features unlock

## 4. Frontend screens

- Billing
- Pricing

Responsive desktop / tablet / mobile required for customer-facing screens. Admin consoles may be desktop-first.

## 5. Backend services and APIs

Representative API surface (final paths must be OpenAPI-controlled):

- `/billing/plans`
- `/billing/checkout`
- `/billing/webhooks`

Authz: customer routes require tenant context (except public marketing). Admin routes require platform admin + audit.

## 6. Database entities and ownership

- `plans`
- `subscriptions`
- `entitlements`
- `billing_events`

Ownership: shared market entities have no customer `tenant_id` (or `tenant_id` NULL). Private entities require `tenant_id NOT NULL` and RLS.

## 7. Workers and schedules

- `webhook-worker`

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

Not implemented.

## 14. Missing capabilities

- PSP integration after OD-BP-005
- GST OD-BP-013

## 15. Dependencies

- MS-016
- MS-018

## 16. Open questions

- OD-BP-005
- OD-BP-013

## 17. Deployment notes

Ship behind feature flags when SaaS infra exists. Local loopback edition remains an engineering baseline under OD-BP-001. Commercial implementation requires separate build authorisation after W0 specs.
## 18. Engineering annex  -  entitlements

### 18.1 Entities

| Entity | Fields (min) |
|---|---|
| `plan` | id, code, features JSON, quotas JSON, active |
| `subscription` | id, tenant_id, plan_id, status, current_period_end, psp_customer_ref |
| `entitlement_snapshot` | tenant_id, computed features/quotas, as_of |
| `billing_event` | id, tenant_id, psp_event_id UNIQUE, type, payload_redacted |

### 18.2 Enforcement points

Server checks before: scan create, backtest create, AI call, export, extra seat invite.

UI may hide buttons; API must still refuse with `ENTITLEMENT_DENIED`.

### 18.3 Webhook rules

- Verify PSP signature.
- Idempotent by `psp_event_id`.
- Map customer ref → tenant_id; reject unknown.
- Never trust client-reported plan.

### 18.4 Acceptance tests

- Lapsed subscription → read-only research per OD policy.
- Quota exceeded → 402/403 with stable error code.
- Spoofed webhook → reject.
- Cross-tenant entitlement mutation → impossible.

