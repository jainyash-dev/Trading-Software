# P0 Batch 7 - Corporate-action acquisition pilot recommendation

**Date:** 2026-11-15
**Status:** RECOMMENDATION ONLY. Not authorized. Nothing downloaded. This is an engineering recommendation, not an owner decision.
**Basis:** `P0_CA_SOURCE_FEASIBILITY_AUDIT.md`, `P0_CA_PROVIDER_ACCESS_MATRIX.csv`, D66, ED-56.

## 1. Purpose

Answer the three open feasibility questions using the smallest acquisition that can settle them, before any large tranche is proposed:

| Q | Question | Why it blocks D66 |
|---|---|---|
| Q1 | Do CDSL "DETAILS OF CORPORATE ACTIONS" communiques carry ISIN, action type, ratio and record date for equity actions, and do they list **every** such action? | CDSL is the only verified, free, non-exchange candidate for Source B |
| Q2 | Is the NSE/FAOP annual circular sequence gap-free, and does every price-scale adjustment for an F&O symbol appear in it? | The only free route seen to an empty-window proof |
| Q3 | Can a reconciliation of two sources over a year reproduce the known 2022 events without unexplained extras or misses? | Tests the reconciliation procedure on real data |

## 2. Proposed scope (smallest defensible)

| Item | Proposal |
|---|---|
| Window | 2022-01-01 .. 2022-12-31 (one calendar year inside D59) |
| Symbols | **TORNTPHARM** (bonus 1:1, ex 2022-07-08), **GAIL** (bonus 1:2, ex 2022-09-06), **HDFCBANK** (no price-scale event in held API data for 2022; empty-window candidate). All three: Nifty 100 membership VERIFIED and identity RESOLVED for the whole of 2022 per `P0_HISTORICAL_COVERAGE_MATRIX.csv` |
| Why not BAJAJFINSV | Its 2022 ISIN change splits the period; it would mix identity and CA questions |
| Source A | NSE/FAOP circulars, **entire 2022 series** (needed for Q2; roughly 150-200 PDFs if the numbering seen, 101 by 5 Sep, holds). NSE/CMPT circulars only as corroboration, never as Source B |
| Source B | CDSL "DETAILS OF CORPORATE ACTIONS" communiques for 2022: **72** listed in the CDSL index. Step 0 first: 2-3 communiques dated around 2022-07-08 and 2022-09-06 to answer Q1 before taking the other ~70 |
| Supporting evidence | Evidence of F&O membership for the three symbols across 2022 (NSE F&O inclusion/exclusion circulars or lot-size files). Without it the sequence argument cannot apply |
| Event types | split, subdivision, consolidation, bonus, rights with terms, demerger/scheme with price effect. Dividends recorded but not price-scale (R-12) |
| Storage | `nse/data/corporate_actions/evidence/nse_faop/2022/`, `.../cdsl_dp/2022/`, `.../fo_tenure/` (new; nothing overwritten) |
| Method | Host-side browser download by the owner or an owner-authorized agent outside `nse/`; original bytes kept; SHA-256, URL, retrieval date, size recorded in `P0_CA_SOURCE_LEDGER.csv` |
| Cost | Free public pages only. **BSE paid data is not part of this pilot** |
| Credentials | None expected. If CDSL requires a login, stop and report |

## 3. Pilot exit criteria (pre-registered)

| Outcome | Criterion | Consequence |
|---|---|---|
| Q1 PASS | Step-0 communiques show ISIN + type + ratio + record date for the TORNTPHARM and GAIL bonuses | Take remaining 2022 CDSL series |
| Q1 FAIL | Fields absent, or the events are missing from the communiques around their record dates | CDSL rejected as Source B; owner chooses between BSE (paid) or no CA completeness route |
| Q2 PASS | 2022 FAOP numbers form a continuous series with no gap; every 2022 non-dividend event in `actions.csv` for F&O symbols (16 such events exist across held symbols) has an FAOP adjustment circular | Sequence argument may be put to the owner for the empty window HDFCBANK 2022, **with its limitations disclosed** |
| Q2 FAIL | Gaps, or an event without an FAOP circular | No empty-window route from NSE; empty windows stay unprovable |
| Q3 PASS | For TORNTPHARM and GAIL, both sources agree on type, ex/record date and ratio; no extra or missing events | Draft `gtf.ca_reconciliation.v1` records and owner approval requests |

Even with all PASS, the owner still decides whether this evidence meets D66 for each window. The pilot produces requests, not approvals.

## 4. Known limitations to disclose in any approval request

- FAOP covers a symbol only while it is in F&O.
- CDSL record dates may derive from the exchange's confirmation; independence of the record date is partial, independence of the executed ratio is the stronger claim.
- A sequence argument proves "no adjustment announced", which equals "no price-scale event" only if the SEBI adjustment rules cover every such event type. That scope must be shown from the SEBI/NSE adjustment rules document, not assumed.
- Three symbols over one year is a feasibility test. It certifies at most 3 x ~248 member-dates and is not representative of the 123,778 member-date population.

## 5. Owner decision requested

See `P0_CA_ACQUISITION_AUTHORIZATION_REQUEST.md`: authorize or decline this pilot exactly as scoped.
