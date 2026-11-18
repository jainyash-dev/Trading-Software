# P0 corporate-action coverage

**Dated 2026-11-10. An empty API response is not evidence that no corporate action occurred.**

Investigation: Corporate-action coverage, agent id 9feeaae3-ddf2-4e2a-aad0-411e1e5dcce5 (read-only).
The 2026-11-10 recount was 191 symbol files, 46 whose body was `[]`, 145 non-empty,
2,064 action rows and 145 coverage rows. `SRTRANSFIN` was then collected with the
approved D56 script. The saved body is `[]` and was not added to coverage. Empty
responses are now 47. Coverage rows stay 145. No price was adjusted.

| File | SHA-256 |
|---|---|
| `coverage.csv` | `00bdb6604e0c090f9e06230fecfdfab3445e8088f796d0d61b2e35ef0ad12761` |
| `actions.csv` | `749757252b68f41199f1194278a5d33e6b608253efe5d03a3dd6a8a6be947fa6` |

Every logged query window is 2016-01-01 through 2025-12-31. Stored ex-dates run from
2016-01-21 through 2025-12-18. That span is the events the API returned, not proof that
every symbol was complete for the decade.

## 1. Classification

| Bucket | Count | Meaning |
|---|---|---|
| `COVERED_WITH_EVENTS` | 141 | Non-empty hash-verified response and at least one parsed action |
| Covered, no parsed price or dividend row | 4 | Non-empty list. Every subject is an annual general meeting |
| `EMPTY_RESPONSE` | 47 | Latest body is `[]`, HTTP 200, `rows=0`, `outcome=COLLECTED`. Includes `SRTRANSFIN` |
| `ERROR` | 0 | No hash mismatch. One earlier `NOT_COLLECTED` line for `SRTRANSFIN` is the failed TLS attempt, superseded by the saved `[]` |
| `NOT_COLLECTED` | 0 | `SRTRANSFIN` now has a saved response. That response is not coverage |
| `PARTIAL` | 0 | No symbol was queried for only part of 2016-2025 |

`JSWSTL` and `SOLAREX` are two of the 46. They were queried and are no longer in the
current member CSVs. The five dummy symbols are skipped before any request. They are not
failed requests.

Part 11 of `IMPLEMENTATION_BLOCKERS.md` said "44 of 189". That sentence was older than
these files. It now records 46 empty responses, 141 parsed-event symbols, 4 AGM-only
symbols, and the missed `SRTRANSFIN` request. Older sections of that file were left as
the record of earlier states.

## 2. Why `[]` is not coverage

The log has no field that means "no events". An empty list is `outcome=COLLECTED`,
`http_status=200`, `rows=0`, and a two-byte file `[]` (SHA-256
`4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`). All 46 share those
bytes. Ten were retried and the second file is the same `[]`: BAJAJHFL, ENRIN, ETERNAL,
ICICIPRULI, ITCHOTELS, LTIM, PAYTM, SWIGGY, TATAMOTORS, TMCV.

`write_coverage` drops a symbol when `rows` is 0. `covered()` is then false.
`qualification._g0` returns `CORPORATE_ACTION_COVERAGE_UNVERIFIED` when a coverage file
is loaded and the replay span has no verified window, and
`CORPORATE_ACTION_COVERAGE_UNKNOWN` when no coverage is supplied. Both are G0 `MANUAL`,
so `derive_status` cannot return `ACTIONABLE`.

The same empty body was returned for names whose events are stored under another ticker.
Examples from the investigation: `ICICIPRULI` is empty while `ICICILIFE` has dividends;
`LTIM` is empty while `LTM` has dividends; `TATAMOTORS` is empty while `TMPV` has
dividends and a demerger; `JSWSTL` is empty while `JSWSTEEL` has a 1:10 split;
`SOLAREX` is empty while `SOLARINDS` has a 1:5 split; `ZOMATO` and `ETERNAL` are both
empty. `in_history` keeps an action only when the action symbol equals the scanned
symbol. A dividend on the successor does not cover the predecessor, and the predecessor's
`[]` does not become "no action".

A verified window with no recorded price-scale action can pass the coverage check
(`ED-46`). That includes 69 dividend-only symbols and the 4 AGM-only symbols. Passing it
does not prove the API listed every split.

## 3. Event types in `actions.csv`

| Type | Rows | Symbols |
|---|---|---|
| DIVIDEND | 1,935 | 139 |
| BONUS | 69 | 42 |
| SPLIT | 28 | 27 |
| RIGHTS | 13 | 10 |
| DEMERGER | 9 | 9 |
| MERGER | 0 | 0 |
| CONSOLIDATION | 0 | 0 |
| ISIN change | 0 | 0 |
| UNPARSED_PRICE_EVENT | 10 | 8 |

Rights and demerger rows store ratio 0,0 and still count as price actions, so an ex-date
inside history makes G0 `MANUAL`. Dividends are not price-scale actions. `D50` keeps raw
OHLC canonical. No adjustment method is approved.

The 10 unparsed subjects, kept as price events with no usable ratio:

| Symbol | Ex-date | Subject |
|---|---|---|
| ADANIENT | 2018-04-05 and 2018-09-06 | Scheme of arrangement |
| BRITANNIA | 2019-08-22 and 2021-05-25 | Scheme of arrangement, bonus debenture 1:1 |
| CGPOWER | 2016-03-15 | Scheme of arrangement |
| GRASIM | 2017-07-19 | Scheme of arrangement |
| ICICIBANK | 2017-06-20 | Dividend plus bonus 1:10, whole subject unparsed |
| TATASTEEL | 2018-01-31 | Rights, fully paid and partly paid |
| TVSMOTOR | 2025-08-25 | Scheme of arrangement, bonus NCRPS 4:1 |
| VBL | 2024-09-12 | Face-value split Rs 5 to Rs 2. The ratio is not an integer, so it is not stored as `SPLIT` |

There is no local corporate-action circular archive. The only source is the saved NSE
API JSON. Renames in `instrument_records.csv` do not copy events onto the other ticker.

## 4. Exception symbols

### EMPTY_RESPONSE (47)

ADANIEXPO, ADANIGAS, ADANITRANS, BAJAJAUTO, BAJAJHFL, BFLSOFTWAR, BHARTI, CADILAHC,
CHOLADBS, CHOLAINV, CROMPGREAV, ENRIN, ETERNAL, GUJAMBCEM, HEROHONDA, HINDALC0,
HINDLEVER, I-FLEX, ICICIPRULI, INFOSYSTCH, INFRATEL, ITCHOTELS, JSWSTL, KWIL, LTI, LTIM,
MARICOIND, MCDOWELL-N, MICO, MOTHERSUMI, MPHASISBFL, MUNDRAPORT, PAYTM, SESAGOA, SOLAREX,
SSLT, SWIGGY, TATAGLOBAL, TATAMOTORS, TATATEA, TELCO, TMCV, TVS-SUZUKI, UNIPHOS, UTIBANK,
ZOMATO, and SRTRANSFIN (collected 2026-11-10).

Open universe rows among these: BAJAJHFL, ENRIN, ETERNAL, LTIM.

### AGM-only verified windows (4)

ADANIENSOL (9), ADANIGREEN (7), AWL (3), DMART (5). `ADANITRANS` is empty and renames to
`ADANIENSOL`, whose window is AGM-only. That is not a split check.

### SRTRANSFIN, collected 2026-11-10 and still not coverage

`D56` already authorised the existing collector. The first attempt at 13:35:37Z logged
`NOT_COLLECTED` because this Python install failed TLS certificate verification. A retry
with the certifi CA bundle at 13:36:36Z got HTTP 200. The body is `[]`, 2 bytes, SHA-256
`4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`, saved as
`raw/ca_SRTRANSFIN_2016_2025.json`. The collector did not add a coverage row. Coverage
stays 145 symbols. `SHRIRAMFIN` still holds the dividends, the 2020-07-09 rights and the
2025-01-10 split. Those rows do not cover the `SRTRANSFIN` ticker. The empty body is not
evidence that no corporate action occurred.

### Dividend-only covered symbols (69)

These windows can pass the coverage check. They are not proof that no split occurred:

ABBOTINDIA, ACC, ADANIPORTS, ALKEM, AMBUJACEM, APOLLOHOSP, ASIANPAINT, ATGL, AUROPHARMA,
AXISBANK, BAJAJ-AUTO, BAJAJHLDNG, BANDHANBNK, BANKBARODA, BOSCHLTD, CIPLA, COALINDIA,
COLPAL, DABUR, DIVISLAB, DLF, GLAND, HAVELLS, HDFC, HDFCLIFE, HEROMOTOCO, HINDALCO,
HINDZINC, HYUNDAI, ICICIGI, ICICILIFE, INDIGO, INDUSINDBK, INDUSTOWER, IRFC, JINDALSTEL,
JIOFIN, JSWENERGY, KOTAKBANK, LICI, LTM, LUPIN, MARICO, MARUTI, MAXHEALTH, MPHASIS, MRF,
MUTHOOTFIN, NHPC, OFSS, PAGEIND, PGHH, PIIND, PNB, SAIL, SBICARD, SBILIFE, SBIN,
SHREECEM, SUNPHARMA, TATAMTRDVR, TATAPOWER, TECHM, TITAN, UBL, ULTRACEMCO, UNIONBANK,
VEDL, ZYDUSLIFE.

## 5. Owner decisions and remaining blockers

| ID | State | Effect |
|---|---|---|
| D50 | `USER_APPROVED` | Raw OHLC stays canonical. No adjustment method is approved. Unverified ratios are not applied |
| D56 | `USER_APPROVED` | Collect official records. Missing or ambiguous evidence stays `DATA_INSUFFICIENT` or `MANUAL` |
| OD-CA-1 | `OWNER_DECISION_REQUIRED` only if a second source or an adjusted series is wanted | The missed `SRTRANSFIN` request is inside the existing D56 collection. A separate adjusted series still needs its own decision |
| R-10 / B7 | Open | API completeness is not established, including inside covered windows |

G0 already fails closed for the 46 empty symbols and for `SRTRANSFIN`. No silent
adjustment follows from this inventory.
