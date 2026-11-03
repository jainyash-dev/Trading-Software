---
name: lookahead-audit
description: Hunt for lookahead leakage in historical replay and scanning. Use for any change touching as_of handling, candle completeness, HTF candle construction, trend or location inputs, universe membership, scan_history, or anything that reads "the last" value of a series.
---

# Lookahead audit

## Run

```
python3 -m nse.validation.run_all --group lookahead --group mtf_freshness
```

## What the tests already prove (tests/test_research_lookahead.py)

- Prefix invariance: a scan at T with all data equals a scan at T with data cut at T, for
  several T and seeds, compared on the full serialised result.
- A later touch does not rewrite an earlier decision; the later scan does change.
- `as_of` inside a session ignores that day's candle; a trailing incomplete candle is ignored.
- Identical inputs give byte-identical JSON; symbol order does not matter; no clock is read.

## Audit checklist for a change

1. Every series read is cut at `as_of` before use (`replay` does this; anything new must too).
2. Higher-timeframe candles: the period in progress is never used (D23).
3. Trend and curve read only completed candles of their timeframe.
4. Universe: `Universe.members(as_of_date)` only; never today's list for a past date.
5. Outcome data (anything after the signal time) is never an input to a signal.
6. Corporate-action adjustment, when it exists, must not use events after `as_of` (B7).

Add an adversarial fixture for each new path: make the future data *disagree* with the past
(e.g. a touch or a breakdown right after T) so leakage changes the answer.
