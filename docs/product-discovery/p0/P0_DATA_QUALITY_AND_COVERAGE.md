# Data quality and coverage

**Dated 2026-11-11. Branch `main`. HEAD `9e302df1a81c2b13696d8fab61f05d377481be2e`.**

This pass recounted the calendar against manifest dates. It did not rehash the 2,478
archives and did not modify raw files.

## Calendar and EOD

| Check | Result | Blocks |
|---|---|---|
| Equity sessions 2016-01-01 .. 2025-12-31 | 2,466 | No, for file coverage |
| Excluded Muhurat and DR-switch sessions | 12, all with an archive | They are not equity candles |
| Missing equity archive dates | 0 | No |
| Archives outside equity or excluded sessions | 0 | No |
| Manifest rows | 4,958 | No |
| Dhanteras 2016-10-28, 2017-10-17, 2018-11-05, 2019-10-25 | `NORMAL_SPECIAL`, trading day, 09:15-15:30 | Closed by D58 |
| 2024-01-20 hours | Confirmed session. Hours inferred from NSE/CMTR/41180 because NSE/MSD/60340 prints no times | Disclosed. Not unresolved |

`eod_ready` can be true for this file set. `data_ready` stays false. An archive does not make a symbol eligible.

## Identity

| Symbol | Date | Old ISIN | New ISIN | Behaviour |
|---|---|---|---|---|
| BAJFINANCE | 2016-09-09 | INE296A01016 | INE296A01024 | `DATA_INSUFFICIENT` from that date. Not joined |
| GRASIM | 2016-10-07 | INE047A01013 | INE047A01021 | `DATA_INSUFFICIENT` from that date. Blocks every later full-index date |
| YESBANK | 2020-03-16 | INE528G01027 | INE528G01035 | `DATA_INSUFFICIENT` from that date. Not joined |

The saved corporate-action JSON files do not name the new ISIN on those sessions.
No new notice was found in the local evidence set. The required document is an official
NSE or depository record that names the new ISIN and the first session under it.

## Corporate actions

Coverage rows: 145. Latest empty HTTP 200 bodies: 47, including `SRTRANSFIN`.
`nse/data/corporate_actions/raw/ca_SRTRANSFIN_2016_2025.json` is 2 bytes, `[]`.
It is not a coverage row. The earlier log line `NOT_COLLECTED` was a TLS failure and is
not the latest result. The statement that `SRTRANSFIN` was never queried is withdrawn
in the owner register dated 2026-11-11.

Empty responses stay uncovered. G0 is `MANUAL` with `CORPORATE_ACTION_COVERAGE_UNKNOWN`
when no coverage file is supplied, and `CORPORATE_ACTION_COVERAGE_UNVERIFIED` when the
replay span has no verified window. Ten `UNPARSED_PRICE_EVENT` rows keep ratio 0,0.
No price was adjusted.

## Price continuity

EQ remains the research series. BE and BZ rows were not copied into it.
ADANIPOWER 2025-09-22 stays two ISINs. CROMPGREAV 2016-03-15 stays an unparsed scheme
with no ratio. The ADANIPOWER and CGPOWER multi-month "gaps" remain BE or BZ trading
paths, which an EQ-only reader reports as missing EQ sessions.

## What unknown does not become

A blank review decision is not acceptance. An empty API list is not "no corporate action."
A derived count of 101 is not forced to 100. A hash match is not owner approval.
`authorises_order` remains `False` in `nse/research/pipeline.py`.
