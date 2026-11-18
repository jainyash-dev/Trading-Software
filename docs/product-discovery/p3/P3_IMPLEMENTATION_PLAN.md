# GTF P3 - Opportunity Intelligence implementation plan

**Date:** 2026-11-15  
**Phase:** GTF P3 (Opportunity Intelligence). Not Product Prompt 03. Crosswalk: Prompt 05 / OI-001…OI-008.  
**Governance chair:** `gtf-autonomous-project-lead`  
**Status after Batch 0:** plan accepted; independent and interface-dependent work proceeds.

## 1. Verified baseline

| Item | Evidence |
|---|---|
| Branch / HEAD | `main` / `69858d07ccb016b74bc1d518b66b9948656ad6cf` |
| Working tree | Heavily dirty (P0/P1/P2 and unrelated). No staging or commits by P3. |
| P0 | `P0_INCOMPLETE`: 123,778 member-dates; **0 certified**; 73,366 exploratory-only (`P0_CERTIFICATION_SUMMARY.json`) |
| P1 | `P1_COMPLETE_WITH_LIMITATIONS` |
| P2 | `P2_COMPLETE_WITH_LIMITATIONS` - Analysis URL + candle quality reusable |
| Existing platform | Scanner ingest, watchlists CRUD (no delete), overview, analysis, plans |
| Opportunity entity | **Absent** before P3 |
| Eligibility authority | Unchanged: `pipeline.run → scanner → qualification` in `nse/` |

## 2. Architectural decisions (AUTO_APPROVED, level C)

| ID | Decision | Rationale |
|---|---|---|
| P3-D1 | Opportunity is **workflow metadata** referencing a stored scan candidate (`scan_key` + `symbol` + `zone_id`), not a second eligibility engine | Preserves canonical authority (OI-001, AR invariants) |
| P3-D2 | `canonical_status` is an immutable snapshot copied from the stored envelope at ingest | Workflow transitions never rewrite GTF status |
| P3-D3 | Source quality labels: `FIXTURE` / `EXPLORATORY` / `UNKNOWN` / `UNAVAILABLE`. `CERTIFIED` is reserved and never assigned while P0 has 0 certified dates | Honest data-quality propagation |
| P3-D4 | Reuse watchlist tables; add delete, per-symbol reason/note/added_at via migration | FR-3.7; avoid duplicate list model |
| P3-D5 | Organizational priority score is non-authoritative descriptive ordering only | No P7 performance claims |
| P3-D6 | New hash route `opportunities`; deep-link to existing `#/analysis?...` | No parallel chart stack |
| P3-D7 | Ingest from stored `scan_result` only; production certified discovery remains P0-gated | Interface-dependent + P0_BLOCKED split |

## 3. Batch plan

| Batch | Scope | Category mix |
|---|---|---|
| 0 | Discovery, plan, dependency matrix | - |
| 1 | Opportunity + notes + history + migration `004` | INDEPENDENT / INTERFACE_DEPENDENT |
| 2 | Watchlist delete, symbol metadata, UI | INDEPENDENT |
| 3 | Lifecycle transitions + audit | INDEPENDENT |
| 4 | Opportunities dashboard UI | INDEPENDENT |
| 5 | Scan ingest adapter + readiness gates | INTERFACE_DEPENDENT / P0_BLOCKED gated |
| 6 | Filters + organizational priority | INDEPENDENT / P7_BLOCKED claims deferred |
| 7 | P2 navigation + UX | INTERFACE_DEPENDENT |
| 8 | Security, reliability, validation | - |
| 9 | Independent review + certification report | - |

## 4. Ownership - P3-owned paths

- `platform/gtf_platform/opportunity/`
- `platform/gtf_platform/db.py` (migration 004 only)
- `platform/gtf_platform/store.py` (watchlist delete / symbol metadata)
- `platform/gtf_platform/routes.py` (opportunity + watchlist delete routes)
- `platform/gtf_platform/openapi.json` (regenerated)
- `platform/tests/test_opportunity*.py` (new)
- `platform/web/src/features/opportunities/`
- `platform/web/src/features/watchlists/` (enhancements)
- `platform/web/src/navigation/` (route + query allowlist)
- `platform/web/src/types/contracts.ts` (types)
- `docs/product-discovery/p3/*`

**Avoid:** `nse/data/**`, `nse/research/p0*`, `nse/sources/**`, P0 membership/CA CSVs, Rulebook/Pine.

## 5. Stop / gate rules

- Do not invent certified scanner results.
- Do not claim ranking predicts returns (P7).
- Do not change methodology or resolve R-5 / OD-CA-1.
- Do not commit or push.
- Do not overwrite concurrent P0/P1/P2 file ownership beyond the listed shared touch points.
