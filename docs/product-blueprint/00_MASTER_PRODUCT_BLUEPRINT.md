# 00  -  Master Product Blueprint

**Programme:** GTF Assignment 00  -  Repository Audit, Product Discovery and Cloud Web SaaS Architecture  
**Date:** 2026-11-18  
**Authority class of this package:** Product/architecture foundation. OD-BP-001 is `USER_APPROVED` for commercial SaaS direction. Commercial cloud **implementation** remains NOT_AUTHORIZED. W0 foundation specs are authorised for specification only.  
**Working-tree rule:** Documentation under `docs/product-blueprint/` (and decision-log acceptance evidence). No feature code, schema, API, deploy, purchase, broker, stage, commit, push, reset, clean, stash or revert unless separately authorised.

## 1. Purpose

This package is the authoritative product and architecture foundation for building a commercially distributable, browser-based, cloud-hosted SaaS web application for Global Trading Framework (GTF).

It reconciles:

1. Owner-confirmed product boundaries stated in Assignment 00 (this session).
2. Existing repository implementation (`nse/`, `platform/`, tests, evidence).
3. Existing owner decisions in `nse/docs/DECISION_LOG.md` (notably **OD-BP-001**, historical D57, D66, D42).
4. Existing product requirements and capability IDs that must be preserved.

## 2. Confirmed product scope (Assignment 00)

| Item | Boundary |
|---|---|
| Product | Global Trading Framework (GTF) |
| Delivery | Browser-based web application |
| Deployment | Cloud-hosted SaaS |
| Market | NSE cash equities |
| Initial customer | Individual traders |
| Initial research universe | Nifty 100 (point-in-time membership) |
| Trading style | Positional and swing |
| Execution | Manual through external broker platforms |
| Access | Browser registration and authentication |
| Customer data | Securely isolated per customer / tenant |
| Objective | Professional, evidence-based stock research and trading decision support |
| Order execution | **Not authorised**  -  no broker order placement |

### Explicitly excluded packaging

Do not design production GTF around Tauri, Electron, desktop installers, desktop-only workflows, a local desktop database as the primary production architecture, or desktop update mechanisms. The primary customer interface is a hosted web application.

## 3. Authority (must read)

| Source | Status | Effect on this blueprint |
|---|---|---|
| **OD-BP-001** Commercial cloud SaaS | `USER_APPROVED` 2026-11-18 | Controlling decision for **commercial production** architecture. See `ADR_OD-BP-001.md` |
| **D57** Local-first web application | `USER_APPROVED` 2026-11-09; **superseded for commercial production by OD-BP-001** | Historical record preserved. Local/dev/test/migration baseline may continue; not commercial production target |
| Assignment 00 SaaS boundaries | Owner-stated; now aligned with OD-BP-001 | Target product direction for architecture and module specs |
| Prior `PRODUCT_REQUIREMENTS.md` | Local-first, one Mac, multi-user/SaaS out of initial release | Superseded for commercial production scope by OD-BP-001; remains evidence of prior local product contract |
| Rulebook / Pine / trading invariants | Unchanged | SaaS packaging must not invent or weaken eligibility rules |
| D66 CA completeness | `USER_APPROVED` | Unchanged. Certification stays dual-source; do not weaken |

**Authorisation boundary:** OD-BP-001 does **not** authorise cloud spend, deployment, database migration, API/schema changes, provider commitments, or commercial implementation. W0 foundation specifications are **authorised for specification only**.

Verdict for this package: **BLUEPRINT_READY_WITH_OPEN_DECISIONS** (OD-BP-001 closed; other commercial ODs remain - see `14_BLUEPRINT_REVIEW_REPORT.md`).

## 4. Document map

| File | Contents |
|---|---|
| `01_PRODUCT_REQUIREMENTS.md` | SaaS product requirements, preserved FR IDs, non-goals |
| `02_MODULE_CATALOGUE.md` | 18-module catalogue summaries |
| `03_SYSTEM_ARCHITECTURE.md` | Modular monolith + workers, cloud topology |
| `04_DATA_ACCURACY_GOVERNANCE.md` | Source→result chain, D66, data states |
| `05_MASTER_REQUIREMENTS_REGISTER.csv` | Traceable requirement register |
| `06_MODULE_DEPENDENCY_MAP.md` | Dependencies and build order |
| `07_TECHNOLOGY_DECISION_REGISTER.md` | Tech choices and alternatives |
| `08_CLOUD_SECURITY_AND_TENANCY.md` | Multi-tenant security model |
| `09_COMMERCIAL_READINESS.md` | Billing, privacy, compliance review needs |
| `10_EXISTING_REPOSITORY_CAPABILITY_MAP.md` | Evidence-based capability map |
| `11_EXISTING_PENDING_WORK_RECONCILIATION.md` | P0-P11 / product prompt reconciliation |
| `12_SPECIFICATION_PROGRAMME_ROADMAP.md` | Spec→build programme |
| `13_OWNER_DECISION_REGISTER.md` | Decisions required before implementation |
| `14_BLUEPRINT_REVIEW_REPORT.md` | Review, risks, verdict |
| `modules/MS-001` … `MS-018` | Module specifications |

## 5. Recommended architecture (summary)

**Pattern:** Modular monolith application API with independently scalable workers.

| Layer | Recommendation |
|---|---|
| Frontend | React + TypeScript SPA, CDN, responsive layouts |
| API | FastAPI application API / gateway (evolve from `platform/gtf_platform`) |
| Engines | Keep deterministic research engines in `nse/` as shared calculation library; no UI reimplementation of gates |
| Primary DB | PostgreSQL (shared market schemas + tenant-scoped customer schemas/tables) |
| Cache / queues | Redis |
| Files | Object storage for raw archives, reports, attachments |
| Workers | Ingestion, validation, CA processing, candles, scans, backtests, alerts, maintenance, recovery |
| Tenancy | Row-level tenant isolation from day one, with cross-tenant security tests |
| Auth | Customer registration, authentication, session/token model suitable for public HTTPS (commercial; local loopback session remains for engineering baseline) |

Desktop shells remain rejected. Local loopback mode may remain a **developer / owner research** configuration, not the commercial primary.

## 6. Module catalogue (18)

1. Data Centre & Source Management  
2. Instrument & Universe Management  
3. Corporate Actions & Market Calendar  
4. Data Quality & Certification  
5. Market Overview  
6. Charting & Technical Analysis  
7. Opportunity Scanner  
8. Fundamental & Company Research  
9. Sector & Market Intelligence  
10. Trade Planning  
11. Portfolio & Risk  
12. Trading Journal & Performance  
13. Backtesting & Strategy Validation  
14. AI Research Assistant  
15. Monitoring, Alerts & Automation  
16. Identity, Access & Customer Management  
17. Subscription, Licensing & Billing  
18. Application, Infrastructure & Release Operations  

## 7. Existing capability (one-line)

Strong local research engines and a substantial single-user browser product (`platform/`) exist. Multi-tenant SaaS identity, billing, Postgres/Redis/object-storage production topology, CDN/WAF and commercial compliance are **not** implemented. P0 historical certification under D66 remains **0 certified member-dates**.

## 8. Preservation rules

Preserve and do not silently rewrite:

- Rulebook citations and trading invariants  
- D66 dual-source completeness  
- Qualification pathway (`scanner` → `qualification` → MTF overlay eligibility)  
- Journal as portfolio/cap authority  
- Existing FR / capability IDs (FR-*, MI-*, SD-*, GTF-*, TP-*, PR-*, TJ-*, etc.)  
- Test and browser evidence classifications (fixture ≠ certified)  
- Status vocabulary (`ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING`, MANUAL_REVIEW, BLOCKED, DATA_INSUFFICIENT)

## 9. Non-claims

This blueprint does **not**:

- Approve itself  
- Authorise cloud spend or provider contracts  
- Claim tenant isolation is implemented  
- Claim P0 certification  
- Claim profitability or predictive skill  
- Authorise broker order execution  

## 10. Next owner action

1. Review remaining open decisions in `13_OWNER_DECISION_REGISTER.md` (especially OD-BP-004/005/008/010/014/015).  
2. Review `docs/product-blueprint/w0/` (W0 foundation specs drafted; Gate H open).  
3. Close Gates D-G (region, identity, billing, licensing) then Gate H before any implementation authorisation.
