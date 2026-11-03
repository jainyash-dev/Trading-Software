---
name: strategy-review
description: Review proposed trading-rule changes, methodology choices, and strategy decisions against the protected Rulebook and evidence.
---

# Strategy Review

Use `trading-council` in Mode B (Trading Product Council), `strategy` workflow, adding Mode A specialist E for test impact on material decisions.

## Review Process

1. Read the protected Trading Rulebook and approved decision register.
2. Do not edit either.
3. Identify the exact rule or decision at issue.
4. Document current wording.
5. Identify ambiguity.
6. Compare alternatives.
7. Evaluate consequences and test implications.
8. Identify evidence required.

Respect the fresh-demand-only rule and exclusion of tested, invalidated, or unknown-freshness zones.

Separate a proposed change from an approved rule.

Only the user can approve a methodology change or protected-file modification.


## Council routing

- `/llm-council strategy <decision id or rule>`.
- Start from the decision's entry in `nse/docs/DECISION_REVIEW.md`: verbatim RB quotes,
  alternatives, and the gate outcomes and tests that change.
- Specialists: B Multi-Timeframe, E Devil's Advocate and F Strategist; engineering E for test
  impact.
- Evidence: run the tests the entry names, e.g.
  `python3 -m nse.validation.run_all --group strategy_gates --group integration`.
- Recommend a default only where the Rulebook supports it; otherwise USER DECISION REQUIRED.
  The status stays PROPOSED until the user approves it.
