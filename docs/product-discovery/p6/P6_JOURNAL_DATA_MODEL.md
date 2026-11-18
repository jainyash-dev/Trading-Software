# P6 Journal Data Model

**Date:** 2026-11-17  
**Authority:** research SQLite (`nse/research/store.py`) remains the sole ledger of actual trades.

## Tables (additive migrations)

| Version | Table | Role | Mutability |
|---|---|---|---|
| v1 | `journal_entries` | Plan snapshot (symbol, zone, levels, checklist, planned prices/qty) | Append-only |
| v1 | `journal_events` | Lifecycle kinds (PLANNED, TRIGGERED, exits, NOTE, …) | Append-only |
| v2 | `journal_orders` | One submission statement per entry | Append-only (one row) |
| v4 | `journal_executions` | ENTRY/EXIT prints (`print_key`) | Append-only |
| v4 | `journal_charges` | Itemised charges (paise) | Append-only |
| v4 | `journal_idempotency` | Retry fingerprints | Append-only |
| v5 | `journal_notes` | Typed review notes | Append-only |
| v5 | `journal_reviews` | Review status + taxonomy classification | Append-only |
| v5 | `journal_attachments` | Attachment metadata (bytes outside DB) | Append-only |

## Attachment storage

- Bytes: `{data_dir}/journal_attachments/{entry_id}/{storage_name}`
- Metadata: `journal_attachments` row with sha256, content_type, size, missing flag
- Allowed types: `image/png`, `image/jpeg`, `image/webp`, `image/gif`
- Max size: 5 MiB
- Exports include the metadata manifest only (`attachments_embedded=false`)

## Immutable vs editable

| Fact | Handling |
|---|---|
| Planned entry/stop/target/quantity | Immutable columns on `journal_entries` |
| Fills, exits, charges | Append-only rows |
| Review notes / classifications | New append-only rows; never UPDATE execution rows |
| Corrections | New rows / refusals; no silent overwrite |

## Platform role

The platform API validates commands and projects read models. It does not keep a second financial ledger or monthly counter.
