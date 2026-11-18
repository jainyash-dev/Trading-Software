# P0 membership decision summary

**Date:** 2026-11-15  
**Verified against:** `docs/product-discovery/p0/P0_MEMBERSHIP_BACKLOG.csv` + `nse/data/universe/nifty100_review.csv`  
**Detailed cards:** `P0_MEMBERSHIP_OWNER_DECISION_PACK.md`  
**Agents must not write `ACCEPTED` / `REJECTED`.**

## Count verification

| Classification | Groups | Rows | Matches reported 24/14/25? |
|---|---|---|---|
| `EVIDENCE_SUFFICIENT_OWNER_DECISION_REQUIRED` | **24** | 91 | Yes |
| `EVIDENCE_INSUFFICIENT` | **14** | 15 | Yes |
| `NOT_APPLICABLE` | **25** | 25 | Yes |

Ledger: **140** `ACCEPTED`, **131** blank. Periods verified with source hash: **85 / 185**.

Four fields remain independent: `membership_evidence_status`, `identity_evidence_status`, `eq_data_status`, `owner_membership_recommendation`.

---

## Exact owner decisions required

### A. Evidence-sufficient (24 groups) - decide first

For **each** `row_key` below, write `decision` = `ACCEPTED` or `REJECTED` in `nifty100_review.csv` (owner only).

Recommendation on file for all 91 rows: `ACCEPT_RECOMMENDED` (not an approval).

| Group | Effective | Kind | Rows | Symbols | Membership / identity / EQ | Recommendation |
|---|---|---|---|---|---|---|
| G-E06 | 2022-09-30 | RELEASE | 12 | ATGL, BEL, HAL, IRCTC, JUBLFOOD, LUPIN, MINDTREE, MOTHERSON, MPHASIS, PNB, SAIL, ZYDUSLIFE | SUFFICIENT / RESOLVED_VERIFIED / EQ_BOUNDARY_OK | ACCEPT_RECOMMENDED |
| G-E07 | 2023-03-31 | RELEASE | 10 | ABB, AWL, BANDHANBNK, BIOCON, CANBK, GLAND, MPHASIS, PAGEIND, PAYTM, VBL | same | ACCEPT_RECOMMENDED |
| G-E08 | 2023-07-13 | RELEASE | 2 | HDFC, JINDALSTEL | same | ACCEPT_RECOMMENDED |
| G-E10 | 2023-09-07 | RELEASE | 1 | JIOFIN | same | ACCEPT_RECOMMENDED |
| G-E11 | 2023-09-29 | RELEASE | 11 | ACC, HDFCAMC, INDUSTOWER, NYKAA, PAGEIND, PNB, SHRIRAMFIN, TATAMTRDVR, TRENT, TVSMOTOR, ZYDUSLIFE | same | ACCEPT_RECOMMENDED |
| G-E12 | 2024-03-28 | RELEASE | 10 | ADANIPOWER, AWL, IRFC, JIOFIN, MUTHOOTFIN, PFC, PGHH, PIIND, RECLTD, UPL | same | ACCEPT_RECOMMENDED |
| G-E13 | 2024-08-30 | RELEASE | 1 | TATAMTRDVR | same | ACCEPT_RECOMMENDED |
| G-E14 | 2024-09-30 | RELEASE | 10 | BERGEPAINT, BHEL, COLPAL, JSWENERGY, LODHA, MARICO, NHPC, SBICARD, SRF, UNIONBANK | same | ACCEPT_RECOMMENDED |
| G-E17 | 2025-03-28 | RELEASE | 10 | ATGL, BAJAJHFL, BHEL, CGPOWER, HYUNDAI, INDHOTEL, IRCTC, NHPC, SWIGGY, UNIONBANK | same | ACCEPT_RECOMMENDED |
| G-E20 | 2025-09-30 | RELEASE | 10 | DABUR, ENRIN, HEROMOTOCO, HINDZINC, ICICIPRULI, INDUSINDBK, MAXHEALTH, MAZDOCK, SOLARINDS, SWIGGY | same | ACCEPT_RECOMMENDED |
| G-I-2023-06-15-VBL | 2023-06-15 | ISIN_CHANGE | 1 | VBL | same | ACCEPT_RECOMMENDED |
| G-I-2023-09-28-HAL | 2023-09-28 | ISIN_CHANGE | 1 | HAL | same | ACCEPT_RECOMMENDED |
| G-I-2024-01-05-NESTLEIND | 2024-01-05 | ISIN_CHANGE | 1 | NESTLEIND | same | ACCEPT_RECOMMENDED |
| G-I-2024-05-15-CANBK | 2024-05-15 | ISIN_CHANGE | 1 | CANBK | same | ACCEPT_RECOMMENDED |
| G-I-2024-09-12-VBL | 2024-09-12 | ISIN_CHANGE | 1 | VBL | same | ACCEPT_RECOMMENDED |
| G-I-2024-10-28-DRREDDY | 2024-10-28 | ISIN_CHANGE | 1 | DRREDDY | same | ACCEPT_RECOMMENDED |
| G-I-2025-01-10-SHRIRAMFIN | 2025-01-10 | ISIN_CHANGE | 1 | SHRIRAMFIN | same | ACCEPT_RECOMMENDED |
| G-I-2025-05-07-NAUKRI | 2025-05-07 | ISIN_CHANGE | 1 | NAUKRI | same | ACCEPT_RECOMMENDED |
| G-I-2025-09-22-ADANIPOWER | 2025-09-22 | ISIN_CHANGE | 1 | ADANIPOWER | same | ACCEPT_RECOMMENDED |
| G-R-2022-12-05-LTIM | 2022-12-05 | RENAME | 1 | LTIM | same | ACCEPT_RECOMMENDED |
| G-R-2023-08-24-ADANIENSOL | 2023-08-24 | RENAME | 1 | ADANIENSOL | same | ACCEPT_RECOMMENDED |
| G-R-2024-06-07-UNITDSPR | 2024-06-07 | RENAME | 1 | UNITDSPR | same | ACCEPT_RECOMMENDED |
| G-R-2025-04-09-ETERNAL | 2025-04-09 | RENAME | 1 | ETERNAL | same | ACCEPT_RECOMMENDED |
| G-R-2025-10-24-TMPV | 2025-10-24 | RENAME | 1 | TMPV | same | ACCEPT_RECOMMENDED |

**Note on G-I-2024-09-12-VBL:** membership evidence is classified sufficient; OD-PX-2 (5-to-2 split parse) remains a separate price/CA issue and must not be conflated with this membership decision.

Full `row_key` list: see `P0_MEMBERSHIP_BACKLOG.csv` filtered to these 24 groups (also enumerated in `P0_MEMBERSHIP_OWNER_DECISION_PACK.md` section A).

### B. Evidence-insufficient (14 groups)

| Group | Issue | Recommendation on file | Exact decision |
|---|---|---|---|
| G-BASELINE-2020-12-31 (BAJFINANCE, GRASIM) | Identity ambiguous (OD-ID-1/2) | DEFER | Leave blank or REJECT until identity resolved; do not accept as identity-clear |
| G-E09/E15/E18/E21/E23 | Dummy ADD seats | DEFER | Leave non-tradable; do not invent ISINs |
| G-R-2023-08-21-JIOFIN and G-R ITCHOTELS/ENRIN/TMCV | Dummy-to-listed; first row BE | ACCEPT_RECOMMENDED (membership) with EQ separate | Membership may be decidable; EQ dates stay NON_EQ_ONLY excluded |
| G-E16/E19/E22 | Removals with BE-only history | ACCEPT_RECOMMENDED | Same: membership vs EQ are separate |
| G-I-2025-06-16-BAJFINANCE | Predecessor ISIN unresolved (OD-ID-1) | DEFER | Defer until OD-ID-1 resolved |

### C. Not applicable (25 count groups)

No membership `decision` required. D60 already approved count arithmetic via `count_approval`. Do not treat as membership periods.

---

## What membership acceptance does *not* do

- Does not certify any member-date (CA gate still fails all rows under D66).
- Does not resolve OD-ID-1 / OD-ID-2.
- Does not convert BE/BZ into EQ research prices.
