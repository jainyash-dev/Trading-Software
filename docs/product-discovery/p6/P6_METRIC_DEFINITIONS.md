# P6 Metric Definitions (Journal-descriptive)

**Evidence class:** `JOURNAL_DESCRIPTIVE`  
**Not:** certified strategy performance, R4 evidence, proven profitability, validated expectancy.

## Counting rules

| Metric | Included | Excluded |
|---|---|---|
| Recorded trades | Journal entries matching filters | None within filter |
| Open trades | `book.counts_as_open == true` | Closed / cancelled / unfilled plans that never triggered |
| Closed trades | Lifecycle state `CLOSED` | Open and planned-only rows |
| Wins / losses | Closed trades with numeric `realised_pnl` &gt; 0 / &lt; 0 | Open trades; null PnL |
| Partially exited | Exit prints present and still open | Fully closed |

An unfilled plan (`PLANNED`, no TRIGGERED) is a recorded journal row but **not** a completed trade and does not count as a win or loss.

## PnL

| Metric | Formula / source | Missing data |
|---|---|---|
| Gross realised | Sum of `position_book.realised_pnl` on closed trades | Null when no closed priced trades |
| Known charges | Sum of `journal_charges.amount_paise` on closed trades | Null when no closed trades |
| Net realised | Gross − known_charges/100 | Only when every closed trade has `charges_state == ACTUAL` (or all ESTIMATED for estimated_net). Otherwise `net_state` is `INCOMPLETE_COSTS` / `UNAVAILABLE` and net is null |
| Average win/loss | Mean of positive / negative gross realised values | Null when no wins/losses |
| Largest win/loss | Max / min of those values | Null when empty |

ABSENT charges are never treated as zero.

## Breakdowns

Dimensions with reliable stored identifiers:

- `trade_type` (from `journal_entries`)
- `mistake_category` / `outcome_class` (latest review row)
- `setup_label` (owner review label) falling back to `trade_type`

Sample size is always shown. Small samples are not ranked or recommended against.

## Rounding

Money uses the store's existing rounding (`position_book` / summary). Charge amounts are integer paise.
