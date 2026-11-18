# Data source registry

Every external data source the research system reads or holds as evidence, and how much
of it is trusted. This is an index: per-file hashes, sizes, URLs and download dates live in
each folder's own registry (linked below), never only here. Created in MP1 (2026-11-09).

Rules for every source (D31, ED-23):
- local files only;
- no network code under `nse/`;
- every file recorded with its URL or supplier, its download date (or `UNKNOWN`, never
  inferred) and its SHA-256;
- a file served today is not proof of what was published on its date.

## 1. Research inputs (read by scans, scan history and backtests)

| Source | Format and schema | Local path / registry | Selection rule | Trust status | Gaps |
|---|---|---|---|---|---|
| NSE CM bhavcopy, legacy | `cmDDMMMYYYYbhav.csv.zip`, schema `LEGACY_14` (`EOD_FORMAT_EVIDENCE.md` §5); two exact variants `LEGACY_13_CRLF`, `LEGACY_13_CRLF_SHORTDATE` (ED-38) | `nse/data/eod/raw/`, `nse/data/eod/manifest.csv` | Trade dates up to 2024-07-05 (ED-20) | 2,108 files, 2016-01-01 to 2024-07-05 (D47, D55; ED-25): every equity session accepted, including the four 2016-2019 Dhanteras sessions (D58), plus excluded-session files (ED-34) | none |
| NSE CM bhavcopy, UDiFF | `BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip`, schemas `UDIFF_2024A` / `UDIFF_2024B` (§9) | same folder and manifest | Trade dates from 2024-07-08 (ED-20) | 370 files (2024-07-08 to 2025-12-31, including 2 Muhurat sessions) | none |
| NSE trading calendar | CMTR holiday circulars, amendments and session notices; `events.csv` | `nse/data/calendar/` (`sources.csv`, `circulars/`) | 2016-2025 (D29, D48) | Every source hash-verified; 2016-2025 reconciled with every equity-session archive (2,466) | no UNRESOLVED date (D58); 2024-01-20 hours inferred from NSE/CMTR/41180 |
| Nifty 100 membership | `universe.py` rows, built by `membership.py` from the baseline and changes | `nse/data/universe/` | point in time, effective-date inclusive | Transcribed and cross-checked; UNVERIFIED until human review (D49) | B11-R, B11-P |
| Instrument identity records | `instruments.py` CSV | `nse/data/universe/instrument_records.csv`, `identity_report.json` | point in time | NSE EQUITY_L and symbolchange; first held bhavcopy session where no listing record fits; 27 ISIN changes evidenced by official CA records (ED-37); renames joined via verified ISIN continuity only (D51) | BAJFINANCE 2016-09-09, GRASIM 2016-10-07, YESBANK 2020-03-16 ISIN changes unevidenced |
| Corporate actions | `corporate_actions.py` CSV | `nse/data/corporate_actions/actions.csv` (2,064 events), `coverage.csv` (145 symbols), `collection_log.jsonl`, `raw/` | ex-date | D50: raw prices canonical, events stored separately, never applied; D56 collection (ED-39) | NSE's API is demonstrably incomplete for some symbols (R-10): 46 of 191 return `[]`, including live ICICIPRULI, ETERNAL and PAYTM (retried 2026-11-09). Completeness audit for covered symbols: `nse/output/data_readiness/ca_completeness_2016_2025.json` |
| User daily CSV | `date,open,high,low,close[,volume]` | caller-supplied | - | adjustment and provenance UNKNOWN unless stated | - |

## 2. Evidence (held to verify the inputs; never read by a scan)

| Evidence | Path / registry | What it establishes | Retrieved |
|---|---|---|---|
| Nine legacy and UDiFF bhavcopy samples; circulars NSE/MSD/62424, 56202, 54028 | `nse/data/eod/evidence/` (`manifest.csv`, `sources.csv`, README) | The UDiFF schemas, the switch date, exact cross-format equality on 4 dates | 2026-11-09, Claude, official URLs |
| NSE/MSD/59999, 60300, 60318 (withdrawn); 60340, 60677, 61893 | `nse/data/calendar/circulars/`, `sources.csv` | D40: 20 Jan 2024 was a regular primary-site session; the two-window sessions were 2 Mar and 18 May 2024 | 2026-10-28 and 2026-11-09 |
| NSE Indices NIFTY 100 releases (Feb 2021 to Aug 2025), the dated list of 31 Mar 2022, `IndexInclExcl.xls` | `nse/data/universe/evidence/sources.csv` | B11 inputs. The extracted lists are labelled unreviewed | 2026-11-09, URLs re-fetched byte-identically |
| NSE corporate-actions API responses (191 historical member symbols, 2016-2025; `.retryN.json` files are later re-requests, never overwrites) | `nse/data/corporate_actions/raw/`, `collection_log.jsonl` (URL, status, SHA-256 per request) | B7 events and terms (free text, read by exact patterns); ISIN-change evidence (ED-37) | 2026-11-09 (API output is not byte-stable) |
| INFY OHLC transcribed from Yahoo screenshots | `nse/data/reference/INFY/`, `nse/data/screenshots/yahoo/INFY` | Nothing external: adjustment UNKNOWN, not independent of NSE data | owner, earlier |

## 3. Not held, needed

| Source | Needed for | Blocker |
|---|---|---|
| TradingView exports (INFY D/W/M/3M OHLC, SMA-50, zones, with chart settings) | external parity | B8, B10, B17 |
| ~~An NSE notice classifying the equity session on the four Dhanteras dates 2016-2019~~ No longer needed: the owner classified them from the held circulars (D58, 2026-11-10) | ten-year calendar | CAL-2 (D54, closed by D58) |
| NSE Indices ad-hoc replacement notices; 2016-2020 releases | complete membership | B11 |
| Kite intraday history and interval documentation | WIT | B6, B15 (WIT BLOCKED) |
| A dated Zerodha cost schedule with sources | execution costs | B12 |
