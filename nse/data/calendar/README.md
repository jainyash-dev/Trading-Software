# NSE trading calendar data (blocker B17)

This folder holds the official NSE circulars and the calendar tables built from them.
`nse/calendar/nse_calendar.py` reads it. Nothing here is downloaded by code.

## 1. What to download and where to put it

Save each PDF into `nse/data/calendar/circulars/`. Two names are involved:

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

### Base holiday circulars, capital market segment (required, one per year)

| Year | Reference (from search; confirm on the PDF) | Circular date (confirm) | Official URL |
|---|---|---|---|
| 2021 | NSE/CMTR/46623 (Circular 113/2020) | 2020-12-11 | https://archives.nseindia.com/content/circulars/CMTR46623.pdf |
| 2022 | NSE/CMTR/50560 (Circular 117/2021) | 2021-12-10 | https://archives.nseindia.com/content/circulars/CMTR50560.pdf |
| 2023 | NSE/CMTR/54757 (Circular 150/2022) | 2022-12-08 | https://archives.nseindia.com/content/circulars/CMTR54757.pdf |
| 2024 | NSE/CMTR/59722 (Circular 154/2023) | 2023-12-12 | https://nsearchives.nseindia.com/content/circulars/CMTR59722.pdf |
| 2025 | NSE/CMTR/65587 (Circular 170/2024) | 2024-12-13 | https://nsearchives.nseindia.com/content/circulars/CMTR65587.pdf |

Use the CMTR (capital market) circulars only. The commodity (COM), currency (CD), debt
(DS) and clearing (CMPT) circulars have different schedules.

### Amendments and special sessions (required where they exist)

Their circular numbers are not yet confirmed, so find them on NSE's circulars page
(https://www.nseindia.com/resources/exchange-communication-circulars) by date and
subject, and save them the same way.

| Event | Approximate circular date | Why it matters |
|---|---|---|
| Trading holiday 22 Jan 2024, and full trading session Saturday 20 Jan 2024 | ~19 Jan 2024 | Added holiday; extra Saturday on regular hours |
| Live session with disaster-recovery switch, Saturday 2 Mar 2024 | ~14 Feb 2024 | Shortened Saturday session |
| Live session with disaster-recovery switch, Saturday 18 May 2024 | ~7 May 2024 | Shortened session; secondary sources disagree on its hours |
| Trading holiday 20 May 2024 (parliamentary elections, Mumbai) | 8 Apr 2024 | Added holiday |
| Trading holiday 20 Nov 2024 (Maharashtra assembly elections) | ~8 Nov 2024 | Added holiday; secondary sources disagree on full vs partial closure |
| Live session Saturday 1 Feb 2025 (Union Budget) | 23 Dec 2024 | Extra Saturday |
| Muhurat trading timings: 4 Nov 2021, 24 Oct 2022, 12 Nov 2023, 1 Nov 2024, 21 Oct 2025 | a few weeks before each | Muhurat sessions are flagged and excluded (D30) |

This list is what targeted searches found. It may be incomplete. Any session or
holiday it misses is caught later by reconciling the calendar against the dates that
have an NSE end-of-day file (`reconcile()`), so a gap here becomes a reported
discrepancy rather than a silent error.

## 2. What happens next

1. You place the PDFs and record, per file, the date you downloaded it.
2. Claude reads each PDF, transcribes its dates into `events.csv` and fills
   `sources.csv` (reference, kind, year, circular date, title, file name, SHA-256,
   download date, URL). You review both before they are relied on.
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
| NSE/CMTR/54023 | `CMTR54023.pdf` | 2026-10-28 | Retrieved from the recorded URL. |
| NSE/CMTR/54757 | `CMTR54757.pdf` | 2026-10-28 | Retrieved from the recorded URL; identical copy on `nsearchives.nseindia.com`. |
| NSE/CMTR/59124 | `CMTR59124.pdf` | 2026-10-28 | Retrieved from the recorded URL; identical copy on `nsearchives.nseindia.com`. |
| NSE/CMTR/41180 | `CMTR41180.pdf` | 2026-10-28 | Retrieved from the recorded URL. Provisional evidence for normal hours of 09:15-15:30 (effective 3 Jun 2019). Later amendments are not yet checked. |

Every row was checked against the circular's extracted text and its rendered page.

Open items:
- Bakri Id 2023 is printed as 28 June in 54757 and reportedly moved to 29 June. No amending circular is held, so both dates are `UNRESOLVED`.
- No TradingView comparison has been made yet (B17 stays open).
