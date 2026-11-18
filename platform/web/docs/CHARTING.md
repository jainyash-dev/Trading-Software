# Charting

## Choice

TradingView Lightweight Charts 5.2.1 is the candle renderer. Licence: Apache-2.0 (`platform/web/node_modules/lightweight-charts/LICENSE` when installed). The chart sets `attributionLogo: true` and the analysis page links to the library.

KLineChart was the documented fallback if hit testing or frame time failed. It was not adopted. Advanced Charts stays out: the vendor does not offer it for this personal-use product.

The library draws candles, volume, the time scale, the price scale, the crosshair, and pan/zoom. Zones and manual drawings are our primitives. They are not library indicators and they do not feed G0-G8.

## Data path

- Candles come from `GET /api/v1/candles` (`gtf_platform.integration.candles`).
- Daily / weekly / monthly series use `mtf.replay` with `htf=("D","W","M")`. The frontend does not aggregate OHLC.
- Volume is traded quantity. CSV `volume` or bhavcopy `TOTTRDQTY` (`traded_qty`). Missing volume is `null`. Zero remains `"0"` only when the source states zero.
- `data_quality.research_use` distinguishes fixtures from exploratory local data. Certified is never inferred from a successful draw.

## Interactions

- Monthly, weekly, and daily switch via the hash query `timeframe`.
- Fit, zoom in, and zoom out call the chart time scale.
- Wheel pan and zoom are the library defaults.
- Engine zones can be selected. They are not draggable.
- M / W / D zone visibility toggles filter stored multi-timeframe overlays.
- Manual drawings (horizontal, trend, rectangle, text) persist in platform SQLite. Drag updates PATCH geometry. Delete removes the row. A drawing cannot change a zone price.
- Invalid or duplicate timestamps refuse the whole series. Rows are not dropped to make the chart draw.

## Browser timing

Headless Google Chrome on this Mac, one animation frame after each action, 9 Nov 2026. Counts are the number of candles passed to `setData`. Eight overlay rectangles were attached for the overlay sample. This is not a sustained frame-rate claim and not market data.

| Set | Candles | Overlays | setData ms | next frame ms | pan ms | zoom ms | resize ms | overlay attach ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| small | 60 | 8 | 0.9 | 4.9 | 25.0 | 27.3 | 13.9 | 8.7 |
| medium | 504 | 8 | 0.9 | 14.9 | 17.3 | 16.1 | 16.3 | 13.8 |
| large | 2520 | 8 | 3.5 | 12.5 | 17.1 | 17.8 | 16.9 | 12.7 |

No row count was reduced. The commands were `npm run build`, a preview on `127.0.0.1:4173`, then `node scripts/chart-benchmark.mjs`. The page showed the fixture banner and a canvas.
