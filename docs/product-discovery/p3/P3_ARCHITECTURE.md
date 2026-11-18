# GTF P3 - Architecture

**Date:** 2026-11-15

## Authority

```
nse research pipeline (canonical)
  → stored scan_result.envelope_json
  → POST /api/v1/opportunities/ingest
  → opportunity rows (workflow metadata)
  → Opportunities UI / filters / lifecycle
  → deep-link #/analysis?... (P2) or #/plans?... (P4 entry)
```

P3 does **not** import the scanner or qualification modules. Status strings are copied from the stored envelope.

## Data model (platform SQLite migration `004_opportunity_intelligence`)

| Table | Role |
|---|---|
| `opportunity` | One row per `(scan_key, symbol, zone_id)` with immutable `canonical_status` |
| `opportunity_transition` | Auditable workflow history |
| `opportunity_note` | Owner research notes (not methodology) |
| `watchlist_symbol` columns `added_at`, `reason`, `note` | Research list metadata |

## Workflow vs methodology

| Field | Meaning |
|---|---|
| `canonical_status` | Stored GTF / scanner status snapshot |
| `workflow_state` | Desk organisation only |
| `source_quality` | FIXTURE / EXPLORATORY / UNKNOWN / UNAVAILABLE (CERTIFIED refused while P0=0) |
| `organizational_priority` | Transparent non-authoritative sort aid |

## API surface

- `GET /api/v1/opportunities`
- `POST /api/v1/opportunities/ingest`
- `GET /api/v1/opportunities/{id}`
- `POST /api/v1/opportunities/{id}/transition`
- `GET|POST /api/v1/opportunities/{id}/notes`
- `GET /api/v1/opportunities/{id}/history`
- `DELETE /api/v1/watchlists/{id}`

## Frontend

Route `#/opportunities` with query allowlist keys `scan`, `workflow`, `q`, `watchlist`, `fixtures`, `sort`. Analysis navigation reuses the P2 URL contract.
