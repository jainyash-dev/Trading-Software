# Data acquisition report (2026-11-02)

> Dated snapshot (2026-11-02). Current decision status is `nse/docs/DECISION_LOG.md`.
> D40 is `USER_APPROVED` in section 1F. The calendar row below records this date's
> measurement, including the label that was current then. It is not the current status.

## What is held (measured with `python3 -m nse.research.cli acquire-coverage`)

| Item | Status |
|---|---|
| Legacy CM bhavcopies | 62 archives, 2022-01-03 to 2023-12-29, manifest SHA-256 verified, provenance USER_CONFIRMED |
| Coverage 2022-2023 | 62 HELD, 432 MISSING of 494 expected sessions (official calendar) |
| Coverage 2016-2021, 2024-2026 | none held |
| UDiFF files | none; format and switch date unverified (B18) |
| Calendar | Official circular tables 2021-2025, hash-verified; not externally validated (B17); D40 PROPOSED |
| Nifty 100 membership | none (B11) |
| Instrument / ISIN history | none |
| Corporate actions | none (B7); PREVCLOSE discontinuities are detected and make G0 MANUAL |
| Intraday | none (B6, D32) |

The requested ten-year window (Nov 2016 - Nov 2026) is far from covered. The official
calendar in the repository starts in 2021, so sessions before 2021 cannot even be
planned as "expected" (they show as CALENDAR_UNVALIDATED candidate weekdays).

## Supported formats

| Format | Status |
|---|---|
| Legacy `cmDDMMMYYYYbhav.csv.zip` | Supported, strict loader, two samples documented (`EOD_FORMAT_EVIDENCE.md`) |
| UDiFF common bhavcopy | Detected by header and quarantined `FORMAT_UNVERIFIED_B18`; never ingested |
| User daily CSV | Supported (`marketdata.from_csv`), labelled PRICE_ADJUSTMENT_UNKNOWN unless stated |

## Acquisition architecture

Owner downloads into an inbox; `acquire-ingest` verifies and copies; `daily-update` handles
one session (closed day, file not yet available with retry count, alert after max attempts,
duplicate, quarantine). There is no network code (D31) and no paid or licensed provider; a
future provider must deliver local files plus provenance and needs owner approval (D17).
Raw files are never overwritten (a revised file for a held session is quarantined), and
raw and adjusted prices are never mixed (nothing adjusts prices).

## What the owner must supply

1. The missing legacy sessions for the chosen window (`acquire-plan` lists them).
2. One UDiFF sample per format variant after the switch, with its source page (B18).
3. Official calendar circulars for any year outside 2021-2025.
4. Nifty 100 constituent history from NSE Indices (B11).
5. Corporate-action records and an adjustment convention (B7).
