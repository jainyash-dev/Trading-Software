# Data architecture

> Product Prompt 00. How market data enters, how it is named, and how a second provider
> is allowed to exist without becoming the research price.
> Operational detail of the current files: [data source registry](../../nse/docs/DATA_SOURCE_REGISTRY.md)
> and [real-data readiness](../../nse/docs/REAL_DATA_READINESS.md).

## 1. Authority

| Topic | Rule |
|---|---|
| Research prices | Accepted official NSE CM bhavcopies, unadjusted (D50, ED-20) |
| Calendar | Local calendar tables built from hash-matched circulars |
| Identity | Instrument records with source hashes |
| Universe | Nifty 100 intervals, verified only after human review (D53) |
| Corporate actions | Separate event store. They explain prices. They do not rewrite them |
| Third-party series | A comparison dataset with its own id, until a named owner approval says otherwise |
| Derived cache | Rebuildable from raw bytes plus loader version. Never canonical |

`DATA_READY` is not claimed. EOD files for every 2016–2025 calendar trading day are
accepted (2,466, including the four Dhanteras dates confirmed by D58). Universe rows are not yet human-accepted:
readiness section 0B records 185 periods `UNVERIFIED` until a human fills
`nifty100_review.csv` (B11-R, D53). Research validation is none. No backtest result
exists, and none is claimed. A registry line that says bhavcopy gaps are none means no
missing trading day. It says nothing about the universe, identity or external validation.

Still open beside those two blockers: an independent corporate-action completeness check
(R-10), and three unevidenced ISIN changes that stay unjoined (BAJFINANCE 2016-09-09,
GRASIM 2016-10-07, YESBANK 2020-03-16). An empty corporate-action response is not
coverage. An `UNPARSED_PRICE_EVENT` inside history stays G0 `MANUAL`. Missing
completeness does not clear `CORPORATE_ACTIONS_UNVERIFIED`. D50 is the non-adjustment
rule. It is not a claim that G0 `PASS` means the corporate-action file was complete.
The UI shows that limitation even when G0 is `PASS`. Changing G0 for a missing file
would be an engine change, and Prompt 00 does not make it.

## 2. Provider adapter

Adapters live in `platform/providers/` or in the existing scripts outside `nse/`.
They do not import into the Zone Engine. `nse/` stays free of network imports.

Each adapter implements:

| Method | Duty |
|---|---|
| `identity` | Stable id, human name, operator |
| `describe` | Instruments, timeframes, historical coverage, update frequency, rights, auth, cost, rate limit |
| `fetch` | Write bytes into an inbox directory and return a receipt |

The receipt contains: provider id, request, local path, byte size, SHA-256, retrieval
timestamp supplied by the caller or the receipt (the research loader still does not read
a clock for scan output), format id, and error if any.

The adapter does not normalise prices into candles. Normalisation is the existing
bhavcopy loader or, for a future format, a new loader that refuses unknown headers the
way the current one refuses unknown UDiFF headers.

### Adapter record

Stored next to the inbox, not inside the price file:

- Provider identity and version of the adapter code.
- Supported instruments and timeframes actually requested.
- Historical coverage the provider claims, stored as a claim, plus the coverage the files actually have.
- Update frequency expected.
- Data rights: a short text the owner recorded when approving the provider. Official NSE public archives are `PUBLIC_OFFICIAL`.
- Authentication: none, or a secret reference. The secret value is not in the record.
- Retrieval time, format id, file hash.
- Validation outcome from ingest: accepted, quarantined, or refused.
- Rate limit and cost notes. Cost `0` is a fact only when the source is the public archive. An unknown cost is `UNAVAILABLE`, not zero.

### Initial adapters

| Adapter | Status |
|---|---|
| Official NSE CM bhavcopy, legacy and UDiFF | Implemented as local ingest. Download scripts already exist outside `nse/` for the approved backfills. A scheduled fetch of those same public URLs is platform work, still outside `nse/` |
| `LocalInboxProvider` | Implemented. Copies and hashes. No network |
| Any paid or third-party vendor | Not implemented. Requires a named approval (OQ-1 in the decisions note) |

No subscription is purchased for Prompt 00. No project file is uploaded to a vendor.

## 3. Canonical model

The canonical daily model is the existing `BhavRow` / `DailyInput` / `TimedCandle` path.

| Concept | Representation |
|---|---|
| Price | Decimal OHLC as parsed. `PRICE_ADJUSTMENT = NONE` |
| Session | Exchange date, candle stamped with the session bounds the calendar allows |
| Symbol on a date | Identity interval |
| Higher timeframe | Constructed by replay from daily bars |
| Quality | `Finding` with severity, code, date, and `known_at(as_of)` |
| Provenance | Manifest row: name, kind, trade date, size, SHA-256, source page, download date, provenance status |

A provider-specific column that the research model does not use stays in `BhavRow.extra`
or in the comparison dataset. It is not promoted into OHLC.

## 4. Source precedence and conflicts

1. For a research scan, the price for a session is the accepted official file selected by ED-20 (legacy through 2024-07-05, UDiFF from 2024-07-08).
2. A third-party file for the same symbol and session is stored under a different dataset id.
3. A comparison job may report equality or conflict. A conflict writes a finding `SOURCE_CONFLICT` on the comparison report. It does not edit the official candle and it does not flip a gate by itself.
4. A second official file for a session that is already accepted is quarantined. The accepted raw file is not overwritten. Non-EQ value errors are isolated and the EQ rows remain the research price (ED-30). Disagreement does not pick a winner.
5. Missing official data stays missing. The scanner's existing data-quality path applies. The overview shows `UNAVAILABLE` or the engine limitation, not a borrowed third-party close.
6. Unknown corporate-action coverage stays `CORPORATE_ACTIONS_UNVERIFIED`. A price-scale event inside history makes G0 `MANUAL`. An empty API response is not coverage. The platform does not mark a vendor-adjusted series as PASS.

## 5. Corporate actions and identity

- Raw OHLC is canonical.
- Events have their own store and coverage file.
- A backtest trade that stays open across a recorded price-scale event or a `PREVCLOSE` discontinuity is excluded from metrics by the existing backtest.
- Renames join only through verified ISIN continuity (ED-29).
- Membership matched only by symbol remains TD-16. The product displays the limitation. Prompt 1 or Prompt 2 closes the debt in the research code; the UI does not paper over it.

## 6. Dataset versioning

A dataset id changes when any accepted input hash changes. Scan manifests record the id.
The platform overview shows the id of the scan it is displaying, which may be older than
the newest dataset on disk. It does not quietly rebind an old scan to new files.

Suggested display fields: dataset id (short), loader version, file counts, earliest and
latest accepted session, limitations.

## 7. Storage layout

| Class | Location | Mutability |
|---|---|---|
| Official raw | `nse/data/eod/raw/` | Immutable after accept |
| Inbox | a local inbox directory | Incoming only |
| Quarantine | the acquisition ledger's quarantine outcome | Kept for inspection |
| Evidence | `nse/data/*/evidence` and source csv files | Added, not rewritten to change a hash |
| Comparison drops | platform application support, per provider id | Separate from raw |
| Parse cache | platform or local cache directory, key = archive SHA-256 + loader version | Disposable |

Git continues to ignore raw market data. Evidence policy stays as the data workstream
set it. Prompt 00 adds no bulk data.

## 8. Validation

Before a scheduled scan leaves `PENDING_DATA`:

1. The session is a confirmed trading session, or the job is skipped with the calendar reason.
2. The official file for that session is accepted in the manifest, or the job waits.
3. Identity and universe files are the ones named in the saved scan config.
4. Coverage for the scan window does not hide an unresolved calendar date inside a range the engine would block, without saying so. The scan may still run; the limitation is visible; a ten-year window that includes CAL-2 is not labelled `eod_ready`.

The existing `eod-coverage` and `readiness` commands remain the data-readiness reports.
The Data Centre screen shells them; it does not recompute acceptance.

## 9. Scheduling and the official fetch

The product decision is that scans run after the close and that official NSE data is a
source. The implementation split is:

- Fetch, if enabled in settings, runs in `platform/` and only for the public bhavcopy URLs the loader already knows (`official_url` records them and does not fetch).
- Rate limit: the approved backfill used one request per second. The scheduled fetch keeps that ceiling unless a later measurement says the public site needs a slower pace.
- Ingest uses the existing acquire path so hashes and quarantine stay identical.
- If fetch is disabled, the scheduler waits for files the owner dropped in the inbox. Both modes are valid. The default in a fresh install is wait-for-inbox, so a new checkout does not start downloading until the owner turns the fetch on. This keeps surprise network use off.

That default is an architecture recommendation (AR-6). It does not withdraw the approval
of the backfills already run.

## 10. Rights, privacy, cost

- Official public archives: no account, no fee in the adapter record.
- Paid vendors: blocked until OQ-1 names the vendor, the rights text, and the budget.
- Logs store paths and hashes, not file bodies.
- Nothing in the adapter uploads a local research file to the source. Requests are downloads of named public objects, or no network at all.
