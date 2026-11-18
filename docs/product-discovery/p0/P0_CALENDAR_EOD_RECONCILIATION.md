# P0 calendar and EOD reconciliation

**Dated 2026-11-10. Calendar versus archives: reconciled for 2016-2025. `DATA_READY` is not claimed.**

Investigation: Calendar and EOD audit, agent id cad63826-9441-4c05-a1b3-d3719b590dce (read-only).
This pass then corrected the living status sentences that still quoted 2,462 accepted
days and four unresolved Dhanteras dates, and regenerated the coverage report.

## 1. Current counts

| Item | Count |
|---|---|
| Calendar years | 2016-2025. 211 events, all `CONFIRMED`. 0 `UNRESOLVED` |
| Equity sessions | **2,466** (`NORMAL` 2,459 + `NORMAL_SPECIAL` 7) |
| Excluded sessions | **12** (10 Muhurat, 2 DR-switch shortened sessions). Files held. No equity candle |
| Archives in `nse/data/eod/raw` | 2,478 zip files, plus 2 standalone CSV copies |
| Manifest rows | 4,958: 2,478 `ARCHIVE`, 2,478 `ARCHIVE_MEMBER`, 2 `STANDALONE_COPY` |
| Missing equity sessions | 0 |
| Archives on a closed day | 0 |
| Duplicate trade dates | 0 |

Earliest equity archive: 2016-01-01. Latest: 2025-12-31. No internal gap. 6-7 July 2024
are a weekend between the last legacy session (2024-07-05) and the first UDiFF session
(2024-07-08).

The earlier figures 2,462 accepted days and 4 unresolved Dhanteras sessions were the
state before D58. D58 (`USER_APPROVED`, 2026-11-10) confirmed 2016-10-28, 2017-10-17,
2018-11-05 and 2019-10-25 as regular equity sessions, 09:15-15:30, `NORMAL_SPECIAL`.
The Gold ETF and SGB evening extension stays in the note and builds no candle.

## 2. Regenerated coverage

`python3 -m nse.research.cli eod-coverage --start 2016-01-01 --end 2025-12-31` wrote
`nse/output/data_readiness/eod_coverage_2016_2025.json` (gitignored). The previous file,
saved 2026-11-09, still listed the four dates as unresolved, 2,462 trading days, and
`eod_ready` false.

| Field | Regenerated value |
|---|---|
| Trading days in window | 2,466 |
| Accepted trading days | 2,466 |
| Missing | 0 |
| Unresolved dates | none |
| Roles | `TRADING_DAY` 2,466, `EXCLUDED_SESSION_D33` 12, 2 standalone copies |
| `eod_ready` | true, no blockers |
| `data_ready` | false. The report does not evaluate universe review or identity |
| Coverage | 100.0% |
| Files loaded | 2,480 |

A full rehash of all 2,478 zips was not repeated. The investigation rehashed 30
archives, including the four Dhanteras files and all 12 excluded files, and all 30
matched the manifest. The 2026-11-09 parse had stored a sha256 for every raw file, and
those hashes matched the manifest for the bytes still on disk.

## 3. Excluded sessions

These 12 files are in `raw/` and in the manifest. They are not equity candles (D30, D52).

| Date | Classification | File |
|---|---|---|
| 2016-10-30 | Muhurat 18:30-19:30 | `cm30OCT2016bhav.csv.zip` |
| 2017-10-19 | Muhurat 18:30-19:30 | `cm19OCT2017bhav.csv.zip` |
| 2018-11-07 | Muhurat 17:30-18:30 | `cm07NOV2018bhav.csv.zip` |
| 2019-10-27 | Muhurat 18:15-19:15 | `cm27OCT2019bhav.csv.zip` |
| 2020-11-14 | Muhurat 18:15-19:15 | `cm14NOV2020bhav.csv.zip` |
| 2021-11-04 | Muhurat 18:15-19:15 | `cm04NOV2021bhav.csv.zip` |
| 2022-10-24 | Muhurat 18:15-19:15 | `cm24OCT2022bhav.csv.zip` |
| 2023-11-12 | Muhurat 18:15-19:15 | `cm12NOV2023bhav.csv.zip` |
| 2024-03-02 | Shortened DR-switch | `cm02MAR2024bhav.csv.zip` |
| 2024-05-18 | Shortened DR-switch | `cm18MAY2024bhav.csv.zip` |
| 2024-11-01 | Muhurat 18:00-19:00 | `BhavCopy_NSE_CM_0_0_0_20241101_F_0000.csv.zip` |
| 2025-10-21 | Muhurat 13:45-14:45 | `BhavCopy_NSE_CM_0_0_0_20251021_F_0000.csv.zip` |

2025-10-21 sits inside the regular clock and remains Muhurat. 2024-01-20 is a confirmed
`NORMAL_SPECIAL` session whose 09:15-15:30 hours are inferred from NSE/CMTR/41180,
because NSE/MSD/60340 prints no times. That inference stays on the readiness list. It
is not an unresolved date.

## 4. Provenance left as found

- 2,475 archives are `SCRIPT_DOWNLOADED_USER_APPROVED` with a URL.
- 3 archives are `USER_CONFIRMED` without an exact page: `cm03JAN2022bhav.csv.zip`, `cm04JAN2022bhav.csv.zip`, `cm29DEC2023bhav.csv.zip`. `downloaded_on` is `UNKNOWN` for `cm04JAN2022` only.
- Calendar source NSE/CMTR/50560 has `downloaded_on` `UNKNOWN` and a verified file hash.
- Inbox holds 2,416 of the 2,478 zips. The research set is `raw/`, not the inbox.
- Two quarantine zips match the raw archives and were ingested afterwards. They are inside the 2,466. Six superseded `.download` leftovers are not the research bytes.

## 5. Status text corrected in this pass

These living records now say 2,466 and no unresolved Dhanteras date:

- `nse/research/readiness.py` `eod_loader.reference_validated` (it still said 1,233 files for 2021-2025)
- `nse/docs/DECISION_LOG.md` D55 implementation row
- `nse/docs/DECISION_REGISTER.md` DATA-2
- `nse/docs/DATA_SOURCE_REGISTRY.md` legacy-bhavcopy and calendar rows
- `nse/docs/IMPLEMENTATION_BLOCKERS.md` Part 11 DATA-2, CAL-2, and the `DATA_READY` paragraph
- `nse/docs/TRACEABILITY.md` rows 84 and 85
- `docs/MILESTONE_STATUS.md` D48, D55, and gate A

The calendar readiness flag already said 2,466 before this pass. `scanner._last_unresolved_date` still implements ED-44 and fires only when a date is unresolved. No date in 2016-2025 is.

## 6. Historical text left unchanged

These still describe the pre-D58 cut. They are earlier audits or narrative drafts, and
were not rewritten as if this count had been known then:

- `nse/docs/REAL_DATA_READINESS.md` sections after the D58 note in 0D
- `docs/product-discovery/00_EXECUTIVE_SUMMARY.md` and the surrounding discovery notes
- `docs/product-discovery/priority-03/PRIORITY_03_EXECUTIVE_REPORT.md` and `RESEARCH_ENGINE_CORRECTNESS_AUDIT.md`
- `docs/implementation/DATA_AND_RELEASE_GATE_STATUS.md`, `IMPLEMENTATION_EXECUTIVE_SUMMARY.md`, `TASK_COMPLETION_MATRIX.md`
- The body of `docs/product-discovery/phase-01/T002_DHANTERAS_EVIDENCE_REPORT.md` (its opening update already records D58)

## 7. What this does not close

An EOD file does not make a symbol eligible. Universe review, the three unevidenced ISIN
changes, and corporate-action coverage stay blocked. TradingView comparison is absent.
The 2024-01-20 hours remain an inference. `DATA_READY` is not claimed.
