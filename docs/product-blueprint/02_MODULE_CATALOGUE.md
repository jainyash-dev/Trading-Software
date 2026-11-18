# 02  -  Module Catalogue

Eighteen product modules for GTF SaaS. Detailed specs: `modules/MS-XXX_*.md`.

| MS | Module | Purpose | Data class | Notes |
|---|---|---|---|---|
| MS-001 | Data Centre & Source Management | Acquire, archive and catalogue market source files | Shared market | Workers: ingest |
| MS-002 | Instrument & Universe Management | Identity intervals and Nifty 100 membership | Shared market | Depends on MS-001 |
| MS-003 | Corporate Actions & Market Calendar | CA events and trading calendar | Shared market | D66 critical |
| MS-004 | Data Quality & Certification | Validation findings and P0 certification gates | Shared market | Depends on 1-3 |
| MS-005 | Market Overview | Session readiness and market context screens | Tenant UI over shared data | Degraded index/sector |
| MS-006 | Charting & Technical Analysis | Candles, zones, drawings, overlays | Tenant drawings; shared candles | No UI gate recompute |
| MS-007 | Opportunity Scanner | Scans, candidates, opportunities, watchlists | Tenant jobs + shared engines | Core product |
| MS-008 | Fundamental & Company Research | Company filings/fundamentals research | Mostly greenfield | OD for sources |
| MS-009 | Sector & Market Intelligence | Sector/breadth/regime context | Degraded until sources | D6 open historically |
| MS-010 | Trade Planning | Plans from candidates; approve/reject | Tenant private | authorises_order=false |
| MS-011 | Portfolio & Risk | Positions, caps, exposure | Tenant private over journal | D42 caps |
| MS-012 | Trading Journal & Performance | Orders, fills, charges, notes, exports | Tenant private | Journal authority |
| MS-013 | Backtesting & Strategy Validation | Historical simulation with manifests | Tenant jobs | No profit claim |
| MS-014 | AI Research Assistant | Explain stored research with citations | Tenant private | Never overrides gates |
| MS-015 | Monitoring, Alerts & Automation | Jobs, schedules, notifications | Tenant + platform | Isolation required |
| MS-016 | Identity, Access & Customer Management | Registration, auth, tenants, admin | Platform + tenant | New for SaaS |
| MS-017 | Subscription, Licensing & Billing | Plans, payments, entitlements | Platform + tenant | New for SaaS |
| MS-018 | Application, Infrastructure & Release Operations | Cloud, CI/CD, DR, observability | Platform | New for SaaS |


## Per-module definition standard

Each `modules/MS-*.md` defines: purpose/boundaries; features/submodules; user workflows; frontend screens; backend services/APIs; database entities/ownership; workers/schedules; external integrations; security/tenant rules; data quality/provenance; testing/acceptance; current implementation; missing capabilities; dependencies; open questions.

## Capability ID crosswalk (preserve)

| Module | Primary existing IDs |
|---|---|
| MS-001-004 | FR-1.*, DS-*, MI-010-012 |
| MS-005 | FR-2.*, MI-001-014 |
| MS-006 | FR-4.*, OI-003 |
| MS-007 | FR-3.*, SD-*, OI-*, GTF-* |
| MS-008 | New SFR-FUND-* |
| MS-009 | MI-004-008, SFR-SECT-* |
| MS-010 | FR-5.*, TP-* |
| MS-011 | FR-6.*, PR-* |
| MS-012 | FR-7.*, TJ-* |
| MS-013 | FR-8.*, QR-* |
| MS-014 | FR-11.*, AI-* |
| MS-015 | FR-10.*, EX-* (non-broker) |
| MS-016 | SFR-ID-* |
| MS-017 | SFR-BILL-* |
| MS-018 | FR-12.*, SFR-OPS-* |
