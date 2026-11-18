# Transaction-cost model

Date: 2026-11-10.

**HISTORICAL RESEARCH - NOT PERFORMANCE GUARANTEE**

No dated official or broker schedule is stored in this repository. Searches for a cost-schedule file found none. `execution_policy.py` states that no Zerodha figures are built in. This mission did not invent a Zerodha fee card, and it did not treat an owner-typed percent as a verified historical cost.

## What the engine can represent

`CostSchedule` (`nse/research/execution_policy.py` lines 48-79) accepts dated periods with a source string and a rate per instrument type, in percent per side. Periods may not overlap. A lookup that crosses a period boundary, or that lacks the instrument, is refused.

`r_multiple` then applies one number:

`side = (cost_pct_per_side + slippage_pct_per_side) / 100`

Entry is marked up by `side`. Exit is marked down by `side`. The planned risk per share is the denominator. The same percent is used on both sides. There is no separate brokerage, exchange charge, SEBI charge, GST, STT, or stamp duty, and no difference between buy and sell.

`EXECUTION_REALISM_GAPS` includes `COSTS_PERCENT_SYMMETRIC_ONLY` and `FLAT_MIN_CAPPED_CHARGES_NOT_MODELLED`. Flat rupee brokerage, minimums, caps, and GST on brokerage cannot be expressed.

The platform route requires the caller to type `cost_pct_per_side` and tells the caller those figures are not a dated Zerodha schedule (`desk.py`).

## Charge classes

| Component | Effective date | Source in repo | Instrument | Side | Basis | Status |
|---|---|---|---|---|---|---|
| Brokerage | - | none | - | - | - | UNVERIFIED |
| Exchange transaction charges | - | none | - | - | - | UNVERIFIED |
| SEBI charges | - | none | - | - | - | UNVERIFIED |
| GST | - | none | - | - | - | UNVERIFIED |
| STT | - | none | - | - | - | UNVERIFIED |
| Stamp duty | - | none | - | - | - | UNVERIFIED |
| Slippage | not a statutory charge | Owner decision B12 names 0.05%, 0.10%, and 0.20% per side as scenarios to run | Not measured on fills | Per side, percent of price | Research scenario, not an observed impact | HYPOTHETICAL |
| Other charges | - | none | - | - | - | UNVERIFIED |

## What is not claimed

Exact net returns are not claimed for any period. A single percent cannot be reconciled to the statutory pieces above, and those pieces have changed over 2016-2025. Using one percent for the whole decade would hide that.

Owner-typed percentages, including any number entered on the backtest screen, are this-run inputs. They are not evidence.

## Hypothetical scenarios that are allowed only with a label

If a later study is run after the data blockers close, the predeclared slippage set is 0.05%, 0.10%, and 0.20% per side, all three reported, none selected as best (`owner_grid`). Cost percent must come from a file that names broker, effective dates, instrument, and the document it was copied from. Until that file exists, any cost percent in a research note must be labelled **HYPOTHETICAL** and must not be described as net of actual NSE or broker charges.

No hypothetical percent was applied to market trades in this mission, because no market backtest was run.

## Sensitivity

See `SENSITIVITY_ANALYSIS_REPORT.md`. The engine can place several cost and slippage models side by side and does not rank them. That capability was not pointed at the Nifty 100 archive.

## Owner decision

B12 already requires a separate dated, instrument-specific schedule. That decision is not satisfied by this file. The owner still needs to supply the schedule, with dates and sources, before any net figure is discussed.
