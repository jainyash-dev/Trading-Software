# Council Report Format

# Council: <decision or subject>

- Date:
- Mode:
- Question:
- Inputs reviewed:
- Evidence limitations:

## Executive Recommendation

State the recommendation, confidence rationale, and the most important caveat.

## Facts and Constraints

List verified facts with file paths, line numbers, test identifiers, timestamps, or source citations.

## Five Perspectives

For each advisor include:

- Position
- Evidence
- Assumptions
- Strongest objection
- Risks
- View-changing evidence

## Peer Review

Summarize:

- Material critiques
- Corrections
- Unresolved disagreements
- Whether review was independent or simulated

## Chair Verification

Required for every material claim that was disputed, marked "verified" by reviewers, or
carries the recommendation (`peer-review-protocol.md` 12-17):

| claim | asserted by / disputed by | primary evidence (file:line, command, test) | VERIFIED / REFUTED / UNVERIFIABLE | correction and its effect |

A REFUTED claim is corrected here even when most reviewers agreed with it.

## Scenario Analysis

For trading:
- Bullish scenario
- Bearish scenario
- Sideways scenario

For engineering:
- Normal operation
- Failure modes
- Recovery
- Rollback

## Decision and Gates

Separate:

- Decided now
- Conditional on evidence
- Requires user approval
- Rejected / out of scope

## Action Plan

Ordered actions with dependencies and acceptance criteria.

## Open Questions

Only questions that genuinely block the next step.

# Specialist Council Formats

Use these for the Engineering, Trading Product and Combined councils. The Council Report
above stays the format for the `general` workflow.

## Engineering Review (Mode A)

```
# Engineering Council: <subject>
Date | Workflow | Independence: separate subagents / single-context
Review scope: <diff, files, proposal>
Files inspected: <paths>
Commands run: <exact commands and result lines>

Findings by severity (CRITICAL, HIGH, MEDIUM, LOW):
| id | severity | specialist | file:line | finding | evidence | status (CONFIRMED / PLAUSIBLE / QUESTION) |

Defects and proposed corrections: <per finding: smallest fix, not applied>
Test requirements: <failing scenario per defect; existing tests that already cover it>
Disagreements: <specialist X vs Y, evidence each, resolved how / UNRESOLVED>
Chair Verification: <claim | by | primary evidence file:line | VERIFIED / REFUTED / UNVERIFIABLE | correction>
Approval status: APPROVED | APPROVED WITH CONDITIONS (list) | NOT APPROVED (blocking ids) | CANNOT ASSESS
Remaining risks: <what is untested or unknown>
```

## Trade Analysis / Position Review (Mode B)

```
# Trading Council: <symbol> <direction> as of <date/time>
Data: <source, file hashes / manifest, as_of>; user-supplied values (labelled); missing information
Independence: separate subagents / single-context
Deterministic evidence: status, gates (G0-G8), overlay status, limitations, verdict cap (evidence_pack.py)
Timeframe context: Y, HY, Q, M, W, D (AVAILABLE or unknown) | location | trend | HTF conflict
Specialists: one paragraph each, with POSITION and citations
Scenarios: bullish | bearish | sideways | breakout / failed breakout | retest | rejection | gap-up / gap-down
Risk: entry range, SL range, target, R:R range, quantity (only with valid inputs; else "not computed: why")
Devil's Advocate: objections and how each was answered (evidence) or left open
Disagreements: <who, what, evidence, resolution / UNRESOLVED>
Chair Verification: <claim | by | primary evidence (pack field, file:line, RB line) | VERIFIED / REFUTED / UNVERIFIABLE | correction>
VERDICT: BUY CANDIDATE | WAIT | AVOID | EXIT / REDUCE | INSUFFICIENT DATA
  cap check: evidence_pack.py --check-verdict exit code
  conditions to enter / wait / exit / avoid: <observable conditions>
  manual checklist (BUY CANDIDATE): <scanner checklist codes>
This is research, not an order. User approval is required for any trade.
```

## Strategy Review

```
# Strategy Council: <decision id>
Rule text (RB lines, verbatim) | current implementation (function) | alternatives | gate outcomes and tests that change
Specialist positions | Devil's Advocate | evidence still needed
Chair Verification: every quoted RB line and cited decision checked against the source file
Recommendation: <only if the Rulebook supports it; else USER DECISION REQUIRED>. Status stays PROPOSED until approved.
```

## Combined Review

```
# Combined Council: <subject>
Part 1, Software correctness (Engineering Council): findings, tests, approval status
Part 2, Strategy validity (Trading Product Council): methodology findings, assumptions, verdict or readiness
Part 3, Interaction: where a software defect invalidates a strategy conclusion, or a strategy assumption makes correct code meaningless
Chair Verification: one table covering both parts
Overall: separate statuses, never merged into one "approved". Software APPROVED + strategy UNVALIDATED is a valid outcome.
```
