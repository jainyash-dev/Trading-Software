# MS-016  -  Identity, Access & Customer Management

| Field | Value |
|---|---|
| Module ID | MS-016 |
| Name | Identity, Access & Customer Management |
| Status | Initial specification (Assignment 00) |
| Implementation authorised | **No** |

## 1. Purpose and boundaries

Registration, authentication, tenants, roles, admin audit  -  SaaS foundation.

**In scope:** behaviours listed below.  
**Out of scope:** broker order execution; UI reimplementation of Zone Engine / MTF / G0-G8; weakening D66; desktop-primary packaging.

## 2. Features and submodules

- Sign up/in
- Tenant workspace
- Roles
- Session revocation
- Admin audit

## 3. User workflows

1. Register → verify → login → workspace

## 4. Frontend screens

- Auth screens
- Account
- Admin

Responsive desktop / tablet / mobile required for customer-facing screens. Admin consoles may be desktop-first.

## 5. Backend services and APIs

Representative API surface (final paths must be OpenAPI-controlled):

- `/auth/*`
- `/tenants/*`
- `/admin/users`

Authz: customer routes require tenant context (except public marketing). Admin routes require platform admin + audit.

## 6. Database entities and ownership

- `users`
- `tenants`
- `memberships`
- `sessions`
- `admin_audit`

Ownership: shared market entities have no customer `tenant_id` (or `tenant_id` NULL). Private entities require `tenant_id NOT NULL` and RLS.

## 7. Workers and schedules

- `email-sender`

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

Not implemented (loopback session only).

## 14. Missing capabilities

- Full stack auth
- RLS
- cross-tenant tests

## 15. Dependencies

- MS-018

## 16. Open questions

- OD-BP-003
- OD-BP-004

## 17. Deployment notes

Ship behind feature flags when SaaS infra exists. Local loopback edition remains an engineering baseline under OD-BP-001. Commercial implementation requires separate build authorisation after W0 specs.
## 18. Engineering annex  -  schemas and flows (initial)

### 18.1 Tables (PostgreSQL)

```sql
-- illustrative; migrations are the source of truth after implementation authorisation
CREATE TABLE tenants (
  id UUID PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  display_name TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('PENDING','ACTIVE','SUSPENDED','CLOSED')),
  created_at TIMESTAMPTZ NOT NULL,
  closed_at TIMESTAMPTZ
);

CREATE TABLE users (
  id UUID PRIMARY KEY,
  email CITEXT UNIQUE NOT NULL,
  email_verified_at TIMESTAMPTZ,
  password_hash TEXT, -- null if OIDC-only
  mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  status TEXT NOT NULL CHECK (status IN ('PENDING','ACTIVE','LOCKED','CLOSED')),
  created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE tenant_memberships (
  tenant_id UUID REFERENCES tenants(id),
  user_id UUID REFERENCES users(id),
  role TEXT NOT NULL CHECK (role IN ('owner','member','admin')),
  PRIMARY KEY (tenant_id, user_id)
);

CREATE TABLE sessions (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  created_at TIMESTAMPTZ NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  ip_hash TEXT,
  user_agent_hash TEXT
);

CREATE TABLE admin_audit (
  id BIGSERIAL PRIMARY KEY,
  actor_user_id UUID,
  action TEXT NOT NULL,
  target_tenant_id UUID,
  payload_redacted JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL
);
```

Enable RLS on all private tables; sessions and memberships enforce tenant match in app and DB.

### 18.2 API flows

1. `POST /api/v1/auth/register` → create user+tenant+owner membership; send verify email.
2. `POST /api/v1/auth/login` → create session; Set-Cookie HttpOnly Secure.
3. `POST /api/v1/auth/logout` → revoke session.
4. `GET /api/v1/session` → user, tenant, entitlements summary.
5. Middleware attaches `RequestContext(user_id, tenant_id, roles)`.

### 18.3 Acceptance tests (minimum)

- Register/login/logout happy path.
- Unverified email cannot access research APIs (policy flag).
- User A cannot read User B resources.
- Revoked session rejected.
- Admin audit row written on break-glass.

