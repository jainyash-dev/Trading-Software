# T-014: Instrument identity search: audit

**Dated 2026-11-10.**

## 1. Summary

| Question | Answer |
|---|---|
| Does search use only a names CSV? | **No.** `search_instruments` in `platform/gtf_platform/integration/reference.py` merges NSE's `EQUITY_L.csv` (names) with the identity master `nse/data/universe/instrument_records.csv` (219 records: 156 LISTING, 36 SYMBOL_CHANGE, 27 ISIN_CHANGE) |
| Was it correct? | **No: two defects, both fixed in Phase 01** (section 4) |
| Does the scanner receive the right identity? | **Yes, by design.** The platform passes a *symbol*. `nse` resolves the point-in-time identity from `instrument_records.csv` (`inputs.load(..., instrument_records=...)`) and fails closed when it cannot |
| Are BAJFINANCE 2016-09-09, GRASIM 2016-10-07 and YESBANK 2020-03-16 joined? | **No.** Verified on the real records (section 5) |
| Can T-014 be marked complete? | **No: PARTIALLY_IMPLEMENTED** (section 7) |

## 2. Data flow (inspected)

```
UI InstrumentFinder / InstrumentSearch ("Symbol, name, or ISIN")
  -> GET /api/v1/instruments?query=   (routes.instruments)
  -> reference.search_instruments: EQUITY_L.csv rows + instrument_records.csv rows,
     substring match on symbol / name / ISIN, max 50, each marked verified or UNVERIFIED
  -> user picks a row; the UI uses row.symbol
  -> scan request (symbols) -> research.prepare -> pipeline.run
  -> inputs.load(instrument_records=...) -> instruments.resolve(symbol, date)  [nse: identity authority]
```

The platform never decides identity or eligibility. `IDENTITY_JOINS_ARE_NOT_PERFORMED_HERE`
is in its limitation list.

## 3. Behaviour matrix (real repository data, after the fix)

Captured with `config.load_settings()` defaults: `EQUITY_L.csv` from
`nse/data/universe/evidence/identity/`, and `instrument_records.csv`.

| # | Behaviour | Query | Result | Verdict |
|---|---|---|---|---|
| 1 | Current symbol | `INFY` | INFY, INE009A01021 | OK |
| 2 | Company name | `Infosys` | INFY; INFOSYSTCH (historical symbol, same ISIN); HCL-INSYS (name contains "Infosys") | OK: substring; ambiguity shown, not merged |
| 3 | Aliases | `HDFC Bank` / `Zomato` | HDFCBANK / ZOMATO (old symbol record) | Partial: no alias table exists, and none was invented. "Zomato" matches only because the old symbol contains it |
| 4 | Ambiguous names | `Tata` | 18 separate securities | OK: listed, never merged |
| 5 | Historical symbols | `ADANITRANS`, `HDFC`, `INFOSYSTCH` | Found under their own symbol | Partial: **not marked as historical** (limitation L1) |
| 6 | ISIN-linked records | `INE296A01016` / `…01024` / `…01032` | BAJFINANCE once per ISIN | OK after the fix (before: current ISINs not found) |
| 7 | Identity changes preserved | `BAJFINANCE`, `YESBANK`, `GRASIM` | 3, 3 and 2 rows: one per ISIN | OK after the fix (before: one row, ISIN missing or stale) |
| 8 | No silent merge | as 6 and 7 | Each (symbol, ISIN) is a separate row | OK |
| 9 | Unverified identities marked | any | `verified: false`, `verification: "UNVERIFIED"` on every row (no universe period is certified, T-001) | OK. Since the fix, verification is per (symbol, ISIN), not per symbol |
| 10 | Scanner gets the canonical identity | scan of `BAJFINANCE` on 2020-01-01 | `nse` resolves `UNKNOWN_INSTRUMENT` (two ISINs), so DATA_INSUFFICIENT | OK (fail-closed). Limitation L2: a chosen ISIN row is not carried into the scan |
|: | Dummy spin-off seats | `DUMMYREL` | No result | Expected: no identity record for a symbol that never trades |

## 4. Defects found and the changes made

**D-1. ISINs from `EQUITY_L.csv` were never read.**
- NSE's header has a space after each comma (`" ISIN NUMBER"`, confirmed byte by byte).
  `_names()` looked up `"ISIN NUMBER"`, so every names row had `isin: null`.
- Result: an ISIN search could not find a current listing. `INE009A01021` returned only
  the historical symbol INFOSYSTCH, and `INE296A01032` (BAJFINANCE today) returned nothing.
- **Fix:** strip whitespace from header keys before the lookup.

**D-2. One identity row per symbol, and verification per symbol.**
- `_identity_rows()` kept the first record per symbol, and `search_instruments` dropped
  every later row with the same symbol. A symbol that traded under several ISINs showed
  one stale ISIN, and its other ISINs were unsearchable.
- `verified` was keyed by symbol. Once a universe period is certified, *every* ISIN of
  that symbol would have shown as verified.
- **Fix:** keep one row per (symbol, ISIN) in both places, and mark `verified` only when
  a verified universe period has that symbol **and** that ISIN. A row without an ISIN is
  never verified (unknown is never PASS).

**Files changed:**
- `platform/gtf_platform/integration/reference.py`: `search_instruments`, `_identity_rows`,
  `_names`; `_verified_symbols` renamed `_verified_identities`. No other caller exists.
- `platform/tests/test_instrument_search.py` (new, 8 tests, synthetic fixtures).

**Unchanged:**
- the response fields;
- `nse/` (identity semantics, qualification);
- every data file.

## 5. The three unresolved ISIN changes (real records, `nse.research.instruments.resolve`)

| Symbol | Day before | From the change date | Later |
|---|---|---|---|
| BAJFINANCE | 2016-09-08: RESOLVED INE296A01016 | 2016-09-09: **UNKNOWN_INSTRUMENT** (INE296A01016 and INE296A01024 both listed) | 2025-06-16: RESOLVED INE296A01032 (evidenced split) |
| GRASIM | 2016-10-06: RESOLVED INE047A01013 | 2016-10-07: **UNKNOWN_INSTRUMENT** | Still UNKNOWN on 2024-01-01: every GRASIM scan after 2016-10-07 is DATA_INSUFFICIENT |
| YESBANK | 2020-03-13: RESOLVED INE528G01027 | 2020-03-16: **UNKNOWN_INSTRUMENT** | Still UNKNOWN on 2024-01-01 |

No join is made, and nothing is approved. Evidence needed to clear each (owner-sourced or
from official NSE records):
- BAJFINANCE and GRASIM: the split records print record dates that fall on the Saturday
  after the ISIN changed, so matching them would be an inference. Needed: an official
  document that dates the new ISIN, such as an NSE circular naming the ex-date and ISIN.
- YESBANK: no official price event is held for 2020-03-16 (the reconstruction scheme).
  Needed: an official NSE or depository notice of the ISIN change and its price scale.

## 6. Tests

| Command | Before | After |
|---|---|---|
| `PYTHONPATH=platform python3 -m pytest -q -p no:cacheprovider platform/tests` | 24 passed | Mid-session: 32 passed, 1 failed (`test_openapi_uses_the_cookie_and_omits_unimplemented_writes`). **Final: 37 passed, 0 failed** (13 security, 12 API, 8 search, 4 product-flow) |
| `PYTHONPATH=platform python3 -m pytest -q -p no:cacheprovider platform/tests/test_instrument_search.py` |: | 8 passed |
| `python3 -m nse.validation.run_all --group risk_instruments` | see `PHASE_01_TEST_REPORT.md` | |

**The mid-session failure was not caused by this change, and it has since cleared.**
- The test compares the checked-in `openapi.json` with the live schema. The difference was
  a new `include_fixtures` query parameter on the scan routes.
- Another writer modified `routes.py` (12:00:51) and `schedule.py` (12:00:27) during this
  session. `reference.py` defines no route.
- The same writer then regenerated `openapi.json` (12:03:25) and added
  `platform/tests/test_product_flow.py`.
- Two peer Claude sessions are registered on this repository.
- Phase 01 changed neither the test nor the snapshot.

## 7. Limitations and recommendation

| ID | Limitation | Risk | Proposed next step (owner or Phase 02) |
|---|---|---|---|
| L1 | Historical symbols (ADANITRANS, HDFC, ZOMATO) look like current listings in results | A user may pick a dead symbol. The scan then fails closed (`UNKNOWN_INSTRUMENT` after the rename), so this misleads without being unsafe | Return `record_type`, `effective_from` and a `current_symbol` hint; show them in the UI |
| L2 | Picking a row passes only its symbol, never its ISIN | A user who picks "BAJFINANCE INE296A01016" may believe that ISIN is what gets scanned. `nse` resolves the identity at as_of instead | Show "identity resolved at scan date" in the UI, or pass and check the ISIN |
| L3 | No alias data | Name search is substring-only | Only from an official source; never invented |
| L4 | Identity records have no company names | Historical names are not searchable | Add names only from official files |
| L5 | Frontend not exercised in a browser in Phase 01 | UI rendering of several rows per symbol is unverified (the UI keys rows by symbol-ISIN, so React keys stay unique) | Run the web tests or a browser check in Phase 02 |
| L6 | Installed FastAPI 0.116.1, pinned 0.121.0 | Test environment drift | Align the environment |

**Recommendation: PARTIALLY_IMPLEMENTED.**
- The search defects are fixed and covered by tests.
- The identity safety (no joins, fail-closed resolution) is verified on real records.
- L1, L2 and L5 remain.
- The platform suite passes (37/37).
