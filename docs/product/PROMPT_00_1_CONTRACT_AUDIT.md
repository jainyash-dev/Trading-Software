# Prompt 00.1 contract correction audit

> Integration-lead audit on 2026-11-09. The research engine was read and executed.
> It was not edited. No application code was added. The Rulebook PDF, the Rulebook
> Markdown, and the Pine script were not opened for writing.
>
> Historical note, same day: section 5 describes the withdrawn per-launch token
> design. D57 replaces that boundary with a browser session. The zone-identity and
> cap findings in this audit are unchanged.

## 1. How this audit was isolated

The Prompt 00 contracts are untracked in the current checkout. A git worktree from
HEAD `9e302df` would not contain them. Copying them into a second worktree would fork
the blueprint the owner already has open. The edits are in this checkout, limited to
the five contract files named in the prompt plus this report. `nse/` was not modified.
Nothing was staged, committed, stashed, reset, or pushed.

## 2. Issue 1: stable zone identity

### Evidence

`zone_engine._zone_id` returns `side-startIndex-createdIndex`
(`nse/zone-engine/zone_engine.py`). Proximal and distal are assigned in `create` and
`create_zero_base` and are not assigned again later in that file.

A synthetic DBR series, the same rows as `tests/test_zone_engine.py`, was run through
`run_engine` on 2026-11-09:

| Series | Engine id | Creation times | Proximal | Distal |
|---|---|---|---|---|
| Base | `demand-2-3` | start 2, created 3 | 95.2 | 94 |
| One candle appended | `demand-2-3` | unchanged | 95.2 | 94 |
| `as_of` drops the appended candle | `demand-2-3` | unchanged | 95.2 | 94 |
| One candle prepended | `demand-3-4` | still 2 and 3 | 95.2 | 94 |
| Leg-in low moved from 94 to 93 | `demand-2-3` | still 3 | 95.2 | 93 |

Coverage `dataset_id` is the SHA-256 of the accepted `(trade_date, sha256)` pairs in
the window (`nse/research/eod_coverage.py`). Three inputs were hashed with that
formula: one session, that session plus another, and the first session with a
different hash. The three digests differed (`24f98c770364e50f`, `e83064766a1e21fe`,
`199aa6dd89ee395f`).

The persisted scan fields are `start_time` and `created_time` from the candle end
(`qualification._zone_record`). The journal and the backtest still select candidates
by the engine `zone_id`.

### Confirmed defect

The Prompt 00 reference included dataset id, the first candle of the series, and the
bar count. An ordinary new session changes the dataset id and the bar count, so every
existing plan would become unresolved. A prepend changes the engine id while the
creation times and prices stay the same, so an id-only join would treat the same zone
as a new one. A new distal can keep the same engine id, so an id-only join would
attach an old plan to a zone whose defining price changed.

### Contract after the correction

Stable reference: symbol, timeframe, side, `start_time`, `created_time`.

Defining properties, compared only after that match: pattern, proximal, distal,
normal_distal, zero_base.

Dataset id, manifest id, engine id, bar count, and the series start are stored as
observation provenance. They are not the reference. The engine id is still what
`journal_add` receives, and the platform refuses that call when the reference is
unresolved, missing, or ambiguous. `zone_engine._zone_id` is unchanged.

### Scenarios the contract now requires

| Case | Expected platform result | Checked against the engine |
|---|---|---|
| Append a later session. Same times and prices | Stay linked. Record the new dataset id as provenance | Engine id stayed `demand-2-3` |
| Unrelated accepted file changes the dataset hash. Prices unchanged | Stay linked | Dataset digest changed in the hash probe |
| Prepend history. Same times and prices. Engine id changes | Stay linked. Store the new engine id as an observation | Id became `demand-3-4`. Times and prices did not |
| Same times, distal changes | `ZONE_IDENTITY_UNRESOLVED`. Do not attach | Id stayed `demand-2-3` while distal moved from 94 to 93 |
| Creation time absent | `ZONE_NOT_IN_SERIES`. Do not attach to another time | Not a separate engine run. The prepend run still found time 3 |
| Two zones share the reference | `ZONE_IDENTITY_AMBIGUOUS` | Not observed on this DBR series |

These platform results are specified. They are not implemented, so they have no
platform test run.

## 3. Issue 2: canonical live cap event

### Evidence

D42, as restated on 2026-11-08, counts 10 trades per IST calendar month by the first
fill or trigger time, and 10 simultaneous open positions, independently. The journal
implements the monthly count as the number of `TRIGGERED` events whose `at` falls in
that IST month (`store.journal_event`, `store.journal_summary`). A second `TRIGGERED`
on the same entry raises `JournalRefused` ("entry already TRIGGERED") and does not
insert a row. That refusal was executed on 2026-11-09: after one `TRIGGERED`, a
repeat at the same time and a repeat at a later time both raised, and the event list
stayed `PLANNED`, `TRIGGERED`. One submission with no trigger left the events as
`PLANNED` and the February summary at 1, from the other entry.

`tests/test_research_store.py` was run with this filter:

`monthly_summary_and_ceiling or ten_trades_is_not_over or one_order_per_zone_until or ed3_a_cancelled_plan or ed3_a_submitted_order or ed3_an_expired_entry or ed3_a_pending_plan or eleventh_simultaneous or month_boundary_is_midnight or events_are_chronological`

Result: 10 passed, 45 deselected.

Those tests establish: the 11th `TRIGGERED` in February is refused; 10 is not over the
ceiling; a closed position frees a concurrent slot and not the monthly slot; a pending
plan blocks a second plan; a cancelled plan with no submission frees the zone; a
submitted order keeps the zone after cancel or expiry; expiry without a submission
row keeps the zone; the 11th open position is refused in a fresh month; an exit at
the same time still counts as open inside `_open_positions`; 23:59 IST on 29 February
is still February.

There is no partial-fill event. `ZONE_INVALIDATED` does not by itself close the
position (`test_stop_loss_hit_and_zone_invalidated_are_distinct` was not in the
filter above; the source and that test keep the state `OPEN` until an exit). That
test was not re-run in this audit. The statement rests on the test body and
`EXITS`, which does not include `ZONE_INVALIDATED`.

### Confirmed defect in the previous contract

The domain model said the first platform `ENTRY` fill consumes the monthly cap, and
that a `JOURNAL_EVENT_PENDING` row counts toward the cap. The journal does not read
platform rows. Counting them would be a second rule. The correction follows the
journal: only a committed `TRIGGERED` consumes the month and the open slot.

### When a live trade consumes each allowance

The table in `docs/architecture/DOMAIN_MODEL.md` is the contract. In short:

1. Monthly allowance: the IST month of a committed `TRIGGERED.at`. One per journal entry. Not a submission, not a pending platform row, not a refused platform row, not an extra share row, not an exit.
2. Open-position slot: from that `TRIGGERED` until an exit event strictly before the later check. Pending and unfilled submissions do not take a slot. An exit does not return the monthly allowance.
3. One-order-per-zone: a pending plan holds it; `CANCELLED` with no submission releases it; a submission holds it through cancel, expiry, and close; `EXPIRED` without a submission row holds it; a legacy cancelled entry holds it.

A platform fill is the owner's price and quantity record. The first entry fill of an
entry is the one that may call `journal_event(..., TRIGGERED)`. Later share rows do
not call it and do not consume another trade or another slot.

## 4. Issue 3: cross-store recovery

### Evidence

The insert of a journal event is inside `with conn`. The cap `SELECT` is before that
block. A second `TRIGGERED` after a committed one was executed and did not add a row.

The two-connection probe was also executed. Nine triggers were stored. Two new
connections each called `journal_event` for a different entry at the same February
timestamp. Both returned committed sequence 2. `journal_summary` reported 11 trades
for February 2024. The ceiling did not hold across connections.

No process was killed mid-write. A crash inside the `with conn` block is therefore
not an observed rollback. It is the normal SQLite behaviour of that block: the insert
commits only if the block finishes. Recovery must not assume a crash left a half-written
event row.

### Contract after the correction

Idempotency key `live-trigger:{entry_id}` for the first entry fill. Recovery reads
the journal before it calls `journal_event`. If `TRIGGERED` already exists with the
same `at` and price, the platform row becomes `LINKED` and the journal is not called.
If the price or time differs, the row becomes `RECONCILE_REQUIRED` and the journal is
not called. If no `TRIGGERED` exists, it is called once. A refusal becomes `REFUSED`
and the same key is not retried into a later success.

`PENDING` does not count as a trade. The fill route stays closed while any row is
`PENDING` or `RECONCILE_REQUIRED`.

The API must use one journal connection and one call at a time. That is necessary
because the probe reached 11. It is not sufficient against a second process.

### Crash points

| Point | What was verified | Recovery specified |
|---|---|---|
| Before the platform insert | No platform code exists. Nothing to run | Same key starts the insert |
| `PENDING`, journal not called | No platform code | Call `journal_event` once |
| Crash inside `with conn` | Not injected. The insert is the whole transaction | Treat as "no `TRIGGERED` yet" and call once |
| `TRIGGERED` committed, platform still `PENDING` | A second call was executed and refused, leaving one row | Match price and time, set `LINKED`, do not call |
| Already `LINKED` | Same refusal path | Return the stored row |
| Journal refuses | 10 existing store tests refuse the 11th, the bad lifecycle, and the missing price | Store `REFUSED` and do not retry that key |
| Two connections at once | Executed. February count became 11 | One API connection. Second process is not authorized. Engine fix belongs to Prompt 02 |

## 5. Issue 4: API process ownership

A second shell cannot receive the bearer token without reading the token file or
receiving it from the first process. Either path gives that shell, and any same-user
reader of the file, the ability to write fills. That is a second journal writer, which
the cap probe shows is enough to pass 10.

The contract is single-instance. The second launch does not read the token file. It
may send a focus message that returns no token and no port, then it exits. A dead pid
allows a new process to delete the old token and start again. The port comes from
binding `127.0.0.1` port 0. The token travels on a pipe, not in argv.

No shell was started. This issue is a design correction, checked against the cap probe
rather than against a Tauri process.

## 6. Files changed

| File | Change |
|---|---|
| `docs/architecture/DOMAIN_MODEL.md` | Stable reference, cap table, recovery and the 11-trade probe |
| `docs/architecture/API_CONTRACTS.md` | Single instance, fill keys, 422 and 409 |
| `docs/architecture/SYSTEM_ARCHITECTURE.md` | Lock, focus socket, one journal connection |
| `docs/architecture/AGENT_OWNERSHIP.md` | Engine id stays with Prompt 02 |
| `docs/product/DECISIONS_AND_OPEN_QUESTIONS.md` | AR-15 replaced. AR-16 and AR-17 added |

No `nse/` file, Rulebook file, or Pine file was edited.

## 7. Assumptions and owner decisions

No new owner decision. D42, D46, and ED-3 stay as written.

Assumption: the scan record's `start_time` and `created_time` remain the creation
evidence the platform compares. That matches `qualification._zone_record` today. If
Prompt 02 renames those fields, the reference moves with them.

Assumption: one `TRIGGERED` is the whole trade, whatever the share count. The journal
has no partial-fill quantity. Extra share rows are records only.

Unresolved, and not an owner question: the non-atomic cap. Closing it means changing
`store.journal_event` so the count and the insert commit together. That file is owned
by Prompt 02.

## 8. Remaining risks

- The monthly ceiling can be exceeded by two connections. Observed: 11 trades. The API
  rule reduces the chance. It does not remove the engine gap.
- Platform recovery and the stable-zone comparison are not implemented, so they have
  no passing test.
- A prepend that changes the base times leaves the old reference unmatched. That is
  the safe outcome, and it will look like a missing zone until a person looks.
- The focus socket is unspecified beyond "no secret in the reply". Prompt 04 can ship
  the exit without the focus socket.

## 9. Readiness

Prompt 04 can start. Its shell work is the single-instance lock, the pipe-delivered
token, and the second-launch exit. It does not need the journal.

Prompt 03 can start for health, scans, reads, and jobs, using one process and labelled
fixtures. It must not open the live fill route until the recovery rules in the domain
model are the code under test, and until that route uses one journal connection.
Prompt 03 must not treat the monthly cap as safe against a second connection.

Prompt 07 must not store a live plan until the stable-reference states are
implemented. It must not change `zone_engine.py` or `store.py`.

The cap race is not resolved. Documentation of it is not a fix.
