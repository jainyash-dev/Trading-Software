---
name: nse-scenario-library
description: Add, run and maintain the scenario laboratory (nse/scenarios/, nse/research/scenarios.py): data-driven cases with candle data, expected gate outcomes and statuses, rule references and explanations, run through the real pipeline. Use after every confirmed bug fix (add a regression scenario), after every newly approved methodology rule, when the owner supplies a chart case, and before claiming a rule is covered.
---

# Scenario library

A scenario states what the Rulebook requires for a concrete chart and checks that the
real pipeline (marketdata -> MTF replay -> G0-G8 -> status) does exactly that.

## Run

```
python3 -m nse.research.cli scenarios-validate          # schema only
python3 -m nse.research.cli scenarios-run               # every scenario; exit 1 on FAIL or INVALID
python3 -m nse.research.cli scenarios-run --only <ID>
python3 -m nse.validation.run_all --group scenarios
```

## Adding a scenario

1. Name the rule first (RB line, R1-R6, D number, spec section). No rule, no scenario.
2. Data: `data_kind` is SYNTHETIC (invented candles, labelled), HISTORICAL_REAL (local raw
   files by path and SHA-256; UNAVAILABLE when absent, never passed) or OWNER_CHART.
3. Expected outcome: derive it from the rule and write the `explanation` saying why. Never
   copy the current output into `expected`; if the expectation cannot be derived, the
   scenario is not ready.
4. Run it. A FAIL is either a defect (fix the code and keep the scenario as a regression)
   or a wrong expectation (correct it only with a rule citation).

## Hard restrictions

- Synthetic scenarios are software evidence only; they never count as market validation.
- A scenario never weakens a gate, and UNAVAILABLE is never counted as PASS.
- Owner chart cases are recorded as supplied; nothing is fabricated to fill the template.

## Verification

`scenarios-run` reports every scenario PASS (UNAVAILABLE listed separately) and the
mutation test in `tests/test_research_scenarios.py` shows a wrong expectation FAILS.
References: `nse/docs/TRACEABILITY.md`, `tests/test_research_e2e.py`.
