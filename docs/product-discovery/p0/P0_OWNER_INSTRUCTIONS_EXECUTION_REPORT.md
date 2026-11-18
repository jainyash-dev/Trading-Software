# P0 execution report: owner instructions after queue V3

**Date:** 2026-11-15
**Programme status:** **P0_CERTIFICATION_BLOCKED**. Certified member-dates **0 of 123,778**.
**Not done (and not authorized):** no ledger decision, no identity-record change, no ISIN join or listing end, no completeness row or D66 marker, no production rebuild, no paid data, no P5, no broker, no staging, commit or push.

## 1. Actions completed under explicit owner authorization

| Q | Action | Result |
|---|---|---|
| Q1 | CDSL step 0: three 2022 "Details of Corporate Actions" communiques retrieved and read (DP2022-367, -391, -505) | Retrieved. Content: ISIN-changing sub-divisions only. Neither pilot bonus present. **Q1 FAIL for bonus events**; pilot stopped as pre-registered (`P0_CA_PILOT_REPORT_2022.md`) |
| Q1 | NSE CM material investigated | TORNTPHARM: NSE/CML/53021 (bonus allotment listing) retrieved. GAIL: not found (inconclusive scan). HDFCBANK: no event expected; nothing searched |
| Q1 | NSE/FAOP corroboration | FAOP52865 (TORNTPHARM) and FAOP53495 (GAIL) retrieved; both agree with held data. Corroboration only |
| Q3 | 91-row acceptance proposal | Prepared: `P0_MEMBERSHIP_ACCEPTANCE_PROPOSAL.md`/`.csv` and `P0_MEMBERSHIP_OWNER_DECISION_FILE_PROPOSED.csv`. Proposal only |
| Q5 | BAJFINANCE Option 1 recorded; NSE/CML Change-in-ISIN circular retrieved | **NSE/CML/33154** (2016-09-06): ISIN changed w.e.f. 2016-09-09; new ISIN effective for trades from ex-date 2016-09-08; new ISIN INE296A01024. Held at `nse/data/universe/evidence/identity/isin_notices/nse_bajfinance_cml33154_2016.pdf`. Identity records untouched |
| Q6 | GRASIM Option 1 recorded; circular retrieved | **NSE/CML/33327** (2016-10-03): w.e.f. 2016-10-07; trades from ex-date 2016-10-06; new ISIN INE047A01021. Held at `.../nse_grasim_cml33327_2016.pdf`. Identity records untouched |
| Q11 | CGPOWER 2016 official terms retrieval | NSE/FAOP/31828, NSE/CMTR/31832, NSE/FAOP/31970 retrieved (section 3) |

Every retrieved file: `P0_CA_SOURCE_LEDGER.csv` (11 rows: publisher, upstream chain, document id, original URL, retrieval UTC, HTTP status, server Last-Modified, size, SHA-256, coverage claim). Files were copied into new folders only; nothing was overwritten.

How the 2016 circulars were located: NSE's circular-listing service needs session cookies, and that request was refused by the session's permission policy and not retried. Instead, the download reference numbers were estimated from dated anchors already held (NSE/CMTR/33424 = 2016-10-17) or public (NSE/FAOP/32123 = 2016-03-31). Bounded, rate-limited scans of the public archive then fetched candidates into a scratch area and kept only the matching documents. Non-matching scan files are not evidence and were not placed in custody. Two further circulars found during the scans, NSE/CML/33104 (Bajaj Finance face-value split, 2016-08-31) and NSE/CML/33298 (Grasim face-value split, 2016-09-29), were **not** placed in custody because the owner authorized the Change-in-ISIN circulars only.

## 2. Retrieval failures and inaccessible documents

| Item | What happened |
|---|---|
| CDSL first attempt | `/Publications/DownloadFile` returned 404 for all three. Corrected to the listing's resolved relative path `/eservices/Publications/DownloadFile`; the **same** documents were retrieved. No substitution |
| NSE circular-listing API | Not used: the session permission policy refused a cookie-based request. Not worked around |
| GAIL 2022 bonus-listing circular | Not found in NSE/CML/53570-53700; 9 of 39 PDFs in range were not text-extractable. **Inconclusive**; not widened |
| CGPOWER share-entitlement ratio | **Not obtained from an official source.** NSE circulars give the event type, dates and handling, not the ratio. A scan for the resulting company's listing circular (NSE/CML/32370-32480) found nothing. The court-approved scheme document was not retrieved |
| 2016 circular freshness | Server Last-Modified for the 2016 circulars is 2019-01-17 (archive re-serve). The bytes may differ from the 2016 originals (risk R-7) |

## 3. Evidence inspected but still insufficient

- **CDSL as Source B:** insufficient for bonus events (absent). Not assumed independent or qualified.
- **NSE CML vs NSE FAOP:** same institution; not an independent pair (owner restriction respected).
- **CGPOWER 2016-03-15** (pre-window): NSE/FAOP/31828 states the event is a **demerger** into Crompton Greaves Consumer Electrical Limited under a court-approved scheme (record 2016-03-16, ex 2016-03-15). F&O contracts expired 2016-03-14 and were re-introduced with no adjustment factor. NSE/CMTR/31832 set a special pre-open price-discovery session. Held bhavcopies: 155.30 -> open 53.00, close 44.00 on 2016-03-15, same ISIN INE067A01029. Classification analysis (not applied): the event is a demerger whose price effect was set by market price discovery, not a share ratio. No share ratio can be inferred. The exception stays **open and fail-closed**: no parser change, no price change, no window change.
- **OD-ID-1/2:** NSE's own circulars now confirm the w.e.f. dates (2016-09-09; 2016-10-07) and the ex-date trade rule. Per the owner's Option 1 decisions nothing changes; this is held for future review.

## 4. 91-row membership proposal

- 91 / 91 rows: ledger row present, row hash current, decision blank, evidence SHA-256 matches, the document supports symbol, direction and effective date, ISIN confirmed (bhavcopy for releases). 87 by automated text check, 4 by manual read (HDFC, JINDALSTEL, JIOFIN E10, TATAMTRDVR).
- All 10 release groups' NIFTY 100 lists match their rows exactly; the 9 ISIN-change and 5 rename groups each have the expected single record.
- **Proposed decision: ACCEPTED for all 91.** No unresolved rows. Limitations: release ISINs come from bhavcopies; ISIN-change rows rest on saved API bodies (same basis as D65); renames on `symbolchange.csv`.
- Ledger untouched: `nifty100_review.csv` SHA-256 `9b0fcba0...` before and after.

## 5. Engineering work and exact test results

| Item | Result |
|---|---|
| ED-57 (ENG-1) | Recorded `PROPOSED` (held), **not implemented**: parser behaviour change needs explicit owner go-ahead and review |
| ED-58 (ENG-2) | Implemented: per-row backlog text; only 2 lines changed; hashes recorded in ED-58 |
| ED-59 (ENG-3) | Implemented in `P0_CA_SOURCE_LEDGER.csv` (publisher, upstream_chain) |
| ED-60 (ENG-4) | Test `test_a_conflict_event_fails_closed_even_with_empty_unresolved` added with a positive control; module 54/54 OK |
| ED-61 (ENG-5) | `run_all --acceptance` run after side-effect inspection |
| Acceptance run | `python3 -m nse.validation.run_all --acceptance --out <scratchpad>`: **PASS**, acceptance_mode true, ran 1,475, failures 0, errors 0, skipped 0, 27/27 checks PASS, 0 prerequisite skips. Finished 19:24 IST, before the ED-60 test was added |
| Post-change groups | `run_all --group risk_instruments --group repository --group architecture --group validation_framework`: PASS, 292 run, 0 failures (risk_instruments 235 = 234 + ED-60) |
| Determinism | Isolated build C byte-identical to builds A and B on all 5 outputs (run after evidence files were added) |
| Protected / production hashes | Rulebook PDF, Rulebook Markdown, Pine Script, production P0 outputs, ledger, DECISION_LOG: unchanged |
| Other | `docs_health` PASS (0 findings); `architecture` PASS (54 modules, 0 violations); `git diff --check` clean; 0 staged |
| Preserved | `evidence/validation_2026-11-15/`: acceptance log and report, post-change report, determinism hashes (A, B, C) |

## 6. Decisions still awaiting the owner

- **Q3 execution:** accept, reject or defer the 91 rows using the proposed decision file (writing to the ledger needs an explicit instruction).
- **D66 path after the pilot:** (a) BSE source (Q2 enquiry, pending); (b) CDSL for ISIN-changing events only; (c) stay blocked; (d) change D66 (owner only).
- **ED-57 / ENG-1:** go-ahead for the fractional split parser change.
- **CGPOWER:** whether to authorize retrieval of the court-approved scheme document or the resulting company's listing circular for the entitlement ratio.
- Pending as before: Q2, Q4, Q7 (OD-PX-4), Q8 (OWN-1), Q9 (OD-PX-3), Q10 (OD-MEM-2/3), Q12 (TV-1), Q13 (R-5).

## 7. Certification count and exact blockers

| Blocker | Member-dates |
|---|---|
| D66: no proved completeness window (no independent second source for bonuses; pilot Q1 failed) | **all 123,778** |
| Membership UNVERIFIED (91 proposed rows plus deferred rows) | 44,627 |
| Identity UNKNOWN (BAJFINANCE 1,098 + GRASIM 1,234 + dummy seats 123) | 2,455 |
| EOD non-EQ / no EQ row | 383 |
| Price continuity exceptions (OD-PX-4 700, OD-PX-3 1, unparsed 3, others) | see `P0_BATCH12_EXCEPTION_ANALYSIS.md` |

**Certified: 0.** Status stays **P0_CERTIFICATION_BLOCKED**. The pilot does not qualify any source pair, and the membership proposal is not membership approval.
