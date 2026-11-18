# P0 corporate-action pilot report: TORNTPHARM, GAIL, HDFCBANK, 2022

**Date:** 2026-11-15
**Authority:** owner Q1, AUTHORIZE WITH CHANGES (2026-11-15). Free public sources only; CDSL step 0 first; NSE CM material to be investigated; NSE/FAOP corroboration only; no expansion; no approvals.
**Pilot status:** **STOPPED AFTER STEP 0. Q1 failed for bonus events.** No source pair qualifies, no reconciliation record was created, and no completeness window or D66 marker exists. Nothing here certifies anything.
**Provenance for every file:** `P0_CA_SOURCE_LEDGER.csv` (publisher, upstream chain, original URL, retrieval UTC time, HTTP status, server Last-Modified, size, SHA-256).

## 1. Step 0: CDSL "DETAILS OF CORPORATE ACTIONS" (owner-required first check)

| Communique | Date | Retrieval | Content (read) | Pilot symbol present? |
|---|---|---|---|---|
| CDSL/OPS/DP/CAIPO/2022/367 | 2022-06-28 | 200, PDF, SHA-256 `c831443a...` | SUB-DIVISION: DUDIGITAL (INE0HPK01012 -> INE0HPK01020, 1:5), PAISALO (INE420C01042 -> INE420C01059, 1:10); record 01-Jul-2022; effective 02-Jul-2022 | No |
| CDSL/OPS/DP/CAIPO/2022/391 | 2022-07-11 | 200, PDF, `099cdfdd...` | SUB-DIVISION: STEEL EXCHANGE (1:10), RADHE DEVELOPERS (1:10); record 13/15-Jul-2022 | No: TORNTPHARM bonus (record 2022-07-11) absent |
| CDSL/OPS/DP/CAIPO/2022/505 | 2022-09-05 | 200, PDF, `0384ac00...` | SUB-DIVISION: DANGEE DUMS (INE688Y01014 -> INE688Y01022, 1:10); record 07-Sep-2022 | No: GAIL bonus (record 2022-09-07) absent |

Retrieval note: the first attempt used `/Publications/DownloadFile` and returned 404 for all three. The listing page's relative link resolves to `/eservices/Publications/DownloadFile`; the same three documents were then retrieved. No other source was substituted.

Fields carried: type of CA, issuer, old ISIN, old face value, record date, new ISIN, new face value, ratio [old ISIN : new ISIN], effective date.

**Finding (verified for 3 of 3 sampled):** these communiques list **ISIN-changing actions** (sub-divisions creating a new ISIN). Neither pilot bonus appears near its record date. That fits the depository practice that a bonus keeps the same ISIN, but that wider explanation is an inference from 3 samples.

**Pre-registered exit criterion** (`P0_CA_PILOT_RECOMMENDATION.md`): "Q1 FAIL: ... the events are missing from the communiques around their record dates". **Q1 = FAIL for bonus events.** As pre-registered and per the owner's "no expansion", the remaining ~69 CDSL 2022 communiques were **not** retrieved.

CDSL is not assumed to be independent or qualified. It is not proposed as Source B for bonus events. It may be relevant to ISIN-changing events (splits), including identity questions. That would need a separate authorization.

## 2. NSE capital-market corporate-action material (investigated)

| Symbol | 2022 non-dividend events in held API data | NSE CM material found | Status |
|---|---|---|---|
| TORNTPHARM | BONUS 1:1, ex 2022-07-08 | **NSE/CML/53021** (Listing, 2022-07-20): "Listing of further issues ... Torrent Pharmaceuticals Limited": TORNTPHARM, EQ, ISIN INE685A01028, "Equity shares of Rs. 5/- each allotted under Bonus Issue", allotment 13-Jul-2022, 169,207,520 securities, dealings from 21-Jul-2022 | Retrieved. States allotment and listing; **does not state ratio, record date or ex-date** |
| GAIL | BONUS 1:2, ex 2022-09-06 | Listing-of-bonus-shares circular **not found**. Bounded scan of NSE/CML/53570-53700 (mid-September 2022): 39 circulars existed; text extraction failed on 9 | **INCONCLUSIVE**: it may be among the 9 unreadable files or outside the range. Not widened (no expansion) |
| HDFCBANK | none | No search made: no 2022 event is expected | No evidence of absence. An empty search would not prove an empty window anyway |

Also found (Batches 12-13 and this pilot): NSE Listing issues "Face Value Split" circulars (for example NSE/CML/33104, 33298) and "Change in ISIN" circulars (33154, 33327, 35870) for splits, and "Listing of further issues" circulars for bonus allotments. These are a third NSE channel. **They are the same institution as NSE/FAOP and as the refused NSE API**, so they cannot form an independent pair with either.

## 3. NSE/FAOP corroboration only

| Circular | Content | Agreement with held API data |
|---|---|---|
| NSE/FAOP/52865 (67/2022), 2022-07-04 | TORNTPHARM bonus 1:1, record 2022-07-11, ex 2022-07-08, factor 2 | Agrees (API: BONUS 1:2 share ratio, ex 2022-07-08, record 11-Jul-2022) |
| NSE/FAOP/53495 (98/2022), 2022-08-30 | GAIL bonus 1:2, record 2022-09-07, ex 2022-09-06, factor 1.5 | Agrees (API: BONUS 2:3 share ratio, ex 2022-09-06, record 07-Sep-2022) |

Used as corroboration only, per the owner. Not Source A or B.

## 4. Pilot questions

| Q | Result |
|---|---|
| Q1 CDSL content and coverage | **FAIL for bonus events**: the fields exist, but the communiques sampled cover ISIN-changing actions only; both pilot bonuses absent |
| Q2 FAOP sequence completeness | **NOT TESTED**: needed the full 2022 FAOP series, which the plan made conditional on step 0 passing; FAOP is corroboration-only under the owner's instruction |
| Q3 two-source reconciliation | **NOT POSSIBLE**: no independent second source for any pilot event. No `gtf.ca_reconciliation.v1` record created |

## 5. Upstream relationships (as far as established)

- NSE (FAOP, CML, API): issuer intimation to NSE under listing regulations. One institution, several channels.
- CDSL: corporate action set up from issuer/RTA instructions (CDSL operating instructions). Whether CDSL's record dates derive from an exchange confirmation was not established for CDSL. NSDL's checklist requires one.
- No document establishes independence between any two of these for a bonus event.

## 6. Conclusion and next decisions (owner)

- With free public sources, no independent second official source was found for **bonus** events in 2022. D66 completeness cannot be shown for TORNTPHARM or GAIL 2022, and an empty window cannot be shown for HDFCBANK 2022.
- Options for the owner (none taken): (a) a BSE source (Q2 enquiry, pending); (b) authorize CDSL retrieval for ISIN-changing events only, which could support split windows but never bonus windows; (c) accept that D66 cannot currently be met, so P0 stays blocked; (d) a methodology change to D66, which only the owner can make.
