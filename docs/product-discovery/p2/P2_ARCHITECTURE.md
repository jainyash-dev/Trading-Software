# P2 Architecture

## Boundaries

```
nse research inputs / EOD
        │
        ▼
gtf_platform.integration.candles  →  CandlePayload + data_quality
        │
        ├── React AnalysisPage + CandleChart (Lightweight Charts 5.2.1)
        │
stored scan bundle (research path) → zones + qualification display only
        │
platform SQLite drawings → annotations (never eligibility)
```

- Eligibility authority remains `pipeline.run → scanner.scan → scan_symbol → qualification.evaluate_symbol`.
- Chart never computes zones, freshness, or gate outcomes.
- `authorises_order` stays false. `data_ready` stays false on the candle quality block.

## Aggregation

Weekly and monthly OHLC come from `mtf.replay(..., htf=("D","W","M"))`. The frontend does not aggregate prices.

## Volume

| Source | Field | Unit |
|---|---|---|
| User CSV | `volume` | traded quantity |
| Bhavcopy | `traded_qty` (NSE `TOTTRDQTY` / UDiFF equivalent) | traded quantity |

Missing volume is JSON `null`. Literal zero remains `"0"`. W/M volume (2026-11-17) is the sum of the constituent daily sessions of the HTF candle, or `null` with `HTF_VOLUME_INCOMPLETE` / `HTF_VOLUME_SESSION_MISMATCH`. The former `VOLUME_NOT_AGGREGATED_FOR_HTF` code is no longer emitted.

## Zones

`zonesFromStored` maps stored `candidates`, `fresh_zones`, and `blocked_zones`.

- Candidate and blocked rows: missing or unknown `overlay_status` maps to `UNKNOWN` (never invent fresh).
- `fresh_zones` rows: the scanner contract (D3) only includes overlay-fresh zones. When `overlay_status` / `freshness` is absent on that list, the chart uses `FRESH` from list membership, not from geometry.
- Visibility toggles filter by timeframe.
