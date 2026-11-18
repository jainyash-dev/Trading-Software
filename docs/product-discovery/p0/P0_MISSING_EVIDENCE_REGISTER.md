# P0 Batch 2 - Missing evidence register

**Date:** 2026-11-15  
**Canonical membership research window (D59):** 2020-12-31 .. 2025-12-31  
**Companion matrix:** `P0_HISTORICAL_COVERAGE_MATRIX.csv` (350 rows: 185 periods + 164 symbols + 1 window summary)  
**Certified member-dates:** 0

Classification vocabulary (as required): Existing evidence available | New official evidence required | Owner decision required | Engineering correction required | Not applicable | Permanently excluded with documented reason.

---

## ME-CA-D66 - Corporate-action completeness (critical path)

| Field | Value |
|---|---|
| Requirement | D66 dual-source completeness for every certified member-date |
| Scope | All 123,778 member-dates in window |
| Classification | **New official evidence required** then **Owner decision required** (per-window dual-hash markers) |
| On disk today | NSE API archives for 145 symbols (refused as completeness sources); `completeness.csv` absent; 0 reconciliation records; 0 approval markers |
| Effect | Blocks every certification row |

## ME-MEM-BACKLOG - Membership ledger decisions

| Field | Value |
|---|---|
| Requirement | Human `decision` ACCEPTED/REJECTED on blank ledger rows |
| Scope | 24 evidence-sufficient groups (91 rows); 14 insufficient (15 rows); 25 N/A count groups |
| Classification | **Owner decision required** (sufficient); insufficient also need **New official evidence** / identity resolution |
| On disk | `P0_MEMBERSHIP_BACKLOG.csv`; agents must not write ACCEPTED/REJECTED |
| Effect | 44,627 member-dates currently membership-unverified (summary 1.5.0) |

## ME-ID-1 / ME-ID-2 - BAJFINANCE and GRASIM ISIN joins

| ID | Scope | Classification | Detail |
|---|---|---|---|
| ME-ID-1 | BAJFINANCE INE296A01016 -> INE296A01024 | Owner decision required | MSEI notice states two dates; do not join |
| ME-ID-2 | GRASIM INE047A01013 -> INE047A01021 | Owner decision required | Same pattern |

## ME-MEM-DUMMY - Dummy seats (OD-MEM-2/3)

| Field | Value |
|---|---|
| Scope | DUMMYREL, DUMMYITC, DUMMYSIEMS, DUMMYTATAM, DUMMYHDLVR (~123 member-dates) |
| Classification | **Permanently excluded with documented reason** (unless owner invents a non-tradable rule) |
| Detail | No instrument records; do not invent ISINs; JIOFIN/ITCHOTELS/ENRIN/TMCV dummy-to-listed transitions |

## ME-PX-1 - BE/BZ-only stretches

| Field | Value |
|---|---|
| Scope | 260 member-dates (ADANIGREEN, ADANITRANS, JIOFIN, ITCHOTELS, ENRIN, TMCV, ...) |
| Classification | **Permanently excluded with documented reason** |
| Detail | `SOURCE_HAS_NO_EQ_ROW`; OD-PX-1 not approved to treat BE/BZ as EQ |

## ME-PX-2 - Unparsed price events

| Field | Value |
|---|---|
| Scope | CGPOWER 2016-03-15 scheme; VBL 2024-09-12 5-to-2 split (and other unparsed subjects) |
| Classification | **New official evidence required** |
| Detail | Do not invent ratios; parser cannot represent some subjects |

## ME-PX-3 - ADANIENSOL 2024-11-21

| Field | Value |
|---|---|
| Classification | Existing evidence available (market-move investigation) + optional **Owner decision required** for exception mechanism |
| Detail | Not a CA; fail-closed exclusion stands without an owner exception rule |

## ME-PX-4 - Muhurat / shortened session PREVCLOSE

| Field | Value |
|---|---|
| Scope | 700 member-dates |
| Classification | **Owner decision required** (optional rule) |
| Detail | Chain intact through held session; rule not adopted |

## ME-B11-P - Pre-2020-12-31 baseline

| Field | Value |
|---|---|
| Classification | **Not applicable** inside D59 research window; open if earlier membership is wanted |
| Detail | `IndexInclExcl.xls` is name-only through 2020-07-31 |

## ME-TV-1 - TradingView parity

| Field | Value |
|---|---|
| Classification | **New official evidence required** (chart exports) |
| Detail | External parity only; Yahoo screenshots are not substitutes |

## ME-ENGINEERING - Stale eligibility matrix membership column

| Field | Value |
|---|---|
| Classification | **Engineering correction required** (optional) |
| Detail | `P0_RESEARCH_ELIGIBILITY_MATRIX.csv` still carries pre-D65 membership wording in places; gate tallies in `P0_CERTIFICATION_SUMMARY.json` (1.5.0) and current `nifty100_universe.csv` (85 verified) are authoritative until an isolated 1.6.0 rebuild |

---

## Batch 2 acceptance

Coverage matrix separates the six requirement families. Largest gap is D66 corporate-action completeness. No silent fill of missing observations.
