---
name: zone-mtf-validation
description: Validate the Zone Engine (nse/zone-engine) and the higher-timeframe freshness overlay (nse/mtf-freshness). Use for any change to zone detection, scoring, freshness, invalidation, HTF candle construction, touch tracking, data-gap or session handling, or eligible_after_overlay / manual_review_after_overlay.
---

# Zone Engine and MTF overlay validation

## Run

```
python3 -m nse.validation.run_all --group zone_engine --group mtf_freshness
python3 -m nse.validation.run_all --group adversarial --group lookahead
```
`tests/test_zone_engine.py` and `tests/test_mtf_freshness.py` hold the synthetic fixtures with
known outcomes; read them before adding cases. Test the public interfaces
(`run_engine`, `replay`, `MtfSnapshot.*_after_overlay`), never a re-implementation.

## Invariants that must hold

- Detection runs on completed candles only; `as_of` cuts input before anything runs.
- A zone is tested by any PL touch after the leg-out (RB 683-697) on every completed candle
  of the finest base, including HTF zones (B16, D24-D28).
- A close beyond the DL invalidates permanently (PS 2613; RB 1627, 1741).
- Data gaps and unclassifiable sessions make a zone UNKNOWN_DATA_GAP or UNVERIFIED_SESSION,
  never FRESH (D27, D33, D34, D36).
- The overlay only removes eligibility, never adds it. Both overlay methods apply the same
  filter (`usable_as_fresh_context`).
- 6+ bases form no zone (RB 787); a base closing outside a full cluster is manual (D35).

## When a test fails

Find the smallest fix; add the failing scenario as a regression test; re-run both groups and
the full required suite. Never change a rule to make a fixture pass: if the fixture is right
and the rule is ambiguous, the zone goes to MANUAL REVIEW and the ambiguity goes to
`nse/docs/IMPLEMENTATION_BLOCKERS.md`.

Pine parity is not claimed (spec 10) until the user supplies TradingView references (B10).
