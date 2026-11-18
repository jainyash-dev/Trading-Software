# T-002: Historical Dhanteras dates: evidence report

**Dated 2026-11-10. Prepared by an agent; the classifications here are recommendations.**
The canonical calendar (`nse/data/calendar/events.csv`) is unchanged.

**Update 2026-11-10: the owner approved option A (D58).** The four rows are now
`CONFIRMED` (`NORMAL_SPECIAL`, 09:15-15:30), and the ED-44 cut no longer applies. The
"Existing calendar value" fields below describe the state before that decision.

## 1. Summary

The four dates are still `UNRESOLVED` in `events.csv`, as owner decision D54 (CAL-2)
requires. For each date:

- an official NSE Capital Market circular is held locally;
- its SHA-256 matches `sources.csv`;
- it was read in full for this report.

All four circulars say the same thing. The equity market ran on **regular hours
("Regular Market Timing (there is no change to this)": Normal Market 09:15-15:30)**. A
separate evening session, 16:25/16:30-19:00 (16:55/17:00-19:00 in 2019), was open **for
Gold ETFs and Sovereign Gold Bonds only**. NSE published a normal bhavcopy for each date.

**The evidence for the equity session is complete and consistent.** What is missing is a
calendar *representation*: `events.csv` has no event type for an extension limited to some
instruments. That is why the rows were left UNRESOLVED (CAL-2). Classifying them is the
owner's decision.

**Why it matters now:**
- ED-44 cuts every scan's history after the latest UNRESOLVED date, 2019-10-25.
- So Monthly and higher timeframes see no candle before 28 Oct 2019.
- The Yearly range stays not ready (ED-31).
- Classifying the four dates would remove the cut (ED-44, "Reversible").

## 2. Shared evidence (all four dates)

| Item | Finding |
|---|---|
| Circular type | NSE Capital Market Segment circular titled "Extended LIVE TRADING session on <date> in Capital Market Segment" |
| Festival | Each circular says the extension is held "on the auspicious occasion of Dhanteras" (NSE's own wording) |
| Equity session | Regular market timing table headed "(there is no change to this)": Pre-open 09:00-09:08, Normal Market/Odd lot 09:15-15:30, Closing session 15:40-16:00 |
| Special session | "Extended market timings for Gold ETF and Sovereign Gold Bonds only": pre-open for order cancellation, re-open, close 19:00, no closing session. Annexure 1 lists the eligible securities (series EQ gold ETFs and series GB bonds only) |
| Bhavcopy | "Bhavcopy will be broadcasted thrice": after the normal market, after the post-close session, and after the extended market (Annexure 2) |
| Holiday lists | None of the four dates is a holiday in that year's base circular (no HOLIDAY row in `events.csv`) |
| Muhurat | A separate circular covers Muhurat, held two days later in each year. It is already CONFIRMED and excluded (D30) |

**Bhavcopies held** (manifest hashes match the files in `nse/data/eod/raw/`):

| Date | File | SHA-256 (prefix) | EQ rows | GB rows | RELIANCE close | GOLDBEES close |
|---|---|---|---|---|---|---|
| 2016-10-28 | `cm28OCT2016bhav.csv.zip` | `584d2bb77728` | 1,544 | 5 | 1054.95 | 2739.35 |
| 2017-10-17 | `cm17OCT2017bhav.csv.zip` | `2cdc1a8fcc81` | 1,479 | 9 | 874.35 | 2679.05 |
| 2018-11-05 | `cm05NOV2018bhav.csv.zip` | `2f9697f7aacb` | 1,533 | 21 | 1090.30 | 2844.10 |
| 2019-10-25 | `cm25OCT2019bhav.csv.zip` | `afbdd9171f8a` | 1,488 | 27 | 1431.20 | 3428.15 |

Every row carries the session date as its TIMESTAMP. The file does not say which of the
three broadcasts it is. For ordinary equities that does not matter: they did not trade in
the extension. For gold ETFs and SGBs the held close may or may not include extension
trades. None of those instruments is in the NIFTY 100 universe.

## 3. Per-date evidence

### 2016-10-28 (Friday)

| Field | Value |
|---|---|
| Calendar date | 2016-10-28 |
| Festival observance | Dhanteras, per NSE/CMTR/33442 ("on the auspicious occasion of Dhanteras") |
| NSE session | Regular equity session held; additional extended session for Gold ETF and SGB only |
| Session type | **Regular** for equities; **special** (instrument-limited extension) for Gold ETF/SGB |
| Official source | NSE/CMTR/33442, Circular 57/2016, dated October 18, 2016. "Extended LIVE TRADING session on Friday, October 28, 2016 in Capital Market Segment". https://nsearchives.nseindia.com/content/circulars/CMTR33442.pdf (local `circulars/CMTR33442.pdf`, SHA-256 `19c48d50…e5f9c259`, matches `sources.csv`) |
| Existing calendar value | `SPECIAL_SESSION`, 09:15-15:30, status **UNRESOLVED** |
| Evidence status | **Verified** for the equity session (circular plus held bhavcopy) |
| Proposed classification | Recommendation: regular equity session (see section 4, option A) |
| Owner decision | |
| Notes | Extension: cancellation pre-open 16:25, re-open 16:30, close 19:00 |

### 2017-10-17 (Tuesday)

| Field | Value |
|---|---|
| Calendar date | 2017-10-17 |
| Festival observance | Dhanteras, per NSE/CMTR/36003 |
| NSE session | Regular equity session held; extended session for Gold ETF and SGB only |
| Session type | **Regular** for equities; **special** for Gold ETF/SGB |
| Official source | NSE/CMTR/36003, Circular 61/2017, dated October 04, 2017. "Extended LIVE TRADING session on Tuesday, October 17, 2017 in Capital Market Segment". https://nsearchives.nseindia.com/content/circulars/CMTR36003.pdf (local copy, SHA-256 `bc414302…ccba7`, matches) |
| Existing calendar value | `SPECIAL_SESSION`, 09:15-15:30, **UNRESOLVED** |
| Evidence status | **Verified** for the equity session |
| Proposed classification | Recommendation: regular equity session (option A) |
| Owner decision | |
| Notes | Extension timings as in 2016 |

### 2018-11-05 (Monday)

| Field | Value |
|---|---|
| Calendar date | 2018-11-05 |
| Festival observance | Dhanteras, per NSE/CMTR/39215 |
| NSE session | Regular equity session held; extended session for Gold ETF and SGB only |
| Session type | **Regular** for equities; **special** for Gold ETF/SGB |
| Official source | NSE/CMTR/39215, Circular 93/2018, dated October 23, 2018. "Extended LIVE TRADING session on Monday, November 05, 2018 in Capital Market Segment". https://nsearchives.nseindia.com/content/circulars/CMTR39215.pdf (local copy, SHA-256 `f86bddc5…161b37`, matches) |
| Existing calendar value | `SPECIAL_SESSION`, 09:15-15:30, **UNRESOLVED** |
| Evidence status | **Verified** for the equity session |
| Proposed classification | Recommendation: regular equity session (option A) |
| Owner decision | |
| Notes | The regular table also lists morning and afternoon block-deal windows and an auction market, all "no change". Extension 16:25/16:30-19:00 |

### 2019-10-25 (Friday)

| Field | Value |
|---|---|
| Calendar date | 2019-10-25 |
| Festival observance | Dhanteras, per NSE/CMTR/42455 |
| NSE session | Regular equity session held; extended session for Gold ETF and SGB only |
| Session type | **Regular** for equities; **special** for Gold ETF/SGB |
| Official source | NSE/CMTR/42455, Circular 130/2019, dated October 18, 2019. "Extended LIVE TRADING session on Friday, October 25, 2019 in Capital Market Segment". https://nsearchives.nseindia.com/content/circulars/CMTR42455.pdf (local copy, SHA-256 `5b3259ab…446a20f`, matches) |
| Existing calendar value | `SPECIAL_SESSION`, 09:15-15:30, **UNRESOLVED** |
| Evidence status | **Verified** for the equity session |
| Proposed classification | Recommendation: regular equity session (option A) |
| Owner decision | |
| Notes | Extension 16:55/17:00-19:00. The circular adds "no trade modification during the extended market". The Maharashtra election holiday on 2019-10-21 (NSE/MSD/42319) is a separate, CONFIRMED row |

## 4. Options for the owner (CAL-2)

| Option | Calendar change (owner-authorised only) | Effect | Risk |
|---|---|---|---|
| **A. Regular equity session (recommended)** | Set the four existing `SPECIAL_SESSION` rows (09:15-15:30) to `CONFIRMED`, keeping their notes on the gold extension. `nse_calendar` then classifies each date `NORMAL_SPECIAL` (regular hours, candles built) | Removes the ED-44 history cut; 2016-2019 candles become usable; the Yearly range can become ready | Low for equities. Gold ETF/SGB closes on those dates may include extension trades; no universe member is affected |
| B. Remove the rows | Delete the four rows; each date becomes an ordinary `NORMAL` weekday | Same scan effect as A | Loses the provenance and the gold-extension note; not recommended |
| C. Keep UNRESOLVED (status quo) | None | History stays cut after 2019-10-25 | Fail-closed and safe, at a real cost in history depth |

A and B are calendar edits, which D54 and the Phase 01 boundary reserve for the owner.
`NORMAL_SPECIAL` is the treatment D30 provisionally gives to special days on regular hours,
such as budget Saturdays. Option A therefore reuses an approved category and needs no new
event type.

## 5. Missing evidence

- None for the equity session on any of the four dates.
- Not established: which of the three same-day broadcasts the held bhavcopy is. This
  matters only for Gold ETF/SGB rows.
- External corroboration (optional): a TradingView daily bar for a NIFTY 100 stock on each
  date (observations TV-CAL-P01-13 to 16 in the T-005 worksheet). TradingView would only
  corroborate; the circular is the authority.

No online search was needed: the official circulars are already in the repository, with
URLs and hashes recorded. No URL, title or date in this report is new; each was read from
the circular itself or from `sources.csv`.
