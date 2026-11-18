# 00 - W0 Master Plan (Cloud SaaS Foundation)

**Programme:** W0 Cloud SaaS Foundation Specification  
**Date:** 2026-11-18  
**Authority:** OD-BP-001 USER_APPROVED (commercial SaaS direction). W0 authorised for **specification only**.  
**Not authorised:** application implementation, schema/API changes, migrations, cloud accounts, purchases, provider contacts, deployments, broker integration, D66 changes, git mutations.

## 1. Purpose

Define the complete cloud SaaS foundation required to transform the existing GTF application into a secure, commercially distributable browser-based multi-tenant product, while preserving deterministic research engines and local engineering baseline.

## 2. Governing decisions

| Decision | Status | Effect |
|---|---|---|
| OD-BP-001 | USER_APPROVED | Commercial production = browser cloud multi-tenant SaaS |
| D57 | Historical USER_APPROVED; superseded for commercial production | Local loopback remains engineering baseline |
| D66 | USER_APPROVED unchanged | Certification dual-source; not weakened by W0 |
| No-broker / authorises_order=false | Binding | Unchanged |

## 3. Workstreams (W0-01 .. W0-12)

| ID | Spec file | Focus |
|---|---|---|
| W0-01 | `01_IDENTITY_AUTHENTICATION_SPEC.md` | Registration, sessions, MFA, admin auth |
| W0-02 | `02_TENANT_ARCHITECTURE_SPEC.md` | Tenants, RLS, isolation examples |
| W0-03 | `03_CLOUD_INFRASTRUCTURE_SPEC.md` | Hosting, CDN, WAF, envs, costs (assumptions) |
| W0-04 | `04_DATABASE_STORAGE_SPEC.md` | Postgres, Redis, objects, SQLite baseline, migration design |
| W0-05 | `05_BACKEND_ARCHITECTURE_SPEC.md` | API monolith, middleware, engine bridge |
| W0-06 | `06_WORKER_ORCHESTRATION_SPEC.md` | Jobs, queues, retries, audit |
| W0-07 | `07_SECURITY_PRIVACY_SPEC.md` | Threat model, privacy, tests |
| W0-08 | `08_SUBSCRIPTION_ENTITLEMENT_SPEC.md` | Plans, PSP evaluation, quotas |
| W0-09 | `09_OBSERVABILITY_OPERATIONS_SPEC.md` | Logs, metrics, traces, alerts |
| W0-10 | `10_BACKUP_DISASTER_RECOVERY_SPEC.md` | RPO/RTO proposals, drills |
| W0-11 | `11_CICD_RELEASE_SPEC.md` | Pipelines, gates, rollback |
| W0-12 | `12_COST_CAPACITY_SPEC.md` | Capacity and cost scenarios |

Supporting: dependency map, tech decisions, owner decisions, risks, review report.

## 4. Existing system mapping (summary)

| Today | W0 target role |
|---|---|
| `platform/web` React/Vite | Customer SPA behind CDN |
| `platform/gtf_platform` FastAPI loopback | SaaS API monolith + auth/tenant middleware |
| Dual SQLite | Local/dev baseline; SaaS system of record = PostgreSQL |
| In-process jobs thread | External workers + Redis queue |
| Local `nse/data` files | Object storage + operator ingest (licence gated) |
| Loopback session | Engineering baseline only; SaaS uses W0-01 identity |
| `nse/` engines | Unchanged eligibility authority; imported by API/workers |

## 5. Design principles

1. Eligibility stays in `nse/` scanners/qualification; no duplicate engines.
2. Shared market data vs private tenant data is a hard boundary.
3. Tenant context from server session, never client-trusted body fields alone.
4. Fail closed on unknown/incomplete/fixture data labels.
5. Local mode remains a **baseline**, not a second commercial edition.
6. Unresolved owner choices stay questions (no invented approvals).
7. Specification never silently authorises spend or deploy.

## 6. Owner approval gates

| Gate | Topic | Status |
|---|---|---|
| A | Architecture completeness | Spec package for review |
| B | Security and tenant isolation review | Spec ready; not owner-passed |
| C | Database and migration review | Spec ready; not owner-passed |
| D | Cloud provider and region | OPEN (OD-BP-010) |
| E | Identity and authentication | OPEN (OD-BP-004) |
| F | Billing and entitlement | OPEN (OD-BP-005) |
| G | Data licensing / commercial dependency | OPEN (OD-BP-014/015) |
| H | Final W0 specification approval | Not granted |

Implementation authorisation must be recorded explicitly after gates A-H as applicable.

## 7. Verdict preview

See `17_W0_REVIEW_REPORT.md`. Expected: **W0_SPECIFICATION_READY_WITH_OPEN_DECISIONS**.
