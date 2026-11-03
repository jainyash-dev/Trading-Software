---
name: project-orchestrator
description: Drive a substantial change to the NSE demand-and-supply research system (nse/) from request to verified result. Use for any multi-file feature, fix or refactor in nse/ or tests/, or when asked to "implement", "build", "finish" or "fix" part of the research pipeline. Picks the smallest set of the other project skills and runs the validation workflow until it passes or a genuine blocker is reached.
---

# Project orchestrator

You carry a change through to evidence. You do not stop at a plan.

## 1. Read first (only what the task touches)

- `CLAUDE.md` (project instructions) and `nse/docs/RESEARCH_PIPELINE.md` (architecture, commands).
- `nse/docs/IMPLEMENTATION_SPECIFICATION.md`: sections 4-8 for trading logic; section 8 lists G0-G8.
- `nse/docs/DECISION_LOG.md`: approved decisions (D1-D39); D40 is PROPOSED.
- `nse/docs/IMPLEMENTATION_BLOCKERS.md`: open items. Never resolve one by assumption.
- `nse/docs/TRACEABILITY.md`: rule to code to test mapping.

## 2. Baseline (run the repository-guardian skill)

```
git status --short --branch
git diff --stat
python3 -m nse.validation.run_all --no-data
```
Record failures that exist before you start. They are not yours to hide.

## 3. Plan as a checklist with acceptance criteria

Each task gets: the files touched, the rule or decision it implements (RB line, D number,
spec section), the test that proves it, and the validation group that runs that test.
Keep the checklist in the conversation (TodoWrite or a list) and tick items only when the
evidence exists.

## 4. Implement

- One pathway: execution zones come only from `MtfSnapshot.eligible_after_overlay` and
  `manual_review_after_overlay`; gates live only in `nse/research/qualification.py`.
- Unknown is never PASS. An unresolved rule becomes MANUAL or DATA_INSUFFICIENT with a reason.
- Never edit `nse/sources/` (the guard hook blocks it). Never invent a threshold.

## 5. Verify, in this order

```
python3 -m nse.validation.run_all --group <the group you touched>
python3 -m nse.validation.run_all --no-data      # every required group
python3 -m nse.validation.run_all                # plus local data and reference checks
```
Use the skills that match the change: strategy-gate-validation (gates), zone-mtf-validation
(engine or overlay), lookahead-audit (anything time-related), reporting-audit (exports),
adversarial-testing (any change that could create a false candidate).

## 6. Repair loop (bounded)

For each failure: capture the exact output; classify it as a code defect, a wrong test
assumption, a missing prerequisite, or an unresolved specification. Fix only the first two
with evidence, add a regression test for a confirmed defect, then re-run the failing test,
its group, and the whole required suite. **At most three repair cycles per failure.** After
that, stop changing code for it: record the evidence, the attempts and the exact decision or
input needed, and carry on with independent work.

Never delete or weaken a test to get green, never change a trading rule to make a test
pass, never report a skipped check as passed.

## 7. Finish

Run release-readiness, then repository-guardian's final check. Report: what changed, the
exact commands and their real counts, what remains blocked and why, and what the user must
decide. Do not stage or commit unless the user explicitly authorised it.
