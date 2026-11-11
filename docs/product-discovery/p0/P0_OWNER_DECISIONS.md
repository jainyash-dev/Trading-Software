# P0 owner decisions

**Dated 2026-11-10.** Section 1 lists decisions the owner has already approved, including D59
in this campaign. Section 2 is still `OWNER_DECISION_REQUIRED`. A recommendation is not a decision.
Canonical membership, identity joins, prices, and corporate-action ratios were not
changed to force a result.

Detailed evidence:

- [Membership](P0_NIFTY100_MEMBERSHIP_REVIEW.md)
- [Identity](P0_IDENTITY_VALIDATION_REPORT.md)
- [Price gaps](P0_PRICE_GAP_INVESTIGATION.md)
- [Corporate actions](P0_CORPORATE_ACTION_COVERAGE.md)
- [TradingView](P0_TRADINGVIEW_VALIDATION_STATUS.md)
- [Calendar and EOD](P0_CALENDAR_EOD_RECONCILIATION.md)

## 1. Already decided

| ID | Decision | What it does not decide |
|---|---|---|
| D50 | Raw unadjusted OHLC is canonical. Unverified ratios are not applied | No adjusted series, and no ratio for an unparsed scheme |
| D51 | A rename joins only on verified ISIN continuity | Does not join an ISIN change |
| D56 | Collect corporate-action records. Missing evidence stays manual or insufficient | Does not treat an empty API list as "no events" |
| D58 | The four Dhanteras dates are confirmed regular equity sessions, 09:15-15:30 | Does not certify the universe, identity, or TradingView |
| D59 | Membership-based Nifty 100 research uses 2020-12-31 onward. This is not certification | Does not accept any review row, join an ISIN, or create a pre-2020 baseline |

## 2. Decisions still required

| ID | Subject | Current state | Evidence in hand | Missing | Recommendation | If left open |
|---|---|---|---|---|---|---|
| OD-MEM-1 | 271 Nifty 100 review rows | D60 and D61 recorded. All 271 `decision` cells still blank. 246 rows have no reviewer | Hash-matched citations. Count arithmetic and ten E03 directions are approved. Periods are not | The owner's `decision` `ACCEPTED` or `REJECTED` on each membership row | Do not treat D60 or D61 as period approval | Every scan stays `UNIVERSE_UNVERIFIED` |
| OD-MEM-2 | DUMMYREL ISIN `INE758E01017` | Packet says verified. Build report says inferred. The Nifty 100 release does not print the symbol | Symbol comes from the Nifty 50 list of 31 July 2023 | An official Nifty 100 assignment of that ISIN | Leave the period unverified | The 2023-07-20 .. 2023-08-20 seat stays unverified |
| OD-MEM-3 | Five dummy seats with no candles | No identity record under the dummy symbol | Releases print the symbol and date for four of them. ISINs are inferred from the later listing | A representation rule | Keep them unverified and out of candidate generation | Those dates stay `UNIVERSE_UNVERIFIED` while the seat is in the file |
| D59, recorded | Moving the window earlier than 2020-12-31 | D59 is approved for 2020-12-31 onward. `IndexInclExcl.xls` is still NOT PARSED | Bhavcopies exist for 2016-2020. Membership does not | An official dated baseline, transcribed under D49, only if the window should start earlier | Leave the window at 2020-12-31 | 2016-2020 stays usable as candle history and is not a survivorship-controlled universe |
| OD-ID-1 | BAJFINANCE 2016-09-09 | `INE296A01016` then `INE296A01024`. Scan is `DATA_INSUFFICIENT` from that date | Bhavcopy flip. Bonus/split ex-date is the previous session. Record date is Saturday 2016-09-10. JSON ISIN stays the old one | A document that names `INE296A01024` on 2016-09-09 | Do not join | The 2016 error also blocks every later scan, including after the evidenced 2025 change |
| OD-ID-2 | GRASIM 2016-10-07 | `INE047A01013` then `INE047A01021`. Open from the baseline, so it taints every later membership date | Bhavcopy flip. Split ex-date 2016-10-06, record date Saturday 2016-10-08. JSON never prints the new ISIN | A document that names `INE047A01021` and the session | Do not join | Accepting all 271 review rows would still leave every in-window date unverified |
| OD-ID-3 | YESBANK 2020-03-16 | `INE528G01027` then `INE528G01035`. No previous-close break | The 2017 split is evidenced and still not joined (`ED-29`). The saved 2016-2025 response has no March 2020 event | A notice naming the new ISIN and the session | Do not join | Scans from 2020-03-16 stay `DATA_INSUFFICIENT` |
| OD-PX-1 | BE and BZ rows when EQ is absent | Loader reads EQ only. ADANIPOWER and CGPOWER traded the "gap" sessions on BE, previous close chained | Raw rows and series codes. No local circular for the series change | Whether research candles may include BE/BZ | Leave the EQ filter. Treat the stretches as missing EQ sessions | The EQ-only discontinuity flag remains. It is not a split |
| OD-PX-2 | CROMPGREAV scheme 2016-03-15 | `UNPARSED_PRICE_EVENT`, ratio 0,0. Close 155.3 to open 53 | One-session unadjusted ex-date. Factor 2.93 is not an integer split | A sourced ratio | Keep raw prices. Exclude continuity-sensitive work across that date | No ratio is invented |
| OD-PX-3 | ADANIPOWER 2025-09-22 | Recorded 1:5 split and ISIN change. Raw close 709.40 to open 148.20 | Action row and both bhavcopies | None for the classification. A joined price scale is not authorised | Keep the two ISINs separate. Do not back-adjust | A pasted price scale remains invalid |
| TV-1 | 34 TradingView observations | All observation cells blank. The only filled file is a Yahoo INFY transcription | Protocol and worksheet | Chart exports or recorded readings | Do not close T-005 | B8, B10, and B17 stay open |
| TV-2 | Unnamed SMA dates | TV-SMA-D-01 and TV-SMA-W-01 do not name the four bars | The rest of each row is specified | The four daily dates and four week-start dates | Name them when the charts are read | Those two rows cannot be compared |
| TV-3 | TradingView plan | Unverified | Protocol says so | Whether export and a split-adjustment toggle exist | Record the answer with the captures | Adjustment comparisons stay `UNKNOWN` |
| OD-CA-1 | Adjusted series, or a second corporate-action source | Not approved. Empty lists are not coverage. `SRTRANSFIN` was collected on 2026-11-10: HTTP 200, body `[]`, not added to coverage. An earlier TLS failure is logged `NOT_COLLECTED` and is not the latest result | D56 collection. 47 bodies are `[]`, including `SRTRANSFIN`. 10 unparsed events have no usable ratio | Completeness proof (R-10), and a decision only if an adjusted series is wanted | Do not adjust. Do not treat the empty `SRTRANSFIN` body as proof of no events | G0 stays `MANUAL` where coverage is absent. Dividend-only windows can pass without proving that no split exists |
| OD-CAL-1 | 2024-01-20 hours | Confirmed `NORMAL_SPECIAL`. Hours inferred from NSE/CMTR/41180 because NSE/MSD/60340 prints no times | The row is not unresolved | Confirm or replace the inferred 09:15-15:30 | Keep the inference visible. Do not mark the date unresolved without a new ruling | The session stays usable, with the inference disclosed |

## 3. Consequence for a historical backtest

No certified research window exists while OD-MEM-1 and OD-ID-2 are open. GRASIM alone
keeps every date from 2020-12-31 unverified after a full review acceptance. Dates before
2020-12-31 have no membership. TradingView parity is not evidenced. Corporate-action
coverage is incomplete, and raw prices stay unadjusted by decision. Calendar and EOD
files for 2016-2025 do reconcile, and that reconciliation does not make a symbol eligible.

## 4. Count arithmetic and E03 mappings, recorded 2026-11-11

Reviewer: Yash Jain. These are two decisions. They are not membership-period approval.

| Decision | Rows | Stored as | Membership `decision` |
|---|---|---|---|
| D60 count arithmetic | 25 `exception:` rows | `count_approval` `APPROVED` | blank |
| D61 E03 mapping and direction | 10 `change:E03:` rows | `mapping_approval` `APPROVED` | blank |

D60 does not approve constituents, dummy seats, inferred ISINs, or a historical Nifty 100 period. Twenty derived counts are 101 and five are 100. The five 101-count dates with dummy seats (2023-07-20 DUMMYREL, 2025-01-06 DUMMYITC, 2025-04-07 DUMMYSIEMS, 2025-10-14 DUMMYTATAM, 2025-12-05 DUMMYHDLVR) stay non-tradable.

D61 approves the ten symbol directions in `ind_prs23082021.pdf` page 5 section 3, effective 30 September 2021 from page 1. It does not certify the open BANKBARODA or CHOLAFIN periods.

The other 246 review rows are not approved. `decision` is blank on all 271 rows.

The 25 dates and derived counts are in
[P0_COUNT_EXCEPTION_PROPOSED_DECISIONS.csv](P0_COUNT_EXCEPTION_PROPOSED_DECISIONS.csv).
The count column is `derived_member_count`. It is the count produced by rolling the
transcribed inclusions, exclusions, renames and ISIN changes. It is not a number printed
as "101" on every NSE page. Rename and ISIN-change rows do not change the count.
Dummy seats can leave the count at 101. The count is not forced to 100.

OD-MEM-4 was the pre-2020 window question. D59 decided the window starts 2020-12-31.
OD-ID-1, OD-ID-2 and OD-ID-3 are separate: they are the three unevidenced ISIN changes.
They are not the same decision as D59 or as the 25 count exceptions.
