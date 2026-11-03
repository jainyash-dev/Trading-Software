---
name: nse-code-review
description: Perform a focused, evidence-based code review of the NSE research repository for correctness, safety, tests, and trading-system invariants. Named nse-code-review so it does not shadow Claude Code's built-in code-review skill.
---

# NSE Code Review

Use `engineering-council` (Mode A, `code-review` workflow) for material or high-risk changes.

## Review Process

Inspect the diff and surrounding code.

Check:

- Correctness
- Edge cases
- Error handling
- Typing
- Security
- Performance
- Test coverage
- Maintainability

For scanner paths, verify use of:

`MtfSnapshot.eligible_after_overlay(timeframe)`

Ensure no raw eligibility bypass exists.

## Output

Report findings first, ordered by severity, with file and line references.

Distinguish confirmed defects from questions and style suggestions.

Do not edit files unless asked.

Preserve all uncommitted work.

Do not commit or push.


## Council routing

- Material or high-risk changes: `/llm-council code-review <diff or paths>`. Specialist B
  always; D for git, file, subprocess or network changes; E for eligibility, gate, overlay or
  report changes; C for data, time or backtest changes.
- Evidence to run before reporting: `python3 -m nse.validation.run_all --group <changed area>`,
  and `cd tests && python3 -B -m unittest -v <module>` for the touched module.
- A finding without a reproduction or an exact quote is a QUESTION, not a confirmed defect.
