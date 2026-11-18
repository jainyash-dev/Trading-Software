# GTF P4 - Architecture

**Date:** 2026-11-15

## Authority

```
nse research pipeline (canonical eligibility)
  -> stored scan_result.envelope_json candidate
    -> POST /api/v1/plans  (snapshot candidate_status immutably)
      -> preview: risk.plan_trade combinations + portfolio_checks (advisory)
        -> submit / reject / cancel / approve
          -> approve -> store.journal_add (caps + ED-3 hard path)
            -> journal order / prints / close (manual)
```

P4 does **not** import qualification or scanner. It copies the stored candidate.
Hard monthly / open / ED-3 enforcement remains in `nse.research.store`.

## Data model (platform SQLite migration `005_trade_plan_lifecycle`)

| Table / columns | Role |
|---|---|
| `trade_plan` + lifecycle columns | Draft through cancel/reject; immutable `candidate_status` |
| `trade_plan_event` | Auditable plan history |
| `trade_plan_note` | Owner notes (not methodology) |

Plan states stored: `DRAFT`, `AWAITING_OWNER`, `APPROVED`, `REJECTED`, `CANCELLED`, `EXPIRED` (expiry deferred).

Journal-derived fill comparison is enrichment on preview, not a second state machine.

## API surface

- `GET /api/v1/plans`
- `POST /api/v1/plans`
- `GET /api/v1/plans/{plan_id}`
- `POST /api/v1/plans/{plan_id}/approve`
- `POST /api/v1/plans/{plan_id}/submit`
- `POST /api/v1/plans/{plan_id}/reject`
- `POST /api/v1/plans/{plan_id}/cancel`
- `POST /api/v1/plans/{plan_id}/reopen`
- `POST /api/v1/plans/{plan_id}/rationale`
- `GET|POST /api/v1/plans/{plan_id}/notes`
- `GET /api/v1/plans/{plan_id}/history`

Existing journal and portfolio routes are unchanged authorities for fills and caps.

## Frontend

Route `#/plans` with query keys `scan`, `symbol`, `zone`, `plan`, `plan_state`, `fixtures`.
Manual-execution disclosure is always shown. `authorises_order` is always false.
