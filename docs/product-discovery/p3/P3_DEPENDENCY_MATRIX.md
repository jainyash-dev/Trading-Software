# GTF P3 - Dependency matrix

**Date:** 2026-11-15  
**Categories:** `INDEPENDENT` | `INTERFACE_DEPENDENT` | `P0_BLOCKED` | `P7_BLOCKED`

| Req ID | Description | Category | Upstream | Impl | Validation | Release restriction |
|---|---|---|---|---|---|---|
| P3-R01 | Opportunity data model + migration | INDEPENDENT | Platform SQLite conventions | COMPLETE | Unit/API | None |
| P3-R02 | Lifecycle states + transition history | INDEPENDENT | Product workflow (not GTF verdicts) | COMPLETE | Transition tests | Workflow ≠ eligibility |
| P3-R03 | Research notes on opportunities | INDEPENDENT | Opportunity id | COMPLETE | API tests | Notes ≠ methodology |
| P3-R04 | Watchlist CRUD enhancements (delete, reason, note) | INDEPENDENT | Existing watchlist tables | COMPLETE | API + UI tests | Watchlist ≠ eligibility |
| P3-R05 | Opportunity dashboard UI | INDEPENDENT | Opportunity APIs | COMPLETE | Vitest + build | Fixture labelling required |
| P3-R06 | Filters / search / sort | INDEPENDENT | Opportunity list API | COMPLETE | API + UI | Filters hide; do not rewrite status |
| P3-R07 | Organizational priority score | INDEPENDENT | Transparent factors only | COMPLETE | Unit tests | Label non-authoritative; no return claim |
| P3-R08 | Ingest from stored scan envelope | INTERFACE_DEPENDENT | `scan_result` + research envelope | COMPLETE | Ingest tests | Preserve provenance + status |
| P3-R09 | Source quality propagation | INTERFACE_DEPENDENT | Scan `fixture` + dataset identity | COMPLETE | Quality tests | Never promote exploratory→certified |
| P3-R10 | Navigate Opportunity → Analysis (P2) | INTERFACE_DEPENDENT | Analysis URL contract | COMPLETE | Navigation vitest | No second chart library |
| P3-R11 | Entry point toward P4 plans | INTERFACE_DEPENDENT | Existing `#/plans` | COMPLETE | Link only | Do not expand P4 |
| P3-R12 | Production historical opportunity discovery on certified data | P0_BLOCKED | P0 certified symbol-dates | DEFERRED | - | Gate: refuse CERTIFIED label while certified=0 |
| P3-R13 | Certified historical opportunity coverage / counts | P0_BLOCKED | P0 certification summary | DEFERRED | - | Show exploratory/unavailable honestly |
| P3-R14 | Performance-based ranking / success-rate claims | P7_BLOCKED | Quantitative validation | DEFERRED | - | Absent from UI and docs claims |
| P3-R15 | Similar historical setups matcher (OI-007) | P7_BLOCKED / out of initial scope | Validated PIT matcher | DEFERRED | - | Omitted |
| P3-R16 | Sector filter | P0_BLOCKED / degraded | Sector source (D6) | DEFERRED | - | Unavailable until sector source |
| P3-R17 | Broker / order path | Disallowed | - | N/A | Architecture | `authorises_order` false |
