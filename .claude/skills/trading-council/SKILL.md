---
name: trading-council
description: Use the LLM Council for trading methodology, stock setups, position decisions, scanner product decisions, and backtest interpretation.
---

# Trading Council

Invoke the central `llm-council` skill in Mode B (Trading Product Council), through its
`trade`, `position`, `scenario` or `strategy` workflow (see "Council routing" below).

## Required Inputs and Discipline

- Read the authoritative Trading Rulebook and approved decision register before interpreting a setup.
- Use current market data only when a verified source and timestamp are available.
- If not, label the analysis as based solely on user-supplied data.
- Check deterministic scanner eligibility and freshness overlay.
- Never infer freshness from appearance alone.
- Tested, invalidated, and unknown-freshness zones are ineligible.
- Only fresh demand zones can be considered for long entries.
- Never convert an AI opinion into a deterministic scanner pass.

## Trade Analysis Output

Use statuses:

- BUY CANDIDATE
- WAIT
- AVOID
- INSUFFICIENT DATA

These four words are advisory descriptions. They are not canonical qualification statuses. The canonical status is the scanner's `derive_status` result in the evidence pack. Do not write BUY CANDIDATE, WAIT, AVOID or INSUFFICIENT DATA back onto a qualification record.

For an existing position, EXIT may be discussed only with position details. REDUCE is not an action. It has no Rulebook basis (RB 2343). Do not recommend it.

Assess:

- Higher-timeframe context
- Zone validity and freshness
- Entry trigger
- Invalidation
- Risk/reward
- Liquidity
- Gap risk
- Missing evidence

Discuss bullish, bearish, and sideways scenarios.

Give entry, stop, targets, or position sizing only when the necessary inputs and Rulebook rules are available.

Do not fabricate probabilities.

## Backtest and Strategy Decisions

Challenge:

- Look-ahead bias
- Survivorship bias
- Corporate-action handling
- Point-in-time universe membership
- Transaction costs
- Slippage
- Liquidity
- Sample size
- Regime dependence
- Out-of-sample validation

Do not claim profitability or readiness from synthetic tests or infrastructure alone.

No broker execution or autonomous order placement.


## Council routing (Mode B)

Run `/llm-council trade|position|scenario|strategy <subject>`. Specialists
(`../llm-council/references/trading-specialists.md`):
- A Market Structure, B Multi-Timeframe, C Risk Manager and D Scenario Analyst run in
  parallel;
- then E Devil's Advocate, on the proposal only;
- then F Trading Strategist.

Workflow:
1. Establish the stock, date, price, timeframe and direction.
2. Establish the source and timestamp of the data.
3. List the missing information.
4. Run the deterministic scan and the evidence pack:
   ```
   python3 -m nse.research.cli scan --as-of <date> --symbols <S> --bhavcopy-dir nse/data/eod/raw \
       --manifest nse/data/eod/manifest.csv --calendar nse/data/calendar --out nse/output/council-<S>-<date>
   python3 .claude/skills/llm-council/scripts/evidence_pack.py --scan nse/output/council-<S>-<date>/scan.json --symbol <S>
   ```
   (Both commands run from the repository root.)
5. Analyse all timeframe context.
6. Collect the specialist assessments.
7. Lay out the bullish, bearish and sideways scenarios.
8. Compute R:R and size only from valid levels and the user's RPT.
9. Have the Devil's Advocate challenge the proposal.
10. Synthesize.
11. State the exact conditions to enter, wait, exit or avoid.

**Verdict cap:** the deterministic status caps the verdict.
`evidence_pack.py --check-verdict "<VERDICT>"` must exit 0. REDUCE has no Rulebook basis
(RB 2343: a trade runs to the full target or the full stop).
