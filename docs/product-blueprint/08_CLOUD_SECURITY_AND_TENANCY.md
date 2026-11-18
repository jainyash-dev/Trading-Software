# 08  -  Cloud Security and Tenancy

**Claim discipline:** Tenant isolation is **designed here**, not implemented in the repository today. Do not mark isolation complete without code + cross-tenant negative tests.

## 1. Entities

| Entity | Definition |
|---|---|
| Customer User | Authenticated human account |
| Tenant | Isolation boundary / customer workspace (initially 1:1 with individual trader) |
| Membership | User↔tenant role binding (`owner`, `member`, later `admin`) |
| Platform Admin | GTF operator with audited break-glass |
| Session | Server-validated auth session/token bound to user+tenant |

## 2. Authentication and authorisation

### Target SaaS

- Registration with email verification.
- Login issuing HttpOnly Secure `SameSite=Lax` or `Strict` session cookie **or** OIDC access/refresh model (OD-BP-004).
- CSRF protection for cookie sessions; origin checks; security headers.
- Password hashing with modern KDF; reset tokens single-use.
- Authorisation: every private handler loads `tenant_id` from server-side session, never from client-supplied body alone.
- Entitlements checked server-side (MS-017).

### Current repository (non-SaaS)

- Loopback host/origin checks + bootstrap session cookie (`platform/gtf_platform/security.py`).
- No multi-user identity store.

## 3. Tenant-scoped API access

Rules:

1. Resolve auth → user → active tenant.
2. Repository queries include `tenant_id = :active`.
3. Resource IDs are unguessable and still checked for tenant match (IDOR tests).
4. Shared market endpoints are read-only and do not accept tenant overrides that mutate shared tables.
5. Admin APIs are separate routes with separate auth and audit.

## 4. Database isolation

- **Primary model:** shared PostgreSQL + `tenant_id` + RLS policies.
- Migrations create RLS for all private tables.
- Application role cannot bypass RLS; migrations use owner role.
- Soft-delete vs hard-delete per OD-BP-006.

## 5. Cache isolation

- Key prefix `t:{tenant_id}:` for private objects.
- Shared keys `mkt:` only for market artefacts.
- Flush operations are tenant-scoped.
- No caching of responses that mix tenants.

## 6. File and attachment access

- Object keys include `tenant/{tenant_id}/...`.
- Access via short-lived signed URLs minted after authz check.
- Magic-byte validation retained from P6 attachment rules.
- Cross-tenant key access must fail in tests.

## 7. Job and notification isolation

- Job rows carry `tenant_id` and `created_by_user_id`.
- Workers set tenant context; logs include tenant id redaction rules.
- Alert destinations belong to tenant; no fan-out across tenants.
- Shared market workers have `tenant_id = NULL` and cannot write private tables.

## 8. Administrative access and audit

- Break-glass requires MFA + ticket id + time-boxed role.
- Every admin read/write of customer data appends audit event.
- Customers can request export of their audit-visible events (scope OD).

## 9. Cross-tenant security tests (mandatory before launch)

| Test | Expect |
|---|---|
| User A reads User B plan by ID | 404/403 |
| User A signed URL for B attachment | deny |
| Job status leak across tenants | deny |
| Cache poison across tenant keys | impossible / denied |
| RLS bypass via raw SQL app role | fail |
| Webhook billing event maps wrong tenant | reject |
| Search endpoints return only tenant rows | pass |

## 10. Export and deletion

- Export: machine-readable archive of private data + manifest.
- Deletion: customer-initiated delete schedules purge of private DB rows, objects, and cancellable jobs; shared market data retained.
- Legal hold flag can delay purge (OD-BP-006).

## 11. Incident response (requirements)

- Severity model, paging, customer notification thresholds (OD-BP-012).
- Credential rotation runbooks.
- No requirement here authorises production monitoring spend.

## 12. What is NOT claimed

The repository does not yet have multi-tenant RLS, customer auth, or cross-tenant CI tests. Current local security is loopback single-user hardening only.
