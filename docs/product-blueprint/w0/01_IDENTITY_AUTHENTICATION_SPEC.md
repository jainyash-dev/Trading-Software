# W0-01 - Identity and Authentication Specification

**Status:** Specification only. Provider selection NOT authorised. OD-BP-004 open.

## 1. Purpose

Provide secure customer identity for public SaaS while preserving local loopback auth as an engineering baseline (OD-BP-001 / D57 historical).

## 2. Current implementation map

| Capability | Today | Path |
|---|---|---|
| Session bootstrap | Loopback-only cookie + host/origin + `X-GTF-Request` | `platform/gtf_platform/security.py` |
| Multi-user identity | Absent | - |
| Registration / email verify | Absent | - |
| MFA | Absent | - |
| Password store | Absent | - |

## 3. Actors

| Actor | Authn | Authz |
|---|---|---|
| Customer user | Email/password or IdP (OD-BP-004) | Tenant membership + entitlements |
| Tenant owner | Same | Manage own tenant settings |
| Platform admin | Separate admin IdP / break-glass | Audited ops; not customer impersonation without ticket |
| Local engineering user | Loopback bootstrap | Single-tenant local data only |

## 4. Functional requirements

### 4.1 Registration
- Collect email, password (if password mode), display name, ToS/privacy acceptance version.
- Create `user` + personal `tenant` + `owner` membership (OD-BP-003: individual default).
- Send email verification; research APIs refuse unverified users if policy flag `require_email_verified=true` (default proposed true for production).

### 4.2 Email verification
- Single-use token, TTL <= 24h (proposed).
- Resend rate-limited.

### 4.3 Login / logout
- Login creates server session bound to `user_id` + `tenant_id`.
- Logout revokes session immediately.
- Concurrent session limit: proposed 5 (open OD if stricter).

### 4.4 Password policy and recovery
- Minimum length 12; breach-check optional later.
- Store only KDF hash (Argon2id or bcrypt; Argon2id recommended).
- Recovery: single-use token email; invalidates prior reset tokens; does not reveal whether email exists in UI timing (anti-enumeration best effort).

### 4.5 MFA
- TOTP recommended at launch for all users OR enforced for paid tiers (OD-BP-004).
- Recovery codes hashed at rest.
- MFA challenge before session elevation for sensitive actions (export, delete, billing change).

### 4.6 Session management
- Session id random 256-bit; stored server-side (DB or Redis) with metadata: created_at, expires_at, ip_hash, ua_hash, mfa_satisfied.
- Cookie: `HttpOnly; Secure; SameSite=Lax` (or Strict if SPA same-site); not in localStorage.
- Absolute timeout proposed 12h; idle timeout proposed 2h (OD if different).
- Revocation list checked every request.

### 4.7 Device/session visibility
- `GET /api/v1/account/sessions` lists active sessions (approx location from IP hash only if policy allows).
- User can revoke any session except must keep one path to avoid lockout (or require email recovery).

### 4.8 Suspension and deletion
- Admin or billing system may set user/tenant `SUSPENDED`.
- Deletion follows OD-BP-006 export/delete workflow; auth credentials disabled first.

### 4.9 Abuse protection
- Rate limits: register, login, reset, MFA (IP + account keys).
- Lockout after N failures with exponential backoff (proposed N=10 / 15 min).
- CAPTCHA/challenge after threshold (provider OD).
- Credential stuffing monitoring alerts (W0-09).

### 4.10 Administrative access
- Separate admin realm; MFA mandatory.
- Break-glass requires ticket id; every action in `admin_audit`.
- No shared customer passwords; no silent impersonation without audited "support session" that customer can see.

### 4.11 Auth audit events
Emit: register, verify_email, login_success, login_failure, logout, password_change, reset_request, reset_complete, mfa_enable, mfa_fail, session_revoke, suspend, delete_request. Redact secrets.

## 5. Alternatives evaluation (no selection authorised)

| Option | Pros | Cons | Cost/ops |
|---|---|---|---|
| A. Self-operated (sessions in GTF + email provider) | Full control; fits FastAPI | Own security burden; email deliverability | Email SaaS fees; eng time |
| B. Managed IdP (Auth0 / Cognito / Clerk / Supabase Auth / Firebase) | Faster MFA/social; battle-tested | Vendor lock; data residency; feature cost | Monthly MAU pricing |
| C. OIDC-only (bring-your-own IdP later) | Enterprise-ready | Weak for individual consumer launch | Complex UX |

**Recommendation for owner review (not approval):** Start with Option A or B after OD-BP-004; require MFA path; keep local loopback path for engineering baseline behind compile/runtime flag `GTF_AUTH_MODE=local|saas`.

## 6. API surface (illustrative)

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/verify-email`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/password/forgot`
- `POST /api/v1/auth/password/reset`
- `POST /api/v1/auth/mfa/setup|verify`
- `GET /api/v1/session`
- `GET|DELETE /api/v1/account/sessions[/{id}]`

Local mode retains existing `/api/v1/session/bootstrap` and must not be exposed on public SaaS origins.

## 7. Data model (min)

`users`, `email_tokens`, `sessions`, `mfa_secrets`, `mfa_recovery_codes`, `auth_audit` - see W0-02/W0-04 for tenant linkage.

## 8. Acceptance tests (spec)

1. Unverified user blocked from private APIs when policy on.
2. Stolen cookie after logout rejected.
3. Cross-user session IDOR denied.
4. Reset token single-use.
5. MFA required path cannot be skipped via API.
6. Local bootstrap rejected when `GTF_AUTH_MODE=saas`.
7. Admin break-glass writes audit row.

## 9. Open questions

OD-BP-004 (method/MFA), email provider, lockout thresholds, session TTLs, CAPTCHA provider.
