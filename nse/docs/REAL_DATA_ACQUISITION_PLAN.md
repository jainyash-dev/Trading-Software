# Real Data Acquisition Plan (prepared, not executed)

**Dated 2026-10-29.** Nothing has been downloaded for this plan. Numbers below were measured
on the repository, with the commands shown. Facts not verified here are marked
*unverified*. Format details live in `DATA_REQUIREMENTS.md` and `EOD_FORMAT_EVIDENCE.md`;
this plan does not repeat them.

## 1. Evaluation window

- **Data window:** 2021-01-01 to 2025-12-31 (D29; the calendar covers exactly these years).
- **Earliest full scan:** 2024-01-01. A full MIT scan needs three completed calendar years
  for the Yearly conflict check (G5), so 2021, 2022 and 2023 must be complete first.
  `inventory.required_start` for as_of 2024-01-01 asks for data from 2021-01-01.
- **Signal window this supports:** 2024-01-01 to 2025-12-31.
- **Earlier signals:** scans before 2024 need 2019-2020 data *and* the 2019-2020 calendar
  circulars, which are not held. That is out of this plan.
- The Monthly trend context (55 months) reaches back to 2019. It is context only, never a
  gate (D21), and is reported as insufficient.

```
python3 -m nse.research.cli inventory --as-of 2025-12-31 --window-start 2021-01-01 \
    --symbols NESTLEIND,TATASTEEL,BAJFINANCE,RELIANCE,HAL,BEL,LICI,ICICIBANK,INFY,MARUTI \
    --out nse/output/inventory-window-2021-2025.json
```

## 2. What is held and what is missing (measured 2026-10-29)

| Year | Trading sessions (calendar) | Files held | Missing |
|---|---|---|---|
| 2021 | 247 | 0 | 247 |
| 2022 | 247 | 61 (2022-01-03 to 2022-03-31) | 186 |
| 2023 | 245 | 1 (2023-12-29) | 244 |
| 2024 | 246 | 0 | 246 |
| 2025 | 248 | 0 | 248 |
| **Total** | **1,233** | **62** | **1,171** |

- The trading sessions include the two regular-hours Saturdays, 2024-01-20 and 2025-02-01
  (NORMAL_SPECIAL; the 20 Jan 2024 hours are inferred, D40).
- Seven excluded sessions are **not required**: Muhurat 2021-11-04, 2022-10-24, 2023-11-12,
  2024-11-01 and 2025-10-21; DR drills 2024-03-02 and 2024-05-18. If NSE publishes a file
  for one, keep it. Reconciliation lists it as information, and the replay excludes it (D30).
- Split by the reported, *unverified*, legacy-to-UDiFF switch of 2024-07-08: 865 sessions fall
  before it and 368 on or after it.
  - The 803 missing legacy-era files are what the strict loader is built for. Format
    continuity across 2021-2024 is *unverified* (B18): a file that deviates is refused, not
    guessed.
  - The 368 UDiFF-era files cannot be loaded at all yet (§4).

**Symbols** (the proposed sample, `DATA_REQUIREMENTS.md` §6, not yet approved):
- Every one has an EQ row in all 62 held files, except LICI. LICI has a row only on
  2023-12-29; its reported listing date of 2022-05-17 is *unverified* here.
- The sample's membership of the current Nifty 100 is not verified, and no constituent file
  is held (D1, B11).

## 3. Source and storage

- **Source:** the NSE website's capital-market daily bhavcopy, downloaded by the user (D31).
  The exact page URL is not recorded in the repository; the current manifest says "Official
  NSE website (user-confirmed; exact page not supplied)". Record the page actually used, at
  download time, in `--source-page` (§5). No URL is assumed here.
- **Storage:** `nse/data/eod/raw/`, zipped as downloaded and outside git (`.gitignore`). Only
  `nse/data/eod/manifest.csv` is committed.
- **Size:** the 62 legacy archives held measure 81,369 to 99,885 bytes (median 82,562).
  - The 865 legacy-era sessions: about 71 MB at the median.
  - UDiFF archive size: *unknown*, no sample seen.

## 4. UDiFF (blocks 2024-07-08 onwards; B18)

**Needed before any UDiFF-era date can be used:**
1. The **last legacy file** NSE published, and the **first UDiFF file**. Together they pin the
   switch date, which is unverified.
2. One UDiFF file for an ordinary 2025 session.
3. If published, the UDiFF file for a 2024 or 2025 Muhurat session (optional evidence).

**Work after the samples:**
- Document the header, date format, series values and every field mapping in
  `EOD_FORMAT_EVIDENCE.md`, with hashes, as for the legacy samples.
- A UDiFF loader then has to be built with the same strictness. It does not exist; this is
  engineering work blocked only on the samples.

## 5. Procedure (user downloads; the tools check)

Work month by month:

1. Save the month's archives into `nse/data/eod/raw/` without renaming them.
2. Record provenance. This prints the rows; add `--append` to write them:
   ```
   python3 -m nse.research.cli manifest-rows nse/data/eod/raw/cm*JAN2021bhav.csv.zip \
       --source-page "<page actually used>" --downloaded-on <YYYY-MM-DD> --provenance-status USER_CONFIRMED
   ```
   - It computes the size and SHA-256 of the archive and its member.
   - It parses every file with the strict loader before writing anything.
   - It refuses a file or date that is already held.
   - It never infers a download date.
3. Run `python3 -m nse.validation.run_all` and read `local_data`.
4. When the window is complete:
   ```
   python3 -m nse.validation.run_all --acceptance --require-window 2021-01-01 2025-12-31
   ```

## 6. Acceptance checks (all exist and are tested)

| Check | How | Tool |
|---|---|---|
| Completeness | Every calendar trading session in the window has a file; the 7 excluded sessions are optional | `run_all --require-window`; `cli inventory` |
| Provenance | Archive and member size and SHA-256 match the manifest | strict loader, `manifest-rows` |
| Duplicates | One file per trade date; one row per symbol and series | `load_many`, strict parser |
| Malformed rows | Exact header, Decimal prices, dates, ISIN format; any deviation refuses the file | `nse_bhavcopy` strict loader |
| Calendar consistency | No file on a closed day; a missing session is reported per month | `nse_calendar.reconcile` in `run_all` |
| Corporate-action evidence | A PREVCLOSE that differs from the last close is listed per symbol; the scanner holds G0 at MANUAL when one falls in the history | `corporate_actions.prevclose_discontinuities`; data_quality.csv |
| History sufficiency per timeframe | Y/HY/Q 3 periods, M 3, W 55, D 3, unbroken | `cli inventory` `history` |

The PREVCLOSE detector was run on the held Q1 2022 files. In 99,288 consecutive symbol
pairs it fires once: SETFGOLD on 2022-01-06, ratio about 0.0101. That is an observation; the
event behind it is not verified.

## 7. Corporate actions (B7)

- **Needed:** split, bonus, rights, consolidation, demerger and merger records for every
  scanned symbol, 2021-2025. Use the `nse/research/corporate_actions.py` format, with a
  source and the SHA-256 of the saved source document.
- **Source:** NSE's corporate-actions listing or company filings. The export format is
  *unverified* (`DATA_REQUIREMENTS.md` §5).
- **Cross-check, once data exists:** every recorded price-scale action should coincide with a
  PREVCLOSE discontinuity on its ex-date, and every discontinuity should be explained by a
  record. This assumes NSE resets PREVCLOSE on the ex-date, which is *unverified* and is
  tested by the cross-check itself.
- **Until an adjustment convention is approved:** no price is adjusted. A symbol whose
  history crosses a price-scale event stays at G0 MANUAL. A backtest trade alive across one
  is excluded from the metrics.

## 8. Remaining dependencies

1. Your approval to download the 1,171 legacy-and-UDiFF-era files (D31).
2. The UDiFF samples (§4), then a UDiFF loader.
3. Approval of the sample symbols, and the official Nifty 100 constituent file (D1, B11).
4. Corporate-action records and an adjustment decision (B7).
