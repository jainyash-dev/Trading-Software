# W0-07 - Security and Privacy Specification

**Status:** Specification only. OD-BP-006/011/012/014/015 open where noted.

## 1. Goals

Protect tenant data confidentiality/integrity; prevent cross-tenant leakage; meet commercial baseline controls before launch.

## 2. Controls

| Area | Requirement |
|---|---|
| In transit | TLS 1.2+ everywhere |
| At rest | Disk encryption for DB/Redis/objects (managed) |
| Secrets | Secret manager; rotation runbook; no secrets in git/images |
| Authn/z | W0-01/02 |
| Isolation | RLS + app checks + object key prefixes + cache prefixes |
| Abuse | Rate limits, lockouts, WAF rules |
| Input validation | Strict schemas; attachment magic bytes (retain P6) |
| Audit | Auth, admin, billing, export/delete, plan approve |
| Logging | Redact passwords, OTPs, tokens, cookies; minimise PII |
| Dependencies | CI vulnerability scan; pin versions |
| Admin access | MFA + ticketed break-glass |

## 3. Personal data inventory (initial)

| Data | Purpose | Lawful basis (review OD-BP-006) |
|---|---|---|
| Email, name | Account | Contract / consent review |
| Auth secrets | Security | Contract |
| Journal/plans | Product | Contract |
| Attachments | Product | Contract |
| Billing refs | Payment | Contract |
| IP/UA hashes | Security | Legitimate interest review |
| Support bundles | Support | Consent / contract |

## 4. Export and deletion

- Export job produces machine-readable archive + manifest.
- Delete: disable auth -> schedule purge of private DB + objects -> confirm.
- Legal hold flag can delay purge (OD-BP-006).

## 5. Threat model (STRIDE-lite)

| Threat | Example | Mitigation |
|---|---|---|
| Spoofing | Session theft | HttpOnly cookie, short TTL, revoke |
| Tampering | IDOR plan id | tenant checks + RLS |
| Repudiation | Admin reads journal | admin_audit immutable |
| Info disclosure | Log leakage | redaction filters |
| DoS | Scan floods | quotas + rate limits |
| Elevation | Customer hits admin API | separate auth realm |

## 6. Incident response (requirements)

Severity SEV-1..4; paging for SEV-1/2; customer notice thresholds OD-BP-012; credential rotation; postmortem template.

## 7. Security test plan

- SAST/dependency scan in CI.
- Cross-tenant negative suite (mandatory).
- Auth abuse tests (brute force).
- Attachment malware/type tests.
- Periodic restore test (W0-10).
- Pen-test before public GA (owner gate).

## 8. Acceptance

Threat model reviewed; redaction tests; isolation suite green; no production secrets in repo.
