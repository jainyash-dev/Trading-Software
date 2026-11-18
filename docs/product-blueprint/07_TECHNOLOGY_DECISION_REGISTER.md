# 07 - Technology Decision Register

Status key: `RECOMMENDED` (blueprint), `CURRENT` (repo today), `DECLINED`, `PENDING_OWNER`, `OWNER_DIRECTION`.

**Packaging authority:** OD-BP-001 (`USER_APPROVED` 2026-11-18) sets commercial production as browser cloud SaaS. Specific providers and purchases remain separately approved. D57 remains the historical local-first decision and the engineering-baseline reference.

| ID | Area | Choice | Status | Rationale | Alternatives |
|---|---|---|---|---|---|
| TD-PKG-1 | Commercial packaging | Browser-based cloud multi-tenant SaaS | OWNER_DIRECTION (OD-BP-001) | Commercial production architecture | Local-first as production (superseded by OD-BP-001) |
| TD-PKG-2 | Local/dev packaging | Loopback browser app / local files+SQLite | CURRENT engineering baseline | OD-BP-001 retains local-first for dev/test/migration | Remove local mode (not required) |
| TD-FE-1 | Frontend | React + TypeScript + Vite | RECOMMENDED + CURRENT | Existing `platform/web`; component SPA | Svelte/Vue (migration cost); server-only HTML (insufficient UX) |
| TD-FE-2 | Charts | TradingView Lightweight Charts | RECOMMENDED + CURRENT | Already integrated | KLineChart fallback; Advanced Charts unsuitable licensing/product fit |
| TD-FE-3 | CSS | Tailwind (existing v4) | RECOMMENDED + CURRENT | Present in web app | CSS Modules only |
| TD-BE-1 | API | FastAPI + Uvicorn | RECOMMENDED + CURRENT | OpenAPI; Python beside engines | Django/Flask; Node (duplicates language boundary) |
| TD-BE-2 | Architecture | Modular monolith + workers | RECOMMENDED | Fits team size; shared transactions early | Microservices-first (ops heavy); pure desktop (declined) |
| TD-ENG-1 | Engines | Keep `nse/` Python stdlib library | RECOMMENDED + CURRENT | A5; tested eligibility | Rewrite in TS (rejected) |
| TD-DB-1 | Primary DB (SaaS) | PostgreSQL managed | RECOMMENDED | Multi-tenant, RLS, PITR | SQLite primary SaaS (declined); MySQL |
| TD-DB-2 | Local/dev DB | Dual SQLite | CURRENT | Engineering baseline | Migrate only after separate authorisation |
| TD-CACHE-1 | Cache/queue | Redis managed | RECOMMENDED | Sessions/rate limits/queues | RabbitMQ-only; DB polling only |
| TD-OBJ-1 | Object storage | S3-compatible | RECOMMENDED | Immutable raw archives | Disk on API VM only (declined for SaaS) |
| TD-AUTH-1 | Auth | Email/password + session cookies or OIDC | PENDING_OWNER (OD-BP-004) | Public SaaS needs real identity | Loopback bootstrap (CURRENT local baseline) |
| TD-AUTH-2 | MFA | TOTP MFA | PENDING_OWNER (OD-BP-004) | Security baseline | WebAuthn later |
| TD-PAY-1 | Payments | Stripe or Indian-capable PSP | PENDING_OWNER (OD-BP-005) | No card storage in GTF | Manual invoicing only |
| TD-HOST-1 | Cloud region | India-preferring region | PENDING_OWNER (OD-BP-010) | Data residency | Other regions |
| TD-HOST-2 | Compute | Containers on managed service | RECOMMENDED | API+workers | Serverless-only (long jobs poor fit) |
| TD-CDN-1 | CDN+WAF | Provider CDN + WAF | RECOMMENDED | Public exposure | None (declined) |
| TD-CI-1 | CI/CD | GitHub/GitLab CI or equivalent | RECOMMENDED | Tests+migrate+deploy | Manual (declined) |
| TD-DESK-1 | Desktop shells | Not commercial product | DECLINED | OD-BP-001 + historical D57 anti-Tauri/Electron | Tauri/Electron |
| TD-BROKER-1 | Broker APIs | Disabled / absent | DECLINED for execution | No order execution | Read-only broker sync (future OD only) |
| TD-AI-1 | LLM provider | Optional adapter default off | PENDING_OWNER | OQ-2 / OD-BP-017 | Deterministic explain only (CURRENT) |

## Migration note

Local SQLite remains valid for owner/dev research checkouts under OD-BP-001's engineering baseline. SaaS production system of record is intended to be PostgreSQL + object storage. Dual-mode support is an engineering programme. Database migration and production cutover require separate owner authorisation (not granted by OD-BP-001).
