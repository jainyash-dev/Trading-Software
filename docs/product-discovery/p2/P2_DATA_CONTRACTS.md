# P2 Data Contracts

## `GET /api/v1/candles`

Query: `symbol`, `timeframe` ∈ {M,W,D}, `as_of`, `dataset_id`.

### Candle row

| Field | Semantics |
|---|---|
| `time` | ISO end of session/period |
| `session_date` | Calendar date of the bar end |
| `open/high/low/close` | Raw unadjusted prices as decimal strings |
| `volume` | Traded quantity string, `"0"` if source zero, or `null` if unavailable. W/M: sum of constituent sessions, `null` if any is unstated |
| `volume_sessions` | W/M only: number of constituent daily sessions summed (absent on D) |

### Series metadata

| Field | Semantics |
|---|---|
| `adjusted` | Always `false` on this route |
| `volume_state` | `PRESENT` \| `PARTIAL` \| `UNAVAILABLE` \| `UNSUPPORTED` |
| `volume_unit` | `TRADED_QUANTITY` when supported |
| `volume_source` | `CSV_VOLUME` \| `BHAVCOPY_TOTTRDQTY` \| null |
| `missing_sessions` | Reported gaps; not filled |
| `excluded_sessions` | Calendar exclusions |
| `invalid_candles` | Rows failing OHLC validation (excluded from `candles`) |
| `data_quality.research_use` | `FIXTURE_NOT_MARKET_DATA` or `EXPLORATORY_ONLY_NOT_CERTIFIED` |
| `data_quality.certified` | Always `false` (route does not run P0 matrix) |
| `data_quality.data_ready` | Always `false` |

## Drawings

Platform table `drawing`. Geometry `{type, points, text}`. Types: horizontal, trend, rectangle, text. Not eligibility inputs.
