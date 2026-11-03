---
name: position-review
description: Review an existing stock position against the Trading Rulebook, current evidence, and risk controls.
---

# Position Review

Use `trading-council` in Mode B (Trading Product Council), `position` workflow.

## Required Information

Request or locate:

- Symbol
- Quantity
- Average entry
- Current price with timestamp and source
- Intended horizon
- Original trade thesis

Do not assume missing position details.

## Review Areas

- Whether the original thesis remains valid
- Fresh-zone and invalidation status
- Gap, liquidity, concentration, and event risks
- Stop/exit rules from the Rulebook
- Scenarios and explicit conditions for hold, reduce, or exit

Use EXIT/REDUCE only when supported by position context and Rulebook criteria.

Clearly label stale or user-supplied prices.

This is analysis, not broker execution. Never place or modify orders.


## Rulebook exit rules (cite them)

- **Exit:**
  - on SL touch (RB 2141 "Exit on TOUCH, not on CLOSE");
  - at the target;
  - when a pre-planned Weekly Demand Trailing stop is touched (RB 2327, 2345).
- **The SL is permanently locked** once the trade triggers (RB 2139). Never suggest moving it.
  Trailing is reference only (D9).
- **No other early exit:** RB 2343, "the trade runs to either the full Target or the full Stop
  Loss. There is no break-even exit". REDUCE has no Rulebook basis. Report a wish to reduce
  as a departure from the plan; never recommend it.

## Council routing

- `/llm-council position <symbol> <entry date> <entry> <SL> <target> <qty> <price, source, time>`.
- Specialists: A Market Structure, C Risk and D Scenario in parallel; then E Devil's
  Advocate; then F Strategist.
- Evidence, at the review date:
  ```
  python3 -m nse.research.cli scan --as-of <review date> --symbols <S> --bhavcopy-dir nse/data/eod/raw \
      --manifest nse/data/eod/manifest.csv --calendar nse/data/calendar --out nse/output/council-<S>-<date>
  python3 .claude/skills/llm-council/scripts/evidence_pack.py --scan nse/output/council-<S>-<date>/scan.json --symbol <S>
  ```
  The zone's overlay status after entry shows whether the DL was closed beyond. Whether
  the SL or the target was touched comes from the daily lows and highs after entry (local
  files), not from memory.
