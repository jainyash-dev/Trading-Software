# GTF P3 - Data contracts

## Opportunity

| Field | Type | Notes |
|---|---|---|
| opportunity_id | string | `opp-…` |
| scan_key | string | Stored scan reference |
| symbol | string | Uppercase ticker |
| zone_id | string \| null | Candidate zone id when present |
| timeframe | string \| null | M / W / D when present |
| as_of | string \| null | From scan |
| dataset_id | string \| null | From scan |
| canonical_status | string | Immutable snapshot |
| workflow_state | enum | DISCOVERED…ARCHIVED |
| source_quality | enum | Never invents CERTIFIED under current P0 |
| fixture | bool | True ⇒ not market data |
| authorises_order | false | Always |
| organizational_priority | object | `authoritative: false` |

## Ingest request

```json
{ "scan_key": "…", "include_rejected": true }
```

Idempotent per `(scan_key, symbol, zone_id)`. Duplicate ingest returns existing rows.

## Transition request

```json
{ "to_state": "UNDER_REVIEW", "reason": "optional unless REJECTED/EXPIRED/ARCHIVED" }
```

Invalid edges → HTTP 409. Destructive targets require a non-empty reason.

## Watchlist item

```json
{ "symbol": "TCS", "reason": "monitor daily demand", "note": "research only" }
```

Membership never implies eligibility.
