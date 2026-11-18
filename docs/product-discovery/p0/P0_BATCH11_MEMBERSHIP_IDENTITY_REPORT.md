# P0 Batch 11 - Membership and identity report

**Date:** 2026-11-15
**Batch status:** COMPLETE_WITH_ISSUES. All safe analysis is done. Membership decisions and the OD-ID-1/2 identity decisions are owner-reserved and still pending.
**Writes in this batch:** none to the ledger (`nifty100_review.csv`), to `instrument_records.csv`, or to any data file. No ACCEPTED/REJECTED value was written. No ISIN was joined or ended.

## 1. Ledger integrity (verified)

Method: rebuilt the expected review rows with `membership.review_template(nifty100_baseline.csv, nifty100_changes.csv, nifty100_count_exceptions.csv)` and compared them with the live ledger.

| Check | Result |
|---|---|
| Template rows vs ledger rows | 271 vs 271; identical key sets |
| Ledger `row_sha256` stale against current transcription | **0 of 271** |
| Ledger decisions | 140 `ACCEPTED`, 131 blank (unchanged since the 1.5.0 build: ledger SHA-256 `9b0fcba0...` equals that build's input hash) |
| Evidence-sufficient rows (91) | 91 hashes current, 91 blank |
| Evidence-insufficient rows (15) | 15 current, 15 blank |
| Not-applicable rows (25) | 25 current, 25 blank |
| Backlog `source_sha256` vs file on disk (131 rows) | 131 match (re-hashed in Batch 8) |

Meaning: an owner decision written now binds to the current transcription rows, and no earlier decision has gone stale.

## 2. The 91 evidence-sufficient rows

Per-row listing (row key, group, symbol, ISIN, effective date, evidence file, evidence hash, the three status fields, recommendation): `P0_MEMBERSHIP_DECISION_SUMMARY_V2.md` section 2. All 91 have membership SUFFICIENT, identity RESOLVED_VERIFIED, EQ EQ_BOUNDARY_OK. The recommendation on file is ACCEPT, which is not a decision.

## 3. BAJFINANCE / GRASIM backlog text defect (investigated)

| Row | `reason` | `missing_evidence` |
|---|---|---|
| `baseline:BAJFINANCE:INE296A01024` | "baseline:BAJFINANCE:INE296A01024: identity on 2020-12-31 is UNKNOWN_INSTRUMENT (two or more ISINs ... INE296A01016, INE296A01024) (+1 more ...)" | Combined text: "GRASIM: an official record joining ... \| BAJFINANCE: an official record joining ..." |
| `baseline:GRASIM:INE047A01021` | **Identical to the BAJFINANCE row** | **Identical** combined text |

Finding: not a swap. The generator wrote one group-level text into both rows of the same group (`G-BASELINE-2020-12-31`). The GRASIM `reason` therefore names BAJFINANCE. No Python module in the repository writes `P0_MEMBERSHIP_BACKLOG.csv` (searched), so it came from a one-off script that is not in the repo. Impact: text only. `classification`, `membership_evidence_status`, `identity_evidence_status`, `eq_data_status` and `owner_membership_recommendation` are correct for both rows. Recommendation: regenerate per-row text when the backlog is next rebuilt. The file is not edited now, to keep the evidence state the Batch 8 pack cites.

## 4. The seven optional rows (membership verified independently of identity and EQ)

Each source file's hash matched (Batch 8). In Batch 11 the text of each document was extracted and read:

| Rows | Document (held) | What it says |
|---|---|---|
| `change:R-2023-08-21-JIOFIN:RENAME:JIOFIN:INE758E01017` | `evidence/circulars/CML58021.zip` -> `CML58021.pdf` (NSE/CML/58021, 18 Aug 2023) | Listing of JIOFIN, Jio Financial Services Limited, ISIN INE758E01017, series "BE - Trade for Trade", effective August 21, 2023 |
| ITCHOTELS rename + `change:E16:REMOVE` | `evidence/releases/ind_prs06022025_1.pdf` (6 Feb 2025) | ITC Hotels included as DUMMYITC from January 06, 2025; listed as ITCHOTELS on January 29, 2025; then excluded from Nifty indices |
| ENRIN rename + `change:E19:REMOVE` | `evidence/releases/ind_prs25062025_2.pdf` (25 Jun 2025) | Siemens Energy India included as DUMMYSIEMS from April 07, 2025 on the Siemens demerger; then excluded |
| TMCV rename + `change:E22:REMOVE` | `evidence/releases/ind_prs13112025.pdf` (13 Nov 2025) | TML Commercial Vehicles included as DUMMYTATAM from October 14, 2025; listed as TMCV on November 12, 2025; excluded from November 17, 2025 (close of November 14) |

Conclusion: the membership evidence is sufficient for all seven on its own. They are blocked only by identity (dummy-to-listed transition has no instrument record) and EQ (BE-only trading while a member). Deciding membership would not certify any of their member-dates.

## 5. OD-ID-1 / OD-ID-2: option 3 investigated

### 5.1 New verified facts

1. **Notice text** (extracted from the held, hash-verified PDFs):
   - BAJFINANCE, MSEI/LIST/4496/2016 (7 Sep 2016): ISIN "shall be changed w.e.f. September 9, 2016"; "The New ISIN shall be effective for trades done on and from the Ex-date i.e. September 8, 2016"; record-date column "September 10, 2016"; reason "Sub-Division ... Rs.10/- to Rs.2/-".
   - GRASIM, MSEI/LIST/4581/2016 (4 Oct 2016): "changed w.e.f. October 7, 2016"; "effective for trades done on and from the Ex-date i.e. October 6, 2016"; record-date column "October 6, 2016".
2. **This two-date pairing is NSE's standard wording too.** NSE/CML/35870 (Listing, 21 Sep 2017, Sutlej Textiles; read from the public archive, not held): ISIN "shall be changed w.e.f. September 27, 2017 being the Record Date"; "The new ISIN shall be effective for all trades done on and from the Ex-Date i.e September 26, 2017." The earlier description of the MSEI notices as "conflicting" was imprecise: the two dates carry different stated meanings.
3. **NSE bhavcopies (held) agree with the notices:**

   | Session | BAJFINANCE | GRASIM |
   |---|---|---|
   | Ex-date | 2016-09-08: old ISIN `INE296A01016`, prev 11,393.30, close 1,162.80 (factor ~10 = bonus 1:1 x split 5) | 2016-10-06: old ISIN `INE047A01013`, prev 4,933.55, close 1,009.20 (factor ~5) |
   | Next session | 2016-09-09: new ISIN `INE296A01024` | 2016-10-07: new ISIN `INE047A01021` |
   | Old ISIN after that | never: 0 occurrences in 2,313 held bhavcopies from 2016-09-01 onward after 2016-09-08 | never after 2016-10-06 |

4. **Why ED-37 left them unjoined:** ED-37 accepts an ISIN change only when an NSE corporate-action record's ex-date or record date equals the first new-ISIN session. NSE API record dates are 10-Sep-2016 and 08-Oct-2016, both Saturdays, so neither matches. A "next session after ex-date" convention was tried and withdrawn as "a convention, not evidence" (D56).
5. **Precedent:** YESBANK 2017 is recorded as `ISIN_CHANGE` with `effective_from` 2017-09-22, the first new-ISIN session, which matched its API record date.

### 5.2 Remaining ambiguity (honest statement)

- The held notices are **MSEI's**, describing MSEI's own system. NSE's own Change-in-ISIN circulars for these two 2016 events are not held and were not found by search (the search index covers the NSE archive poorly).
- Record dates are inconsistent: BAJFINANCE's notice prints a Saturday; GRASIM's MSEI notice says 6 Oct while NSE's API says 8 Oct (Saturday).
- The w.e.f. date in both notices equals the first NSE session under the new ISIN. That is an observed agreement, not an NSE statement.

### 5.3 Evidence that would support an old-ISIN cessation record (option 3) or a join (option 2)

| Strength | Evidence | Status |
|---|---|---|
| Strongest | NSE/CML "Change in ISIN" circular for Bajaj Finance (about 7 Sep 2016) and Grasim (about 4 Oct 2016), stating the w.e.f. date | Not held. Retrieval needs owner authorization (download). Public archive host is reachable |
| Strong | Depository (NSDL/CDSL) record of the ISIN change / corporate action with execution date | Not held; CDSL 2016 communique series exists (49 titled "Details of Corporate Actions"), contents unverified |
| Present | MSEI notices (held, hash-verified) + NSE bhavcopy first/last sessions (held, hash-verified) | Held. Sufficiency is the owner's judgment |

How option 3 would be recorded (engineering, not done): `instrument_records.csv` allows `effective_to` only on `LISTING` rows (`instruments.load`). A cessation would set `effective_to` on the old ISIN's LISTING row (2016-09-08 BAJFINANCE; 2016-10-06 GRASIM), citing the document the owner accepts. No `ISIN_CHANGE` row, so no price join. Effect: `resolve()` returns the new ISIN on every later date. The 1,098 BAJFINANCE and 1,234 GRASIM member-dates would then pass the identity gate only; membership (baseline rows blank) and D66 corporate-action completeness still exclude them.

## 6. EQ series

`P0_EQ_SERIES_VALIDATION.csv` (Batch 8, from the isolated 1.6.0 matrix, re-confirmed by a fresh build in Batch 13): 123,395 EQ ACCEPTED, 260 BE-only, 123 dummy NO_EQ_ROW. BE/BZ never substitutes for EQ.

## 7. Batch acceptance

| Item | Status |
|---|---|
| 1. Reconcile 91 rows | COMPLETE |
| 2. Evidence references and hashes | COMPLETE (131/131 files; 271/271 row hashes current) |
| 3. Backlog copy defect | COMPLETE (text defect; no status impact) |
| 4. Seven optional rows | COMPLETE (membership evidence sufficient on its own) |
| 5. Option 3 investigation | COMPLETE; decision BLOCKED on owner |
| 6. Cessation evidence requirements | COMPLETE (section 5.3) |
| 7. Preserve ledger decisions | COMPLETE (ledger hash unchanged) |
