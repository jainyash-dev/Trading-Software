# Historical data certification

Date: 2026-11-10. Counts were recomputed from the current files. The older written totals were checked, not copied.

**Raw unadjusted OHLC is canonical.** Nothing in this certification adjusts prices. Adjusted and unadjusted series were not mixed, because no adjusted series is the research input (D50).

`DATA_READY` is false. `eod_ready` is false.

## 1. Dataset inventory

Method: Python `csv` / `json` counts on 2026-11-10, plus the coverage report at `nse/output/data_readiness/eod_coverage_2016_2025.json`.

| Item | Recomputed | Report cross-check |
|---|---|---|
| Manifest rows | 4,958 | - |
| `ARCHIVE` rows | 2,478 | Coverage `held_files` 2,478 |
| `ARCHIVE_MEMBER` rows | 2,478 | One member per archive |
| `STANDALONE_COPY` rows | 2 | Identical copies of 2022-01-03 and 2023-12-29 |
| Unique archive trade dates | 2,478, from 2016-01-01 to 2025-12-31 | Coverage `distinct_trade_dates` 2,478 |
| Current `manifest.csv` SHA-256 | `3ca878761da3486b59c819dcbbf82a20b52906b4d9787e6af73fe22c88d0ff3e` | Same hash stored on the coverage report. The report is not stale relative to the manifest |
| Dataset id on that report | `64c68b3b7b92b9644d9c3210abf3453f1bdf5b35a105ec22dee2b9399bcdf0fa` | Loader 2.1.0 |
| Files in the coverage file list | 2,480 | 2,478 archives plus 2 standalone copies |
| `ACCEPTED_FOR_RESEARCH` | 2,474 | 2,462 role `TRADING_DAY` plus 12 role `EXCLUDED_SESSION_D33` |
| Not accepted | 6 | 4 Dhanteras archives (`VALIDATED` only) and 2 standalone copies |
| Schemas | - | `LEGACY_14` 2,108; `LEGACY_13_CRLF` 1; `LEGACY_13_CRLF_SHORTDATE` 1; `UDIFF_2024B` 370 |
| Missing trading days in the coverage calendar block | 0 | `calendar.missing.count` 0. `unverified_weekdays` 0 |
| Files on closed days | 0 | `files_on_non_trading_days` empty |
| EQ symbols seen in the coverage pass | 3,273 | 2,791 of them are absent on some held dates. Absence is not called a missing file without identity history |

Archive provenance on the manifest: 2,475 `SCRIPT_DOWNLOADED_USER_APPROVED`, 3 `USER_CONFIRMED`.

The acquisition ledger still contains two `QUARANTINED` / `FORMAT_UNKNOWN` events for `cm10JUL2017bhav.csv.zip` and `cm13JUL2020bhav.csv.zip`. The coverage file list now has both as `ACCEPTED_FOR_RESEARCH` (`LEGACY_13_CRLF` on 2017-07-10 and `LEGACY_13_CRLF_SHORTDATE` on 2020-07-13). The quarantine lines are the first ingest, not the current acceptance state. `backfill_report.json` still shows `QUARANTINED: 2`. That file is a ledger summary, not the acceptance count.

### Compared with the older written claims

| Older claim | This recount |
|---|---|
| 2,478 archives | Matches `ARCHIVE` count |
| Coverage 2016-2025 | Matches the date span |
| Four unresolved Dhanteras dates | Matches |
| Unreviewed universe | Matches: 0 decisions |
| 46 empty corporate-action responses | Matches the latest log row per symbol with `rows == 0` |
| Three unresolved ISIN cases | Matches `isin_changes_unevidenced` |
| No certified full-universe research result | Still true |

## 2. Symbol coverage

The EOD archives are full-market files, not a Nifty 100 extract. INFY and RELIANCE each have an EQ row on all 2,478 held archive dates in the coverage report's requested-symbol block. That is file presence, not a tradable research universe.

3,273 distinct EQ symbols appear somewhere. A symbol missing from a later file may be suspended, renamed, listed later, or delisted. This certification does not fill those gaps.

## 3. Trading-session coverage

From the coverage report's calendar block, which uses the current calendar and the current manifest hash:

| Year span | Trading days in window | Accepted trading-day files | Missing |
|---|---|---|---|
| 2016-2025 | 2,462 | 2,462 | 0 |

Excluded sessions held and accepted only in the excluded role: 12. Of those, 10 are `EXCLUDED_MUHURAT` and 2 are `EXCLUDED_SHORTENED`. They are not normal candles.

## 4. Missing-session report

No calendar trading day in 2016-2025 lacks an accepted archive. That statement is the coverage report, re-tied to the current manifest hash. It is not a second byte-by-byte reload of every zip in this session. The data-readiness tests are recorded in `PRIORITY_03_TEST_REPORT.md`.

Sessions that are held and must not be used as normal sessions:

- 12 excluded sessions, role `EXCLUDED_SESSION_D33`.
- 4 unresolved Dhanteras files, not accepted: `cm28OCT2016bhav.csv.zip`, `cm17OCT2017bhav.csv.zip`, `cm05NOV2018bhav.csv.zip`, `cm25OCT2019bhav.csv.zip`.

## 5. Corporate-action coverage

| Item | Count | Source |
|---|---|---|
| `actions.csv` rows | 2,064 | Direct count. SHA-256 `749757252b68f41199f1194278a5d33e6b608253efe5d03a3dd6a8a6be947fa6`, equal to `ca_completeness_2016_2025.json` |
| By type | DIVIDEND 1,935; BONUS 69; SPLIT 28; RIGHTS 13; DEMERGER 9; `UNPARSED_PRICE_EVENT` 10 | Direct count |
| Symbols with at least one action row | 141 | Direct count |
| `coverage.csv` symbols, all with `rows > 0` | 145 | Direct count. Zero-row coverage lines: 0 |
| Collection-log symbols | 189 | `collection_log.jsonl` |
| Latest response `rows == 0`, and not in `coverage.csv` | 46 | Listed below |
| Covered symbols absent from the log | 2: INFY, RELIANCE | They are in `coverage.csv` from the earlier INFY/RELIANCE collection (D50), not missing from coverage |

Empty latest responses, not coverage:

ADANIEXPO, ADANIGAS, ADANITRANS, BAJAJAUTO, BAJAJHFL, BFLSOFTWAR, BHARTI, CADILAHC, CHOLADBS, CHOLAINV, CROMPGREAV, ENRIN, ETERNAL, GUJAMBCEM, HEROHONDA, HINDALC0, HINDLEVER, I-FLEX, ICICIPRULI, INFOSYSTCH, INFRATEL, ITCHOTELS, JSWSTL, KWIL, LTI, LTIM, MARICOIND, MCDOWELL-N, MICO, MOTHERSUMI, MPHASISBFL, MUNDRAPORT, PAYTM, SESAGOA, SOLAREX, SSLT, SWIGGY, TATAGLOBAL, TATAMOTORS, TATATEA, TELCO, TMCV, TVS-SUZUKI, UNIPHOS, UTIBANK, ZOMATO.

Several of these are old symbols. An empty response under an old symbol is still not proof that the issuer had no action, and it is not transferred onto the new symbol by assumption.

Completeness audit against bhavcopy gaps (`ca_completeness_2016_2025.json`, actions hash matches):

| Check | Result | Limit |
|---|---|---|
| One-session gaps of at least 1.4x | 86 explained by a recorded price action | A bonus below 1.4x is outside this check |
| Gaps across a stretch with no EQ row | 2 unexplained: ADANIPOWER 2021-06-11 to 2021-09-20 (67 sessions, close 148.3 to open 96.05); CGPOWER 2021-09-15 to 2022-01-04 (75 sessions, close 89 to open 197) | Not one-session gaps. Not certified as corporate actions, and not ignored |
| Recorded split, bonus, and consolidation events | 94 of 94 marked `CONSISTENT` with the observed gap | The audit's own tolerance does not fail a ratio at or below 1.35 |
| PREVCLOSE breaks | 19 | The audit states NSE does not adjust PREVCLOSE for splits, so a split shows up as a price gap |

Prices were not adjusted to explain any of these.

## 6. Instrument identity

`nse/data/universe/identity_report.json`:

| Item | Count |
|---|---|
| Records | 219, all marked verified in that report |
| LISTING | 156 |
| SYMBOL_CHANGE | 36 |
| ISIN_CHANGE evidenced | 27 |
| DELISTING / MERGER records | 0 |

Unevidenced ISIN changes, not joined:

| Symbol | Last old session | First new session | Old ISIN | New ISIN |
|---|---|---|---|---|
| BAJFINANCE | 2016-09-08 | 2016-09-09 | INE296A01016 | INE296A01024 |
| GRASIM | 2016-10-06 | 2016-10-07 | INE047A01013 | INE047A01021 |
| YESBANK | 2020-03-13 | 2020-03-16 | INE528G01027 | INE528G01035 |

These three stay unresolved. A later evidenced change for the same symbol (for example BAJFINANCE's 2025 bonus) does not close the earlier break.

## 7. Universe membership

| Item | Result |
|---|---|
| `nifty100_universe.csv` rows | 185 membership intervals |
| Earliest `effective_from` | 2020-12-31 |
| Latest `effective_from` | 2025-12-05 |
| Rows with a non-empty `source_sha256` | 0. Hashes are described as withheld until human review |
| `nifty100_review.csv` | 271 rows. Decision, reviewer, and reviewed-on are blank on every row |
| `nifty100_review_packet.csv` | 267 `VERIFIED`, 4 `INFERENCE`. These are agent verdicts. They are not decisions |
| Human-accepted periods | 0 |
| Membership before 2020-12-31 | Not in this file (B11-P) |

`universe.load` treats an empty hash as unverified (`models.source_verified`). `Universe.limitations` returns `UNIVERSE_UNVERIFIED` when any in-force row is unverified. A backtest of this file also receives `SURVIVORSHIP_UNCONTROLLED` (`backtest._limitations`).

**The Nifty 100 historical universe is not certified.**

`docs/product-discovery/phase-01/T001_NIFTY100_OWNER_REVIEW.md`, written while this audit was open, reports the same 0 of 271 decisions and 185 unverified periods. It also reports a scratch simulation, which this mission did not re-run: marking every review row accepted would still leave 8 periods unverified (BAJFINANCE, GRASIM, YESBANK, and five dummy spin-off seats). That does not change the current certification. It means a completed human review would still not make those eight periods verified.

## 8. Eligible research window

| Slice | Class | May it support a strategy result? |
|---|---|---|
| Raw EOD archives, 2,462 trading days, 2016-01-01 to 2025-12-31, unadjusted | Fully evidenced as files | No. Files are not a strategy test |
| 12 excluded sessions | Evidenced, excluded from normal candles | No |
| Four Dhanteras dates | Unverified session class. Files held, not accepted | No. ED-44 also drops history through 2019-10-25 on any later scan that uses this calendar |
| 2016-01-01 through 2019-10-25 as zone or trend history | Excluded from scanner history while CAL-2 is unresolved | No |
| Nifty 100 membership, all dates | Unverified | No index study |
| Symbols among the 46 empty corporate-action responses | Unverified for actions | G0 MANUAL if a scan includes them without a covering window |
| BAJFINANCE, GRASIM, YESBANK across the unevidenced ISIN dates | Excluded from a joined history | Identity fails closed |
| INFY and RELIANCE daily bars as republished prices | Partially evidenced (Yahoo screenshots for INFY Q1 2022 only; both names are in the corporate-action coverage file) | Still not a strategy test: no zone reference, no reviewed universe, no dated costs |
| Any window advertised as certified 2016-2025 research | Not claimed | No |

There is no date range on which this mission will certify a Nifty 100 backtest. The least incomplete later window, if the owner finishes T-001 and supplies costs, still cannot start its zone history before the session after 2019-10-25, has no membership file before 2020-12-31, and needs warm-up (55 weekly bars for the trend gate; three completed higher-timeframe periods for conflict and curve). That is a restriction, not a certification.

## Independent recount after the first draft

A separate read-only pass hashed the raw files and re-ran the calendar reconcile. It agrees with the table above.

| Check | Result |
|---|---|
| All 2,480 files in `nse/data/eod/raw` | Size and SHA-256 match `manifest.csv`. All 2,478 zip members match the `ARCHIVE_MEMBER` rows |
| Calendar reconcile, 2016-01-01 through 2025-12-31, against the 2,478 archive dates | 0 missing trading days, 0 archives on a weekend or holiday. Trading-day files: 245, 246, 244, 243, 251, 247, 247, 245, 246, 248 by year from 2016 through 2025 (2,462) |
| Empty corporate-action files on disk | 56 JSON files are `[]`. 46 symbols have an empty latest response. The other 10 are `.retry1.json` copies, still empty, for BAJAJHFL, ENRIN, ETERNAL, ICICIPRULI, ITCHOTELS, LTIM, PAYTM, SWIGGY, TATAMOTORS, and TMCV |
| Empty-coverage names still on `nifty100_universe.csv` | 16 of the 46. Four of those rows have no end date: BAJAJHFL, ENRIN, ETERNAL, LTIM |
| INFY and RELIANCE | In `coverage.csv` (24 and 14 rows) and absent from `collection_log.jsonl`, as the first draft said |
| Per-symbol missing EQ rows inside an otherwise present archive | Not recomputed by either pass |

OHLC inside the zips was not re-parsed. The 210 isolated non-EQ rows remain the stored loader figure, tied to the same manifest hash.

## Evidence quality

| Layer | Quality |
|---|---|
| Official EOD bytes versus the manifest | Strong for file integrity. The coverage report hash matches |
| Calendar transcription | Strong for confirmed rows, blocked on four dates |
| Corporate-action API extracts | Partial. Empty responses and the two multi-month gaps stay open |
| Identity | Strong where a record is sourced, blocked on three ISIN breaks and on missing delisting/merger rows (counts are 0) |
| Universe | Not certified |
| External chart check | Absent |
