# Data Requirements: External Validation Phase

**Project:** NSE GTF Demand & Supply Swing-Trading Research System
**Date:** 2026-10-26
**Window:** 2021-01-01 to 2025-12-31 (D29)
**Rules:**
- Local files only, with provenance, download date and file hash (D31).
- No network-fetching code.
- No broker API (D32).
- Anything marked *to confirm* has not been verified and must not be relied on until it is.

---

## 1. Trading calendar (B17)

See `nse/data/calendar/README.md` for the exact circulars to download and where to put them.

---

## 2. Daily end-of-day data (B6)

### 2.1 Files
NSE changed its capital-market bhavcopy format during the window. NSE's report listing says the old file was discontinued with effect from 8 July 2024.

| Period | File (as NSE names it) | Format |
|---|---|---|
| 2021-01-01 to the last day before the switch | `cmDDMMMYYYYbhav.csv.zip` (legacy CM bhavcopy) | Legacy CSV |
| From 2024-07-08 | `BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip` (UDiFF common bhavcopy) | UDiFF CSV |

**Column names are not confirmed.** Secondary sources report that the UDiFF file renamed the columns and changed the date format; no reliable source in hand lists them. The loader will be written against the actual header rows of your sample files.

### 2.2 Fields the loader needs (in whichever names each format uses)
- **Required:**
  - trade date;
  - symbol;
  - series (only `EQ` rows are used);
  - ISIN;
  - open, high, low, close;
  - traded quantity (volume).
- **Wanted for cross-checks:** previous close (it reveals unadjusted corporate-action gaps) and number of trades.

### 2.3 What to provide, in this order
1. **Two sample files first:** one legacy file from the last week before the switch (e.g. 5 July 2024) and one UDiFF file (e.g. 8 July 2024). Nothing else is built until the headers are seen.
2. After the loader is approved, **every daily file for the window** (about 1,240 trading days).
3. **Placement:** `nse/data/eod/raw/`, as downloaded (zipped). Record the download date per batch. The loader writes a manifest with each file's SHA-256.

**Decision needed (repository size):** roughly 1,240 zip files. My recommendation is to keep them **out of git** (local only) and commit only the manifest of names and hashes. That needs a `.gitignore` entry, which this repository does not yet have.

### 2.4 Known limitation
Bhavcopy prices are **unadjusted**. They cannot be used for zone detection across a split or bonus until B7 is settled; until then they serve calendar reconciliation and price cross-checks only.

---

## 3. TradingView exports (B8, B10; also a daily-data cross-check)

- **Availability:** TradingView's "Export chart data" writes a CSV of the bars loaded on the chart, plus any plotted indicator values visible at the time.
  - Plan requirements and bar limits are *to confirm*. Secondary sources say export needs a paid plan, with about 10,000 bars on lower tiers.
- **Zones are probably not exported (*to confirm*).** The indicator draws its zones as boxes, lines and labels, which are drawings, not plotted series. So each zone would have to be recorded manually: proximal line, distal line, pattern, score label (`X/7`), test marking and the bar it starts on.
  - A recording template will be proposed once you confirm what the export contains.
  - The Pine Script will not be modified to export them.
- **Indicator settings for parity:** unchanged, except **max base candles = 5** (an existing input; D12, PR4).
- **What to provide first:** one daily export for one stock with the indicator loaded. Its columns (time format, time zone, OHLC, volume, plot columns) decide the loader format.
- **Placement:** `nse/data/tradingview/<SYMBOL>/<timeframe>.csv`, with download date recorded.

---

## 4. Intraday data (75-minute and 125-minute; B15, D16)

### 4.1 Requirements
- **Bar alignment:** 75-minute bars must start at 09:15, 10:30, 11:45, 13:00 and 14:15. 125-minute bars must start at 09:15, 11:20 and 13:25 (RB 186-193). No 60- or 120-minute substitutes.
- **Finer base series:** the HTF freshness orchestrator needs an interval that divides both 75 and 125 minutes: 1, 5 or 25 minutes.
- **Depth, per stock:**

| Purpose | Minimum | Preferred | 75m candles | 125m candles | 25m candles |
|---|---|---|---|---|---|
| Parity sample size | 6 months | 12 months | ~625 / ~1,240 | ~375 / ~745 | ~1,860 / ~3,720 |
| Whole window | - | 5 years | ~6,200 | ~3,700 | ~18,600 |

(About 248 sessions a year; 5, 3 and 15 candles per session.) The WIT trend gate is Daily (D22), which comes from daily data. Intraday depth therefore matters for 75/125-minute zones and for the orchestrator's intraday base, not for the trend.

### 4.2 Local options
| Option | Status | Concern |
|---|---|---|
| TradingView export of 75m, 125m and 25m charts | Possible; plan and bar limits *to confirm* | **Alignment risk.** TradingView's own 2020 note says larger intraday bars align to the week, month or year rather than the session, so its 75/125-minute bars may not start at 09:15 every day. Must be checked on a sample before any parity use. |
| NSE's own historical intraday data | Sold by NSE as a paid product (*to confirm* availability, format and cost) | Paid; licence terms |
| Broker APIs (Kite Connect and others) | **Not used** (D32) | Needs your separate, explicit approval |

### 4.3 Recommendation
1. Export **one** 75-minute and **one** 125-minute chart for one stock and check that every day's first bar starts at 09:15.
2. If aligned, export 12 months (calendar 2025) of 75m, 125m and 25m bars for the sample.
3. If not aligned, or the bar limits are too small, I will bring a separate recommendation for your approval (NSE paid data or a broker API). No broker connection is made before that.

---

## 5. Corporate actions (B7; later step)
Corporate-action work starts only after the data source and an adjustment convention are agreed. The required record is then each sample stock's corporate actions for 2021-2025 from NSE's corporate-actions listing (export format *to confirm*), saved under `nse/data/corporate_actions/`.

---

## 6. Proposed sample stocks (for approval)

**Selection criteria:**
- sector diversity;
- split/bonus coverage (only events verified from a filing or exchange notice);
- a non-split adjustment (a demerger);
- a recent listing (partial first period and insufficient-history paths);
- control stocks expected to have no split or bonus.

| # | NSE symbol | Sector | Role | Event in window and evidence |
|---|---|---|---|---|
| 1 | NESTLEIND | FMCG | Split | Sub-division 1:10 (face value 10 to 1); record date and ex-date 2024-01-05. Company announcement; BSE filing |
| 2 | TATASTEEL | Metals | Split | Sub-division 1:10; ex-date 2022-07-28, record date 2022-07-29; new ISIN INE081A01020. NSE F&O adjustment circular; reports |
| 3 | BAJFINANCE | NBFC | Split + bonus, same day | Sub-division 1:2 (face value 2 to 1) and bonus 4:1; record date and ex-date 2025-06-16. Company filing of 6 June 2025 |
| 4 | RELIANCE | Energy / conglomerate | Demerger + bonus | Jio Financial Services demerger: special pre-open price-discovery session 2023-07-20 (NSE index adjustment notice). Bonus 1:1, record date 2024-10-28 (company filing) |
| 5 | HAL | Defence | Split | Sub-division 1:2 (face value 10 to 5); ex-date 2023-09-28, record date 2023-09-29. NSE circular of 27 Sep 2023 |
| 6 | BEL | Defence electronics | Bonus | Bonus 2:1; ex-date 2022-09-15, record date 2022-09-16. BEL notice to NSE (an earlier recollection of "March 2022" was wrong) |
| 7 | LICI | Insurance | Recent listing | Listed on NSE 2022-05-17 (issue price 949; opened at 872) |
| 8 | ICICIBANK | Banking | Control | No split or bonus expected; *to confirm* from the corporate-actions file |
| 9 | INFY | IT services | Control | No split or bonus expected; *to confirm* |
| 10 | MARUTI | Automobiles | Control | No split or bonus expected; *to confirm* |

**Before approval:**
- Confirm each symbol is in the **current** official Nifty 100 list. Download `ind_nifty100list.csv` from NSE Indices into `nse/data/universe/` (D1). Point-in-time membership remains B11.
- Ex-dates in this table come from filings and reports. They are re-checked against the bhavcopy data once it is loaded (a previous-close gap on the ex-date).

**Deliberately left out of the first sample** (candidates for a second round):
- ITC (ITC Hotels demerger, January 2025);
- HDFC Bank (HDFC Ltd merger, July 2023);
- Eternal, formerly Zomato (symbol change).
