# 01  -  Product Requirements (SaaS target)

**Status:** Blueprint requirements for Assignment 00. Not stamped into `DECISION_LOG.md`.  
**Supersedes for target scope:** local-only initial-release exclusions in `docs/product/PRODUCT_REQUIREMENTS.md` §§1 and 3 (multi-user / hosted SaaS).  
**Does not supersede:** Rulebook, D66, trading invariants, no-broker rule, D42 caps (as methodology/product risk rules).

## 1. Product identity

| Item | Requirement |
|---|---|
| Name | Global Trading Framework (GTF) |
| Category | Commercially distributable browser SaaS for NSE research and trading decision support |
| Initial customers | Individual traders |
| Market | NSE cash equities |
| Style | Positional and swing |
| Universe (initial) | Nifty 100 point-in-time membership |
| Timeframes | Monthly, Weekly, Daily (MIT). WIT remains blocked until separately authorised |
| Execution | Customer places orders on external broker platforms; GTF records plans, orders and fills typed by the customer |
| Interface | Hosted web application in supported browsers |
| Tenancy | Per-customer isolation |
| Order routing | Forbidden |

## 2. What the product is

Customers can, within entitlement:

1. Register, authenticate and manage a workspace.
2. See whether shared market datasets and their private research artefacts are usable and fresh.
3. Scan the supported universe (or entitled subset) after session close, on demand, or historically.
4. Read why each symbol passed, failed, or needs manual review.
5. Open Monthly / Weekly / Daily charts with engine zones and private drawings.
6. Build trade plans from stored candidates with risk and size checks.
7. Record manual broker orders and fills.
8. Watch positions against portfolio and risk rules (including owner-stated 10/10 caps until product policy changes).
9. Keep a journal separating plan, order, fill, charges and reviews.
10. Run backtests with dataset, execution model and run manifest attached.
11. Use optional AI research assistance that explains stored research and never overrides eligibility.
12. Export and delete their private data.
13. Subscribe and manage billing entitlements.

## 3. What the product is not

- An order router, broker client, or unattended trading system.
- A second copy of the Zone Engine, MTF overlay, or G0-G8.
- A desktop-installed primary product (Tauri / Electron / installers).
- A source of win rates, expectancy, drawdown or profit claims without a real, reproducible run under defined gates.
- An intraday / WIT / F&O product in the initial SaaS catalogue.
- A guarantee of trading profitability.

## 4. Actors and roles

| Role | Responsibility |
|---|---|
| Customer (trader) | Uses research, plans, journal; places external broker orders; owns private data |
| Tenant admin (may equal customer for individual plans) | Manages workspace members if multi-seat later; billing contact |
| Platform operator / GTF admin | Operates shared market data, infra, support; audited break-glass access |
| Research engine | Deterministic eligibility authority; not a user |

Initial commercial plan: individual traders (single-seat tenants). Multi-seat organisational tenancy is an extension requiring OD-BP-003.

## 5. Preserved principles (adapted for SaaS)

| Id | Principle | SaaS consequence |
|---|---|---|
| P1 | Deterministic eligibility | Only scanner/qualification pathway assigns gates and status |
| P2 | Explainability | Gate outcomes, reasons, evidence references visible |
| P3 | Reproducibility | Run manifests: dataset hash, code revision, methodology version, config |
| P4 | Point-in-time | Historical `as_of` uses only `known_at` information |
| P5 | One methodology | Platform calls engines; UI does not reimplement zones/gates |
| P6 | Human control | `authorises_order` stays false |
| P7 | Data integrity over convenience | Missing/stale/fixture/provisional never presented as certified or PASS |
| P8 | Unknown stays unknown | DATA_INSUFFICIENT / MANUAL / UNAVAILABLE preserved |
| P9 | Traceable operations | Tenant-scoped audit for scans, plans, orders, fills, exports, deletes, admin access |
| P10 | No unsupported performance claims | Software completion ≠ strategy validation ≠ profitability |
| P11 | Tenant isolation | No cross-tenant reads/writes via API, cache, jobs, files or support tools without audited break-glass |
| P12 | Shared vs private data | Market data shared read-only; customer journals/plans/settings private |

## 6. Functional requirements by module family

Preserve existing FR numbering from `docs/product/PRODUCT_REQUIREMENTS.md` where behaviour is unchanged. New SaaS IDs use `SFR-*`.

### 6.1 Data and certification (Modules 1-4)  -  FR-1.* + SFR-DATA-*

- FR-1.1-1.11 remain binding for market-data behaviour.
- SFR-DATA-01: Shared market archives live in object storage with immutable raw objects and content hashes.
- SFR-DATA-02: Certification labels (provisional / certified / blocked) are first-class and visible in API/UI.
- SFR-DATA-03: D66 dual independent official CA sources required for completeness windows; single source never suffices.
- SFR-DATA-04: Fixture and synthetic datasets cannot enter customer-facing "certified" modes.

### 6.2 Research terminal (Modules 5-9)  -  FR-2, FR-3, FR-4 + gaps

- FR-2.* overview; index/sector series remain UNAVAILABLE until sources authorised.
- FR-3.* scanner/discovery; WIT blocked.
- FR-4.* charting; drawings are tenant-private.
- SFR-FUND-01: Fundamental & company research module is largely greenfield (Module 8).
- SFR-SECT-01: Sector & market intelligence remains degraded until D6 / sector source decisions.

### 6.3 Planning, portfolio, journal, backtest (Modules 10-13)

- FR-5.* plans; approval never places orders.
- FR-6.* portfolio/risk; D42 10/10 caps remain unless owner changes product policy for SaaS.
- FR-7.* journal; research journal remains accounting authority.
- FR-8.* backtest; no profitability claim without R4-class evidence.
- SFR-PERF-01: Performance analytics are descriptive unless a validated strategy gate is separately approved.

### 6.4 AI, monitoring (Modules 14-15)

- FR-11.* assistant constraints; AI never overrides eligibility.
- FR-10.* scheduling/alerts; tenant-scoped delivery.
- SFR-ALERT-01: Alert content must not leak other tenants' symbols/plans via shared channels misconfiguration.

### 6.5 Identity, billing, ops (Modules 16-18)  -  largely new

| Id | Requirement |
|---|---|
| SFR-ID-01 | Email/password or approved IdP registration with verified email |
| SFR-ID-02 | Session/token auth over HTTPS; CSRF/XSS protections appropriate to public web |
| SFR-ID-03 | Every data API requires authenticated tenant context |
| SFR-ID-04 | Password reset, session revocation, MFA policy (MFA strength = OD-BP-004) |
| SFR-BILL-01 | Subscription plans and entitlements gate features and quotas |
| SFR-BILL-02 | Payment provider integration (provider = OD-BP-005); no card data stored in GTF DB |
| SFR-BILL-03 | Entitlement checks server-side; UI hiding is not enforcement |
| SFR-OPS-01 | CDN + WAF + TLS for public endpoints |
| SFR-OPS-02 | Backup/restore with tenant-aware recovery runbooks |
| SFR-OPS-03 | Customer data export and deletion (GDPR-like / Indian DPDP review  -  OD-BP-006) |
| SFR-OPS-04 | Observability: metrics, logs, traces with PII redaction |

## 7. Non-functional requirements

| Id | Requirement |
|---|---|
| NFR-SaaS-1 | Target availability objective set after OD-BP-007 (proposed starter: 99.5% monthly for control plane; research jobs best-effort) |
| NFR-SaaS-2 | RPO/RTO targets set after OD-BP-007 |
| NFR-SaaS-3 | Cross-tenant isolation tested in CI (negative tests mandatory) |
| NFR-SaaS-4 | Secrets in managed secret store; no secrets in git |
| NFR-SaaS-5 | `nse/` remains free of network and broker imports |
| NFR-SaaS-6 | Performance budgets measured; do not invent numbers here |
| NFR-R1-R5 | Existing release gates retained as research trust gates; SaaS launch ≠ R1 certified |

## 8. Data states customers must see

| State | Meaning | UI/API rule |
|---|---|---|
| MISSING | Required input absent | Block dependent actions; show reason |
| STALE | Data older than policy | Label STALE; do not invent fresh prices |
| PROVISIONAL | Research-allowed, not certified | Banner; cannot claim CERTIFIED |
| FIXTURE | Synthetic/test | Never customer production default |
| INCOMPLETE | Partial coverage | Completeness flags required |
| FAILED | Validation failed | Quarantine; fail closed |
| CERTIFIED | Passed certification gates including D66 where applicable | Only after evidence |

## 9. Acceptance for requirements document

- OD-BP-001 accepted commercial SaaS production scope (2026-11-18). Implementation, spend and deploy remain separately authorised.
- No implementation authorised solely by existence of this file or by OD-BP-001 alone.
