# 10  -  Existing Repository Capability Map

**Audit date:** 2026-11-18  
**Method:** Repository inspection of `nse/`, `platform/`, `tests/`, docs and evidence. UI screens alone do not prove capability.

## Status vocabulary used here

| Label | Meaning |
|---|---|
| IMPLEMENTED | Code path exists |
| TESTED | Automated tests exist for the path |
| BROWSER_EVIDENCED | Fixture browser pack exercised UI |
| INDEPENDENTLY_REVIEWED | Review doc exists for a phase (not owner ACCEPTED) |
| ACCEPTANCE_READY | Phase closure claims engineering ready; owner ACCEPTED not assumed |
| OWNER_ACCEPTED | Explicit owner acceptance stamp found |
| CERTIFIED | Historical data certification gate passed |

## 1. Stack today

| Layer | Reality |
|---|---|
| Frontend | React 19 + TS + Vite + Tailwind in `platform/web` |
| API | FastAPI in `platform/gtf_platform` (~59 OpenAPI paths), loopback |
| Engines | `nse/zone-engine`, `nse/mtf-freshness`, `nse/research/*` |
| DB | Dual SQLite (platform + research journal/scans) |
| Jobs | In-process thread; optional scheduler |
| Infra | No Docker/CI cloud configs found for SaaS |
| Auth | Loopback session bootstrap; not customer SaaS auth |
| Billing | Absent |
| Broker | Absent / disabled providers |

## 2. Capability map by MS module

| MS | Module | Implemented | Tested | Browser | Ind. review | Acceptance-ready claim | Owner-accepted | Certified |
|---|---|---|---|---|---|---|---|---|
| 001 | Data Centre | Yes (local files/acquisition) | Yes | Partial (data UI) | P0 docs | Engineering builders yes | No for SaaS | No |
| 002 | Instruments/Universe | Yes | Yes | Partial | P0 membership reviews | Partial ACCEPTED rows | Membership rows via D65/D67 | Member-dates 0 |
| 003 | CA & Calendar | Yes partial | Yes | Partial | P0 CA docs | Calendar strong; CA completeness no | D58 calendar; D66 policy | CA windows 0 |
| 004 | Quality & Cert | Builder yes | Yes | Data readiness UI | P0 final cert report | Builder only | No certification | **0 member-dates** |
| 005 | Overview | Yes | Yes | P10 | P10 | P10 claim fixture | No | N/A |
| 006 | Charting | Yes | Yes | P2/P10 | P2-P4 | Yes w/ limitations | No | N/A |
| 007 | Scanner | Yes | Yes | P3 | P2-P4 | Yes w/ limitations | No | Uses unverified/fixture often |
| 008 | Fundamentals | No | No | No | No | No | No | No |
| 009 | Sector intel | Degraded UNAVAILABLE | N/A | Shows unavailable | No | Honest degrade | No | No |
| 010 | Trade planning | Yes | Yes | P4 | P2-P4 | Yes w/ limitations | No | N/A |
| 011 | Portfolio & risk | Yes | Yes | P10 | P5 | P5 ACCEPTANCE_READY | Not stamped | N/A |
| 012 | Journal & perf | Yes | Yes | P10 | P6 | P6 ACCEPTANCE_READY | Not stamped | N/A |
| 013 | Backtest | Engine yes; API thin; UI partial | Engine yes | Partial | Limited | Not full product | No | No R4 |
| 014 | AI assistant | Deterministic explain only | Explain tests | Partial | No LLM | Not LLM assistant | No | N/A |
| 015 | Alerts/automation | Research alerts + jobs partial | Partial | Jobs UI partial | No | No | No | N/A |
| 016 | Identity SaaS | **No** | Loopback security yes | N/A | No | No | No | N/A |
| 017 | Billing | **No** | No | No | No | No | No | N/A |
| 018 | Cloud ops | **No** | repo validation only | No | No | No | No | N/A |

## 3. Evidence anchors

- Research tests: `tests/test_research_*.py`, `python3 -m nse.validation.run_all`
- Platform tests: `platform/tests/`
- Web tests: `platform/web` vitest
- Browser: `docs/implementation/evidence/p2-p4-browser/`, `p10-browser/` (fixture)
- P5/P6 closure: `docs/product-discovery/p5/P5_CLOSURE_REPORT.md`, `p6/P6_CLOSURE_REPORT.md`
- P0 cert: `docs/product-discovery/p0/P0_FINAL_CERTIFICATION_REPORT.md`  -  not certified
- OpenAPI: `platform/gtf_platform/openapi.json`

## 4. Explicit absences

SaaS registration, multi-tenant RLS, Postgres/Redis/object-storage production, CDN/WAF, billing, LLM provider, paper API, analytics API, Docker/CI cloud, broker execution.

## 5. Doc staleness warning

`docs/product-discovery/00_EXECUTIVE_SUMMARY.md` and `03_REPOSITORY_IMPLEMENTATION_AUDIT.md` (2026-11-10) understate later P2-P6/P10 platform work. Prefer OpenAPI + closure reports + this map for current software capability. Prefer P0 final certification report for data certification truth.
