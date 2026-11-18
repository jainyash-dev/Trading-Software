# P0 Milestone 2 handoff: evidence and certification closure

Prepared 2026-11-15 at the end of Milestone 1, against HEAD `69858d0` plus the working tree. None of the Milestone 1 work is committed: no commit was authorised.

Milestone 2 owns the external evidence, the remaining owner decisions, the final certified dataset and the final certification report. This file lists exactly what each of those needs, so Milestone 2 does not repeat Milestone 1's investigations.

Labels used below: **fact** means recomputed from files on disk in Milestone 1; **inference** is a judgement; **recommendation** is not an owner decision.

## Status at handoff (fact)

| Item | Value |
|---|---|
| Certification builder | `nse/research/p0_certification.py` build 1.5.0 |
| Member-dates 2020-12-31..2025-12-31 | 123,778 |
| Certified (`CERTIFIED_P0_DATA`) | **0** |
| Exploratory only (D62) | 73,366 |
| Membership periods verified | 85 of 185 |
| Ledger `nse/data/universe/nifty100_review.csv` | SHA-256 `9b0fcba06cc57761a4adbf0a938e004fb6adf808ba7724842248977391ec1f39`; 140 `ACCEPTED`, 131 blank |
| Completeness register `nse/data/corporate_actions/completeness.csv` | does not exist; 0 proved windows |
| Input hashes of the current build | `P0_CERTIFICATION_SUMMARY.json` `inputs_sha256` |

Every member-date fails the corporate-action gate. That gate, not membership, is the reason nothing certifies.

## A. Membership evidence backlog (T-001)

All 131 undecided ledger rows are listed with evidence in `P0_MEMBERSHIP_BACKLOG.csv`: row key, symbol, ISIN, source file and SHA-256, content inspection, boundary EQ ISINs, missing evidence, and the periods each group would verify.

Each group was checked in Milestone 1 (fact). Row hashes match the template. Source hashes match. Release text was extracted from the PDF content streams; page numbers are not verified, because no renderer is installed. Each release's Nifty 100 lists match the ledger rows exactly. Boundary EQ rows carry the ledger ISIN, and identity resolves with verified records.

**24 groups: evidence sufficient, owner decision required.** All are `ACCEPT_RECOMMENDED` on file except VBL-2024 (note below). Accepting all 24 cumulatively in date order is projected to take verified periods from 85 to about 175. That figure is a dry run on a scratch copy, not a result.

| Group | Effective | Kind | Rows | Periods if accepted alone |
|---|---|---|---|---|
| G-E06 | 2022-09-30 | release | 12 | 8 |
| G-R-2022-12-05-LTIM | 2022-12-05 | rename | 1 | 2 |
| G-E07 | 2023-03-31 | release | 10 | 5 |
| G-I-2023-06-15-VBL | 2023-06-15 | ISIN change | 1 | 0 |
| G-E08 | 2023-07-13 | release | 2 | 2 |
| G-R-2023-08-24-ADANIENSOL | 2023-08-24 | rename | 1 | 2 |
| G-E10 | 2023-09-07 | release | 1 | 0 |
| G-I-2023-09-28-HAL | 2023-09-28 | ISIN change | 1 | 1 |
| G-E11 | 2023-09-29 | release | 11 | 8 |
| G-I-2024-01-05-NESTLEIND | 2024-01-05 | ISIN change | 1 | 2 |
| G-E12 | 2024-03-28 | release | 10 | 8 |
| G-I-2024-05-15-CANBK | 2024-05-15 | ISIN change | 1 | 1 |
| G-R-2024-06-07-UNITDSPR | 2024-06-07 | rename | 1 | 2 |
| G-E13 | 2024-08-30 | release | 1 | 0 |
| G-I-2024-09-12-VBL | 2024-09-12 | ISIN change | 1 | 1 |
| G-E14 | 2024-09-30 | release | 10 | 7 |
| G-I-2024-10-28-DRREDDY | 2024-10-28 | ISIN change | 1 | 2 |
| G-I-2025-01-10-SHRIRAMFIN | 2025-01-10 | ISIN change | 1 | 1 |
| G-E17 | 2025-03-28 | release | 10 | 4 |
| G-R-2025-04-09-ETERNAL | 2025-04-09 | rename | 1 | 2 |
| G-I-2025-05-07-NAUKRI | 2025-05-07 | ISIN change | 1 | 2 |
| G-I-2025-09-22-ADANIPOWER | 2025-09-22 | ISIN change | 1 | 1 |
| G-E20 | 2025-09-30 | release | 10 | 9 |
| G-R-2025-10-24-TMPV | 2025-10-24 | rename | 1 | 2 |

"Periods if accepted alone" counts periods both opened and closed by accepted rows. A group whose periods also need a later group shows 0 alone.

**VBL 2024-09-12.** The file says `INSUFFICIENT_EVIDENCE`. Milestone 1 found the ISIN change INE200M01021 to INE200M01039 and the Rs 5 to Rs 2 split (ex-date 2024-09-12) consistent in the corporate-action body and the bhavcopies. What remains open is the split ratio (5-to-2), which the parser cannot represent as a whole-number ratio. That is a price-gate matter (OD-PX-2), not a membership one. Recommendation: present the membership row to the owner with that note.

**14 groups: evidence insufficient.**

| Group | What is missing |
|---|---|
| G-BASELINE-2020-12-31 (GRASIM, BAJFINANCE rows) | The constituent list was decrypted and names both symbols. Their closes match the 2020-12-31 bhavcopy. The list prints no ISIN, and identity is unresolved (section B) |
| G-E09, G-E15, G-E18, G-E21, G-E23 (dummy ADDs) | The dummy symbol has no bhavcopy row and no instrument record. E09's release does not print DUMMYREL at all ("spun off entity") |
| G-R JIOFIN, ITCHOTELS, ENRIN, TMCV (dummy-to-listed renames) | The old symbol is a placeholder with no row; the new symbol's first row is BE, not EQ |
| G-E16, G-E19, G-E22 (removals of ITCHOTELS, ENRIN, TMCV) | The release evidence agrees. The instrument traded only in BE before removal, so there is no EQ boundary row. Inference: membership itself may be decidable from the release; the BE dates stay excluded by the EOD gate either way |
| G-I-2025-06-16-BAJFINANCE | The predecessor ISIN INE296A01024 is unresolved (OD-ID-1) |

**25 count groups: not applicable.** D60 approved their arithmetic, and they are not membership rows.

**Series and membership are separate (fact).** The converter decides index membership and does not look at the trading series. If the dummy-to-listed renames were accepted, membership periods for BE-only listings would become verified. Their BE dates would still fail the EOD gate (`NON_EQ_ONLY`), and BE is never read as EQ.

## B. Identity evidence backlog (T-005)

| Item | Member-dates affected | Exact evidence needed |
|---|---|---|
| GRASIM `INE047A01013` to `INE047A01021` | 1,234 (every window session) | One official notice that states a single effective session for the ISIN change. MSEI/LIST/4581/2016 states both 6 and 7 October 2016 (OD-ID-2). An NSE CM notice or depository (NSDL/CDSL) corporate-action record for the October 2016 change would settle it |
| BAJFINANCE `INE296A01016` to `INE296A01024` | 1,098 (before 2025-06-16) | Same kind of record for September 2016. MSEI/LIST/4496/2016 states both 8 and 9 September 2016 (OD-ID-1) |
| Dummy seats DUMMYREL, DUMMYITC, DUMMYSIEMS, DUMMYTATAM, DUMMYHDLVR | 123 | None can resolve them: they are non-tradable placeholders. DUMMYREL does not resolve to JIOFIN (tested). An owner rule is needed only if the "full index" claim must account for them (OD-MEM-2/3) |

The rename policy (fact, ED-54):
- Tickers join only through a VERIFIED SYMBOL_CHANGE record, along a single-ISIN chain, from its effective date.
- The 35 rename links touching the universe are published with their evidence file, hash and record line in `P0_CERTIFICATION_SUMMARY.json` `rename_links`. All 35 are verified.

## C. Corporate-action completeness dependency (OD-CA-1)

**The architecture (fact, D62 and ED-54).** Three tiers:
- `CA_COMPLETENESS_VERIFIED`: passes the gate.
- `CA_RESPONSE_PRESENT_NOT_COMPLETE`: exploratory only.
- `CORPORATE_ACTIONS_UNVERIFIED`.

The only way to reach the first tier is a row in `nse/data/corporate_actions/completeness.csv`, with columns `symbol, from_date, to_date, source, source_file, source_sha256, owner_decision, recorded_on, notes`. Such a row counts only when all of these hold:
- the cited file is held and hashes to `source_sha256`;
- `owner_decision` is a decision whose status in DECISION_LOG.md is `USER_APPROVED` AND whose own entry contains a bullet that starts exactly `- **Completeness source accepted:**` and lists, separated by `; `, items of the exact form `<sha256 of the source file> <SYMBOL> <YYYY-MM-DD>..<YYYY-MM-DD>`. The register row must match one item exactly (bytes, symbol and window). For example:

  `- **Completeness source accepted:** 3f2a...c9 INFY 2016-01-01..2025-12-31; 3f2a...c9 TCS 2016-01-01..2025-12-31`

  An id alone, a `USER_STATED` or `PROPOSED` decision, a general approval such as D62, or a marker that names other bytes, symbols or dates does not count;
- the cited file is not a saved API response (`ca_*.json`, or anything under `raw/`);
- the saved NSE response for that symbol is hash-verified (in `coverage.csv`, or for `[]` in `collection_log.jsonl`), parses as a list of events, and has no unparsed price subject;
- the ticker has never been renamed away and is not ambiguous; an old ticker's response, and any renamed ticker's `[]`, never pass (ED-55);
- the cited source is not a copy of a saved API response, whether by name, location, bytes or content.

With such a row, an empty `[]` response becomes `COVERED_NO_EVENTS_PROVED`, and a parsed response becomes `CA_COMPLETENESS_VERIFIED`. The file does not exist, so nothing passes.

**Why the held responses do not prove completeness.**
- The NSE corporate-actions API documents no completeness guarantee (R-10).
- `[]` cannot be told apart from "this ticker was renamed" (ED-39).
- A non-empty response shows that the listed events exist, not that no other event exists.
- PREVCLOSE cannot reveal an omitted split, because NSE prints the unadjusted prior close on the ex-date (55 of 55 events, ED-50).
- The 15% price screen catches every recorded split. It misses all 13 rights issues, 3 small bonuses and 4 small demergers (section F).

**What would satisfy the gate (recommendation; acquisition and acceptance are owner decisions).**
- An independent, official, dated record of every corporate action for a symbol over a stated window, from a source other than the API body. Candidates:
  - NSE's own corporate-action announcements archive for the symbol, as a full dated export rather than a single API call;
  - BSE's corporate-action records for the same ISIN;
  - depository (NSDL/CDSL) records of ISIN-level events.
- The completeness claim comes from reconciling two independent sources. Both list the same events for the window, and each event's ex-date and ratio agree.
- Then an owner decision (D<n>) accepts that reconciliation as proof for named symbols and windows.

**Practical plan (recommendation).**
1. Owner approves a collection scope; new downloads are outside D56.
2. Collect the second source for the 85 currently verified periods first.
3. Reconcile event by event, recording every disagreement as a conflict that excludes.
4. Write the register rows under an owner decision id, then rebuild.

No source has been invented here.

## D. Historical baseline dependency (B11-P)

- Fact: no constituent list with symbols or ISINs exists on disk before 2020-12-31.
- Fact: `nse/data/universe/evidence/baseline/IndexInclExcl.xls` (SHA-256 `8869bb7c…`) is a company-name change log for 2003-03-19..2020-07-31 (168 inclusions, 168 exclusions). It has no symbol and no ISIN, and cannot seed a baseline (P0_INDEX_INCL_EXCL.md).
- Needed: dated official Nifty 100 constituent lists with symbols or ISINs, for example NSE Indices month-end constituent files, for each year to be added before 2020-12-31. D59 keeps the window at 2020-12-31 until then.

## E. TradingView validation backlog (T-006)

- Status (fact): `WAITING_FOR_EXTERNAL_EVIDENCE`. The 34 rows of `docs/product-discovery/phase-01/T005_tradingview_comparison_worksheet.csv` have every observed, evidence, hash, result and reviewer field blank. There is no `nse/data/tradingview/`. The INFY reference rows are Yahoo Finance screenshots, not TradingView.
- Components still externally unvalidated: 29 (`python3 -m nse.research.cli readiness`, `externally_validated=false`).
- Required exports, per the worksheet and `nse/data/reference/README.md`:
  - INFY candles on D, W, M, Q, HY and Y;
  - SMA-50;
  - GTF zones and their freshness;
  - TATASTEEL around 2022-07-28 with adjustment on and with adjustment off.
- Each export needs a file name and SHA-256 recorded on its reference row.
- Method: `python3 -m nse.research.cli compare-references` against the EQ replay, with the adjustment setting matched. Raw NSE OHLC must only be compared with an unadjusted TradingView export.

## F. Price exception backlog

| Item | Member-dates | Evidence (fact) | Decision needed |
|---|---|---|---|
| OD-PX-3: ADANIENSOL 2024-11-21 | 1 | Open, low and close are 697.25, which is 0.8000 x the 871.55 prior close: the 20% band. The Adani group fell the same day; seven non-group stocks moved -2.8% to +0.8%. PREVCLOSE is intact, the ISIN unchanged, and the body lists AGMs only | Whether a reviewed market move may pass the price screen. No exception mechanism exists. It stays excluded |
| OD-PX-4: steps across a held Muhurat or shortened session | 702, on 7 dates (2021-11-08, 2022-10-25, 2023-11-13, 2024-03-04, 2024-05-21, 2024-11-04, 2025-10-23): 700 `PREVCLOSE_BREAK_ACROSS_EXCLUDED_SESSION` and 2 `STEP_ACROSS_EXCLUDED_SESSION` (ED-55) | For the 700, the chain is intact through the held session: PREVCLOSE equals that session's EQ close, whose PREVCLOSE equals the prior regular close. Under a rule allowing that, all 700 would pass the price gate, and 439 would then pass every data gate except corporate action. The 2 others had excluded-session closes equal to the prior close | Whether to adopt that rule. D52 does not cover held files. Measured only, not adopted |
| OD-PX-2: unparsed ratios | Steps on CGPOWER 2016-03-15 and VBL 2024-09-12 | Terms not representable as a whole-number ratio | Official terms the parser can represent |
| OD-PX-1: BE/BZ stretches | 260 in membership | See section H | None. Contained by exclusion |
| R-12 residual | not countable | See section G | A completeness source (section C) |

## G. Certification readiness and known technical limitations

- Builder 1.5.0. Rebuilt twice after the last change; all five outputs byte-identical, including the 54 MB matrix.
- Reconciliation checks in the summary, all true:
  - member-dates equal an independent `Universe.members` count;
  - certified plus excluded equal the rows;
  - every excluded date is in exactly one register interval;
  - one row per symbol-date;
  - no order authorised.
- Synthetic end-to-end fixture: `tests/test_research_p0_build_e2e.py` drives the real `build()` through every gate state, including a certified row reachable only with a completeness-register window.
- Independent review: Milestone 1 review in `P0_EXECUTION_TRACKER.md`.
- Known limitations (fact):
  - **R-12 residual.** The 15% whole-range screen detects 99 of 125 recorded price events in 2016-2025. It misses all 13 rights issues, 3 small bonuses (BEL 10:11, NTPC 5:6, BERGEPAINT 5:6), 4 demergers (MOTHERSON 2022, RELIANCE 2023, ITC 2025, HINDUNILVR 2025) and 6 unparsed events. A recorded action still holds G0. An omitted small event does not.
  - **No safe lower band.** Over 123,352 member steps without a recorded action, the screen's false positives are 1 at 15%, 3 at 12%, 4 at 10%, 21 at 8% and 97 at 5%. Lowering to 12% gains 2 events, both already recorded. The 26 undetected events sit inside the ordinary price distribution (median low/prior 0.952). Recommendation: keep 15%; close the residual with OD-CA-1.
  - **User CSV inputs** now pass the same screen (ED-54). They carry `PRICE_ADJUSTMENT_UNKNOWN` unless the adjustment is stated.
  - Release PDFs were read by text extraction; page numbers are not verified. `ind_prs23082021.pdf` (E03, already accepted under D61 and batch 1) is image-only.

## H. ADANIPOWER, CGPOWER and other non-EQ stretches (fact)

- 25 stretches across the universe symbols where the exchange printed the security only in BE or BZ. Every one is `SOURCE_HAS_NO_EQ_ROW`: the held file for each session has no EQ row for that symbol or ISIN. This was checked by the loader and by an independent re-read of the CSV text.
- The PREVCLOSE chain is intact through every stretch. BL rows always coexist with EQ (1,312 symbol-days) and never replace it.
- Recovery is impossible by definition: the exchange's own file has no EQ row. The gap is **contained, not resolved**: those dates fail the EOD gate.
- ADANIPOWER, all on INE814H01011: 5 stretches, 204 equity sessions (2021-06-14..09-17 67; 2021-10-22..10-29 6; 2022-08-25..11-25 62; 2022-12-26..12-30 5; 2023-12-14..2024-03-15 64). The two longer stretches also contain a held excluded-session file each (2022-10-24 Muhurat, 2024-03-02 shortened), so they span 63 and 65 held files. 0 member-dates: it joined on 2024-03-28.
- CGPOWER, all on INE067A01029: 4 stretches (BZ 2019-12-26..2020-02-12 36; BE 2020-09-02..09-11 8; 2021-06-09..09-09 65; 2021-09-16..2022-01-03 74 equity sessions plus the held 2021-11-04 Muhurat file). 0 member-dates: it joined on 2025-03-28. Earlier board figures of 75 and 74 for the last stretch differ only by that held Muhurat file.
- Member-dates affected (260): ADANIGREEN 65, ADANITRANS 167, JIOFIN 10, ITCHOTELS 9, ENRIN 6, TMCV 3. They match the matrix's `NON_EQ_ONLY` dates exactly.
- Circulars on disk explain JIOFIN (CML58030) and the BE listings of ITCHOTELS, ENRIN and TMCV. Nothing on disk explains the others' transfers.

## Owner decisions and external evidence, consolidated

| ID | Type | What is needed |
|---|---|---|
| OD-CA-1 | Owner plus external | A second, independent corporate-action source; an approved collection scope; an owner decision per accepted reconciliation |
| T-001 batch 3+ | Owner | Decisions on the 24 sufficient groups (backlog file) |
| OD-ID-1 / OD-ID-2 | External | Single-date ISIN-change records for BAJFINANCE (Sept 2016) and GRASIM (Oct 2016) |
| OD-MEM-2/3 | Owner, optional | A rule for non-tradable dummy seats in a full-index claim |
| B11-P | External | Pre-2020 dated constituent lists with symbols or ISINs |
| TV-1 | External | TradingView exports listed in section E |
| OD-PX-2 | External | Representable terms for the two unparsed ratios |
| OD-PX-3 / OD-PX-4 | Owner, optional | Exception rules for a reviewed market move, and for steps across held excluded sessions |
