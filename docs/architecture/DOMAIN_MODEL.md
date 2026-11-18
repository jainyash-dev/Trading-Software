# Domain model

> Product Prompt 00. Entities the desktop product stores or displays. Where an entity
> already exists, the existing module is the authority and this page does not redefine it.
> Trading status strings are the constants in `nse/research/models.py`.

## 1. Conventions

- Times that the engine already stores are exchange-local. IST month boundaries use `models.ist_month` (fixed +05:30, ED-8).
- Primary keys are opaque strings unless a natural key is stated.
- Research decisions are immutable after the run is final. A correction is a new run (D44).
- Application edits (drawings, settings) are versioned and audited.
- `UNAVAILABLE` means the product has no source. `NOT_SUPPLIED` means a check was skipped because an input was absent. Neither is a number and neither is `PASS`.
- Derived tables may be rebuilt from raw files plus manifests. They are not a second price history.

## 2. Identity and market data

### Instrument

Already produced by `nse/research/instruments.py`.

| Field | Meaning |
|---|---|
| `canonical_id` | `ISIN:` plus the earliest ISIN of the lineage, when the records resolve |
| `symbol` | Trading symbol on a date |
| `name` | Company name when the identity file has it |

An unresolved symbol is still shown. Its scans carry the existing identity findings.

### ISIN identity interval

| Field | Meaning |
|---|---|
| Natural key | symbol, event type, `effective_from`, source hash |
| Types | `LISTING`, `SYMBOL_CHANGE`, `ISIN_CHANGE`, `DELISTING`, `MERGER` |
| Validity | `effective_from` inclusive. `effective_to` only on `LISTING`, as the current loader implements |
| Provenance | `source` and 64-character `source_sha256`, or the row is `UNVERIFIED` |

Point-in-time: a scan at date T uses the interval covering T. A future segment is ignored.
An ISIN change without evidence is `DATA_INSUFFICIENT` across the break. The three
unevidenced changes named in the readiness note stay unjoined.

### Universe membership interval

| Field | Meaning |
|---|---|
| Natural key | index id (`NIFTY100` for the initial universe), symbol, `effective_from` |
| Validity | `effective_from <= as_of` and (`effective_to` empty or `as_of <= effective_to`) |
| Verified | Existing rule: source hash plus a human `ACCEPTED` review row whose hash matches (D53) |

Overlapping intervals for one symbol are refused. Unverified in-force rows make the scan
`UNIVERSE_UNVERIFIED`. The converter rolls forward from one baseline (TD-15). Dates before
that baseline are outside the verified window.

### Trading session

| Field | Meaning |
|---|---|
| Primary key | session date |
| Classification | `WEEKEND`, `HOLIDAY`, `NORMAL`, `NORMAL_SPECIAL`, `EXCLUDED_MUHURAT`, `EXCLUDED_SHORTENED` |
| Status | `CONFIRMED` or `UNRESOLVED` |

An `UNRESOLVED` date is a property of the calendar, not a silent holiday. Ranges that
contain one are blocked (ED-31, D54). No date is unresolved today: the four 2016-2019
Dhanteras dates were, until the owner confirmed them as regular equity sessions (D58).

### Dataset

| Field | Meaning |
|---|---|
| Primary key | dataset id already computed for a coverage or research run (SHA-256) |
| Contents | manifest hash, loader version, calendar hash, identity file hash, universe file hash, corporate-action file hash |
| Versioning | A new accepted file produces a new dataset id. Old ids remain |

### Market candle

| Field | Meaning |
|---|---|
| Natural key | dataset id, symbol, timeframe, session date |
| Fields | open, high, low, close, volume when the file has it, provenance |
| Authority | Daily bars from accepted bhavcopies. Weekly and higher bars are constructed by the existing replay. They are not stored as a second source |

The engine zone id is `side-startIndex-createdIndex` (`zone_engine._zone_id`). On the
synthetic DBR series used by `tests/test_zone_engine.py`, that id stays `demand-2-3`
when a later candle is appended and when `as_of` drops the tail. Prepending one candle
changes it to `demand-3-4` while `start_time`, `created_time`, proximal, and distal stay
the same. A deeper leg-in low keeps the id `demand-2-3` and changes distal. The id
therefore survives an ordinary new session, misses a prepend, and does not by itself
detect a new distal. The research journal and the backtest still join on this id.
Prompt 00.1 does not change that join.

The desktop stable zone reference is not the engine id and does not include the dataset
id, the first candle of the series, or the bar count. Coverage `dataset_id` is the
SHA-256 of the accepted date and file-hash pairs in the window (`eod_coverage`). Adding
one session, or changing one file hash, changes that id. Putting it, or the bar count,
into the zone reference would mark every existing plan unresolved after an ordinary
new session or an unrelated accepted file.

Stable reference, taken from the persisted scan zone record:

- symbol
- timeframe
- side
- `start_time` (close time of the base-start candle)
- `created_time` (close time of the creation candle)

Those two times are the creation evidence. They are the scan fields
`start_time` and `created_time`, which `qualification._zone_record` stores from the
candle `end`. They are not bar indexes.

Defining properties, compared only after the stable reference matches:

- pattern
- proximal
- distal
- normal_distal
- zero_base

| Later observation | Result |
|---|---|
| Same reference and same defining properties. Engine id or dataset id may differ | Same zone. The plan stays linked. The new engine id and dataset id are stored as a new observation |
| Same reference, any defining property differs | `ZONE_IDENTITY_UNRESOLVED`. The plan is not attached to that zone and a second order is not offered |
| Reference absent from the new scan | `ZONE_NOT_IN_SERIES`. The plan is not attached to a different `created_time` |
| Two zones in one scan share the reference | `ZONE_IDENTITY_AMBIGUOUS`. No automatic attachment |

Dataset id, manifest id, engine zone id, bar count, and the series start are provenance
of an observation. They are stored on the link. They are not the identity. Lifecycle
fields (`test_count`, overlay status, leg-out count) are not defining properties.
Proximal and distal are set only in `create` and `create_zero_base`. A later bar does
not rewrite them. A prepend that builds a different base changes the times or the
prices, and the table above leaves the old plan unattached.

Prompt 07 implements this comparison in the platform store. It does not change
`zone_engine._zone_id`. Prompt 02 may replace the engine id only if that workstream
takes the file. Until then, a live plan still records the engine id that the journal
will use, and the platform refuses to call `journal_add` when the stable reference is
unresolved, missing, or ambiguous.

### Corporate-action event

Stored by `nse/research/corporate_actions.py`. Types include `SPLIT`, `BONUS`, `RIGHTS`,
`CONSOLIDATION`, `DEMERGER`, `MERGER`, `DIVIDEND`, and `UNPARSED_PRICE_EVENT`.
`DIVIDEND` is recorded and is not a price-scale event. Prices are not adjusted. An
unparsed price event inside history keeps G0 `MANUAL`.

## 3. Research

### Zone and zone lifecycle event

The engine and the overlay own lifecycle. The product stores snapshots, not a second
state machine.

| Snapshot field | Meaning |
|---|---|
| Engine id and natural key | As above |
| Overlay status | `FRESH`, `TESTED`, `INVALIDATED`, `UNKNOWN` |
| Provenance | manifest id, `as_of`, timeframe |

A later snapshot does not edit an earlier one.

### MTF snapshot

The in-memory `MtfSnapshot` for one symbol at one `as_of`. The product persists the
decision bundle (`decision_replay.bundle`) and the scan JSON. Eligible zones are those
returned by `eligible_after_overlay(timeframe)`. Manual-review zones come from
`manual_review_after_overlay(timeframe)` and stay ineligible.

### Gate evaluation

`GateResult`: gate id `G0`–`G8`, outcome
`PASS | FAIL | MANUAL | DATA_INSUFFICIENT | BLOCKED | NOT_EVALUATED`, reasons,
manual-review notes, evidence, sources.

`derive_status` is the only status function. Order of restrictiveness:
`BLOCKED`, `REJECTED`, `DATA_INSUFFICIENT`, `MANUAL_REVIEW`,
`ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING`.

### Research scan

| Field | Meaning |
|---|---|
| `scan_key` / `run_id` | Existing store key and manifest run id |
| `as_of`, `trade_type`, universe label, calendar label | From the scan |
| `pipeline_version`, engine versions | Methodology |
| `dataset_id` | Input identity |
| Completeness | Platform field: `COMPLETE`, `PARTIAL`, `FAILED`, plus `INTERRUPTED` while running |
| Body | `research.json` envelope, schema `research-pipeline/1` |

`authorises_order` on the envelope is false. `ranking` text says the row order is not a
quality ranking.

### Candidate

A row inside a scan. Identity: `scan_key` plus symbol plus engine zone id plus trade type.
Displayed fields include status, nine gates, levels, limitations, and manual checks.
The eleven checklist items in `models.CHECKLIST` stay manual even on the best status.

## 4. Trading records

These three are different facts.

```
 Trade plan   what the research suggested and what the owner approved
 Order record what the owner says they submitted in Kite
 Fill         the execution the owner says happened
```

### Trade plan

Built from `pipeline._trade_plan` plus owner selections.

| Field | Meaning |
|---|---|
| `plan_id` | New platform id |
| `plan_version` | Increments when the owner edits a selection. Old versions remain |
| Source | `scan_key`, symbol, zone natural key, engine zone id |
| Copied | candidate status, gates, level ranges, manual checks, portfolio checks |
| Owner selections | chosen entry, chosen stop structure (`NORMAL` or `EXCEPTIONAL`), chosen target if several were printed, risk stage, risk percent, quantity |
| Empty until chosen | `selected_entry`, `selected_stop`, `selected_quantity` |
| Approval | approver, time, version approved. Absent until the owner approves |
| `authorises_order` | false |

Lifecycle:

`DRAFT` → `AWAITING_OWNER` → `APPROVED` → `ORDER_RECORDED` → `FILLED` → `CLOSED`

Side paths: `CANCELLED` (no submission: the zone allowance can be released, ED-3),
`EXPIRED`, `SUPERSEDED` (a newer version exists).

`APPROVED` means the owner accepts this plan as the one they might type into Kite. It
does not mean the candidate became actionable and it does not mean an order exists.

A plan whose copied status is `BLOCKED`, `REJECTED`, or `DATA_INSUFFICIENT` cannot move
to `ORDER_RECORDED`.

### Entry proposal, stop structure, target

These are fields of the plan, not separate authorities.

- Entry proposal: a price inside the printed entry range, or empty.
- Stop structure: `NORMAL` or `EXCEPTIONAL`, each a price inside the printed range. HTF stop remains empty unless the engine provided one.
- Target: proximal, zone id, freshness, timeframe, and the provenance string from the plan. No target is invented when G7 has none.

### Risk assessment

The `risk.py` plan status, copied onto the plan version:
`INVALID_LEVELS`, `NOT_APPLICABLE_STATUS`, `RISK_RULE_FAILED`, `MANUAL_REVIEW`,
`WITHIN_RISK_RULES_MANUAL_CHECKS_PENDING`.
Stage bands stay those already implemented (P-RISK-1). Above the stage maximum fails.
Below the minimum, or no stage, is manual. Above 2% with no stage fails.

### Order record

Extends the existing `journal_orders` fact.

| Field | Meaning |
|---|---|
| `entry_id` | Journal entry |
| `submitted_at` | Owner-supplied IST time |
| `order_ref` | The reference the owner copies from Kite. Optional but searchable |
| `broker` | Constant `KITE_MANUAL` for the initial product |
| `note` | Free text |

One submission per entry. Nothing is sent. A submitted order holds the zone through
cancellation, expiry, stop, and close (ED-3). A legacy entry with unknown submission
history keeps the zone used.

### Fill

New. Append-only. Not in `store.py` today; Prompt 7 adds it in the platform database
with `entry_id` as a logical reference.

| Field | Meaning |
|---|---|
| `fill_id` | Primary key |
| `entry_id` | Plan / journal entry |
| `filled_at` | IST timestamp the owner records |
| `price`, `quantity` | Actuals |
| `kind` | `ENTRY` or `EXIT` |
| `source` | `OWNER_ENTERED` |

A platform fill does not consume a cap by existing. The research journal does, and only
through the events below. D42 counts the first fill or trigger in the IST month. The
implementation of that sentence is one `TRIGGERED` event (`store.journal_event`,
`journal_summary`). There is no partial-fill event and no second `TRIGGERED` on an entry.
A repeated `TRIGGERED` raises `JournalRefused` and leaves the original row in place.

| Event | Monthly allowance | Open-position slot | One-order-per-zone allowance |
|---|---|---|---|
| Plan only (`PLANNED`, no submission) | No | No | Holds it while the plan is pending. `CANCELLED` with no submission releases it (ED-3) |
| Order submitted, not filled | No | No | Holds it. Cancel, expiry, stop, and close do not release it |
| `EXPIRED` with no submission row | No | No | Holds it. Expiry is treated as a live order |
| `TRIGGERED` committed | Yes. IST month of that event's `at`. One per entry | Yes, from that `at` until an exit event strictly before the later check. An exit at the same timestamp still counts as open | Already held if a submission exists. Also held because the order triggered |
| Later `ENTRY` share rows on the same entry | No. They must not call `journal_event` | No extra slot. Quantity for valuation is the sum of `LINKED` entry fills | Unchanged |
| Exit (`STOP_LOSS_HIT`, `TARGET_HIT`, `CLOSED_MANUAL`) | No release | Releases the slot for a later timestamp | No release |
| `ZONE_INVALIDATED` | No | Does not by itself close the position. The store test keeps the state `OPEN` until an exit | No release |
| Platform `REFUSED` fill | No | No | Unchanged |
| `JOURNAL_EVENT_PENDING` | No. It is not a trade | No | Unchanged |
| `TRIGGERED` with no platform fill | Yes. The journal already counted it | Yes, by the same rule | Unchanged. The portfolio shows `FILL_NOT_RECORDED` |
| Legacy cancelled entry with no submission history | No | No | Holds it |

A fill time before `submitted_at` is refused by the journal's chronological check when
the call is `TRIGGERED`, and the platform does not keep it as `LINKED`. The eleventh
`TRIGGERED` in an IST month, and the eleventh open position, are refused by
`journal_event`. The platform records that refusal as `REFUSED` and does not keep a
second counter.

### Position

A projection, rebuildable from fills and exits.

| Field | Meaning |
|---|---|
| `position_id` | Primary key |
| `entry_id` | Source journal entry |
| `state` | `PENDING`, `OPEN`, `CLOSED` |
| `quantity_open` | From entry fills minus exit fills |
| `average_entry` | From entry fills |
| `stop` | Last recorded stop |
| `valuation` | Latest accepted close on or before the valuation date, with that date. Otherwise `UNAVAILABLE` |

Pending orders do not consume an open-position slot. Open positions do. The monthly cap
counts fills, not pending orders.

### Trade

The closed lifecycle of one journal entry: plan, order, fills, exit, and journal notes.
It is a view, not a third store of prices.

### Journal entry

The existing `journal_entries` row plus platform notes.

Existing event kinds remain: `PLANNED`, `TRIGGERED`, `STOP_LOSS_HIT`, `TARGET_HIT`,
`CANCELLED`, `EXPIRED`, `CLOSED_MANUAL`, `ZONE_INVALIDATED`, `NOTE`.

Platform notes (rationale, setup class, rule adherence, mistake class, chart reference)
hang off `entry_id` and can be edited. They are not market data. Setup class is a label
the owner types. It is not a new setup the engine detects.

## 5. Research programmes

### Backtest run

Existing backtest output plus manifest. Stores the execution model: expiry sessions,
same-bar policy, gap policy, slippage, cost schedule id, caps. A run without a calendar
is refused. Caps above 10 are refused.

### Backtest trade

One simulated lifecycle inside that run. It is not a journal entry and does not consume
the live monthly cap.

### Strategy validation run

A platform record that points at one or more backtest manifests and states the question
(in-sample, out-of-sample, walk-forward, sensitivity). It stores the figures Prompt 10
computes and the sample size. It does not store a verdict of "the strategy works".

### Paper-trading run

| Field | Meaning |
|---|---|
| `paper_run_id` | Primary key |
| `label` | Always includes `SIMULATED` |
| Execution assumptions | The same fields as a backtest model |
| Cap counters | Private to this run. They are not `journal` month counts |
| Links | scan manifests used as the signal source |

Simulated orders and simulated fills live under the paper run. They use the execution
policy. They are never written into `journal_orders`.

## 6. Application state

### User drawing and user annotation

| Field | Meaning |
|---|---|
| Primary key | `drawing_id` |
| Scope | symbol, timeframe, optional `as_of` |
| Geometry | horizontal, trend, rectangle, or text, in price and time |
| Provenance | `owner`, updated time, version |
| Isolation | no foreign key into gate evidence |

### Watchlist

`watchlist_id`, name, ordered symbols. A symbol can sit on a list the universe does not
include. Scanning a watchlist is an ad-hoc scan unless every symbol is a verified member
at `as_of`.

### Saved scan configuration

Paths and parameters. Secrets are not a field.

### Application configuration

Capital, risk stage, data directories, backup directory, scheduler enabled flag,
assistant enabled flag, assistant payload policy. Edits write an audit event.
Paths and public origins are process configuration. They are not hard-coded inside
a domain function.

### Browser session

D57. Not a research record and not a row in either SQLite file. An in-memory value
for the current API process, delivered only as an HttpOnly cookie. It is not a
bearer token, not a URL parameter, and not a domain field the UI stores. Restarting
the process ends it. A second process does not receive it.

### Job

| Field | Meaning |
|---|---|
| `job_id` | Primary key |
| `kind` | `SCAN`, `REPLAY`, `BACKTEST`, `INGEST`, `PAPER_STEP`, `REPORT` |
| `idempotency_key` | As defined for scans; other kinds define their own in the API |
| `state` | `PENDING_DATA`, `VALIDATING`, `RUNNING`, `SUCCEEDED_COMPLETE`, `SUCCEEDED_PARTIAL`, `FAILED`, `INTERRUPTED`, `CANCELLED`, `SKIPPED_HOLIDAY`, `SKIPPED_UNRESOLVED_CALENDAR` |
| Heartbeat | Updated while running. `SUCCEEDED_COMPLETE` is written only if heartbeats continued through the run. On launch, or on a wake or a wall-clock jump, a job still `RUNNING` whose heartbeat did not advance across the gap becomes `INTERRUPTED` before any completion write |

### Audit event

Append-only: time, actor (`owner` or `system`), action, object id, before/after digest
for settings. No secret fields.

## 7. Indexing and retention

| Access path | Index |
|---|---|
| Scans by `as_of` and trade type | already implied by store use; keep it |
| Journal by symbol and IST month | required for the cap check |
| Fills by `entry_id` | required |
| Drawings by symbol and timeframe | required |
| Jobs by state | required for recovery |
| Audit by object id | required |

Retention: raw archives and final research runs are kept. Logs rotate locally after a
retention the owner sets in settings (default proposal: 90 days of logs, unlimited
research runs). The proposal is applied in Prompt 12 and can be changed without a
methodology decision. Deleting a research run is an explicit owner action, audited, and
unavailable while a journal entry cites it.

## 8. Cross-store consistency

The research journal is the only live cap. `GET /portfolio` returns
`trades_triggered_this_month` and `open_positions` from that journal. A platform row
never adds a trade the journal does not already count.

`journal_event` reads the monthly count and then inserts in a separate `with conn`
block. The count and the insert are not one transaction. A probe on 2026-11-09, with
nine `TRIGGERED` events already stored, opened two connections and called
`journal_event` once on each. Both commits succeeded, and `journal_summary` reported
11 trades for February 2024. Prompt 00.1 does not patch `store.py`.

The desktop API uses one journal connection and runs those calls one at a time. That
removes the race inside the API. It does not stop a second connection, including the
research CLI, from committing an eleventh `TRIGGERED`. While the app holds the instance
lock, live journal writes go through the API. A CLI write during that window remains
a confirmed engine gap for Prompt 02.

Platform fill states: `JOURNAL_EVENT_PENDING`, `LINKED`, `REFUSED`,
`RECONCILE_REQUIRED`.

Idempotency key for the first entry fill of an entry: `live-trigger:{entry_id}`.
The body carries `filled_at` and `price`. A later share row on the same entry uses
`live-fill:{fill_id}` and does not call `journal_event`. An exit uses
`live-exit:{entry_id}:{kind}`.

Write order for the first entry fill:

1. Require the journal entry and its one submission. Require a stable zone reference
   that is not unresolved, missing, or ambiguous.
2. Insert the platform row as `JOURNAL_EVENT_PENDING` with the idempotency key, or
   return the existing row for that key.
3. Read `journal_events`. If a `TRIGGERED` row is already there, do not call
   `journal_event`. Matching `at` and `price` becomes `LINKED`. Any difference becomes
   `RECONCILE_REQUIRED`.
4. If no `TRIGGERED` row exists, call `journal_event` once. Success becomes `LINKED`.
   `JournalRefused` or `StoreError` becomes `REFUSED`, and the refusal text is stored.
   The same key does not call the journal again.

Crash points:

| Point | Journal | Platform | Recovery |
|---|---|---|---|
| Before step 2 | Unchanged | No row | The same key starts at step 2 |
| After step 2, before step 4 | Unchanged | `PENDING` | Step 3 then step 4. One insert |
| Inside the journal `with conn` block | SQLite rolls the insert back | `PENDING` | Same as the previous row |
| After the insert commits, before `LINKED` | One `TRIGGERED` | `PENDING` | Step 3 matches price and time and sets `LINKED`. It does not call `journal_event` |
| After `LINKED` | One `TRIGGERED` | `LINKED` | The same key returns that row |
| Journal refuses the insert | No new event | `REFUSED` | The same key returns `REFUSED` and does not retry into a later success |
| CLI inserted a different price first | That `TRIGGERED` | `RECONCILE_REQUIRED` | No second event. The cap follows the journal row. The owner resolves it by hand |

The API accepts no new fill while any row is `JOURNAL_EVENT_PENDING` or
`RECONCILE_REQUIRED`. Launch runs this recovery before the fill route is open.
`PENDING` does not count as a trade. `REFUSED` does not count. `RECONCILE_REQUIRED`
does not add a count of its own. The journal row, if one exists, already counts.

A `TRIGGERED` event with no `LINKED` fill is `FILL_NOT_RECORDED`. It still counts.

Paper code does not call `journal_add` or `journal_event`. It does not pass paper
counts into `merge_portfolio`. A paper run refuses its own eleventh simulated trigger
and its own eleventh open simulated position. Live scans read the research journal only.

## 9. Point-in-time rules (summary)

1. A scan body is immutable.
2. A plan version is immutable after approval. A change creates a version.
3. Orders and fills are append-only.
4. Drawings can change and are ignored by scans.
5. A paper book never updates a live cap counter.
6. Rebuilding a derived cache does not change a stored scan.
