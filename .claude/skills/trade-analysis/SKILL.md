---
name: trade-analysis
description: Analyze a specific stock or trade setup under the project's Trading Rulebook and deterministic zone eligibility rules.
---

# Trade Analysis

Use `trading-council` in Mode B (Trading Product Council), `trade` workflow, with the full specialist roster (A-F) when the decision is material.

## Analysis Process

1. Identify symbol, exchange, timeframe, data source, and as-of timestamp.
2. Read the Trading Rulebook and approved decision register.
3. Verify zone freshness and deterministic eligibility.
4. Tested, invalidated, or unknown-freshness zones cannot qualify.
5. Assess multi-timeframe context, location, trigger, invalidation, liquidity, gap risk, and reward relative to risk.
6. Return the canonical qualification status from `derive_status` and the evidence pack.
   You may also give one advisory description, and only when `verdict_cap` allows it:
   - BUY CANDIDATE
   - WAIT
   - AVOID
   - INSUFFICIENT DATA
7. State what would change the status and what evidence is missing.

The advisory description is not a qualification status. Never write BUY CANDIDATE, WAIT,
AVOID or INSUFFICIENT DATA back as the canonical status. The evidence pack's
`verdict_cap` is the strongest advisory description you may use. An attractive R:R never
raises it.

## Important

Do not imply a BUY CANDIDATE is an instruction to place an order.

Never invent prices or probabilities.

If the user provides a chart or values, distinguish those inputs from independently verified market data.


## Council routing

- `/llm-council trade <symbol> <as-of date> [<zone id or PL>]`.
- Deterministic evidence first:
  ```
  python3 -m nse.research.cli scan --as-of <date> --symbols <S> --bhavcopy-dir nse/data/eod/raw \
      --manifest nse/data/eod/manifest.csv --calendar nse/data/calendar --out nse/output/council-<S>-<date>
  python3 .claude/skills/llm-council/scripts/evidence_pack.py --scan nse/output/council-<S>-<date>/scan.json --symbol <S>
  ```
- The pack's `verdict_cap` is the strongest status you may return. An attractive R:R never
  raises it.
- Check the final status with `--check-verdict "<STATUS>"`.
- No local data for the symbol and date means INSUFFICIENT DATA.
