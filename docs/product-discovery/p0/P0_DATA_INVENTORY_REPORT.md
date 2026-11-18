# P0 Batch 0 - Data inventory report

**Programme:** GTF P0 Historical Data Certification  
**Batch:** 0 (read-only preflight)  
**Date:** 2026-11-15  
**HEAD verified:** `69858d07ccb016b74bc1d518b66b9948656ad6cf` (matches prior report)  
**Working tree:** dirty, ~197 paths; all preserved; no staging or commits  
**Builder code version:** `1.6.0` (`nse/research/p0_certification.py` `BUILD_VERSION`)  
**On-disk certification summary builder:** `1.5.0` (stale vs code; certified count still 0)  
**Decision-log SHA-256:** `ab748e1c2a406bf4304d9402a285747841a00b400f49028677bb6195e79c913d`

This report describes what is on disk. A filename that looks official is not treated as official without provenance.

---

## 1. Governance verification (read-only)

| ID | Status in log | Binding use for this programme |
|---|---|---|
| D62 | `USER_APPROVED` | Three CA evidence tiers; weaker tier never certifies |
| D63 | `USER_APPROVED` | Six P0 data gates; not GTF trade eligibility |
| D65 | `USER_APPROVED` | Exactly 17 named membership rows `ACCEPTED` |
| D66 | `USER_APPROVED` | Dual-source CA completeness + event reconciliation + dual-hash owner marker |
| ED-55 | `AUTO_APPROVED` | Fail-closed hardening through builder 1.5.0 path |
| ED-56 | `AUTO_APPROVED` | Implements D66; dual-source schema; builder 1.6.0 |

**Parser check:** `corporate_actions.completeness_decisions` requires marker `- **Completeness window accepted:**` with two distinct 64-hex source hashes, reconciliation hash, symbol and window; `USER_APPROVED` only. Legacy single-hash marker never qualifies. **Zero** such markers exist in `DECISION_LOG.md` today.

**Completeness register:** `nse/data/corporate_actions/completeness.csv` is **absent**. Proved windows: **0**.

No owner approval was inferred.

---

## 2. Historical price data (EOD)

### Files found

| Path | Role | Count / size | SHA-256 (where single file) | Usable for certification? |
|---|---|---|---|---|
| `nse/data/eod/raw/` | Held archives | 2478 `.zip` + 2 `.csv` | per-file in manifest | Custody only until gates pass |
| `nse/data/eod/manifest.csv` | Provenance ledger | 4958 rows | `3ca878761da3486b59c819dcbbf82a20b52906b4d9787e6af73fe22c88d0ff3e` | Yes as custody index |
| `nse/data/eod/acquisition_ledger.jsonl` | Acquisition outcomes | 1,813,310 bytes | hashed in programme notes | Custody trail |
| `nse/data/eod/download_log.jsonl` | Download log | present | - | Custody trail |
| `nse/data/eod/backfill_report.json` | Backfill summary | tiny | - | Engineering note |
| `nse/data/eod/quarantine/` | Quarantined files | 118 entries | - | Not usable until cleared |
| `nse/data/eod/inbox/` | Inbox / partial | 2419 entries | - | Not certified |
| `nse/data/eod/evidence/` | Samples / circulars | present | - | Supporting only |

### Formats and fields

| Format | Filenames | Count in `raw/` | EQ OHLC fields observed |
|---|---|---|---|
| Legacy CM bhavcopy | `cmDDMMMYYYYbhav.csv.zip` | 2108 | `SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,TIMESTAMP,TOTALTRADES,ISIN` |
| UDiFF CM | `BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip` | 370 | `TradDt,ISIN,TckrSymb,SctySrs,OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,TtlTradgVol,TtlNbOfTxsExctd,...` |
| Standalone CSV copy | 2 files | 2 | Same family as member CSVs |

Volume / traded quantity, previous close, and number of trades are present in both layouts under the column names above.

### Date and session coverage

| Metric | Value |
|---|---|
| Manifest `ARCHIVE` rows | 2478 |
| Unique `trade_date` | 2478 |
| Range | 2016-01-01 .. 2025-12-31 |
| Provenance (dominant) | `SCRIPT_DOWNLOADED_USER_APPROVED` / archive variants |
| Backfill: downloaded | 2416 |
| Backfill: quarantined | 2 (`FORMAT_UNKNOWN`) |
| Archives on non-sessions (from cert summary) | 7 dates listed in `P0_CERTIFICATION_SUMMARY.json` |

### Missing / quality notes

- Manifest has no separate `status` column; usability is via `provenance_status` and kind (`ARCHIVE` / `ARCHIVE_MEMBER` / `STANDALONE_COPY`).
- Quarantine holds 118 paths; do not treat as accepted EQ history.
- Prior certification summary: EOD gate `ACCEPTED` 123,395; `NON_EQ_ONLY` 260; `NO_EQ_ROW` 123 (member-dates inside D59 window). Those counts are from the last on-disk build (1.5.0), not re-run in Batch 0.
- **Unknown without a fresh build:** current 1.6.0 gate tallies on the full member-date grid (code changed; production outputs not rebuilt).

### Officiality

Files under `raw/` are held local copies with URL/page provenance in the manifest. They are **usable as custody evidence** for EOD integrity checks. They are **not** by themselves a corporate-action completeness proof (D66).

---

## 3. Corporate-action data

### Files found

| Path | Role | SHA-256 / count | Usable for D66 completeness? |
|---|---|---|---|
| `nse/data/corporate_actions/raw/` | Saved NSE API JSON bodies | 202 files (145 non-empty, 57 empty `[]`) | **No** - saved API responses are refused as completeness sources (ED-56 / R-3) |
| `nse/data/corporate_actions/coverage.csv` | Symbol window → file/hash | `00bdb6604e0c090f9e06230fecfdfab3445e8088f796d0d61b2e35ef0ad12761` (145 symbols) | Custody / exploratory tier only |
| `nse/data/corporate_actions/collection_log.jsonl` | Retrieval log | `c5dd2c53282fc9a965c29ab23efdea23f3a3d2ce6b9d2267ab27dac257b34dc4` (201 lines) | Provenance of API pulls |
| `nse/data/corporate_actions/actions.csv` | Parsed actions | `749757252b68f41199f1194278a5d33e6b608253efe5d03a3dd6a8a6be947fa6` (2064 rows) | Parsed events for screens; not completeness |
| `nse/data/corporate_actions/conversion_report.json` | Parse skip/unparsed | present | Defect register |
| `nse/data/corporate_actions/completeness.csv` | Dual-source register | **ABSENT** | Required for CA gate pass |
| Reconciliation records | D66 `gtf.ca_reconciliation.v1` | **ABSENT** | Required |

### Coverage

| Metric | Value |
|---|---|
| Symbols in coverage | 145 |
| Stated window | 2016-01-01 .. 2025-12-31 (per row notes: NSE corporate-actions API) |
| Empty bodies | 57 files (including retries; prior board: 47 symbols) |
| Parsed action types | DIVIDEND 1935, BONUS 69, SPLIT 28, RIGHTS 13, DEMERGER 9, UNPARSED_PRICE_EVENT 10 |
| Unparsed price subjects (conversion report) | 10 including CGPOWER 2016-03-15, VBL 2024-09-12 |

### Owner approval markers

- `- **Completeness window accepted:**` count in decision log: **0**
- Legacy `- **Completeness source accepted:**` count: **0**

### What remains unknown / missing for D66

1. Independent official **Source A** and **Source B** (non-API) per symbol-window.
2. Proven independence (distinct bytes and hashes; not the same file twice).
3. Event-by-event reconciliation records with `status=RECONCILED` and empty `unresolved`.
4. Explicit owner dual-hash approvals.
5. Whether any empty window can be proved (empty API `[]` is never proof).

---

## 4. Universe and identity

### Membership

| Path | SHA-256 / metric | Notes |
|---|---|---|
| `nse/data/universe/nifty100_baseline.csv` | `d82af7f7d45f209d77268a3e82dc1ed8a3d317db7077d5e39d712c390e926b9c` | Composition in force on baseline as-of |
| `nse/data/universe/nifty100_changes.csv` | `ddd4302e31a5ce7c1508c5a64b5a2b75cbab824b30a73c2e34bed3e483e0da65` | ADD/REMOVE/ISIN/rename events |
| `nse/data/universe/nifty100_count_exceptions.csv` | present | Count arithmetic (D60) |
| `nse/data/universe/nifty100_review.csv` | `9b0fcba06cc57761a4adbf0a938e004fb6adf808ba7724842248977391ec1f39` | 271 rows: **140 `ACCEPTED`, 131 blank** |
| `nse/data/universe/nifty100_universe.csv` | `15775fa1262b706edf7188b80cf740f5ec8144c94143da7fe0bb28e1d37c22c6` | 185 periods, 164 symbols; series EQ 181 / BE 4 |
| `docs/product-discovery/p0/P0_MEMBERSHIP_BACKLOG.csv` | `bbaaa727134fb8b5148d02f04efe54466ea577444be4b42fa8cab3f33a91d0e7` | Four-field backlog |

### Backlog group counts (verified against CSV)

| Classification | Groups | Rows |
|---|---|---|
| `EVIDENCE_SUFFICIENT_OWNER_DECISION_REQUIRED` | **24** | 91 |
| `EVIDENCE_INSUFFICIENT` | **14** | 15 |
| `NOT_APPLICABLE` | **25** | 25 |

Agents must not write new `ACCEPTED`/`REJECTED` ledger decisions.

### Identity evidence

| Path | Role |
|---|---|
| `nse/data/universe/instrument_records.csv` | 220 records (hash `f7ce39b0241366a62b979bf80292a5dc89e8c22f6482b8b428d1a5cd014eed1b`) |
| `nse/data/universe/identity_report.json` | 219 verified records; 27 ISIN changes evidenced; **3 unevidenced** (BAJFINANCE, GRASIM, YESBANK new ISIN recorded separately) |
| `nse/data/universe/evidence/identity/symbolchange.csv` | Symbol-change extract |
| `nse/data/universe/evidence/identity/EQUITY_L.csv` | Listed equity extract |
| `nse/data/universe/evidence/identity/isin_notices/*.pdf` | MSEI BAJFINANCE/GRASIM; NSE YESBANK |
| `nse/data/universe/evidence/baseline/*` | Index packages + `IndexInclExcl.xls` (name-only; not pre-2020 baseline) |
| `nse/data/universe/evidence/circulars/*` | Membership circulars |
| `nse/data/universe/evidence/releases/*` | Press releases |
| `nse/data/universe/evidence/sources.csv` | 38 provenance rows |

### Dummy / non-EQ notes (from prior board; not re-decided)

- Dummy seats (DUMMYREL, DUMMYITC, …): no inventable ISINs; OD-MEM-2/3 open.
- BE/BZ-only stretches: OD-PX-1 contained; EQ-only research rule stands.

---

## 5. Calendar

| Path | Metric | SHA-256 |
|---|---|---|
| `nse/data/calendar/events.csv` | 211 events, all `CONFIRMED` | `5ea4d0e6fd730af5b5c21d539ef373046d051fd1ec80b51de4d61716450f611c` |
| `nse/data/calendar/sources.csv` | 40 sources with circular SHA-256 | `cd0509d99ad93c8d823af1f89fc6664e4ea5a68b7c1d1f1f6e9a5d151d6664ef` |
| `nse/data/calendar/circulars/` | 40 circular files | per `sources.csv` |

Event mix: HOLIDAY 192, MUHURAT_SESSION 10, SPECIAL_SESSION 7, SHORTENED_SESSION 2. Date span of event rows: 2016-01-26 .. 2025-12-25.

OD-CAL-1 (2024-01-20 hours inferred) remains disclosed, not blocking certification by itself.

---

## 6. Certification artefacts (current on disk)

| Path | State | Notes |
|---|---|---|
| `docs/product-discovery/p0/P0_CERTIFICATION_SUMMARY.json` | Present; builder **1.5.0** | `certified_symbol_dates`: **0**; member-dates 123,778 |
| `docs/product-discovery/p0/P0_CERTIFIED_RESEARCH_UNIVERSE.csv` | Header-only / empty certified set | Not a successful certification |
| `docs/product-discovery/p0/P0_EXCLUSION_SUMMARY.csv` | Present | Exclusion tallies from last build |
| `docs/product-discovery/p0/P0_MEMBERSHIP_REFERENCE_HISTORY.csv` | Present (prior programme) | Reference history output |
| Completeness / reconciliation outputs | Absent | Block CA gate |

**Do not treat on-disk summary as proof that builder 1.6.0 was run on production paths.** P0-P4 completion report states no production rebuild after 1.6.0.

---

## 7. Programme file ownership (this programme)

Files this programme may create or update under `docs/product-discovery/p0/` (and later an isolated certification output directory):

1. `P0_DATA_INVENTORY_REPORT.md` (this file)
2. `P0_PIPELINE_VALIDATION_REPORT.md`
3. `P0_HISTORICAL_COVERAGE_MATRIX.csv`
4. `P0_MISSING_EVIDENCE_REGISTER.md`
5. `P0_CA_RECONCILIATION_REGISTER.csv`
6. `P0_CA_SOURCE_ACQUISITION_PROPOSAL.md`
7. `P0_MEMBERSHIP_OWNER_DECISION_PACK.md`
8. `P0_EXCEPTION_RESOLUTION_REGISTER.md`
9. `P0_SOURCE_TO_OUTPUT_AUDIT.md`
10. `P0_CERTIFICATION_FINAL_REPORT.md`
11. Isolated build directory (to be chosen; must not overwrite production paths)

All other dirty working-tree paths remain owner/other-workstream property.

---

## 8. Batch 0 acceptance

| Question | Answer |
|---|---|
| What data exists? | Full EOD custody 2016-2025 (2478 archives); CA API archives for 145 symbols; membership ledger + evidence; calendar with circular provenance; identity records |
| What does it cover? | Price sessions across the held archives; membership periods with 85/185 verified (prior); CA exploratory responses only |
| What is missing for certification? | Dual-source CA evidence + reconciliations + owner dual-hash approvals; remaining membership ledger decisions; several identity/price/TV blockers |
| Certified member-dates today? | **0** |

**Batch 0 status:** ACCEPTED - inventory complete; no production files modified.
