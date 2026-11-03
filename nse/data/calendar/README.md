# NSE trading calendar data (blocker B17)

This folder holds the official NSE circulars and the calendar tables built from them.
`nse/calendar/nse_calendar.py` reads it. Nothing here is downloaded by code.

## 1. What to download and where to put it

Save each circular into `nse/data/calendar/circulars/`. Two names are involved:

- **Source file name:** the name NSE serves, at the end of the official URL (for example
  `CMTR59722.pdf`). It is recorded only through the `url` column of `sources.csv`.
- **Local file name:** the name of the file in `circulars/`, recorded in the `file_name`
  column. The file is identified by its SHA-256, not by its name.

New downloads keep the source file name as their local file name. A file supplied under
another name keeps that name; it is not renamed. The only such file is
`NSE_CMTR_50560_2022_trading_holidays.pdf.pdf` (source file name `CMTR50560.pdf`). It is
byte-identical (same SHA-256 and size) to the copy retrieved from
https://archives.nseindia.com/content/circulars/CMTR50560.pdf on 2026-10-28. Its own
download date is not known, so `downloaded_on` is `UNKNOWN`; the retrieval date of the
identical archive copy is not used as its download date (§4).

Some circulars are served only as a ZIP that holds the circular PDF and its attachments
(for example `CMTR57285.zip`; the `.pdf` URL returns 404). The ZIP is stored and hashed
exactly as served.

### Base holiday circulars, capital market segment (one per year; all obtained)

| Year | Reference | Circular date | Holidays printed (weekday + weekend) |
|---|---|---|---|
| 2021 | NSE/CMTR/46623 (Circular 113/2020) | 2020-12-11 | 14 + 5 |
| 2022 | NSE/CMTR/50560 (Circular 117/2021) | 2021-12-10 | 13 + 5 |
| 2023 | NSE/CMTR/54757 (Circular 150/2022) | 2022-12-08 | 15 + 4 |
| 2024 | NSE/CMTR/59722 (Circular 154/2023) | 2023-12-12 | 14 + 5 |
| 2025 | NSE/CMTR/65587 (Circular 170/2024) | 2024-12-13 | 14 + 4 |

Use the CMTR (capital market) circulars, and Member Service Department (MSD) circulars
where they set capital-market sessions. The commodity (COM), currency (CD), debt (DS),
NSE Invest (NMF) and clearing (CMPT) circulars have different schedules and are not used.

### Amendments and special sessions (obtained)

| Date | Event | Circular | Calendar treatment |
|---|---|---|---|
| 2021-11-04 | Muhurat, Normal Market 18:15-19:15 | NSE/CMTR/50050 | Excluded (D30) |
| 2022-10-24 | Muhurat, 18:15-19:15 | NSE/CMTR/54023 | Excluded (D30) |
| 2023-06-28 / 06-29 | Bakri Id moved from 28 to 29 June | NSE/CMTR/57285 (ZIP) | 28 June normal; 29 June holiday |
| 2023-11-12 | Muhurat (Sunday), 18:15-19:15 | NSE/CMTR/59124 | Excluded (D30) |
| 2024-01-20 | Saturday regular session from the primary site, "as per regular market timings" (withdraws the DR-switch session of NSE/MSD/59999, 60300, 60318) | NSE/MSD/60340 | NORMAL_SPECIAL (D30 provisional); hours taken from NSE/CMTR/41180 |
| 2024-01-22 | Added holiday | NSE/CMTR/60338 (ZIP) | Holiday |
| 2024-03-02 | Saturday DR-switch session: 09:15-10:00 and 11:30-12:30 | NSE/MSD/60677 | Shortened, excluded (D30) |
| 2024-05-18 | Saturday DR-switch session: 09:15-10:00 and 11:30-12:30 | NSE/MSD/61893 | Shortened, excluded (D30) |
| 2024-05-20 | Added holiday (parliamentary elections, Mumbai) | NSE/CMTR/61518 | Holiday |
| 2024-11-01 | Muhurat, 18:00-19:00 | NSE/CMTR/64628 | Excluded (D30) |
| 2024-11-20 | Added holiday (Maharashtra assembly elections) | NSE/CMTR/64960 | Holiday |
| 2025-02-01 | Saturday Budget session, 09:15-15:30 printed | NSE/CMTR/65729 | NORMAL_SPECIAL (D30 provisional) |
| 2025-10-21 | Muhurat, 13:45-14:45 (inside regular clock hours) | NSE/CMTR/70319 | Excluded (D30) |

**Completeness is not proven.** These are the events targeted searches and number-range
checks found. A missed holiday or session is caught only by reconciling the calendar with
the dates that have an NSE end-of-day file (`reconcile()`). That has been done for
2022-01-03 to 2022-03-31 only (clean); the other periods have no EOD files yet.

## 2. What happens next

1. Each new circular is saved here and recorded with its download date.
2. Its dates are transcribed into `events.csv`, and `sources.csv` gets its reference,
   kind, year, circular date, title, file name, SHA-256, download date and URL.
   `tests/test_nse_calendar_data.py` holds an independent second transcription.
3. Rows where the circulars and other evidence disagree are marked `UNRESOLVED`
   with a note. The calendar refuses to answer for those dates until resolved.

`sources.template.csv` is a starting point for `sources.csv`. It is not read by code.

## 3. File formats

See the module docstring in `nse/calendar/nse_calendar.py` for the exact columns of
`sources.csv` and `events.csv` and the rules applied to them.

## 4. Recorded provenance (2026-10-28, D40)

`sources.csv` has no note column, so the provenance notes for each file are kept here.

| Source | File in `circulars/` | Downloaded | Provenance |
|---|---|---|---|
| NSE/CMTR/50560 | `NSE_CMTR_50560_2022_trading_holidays.pdf.pdf` | UNKNOWN | Supplied by the user. Its original download date is not known and is not inferred from file times. The copy retrieved from the recorded archive URL on 2026-10-28 is byte-identical (same SHA-256 and size), so the URL is recorded. The file keeps its supplied name. |
| NSE/CMTR/54757, 59124 | `CMTR54757.pdf`, `CMTR59124.pdf` | 2026-10-28 | Retrieved from the recorded URL; identical copies on `nsearchives.nseindia.com`. |
| NSE/CMTR/41180 | `CMTR41180.pdf` | 2026-10-28 | Provisional evidence for normal hours of 09:15-15:30 (effective 3 Jun 2019). NSE/CMTR/65729 (2024-12-23) states the same hours as the "standard market timings". A systematic review of timing circulars between them has not been made. |
| All other sources in `sources.csv` | the NSE file name | 2026-10-28 | Retrieved from the recorded URL. |

Every row in `events.csv` was checked against the circular's extracted text. The base
circulars and every circular with a timing table were also checked on the rendered pages.

Open items:
- No TradingView comparison has been made yet (B8, B17).
- Reconciliation with EOD files covers Q1 2022 only.
