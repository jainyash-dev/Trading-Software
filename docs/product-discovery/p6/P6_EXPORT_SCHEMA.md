# P6 Journal Export Schema

**Format id:** `gtf-journal-export-v1`  
**Endpoint:** `GET /api/v1/journal/export` (same filters as journal list)  
**Evidence class:** `JOURNAL_DESCRIPTIVE`

## Top-level object

| Field | Type | Notes |
|---|---|---|
| `format` | string | `gtf-journal-export-v1` |
| `evidence_class` | string | Always `JOURNAL_DESCRIPTIVE` |
| `total` | int | Row count |
| `filters` | object | Applied filters |
| `attachments_embedded` | bool | Always false |
| `rows` | array | Trade objects |
| `authorises_order` | bool | Always false |

## Row object

| Field | Contents |
|---|---|
| `entry_id`, `symbol`, `zone_id`, `trade_type`, `direction` | Identity |
| `lifecycle_state` | Derived state |
| `planned` | Immutable plan snapshot |
| `actual` | Execution summary from prints/book |
| `deltas` | Planned vs actual deltas (null when unavailable) |
| `events` | Full lifecycle event list |
| `executions` | Print rows |
| `charges`, `charges_state` | Charge lines and completeness |
| `book` | `position_book` projection |
| `notes`, `review`, `reviews` | Review artefacts |
| `setup` | trade_type / pattern / core / setup_label |
| `attachments` | Metadata manifest only |
| `attachments_included` | Whether manifest was requested |

## Safety

- No session tokens or secrets
- User text exported as JSON strings (no spreadsheet formula injection in this JSON path)
- Attachment bytes are not embedded; download via authenticated attachment GET
