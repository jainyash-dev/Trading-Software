---
name: release-readiness
description: Produce an evidence-based readiness statement for the NSE research system, capability by capability. Use at the end of a substantial task, before telling the user something is done, and whenever asked "is it ready", "is it validated" or "what is left".
---

# Release readiness

## Run

```
python3 -m nse.validation.run_all                 # writes nse/output/validation/report.json
python3 -m nse.validation.run_all --acceptance    # missing local evidence FAILS instead of skipping
python3 -m nse.research.cli readiness
```

## How to judge

Read `report.json`, not your memory of the work. For each capability in
`nse/research/readiness.py` report the separate states:

implemented / unit_tested / integration_tested / reference_validated / externally_validated /
deferred / blocked / requires_human_decision

- `*_tested_state` must be CONFIRMED by this run; UNCONFIRMED means its tests did not pass here.
- A skipped test (PREREQUISITE MISSING) is not a pass. Name the missing prerequisite.
- reference_validated needs a recorded comparison; externally_validated needs TradingView or
  other independent evidence. Synthetic tests never count.
- Never collapse the states into one green tick. Never call the strategy validated or
  profitable because tests pass.

## Output

1. Exact commands and counts (ran / failures / errors / skipped) per group.
2. Per capability: states with evidence paths.
3. What is externally unverified; which rules are unresolved; which outputs stay restricted
   (WIT BLOCKED; nothing is ever approved).
4. The minimum human decisions needed, from `nse/docs/IMPLEMENTATION_BLOCKERS.md`.
