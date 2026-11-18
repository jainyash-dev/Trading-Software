# T-001: NIFTY 100 historical membership: owner review package

**Dated 2026-11-10. Prepared by an agent; nothing here is an owner decision.**
Every `proposed_*` value is a recommendation. Every `owner_*` field is blank.

## 1. Overall status

| Item | Value |
|---|---|
| Review status (`membership.convert`) | **NOT_REVIEWED**: 0 of 271 rows decided |
| Universe periods | 185, **all UNVERIFIED** |
| Point-in-time membership certified | **No** |
| `DATA_READY` | Not claimed, unchanged |
| Canonical files changed in Phase 01 | **None** (hashes below) |

The previous audit's counts still hold: 271 review rows with blank decisions and 185
unverified periods. The blank `source_sha256` in `nifty100_universe.csv` is deliberate.
The converter withholds a period's source hash until the rows behind that period are
accepted (D49). The transcription rows themselves all carry hashes.

## 2. What was checked (facts, re-run on 2026-11-10)

| Check | Result |
|---|---|
| `nifty100_review.csv` vs `nifty100_review_packet.csv` | Same 271 `row_key`s, same `row_sha256` on every row |
| Review hashes vs the current transcription rows | 0 stale. Every review hash equals the hash `membership.convert` computes now |
| Evidence registry `evidence/sources.csv` (38 files) | Every file present; every SHA-256 matches |
| The cited source file of each of the 271 rows | All 271 present and hash-matching |
| `membership.convert` re-run in memory | Output and report identical to the files on disk (185 periods, same report) |
| Overlapping periods (same ISIN or same symbol) | **None** |
| Member counts | 100 on 27 dates and 101 on 20 dates. Every 101 is backed by a count-exception row citing its release |
| Conflicting evidence | **None open.** Two independent transcriptions agreed on 122 of 123 ADD/REMOVE rows. The one difference (Jio Financial on 2023-07-20) is settled by an official document (`DUMMYREL` in the NIFTY 50 list of July 31, 2023) |

Protected universe files are unchanged by this phase:
`nifty100_review.csv` `a9289cbe…6938886`, `nifty100_universe.csv` `1ce5442a…af5ebb`.

## 3. How a period becomes verified (from `nse/research/membership.py`)

A period is verified only when all three hold:

1. **Its start row and its end row are ACCEPTED**, with hashes that still match.
2. **All 25 count-exception rows are ACCEPTED.** This is a global gate: if one exception is undecided, rejected or stale, *no* period is verified.
3. **The period has no identity finding.** This is independent of the review.

### Simulation (scratchpad only; not a decision)

To show what the review can and cannot achieve, a scratch copy of the review file was
marked all-ACCEPTED, with reviewer `SIMULATION-NOT-A-DECISION`, and converted in memory.
The canonical file was not touched. Result: review status `COMPLETE`; **177 of 185 periods
verified and 8 still unverified**. Those 8 cannot be verified by any review decision:

| Period | Why it stays unverified | What would clear it |
|---|---|---|
| BAJFINANCE INE296A01024, 2020-12-31 to 2025-06-15 | Two ISINs listed as BAJFINANCE (unevidenced change 2016-09-09) | Official evidence linking INE296A01016 to INE296A01024 (T-014) |
| GRASIM INE047A01021, 2020-12-31 to open | Two ISINs listed as GRASIM (unevidenced change 2016-10-07) | Same, for GRASIM |
| YESBANK INE528G01035, 2021-03-31 to 2022-03-30 | Two ISINs listed as YESBANK (unevidenced change 2020-03-16) | Same, for YESBANK |
| DUMMYREL, DUMMYITC, DUMMYSIEMS, DUMMYTATAM, DUMMYHDLVR (5 spin-off seats) | No identity record for a dummy symbol, which never trades | An owner decision on how dummy seats are represented (they never have candles, so they never produce candidates) |

## 4. Review inventory

The full row-level inventory is
[T001_nifty100_owner_worksheet.csv](T001_nifty100_owner_worksheet.csv): 271 rows, one per
review row, in the same order as `nifty100_review.csv`.

| Row type | Rows |
|---|---|
| Baseline (31 Dec 2020 official list) | 100 |
| Change: ADD / REMOVE | 62 / 61 |
| Change: ISIN_CHANGE (official corporate-action record) | 13 |
| Change: RENAME (same ISIN) | 10 |
| Count exceptions (101, or back to 100) | 25 |
| **Total** | **271** |

### Evidence status (recommendation categories)

| Evidence status | Rows | Proposed action | Meaning |
|---|---|---|---|
| EVIDENCE_CONFIRMED | 251 | ACCEPT_RECOMMENDED | Verifier VERIFIED against the cited official document; file hash matches |
| EVIDENCE_CONFIRMED_LIVE_LIST | 6 | ACCEPT_RECOMMENDED | Same-ISIN renames taken from NSE's live `symbolchange.csv` (copy of 2026-11-09). This is an official list, but the copy is not a dated document |
| EVIDENCE_CONFIRMED_VISUAL_READ | 10 | ACCEPT_AFTER_VISUAL_CHECK | Event E03 (effective 2021-09-30). Its release `ind_prs23082021.pdf` is image-only and was read visually. Check page 5, section "3) NIFTY 100" yourself |
| EVIDENCE_INCOMPLETE | 4 | OWNER_JUDGEMENT_REQUIRED | Dummy spin-off ADD rows. Symbol and date are printed verbatim; the ISIN is inferred from the later listing by entity name only |
| EVIDENCE_CONFLICTING | 0 |: |: |
| EVIDENCE_ABSENT | 0 |: |: |

Every row needs an owner decision. Recommended rows are not accepted rows.

### Rows that need particular attention

**P1: all 25 count exceptions (global gate).** These are the effective dates 2023-07-20 to
2025-12-05 on which the official count is 101, or returns to 100. Each cites the release
from which the count was derived. If any one of them is not accepted, every period stays
unverified.

**P2a: visual check of E03 (10 rows), from `evidence/releases/ind_prs23082021.pdf` page 5.**
- REMOVE: ABBOTINDIA, ALKEM, MRF, PETRONET, UBL.
- ADD: BANKBARODA, CHOLAFIN, JINDALSTEL, PIIND, SAIL.

**P2b: dummy ISIN inferences (4 rows).**
- `change:E15:ADD:DUMMYITC:INE379A01028`
- `change:E18:ADD:DUMMYSIEMS:INE1NPP01017`
- `change:E21:ADD:DUMMYTATAM:INE1TAE01010`
- `change:E23:ADD:DUMMYHDLVR:INE2KCE01013`

  Accepting such a row accepts the inferred ISIN. Rejecting it leaves that dummy period
  unverified. The dummy period stays unverified either way (section 3), so this decision
  changes the review status, not what a scan can use.

**P3: the remaining 232 rows** (baseline, reconstitution ADD/REMOVE, official-record ISIN
changes and renames). The verifier's evidence is in `verifier_detail`. Spot-check by
event rather than row by row: one release usually covers 10 to 12 rows.

## 5. Period coverage summary

| Item | Value |
|---|---|
| Coverage | 2020-12-31 (baseline) to open; the last event is 2025-12-05 |
| Symbols | 164 |
| Periods | 185 (84 closed, 101 open; 101 open because of the DUMMYHDLVR seat from 2025-12-05) |
| **Before 2020-12-31** | **No membership at all.** Bhavcopies are held from 2016-01-01, but there is no point-in-time NIFTY 100 universe for 2016-2020. A scan or backtest dated before 2021 cannot use the universe, and today's constituents must not stand in for it (master prompt section 8) |
| Gaps | None unexplained. Each re-entry is a separate period with its own ADD row |

### Symbol-level exceptions (20 symbols with more than one period)

| Kind | Symbols |
|---|---|
| Left and re-entered the index (same ISIN, separate periods) | BANKBARODA, ENRIN, HINDZINC, JINDALSTEL, JIOFIN, PFC, PNB, ZYDUSLIFE |
| ISIN changed while a member (official record; never joined: ED-29) | ADANIPOWER, BAJAJFINSV, BAJFINANCE (2025), CANBK, DRREDDY, HAL, JUBLFOOD, NAUKRI, NESTLEIND, SHRIRAMFIN, TATASTEEL, VBL (two changes) |
| Unevidenced ISIN change before or inside the window (identity finding) | BAJFINANCE (2016), GRASIM (2016), YESBANK (2020): see T-014 |

## 6. Recommended next actions (for the owner)

1. Decide the 25 count exceptions first (P1). Without them nothing else takes effect.
2. Open `ind_prs23082021.pdf` page 5 and decide the 10 E03 rows (P2a).
3. Decide the 4 dummy-ISIN rows (P2b). Either answer is consistent with the rules.
4. Work through the 232 P3 rows by event, using the worksheet's `source_doc` column.
5. Copy decisions into **`nse/data/universe/nifty100_review.csv`** (columns `decision`,
   `reviewer`, `reviewed_on`, `notes`). Do not edit `row_key` or `row_sha256`. Then re-run
   the conversion command in `nse/data/universe/README.md`.
6. Separately, decide whether the 5 dummy seats need a representation rule (an owner
   decision, not a data fix).

## 7. How to use the worksheet

- Columns `row_id` and `row_sha256` are the review file's `row_key` and `row_sha256`.
- `periods_starting` and `periods_ending` name the periods each row opens or closes.
  `affects_all_periods = YES` marks the count exceptions.
- `owner_decision`, `owner_reviewer`, `owner_reviewed_on` and `owner_notes` are blank,
  for your working notes. **Nothing reads the worksheet.** Only `nifty100_review.csv`
  counts.
- Rebuild it at any time:
  `python3 docs/product-discovery/phase-01/tools/build_t001_worksheet.py`. It reads
  only; it writes nothing but the worksheet.

Columns added beyond the suggested set: `row_sha256`, `row_type`, `isin`, `event_id`,
`action`, `reason`, `announcement_date`, `source_file_hash_check`, `verifier_verdict`,
`verifier_detail`, `periods_starting`, `periods_ending`, `affects_all_periods`,
`identity_finding`, `review_priority`, `owner_reviewer`, `owner_reviewed_on`.

## 8. Boundary kept

- No decision written.
- No row accepted.
- No hash generated or filled.
- No period changed.
- No file under `nse/data/universe/` modified.
- `DATA_READY` unchanged.

No recommendation uses current membership, market capitalisation or later performance.
Each rests on the cited official document and the verifier's check of it.
