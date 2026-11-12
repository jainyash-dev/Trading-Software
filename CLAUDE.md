# CLAUDE.md

Project instructions for Claude Code in this repository. Keep this file short; detail
lives in the documents it points to.

## What this is

An NSE (India) demand-and-supply swing-trading **research and decision-support** system
built on the owner's GTF methodology (Trading Rulebook). It ingests local NSE end-of-day
files, detects zones on every timeframe, enforces freshness through the MTF overlay,
applies gates G0-G8, explains every result and replays any historical decision. It is
not a trading bot: nothing places an order, connects to a broker or approves a trade.

The owner's full master implementation prompt (formerly this file) is binding and kept
verbatim in [docs/owner/MASTER_IMPLEMENTATION_PROMPT.md](docs/owner/MASTER_IMPLEMENTATION_PROMPT.md).
Read the sections relevant to your task before substantial work; section numbers cited
elsewhere (for example "section 21.11") refer to it.

The root `trader-*` folders are the separate, legacy US day-trading skill pack this repo
was forked from. Leave them alone unless a task names them.

## Where things are

| Path | What |
|---|---|
| `nse/zone-engine/`, `nse/mtf-freshness/` | Zone Engine and MTF freshness overlay (the eligibility authority) |
| `nse/eod/`, `nse/calendar/` | NSE bhavcopy loader, replay, reference comparison, trading calendar |
| `nse/research/` | Pipeline: data, methodology (G0-G8), scanner, reports, backtest, risk, store, CLI |
| `nse/validation/` | `run_all` (single validation command), architecture and docs-health checks |
| `nse/docs/` | Specification, decision log and register, blockers, traceability, engineering decisions |
| `docs/` | Architecture, roadmap, milestones, runbook, skills registry, debt, scorecard, agents |
| `.claude/` | Project skills, agents, hooks; `vendored-skills.json` pins third-party skills |
| `tests/` | unittest modules, each assigned to a `run_all` group |

Architecture and layer rules: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Commands, setup and troubleshooting: [docs/OPERATIONS_RUNBOOK.md](docs/OPERATIONS_RUNBOOK.md).

## Commands (run from the repository root)

```
python3 -m nse.validation.run_all                    # everything: tests, repo, data, lint, readiness
python3 -m nse.validation.run_all --list             # groups; then --group <name> for a targeted run
python3 -m nse.validation.architecture               # layer, cycle, single-definition, safety rules
python3 -m nse.validation.docs_health                # stale links and commands in the docs
python3 -m pytest -q -p no:cacheprovider             # the same tests through pytest
python3 -m nse.research.cli --help                   # scanner, reports, backtest, store, dashboard
```

Python 3.10+; `nse/` uses the standard library only (rule A5). Dev tools are optional.

## Authority (highest first; D12, rulebook-strict)

This is the same order as `gtf-autonomous-project-lead` sections 3 and 6. A lower item
does not override a higher one.

1. Explicit rules of the canonical Rulebook PDF (root); cite its Markdown companion in
   `nse/sources/` as `RB <line>`. An explicit Rulebook rule is not overridden by an owner
   decision, this file, a skill, or current code. A change to the Rulebook follows the
   formal methodology-change process.
2. Owner decisions in `nse/docs/DECISION_LOG.md`, subject to the Rulebook. Read the log
   through its last heading and apply that entry's status and scope. Do not assume a
   fixed decision number is current. `USER_APPROVED` and `USER_STATED` are not
   interchangeable. `USER_STATED` is a recorded operating constraint within its wording.
   D42 stays `USER_STATED`. `PROPOSED` is not a rule. None of these overrides item 1.
3. The Pine Script in `nse/sources/` where the Rulebook is silent and nothing conflicts.
   Pine does not override the Rulebook.
4. `gtf-autonomous-project-lead`, the only GTF governance chair. It cannot override items 1-3.
5. The active GTF specialist.
6. The procedure skill for the check.
7. Advisory councils (`llm-council`, `engineering-council`, `trading-council`) and their
   recommendations. A recommendation is not an owner decision and does not decide eligibility.

`autonomous-gtf-project-council` is the staffing playbook. It is not a second chair.
Decision registers and `nse/docs/ENGINEERING_DECISIONS.md` restate or record implementation.
They do not outrank items 1-3. An `ED-<n>` entry is never an owner decision. Current code
describes what the software does today. A defect is not an approved methodology.

The council skill's section 2 lists owner decisions before the Rulebook. That wording
difference is risk R-5 in `nse/docs/ENGINEERING_DECISIONS.md`. R-5 is unresolved.
Until the owner records a resolution, nobody overrides an explicit Rulebook rule.
GTF phase Pn is not Product Prompt n.

Never invent or silently change a trading rule. An ambiguity that affects eligibility
makes the output MANUAL / BLOCKED / DATA_INSUFFICIENT and is recorded for the owner.

## Trading invariants (tests enforce them; never weaken them)

- Only fresh, unbreached demand zones can qualify; tested, invalidated and unknown-freshness zones never do.
- Candidates come only from `MtfSnapshot.eligible_after_overlay(timeframe)` (and
  `manual_review_after_overlay`), never from `EngineResult.eligible` or raw assessments.
- One qualification pathway (`qualification` via `scanner`); reports, replay and backtest reuse it.
- Status is the most restrictive gate outcome (`models.derive_status`). MANUAL_REVIEW, BLOCKED
  and DATA_INSUFFICIENT never become actionable; the best status still has manual checks pending.
- Unknown information never becomes PASS. Historical decisions are point-in-time (prefix invariance).
- Owner limits: at most 10 trades per IST calendar month and 10 simultaneous positions,
  independent caps. WIT (75/125-minute) stays BLOCKED. No broker integration or live execution.

## Repository safety

- Never modify `nse/sources/` (Pine Script, Rulebook Markdown) or the root Rulebook PDF; their
  hashes are pinned. Never edit vendored skills; re-vendor them (`docs/SKILLS_REGISTRY.md`).
- Never commit, push, stage, stash, reset, clean or rewrite history without explicit owner
  authorisation. `.claude/hooks/guard.py` blocks the recognisable forms; it is not a sandbox.
- Treat uncommitted and untracked files as the owner's work. Inspect before overwriting.
- No network access from `nse/`, no paid data or services, no credentials in the repo.

## Always binding (from the master prompt; read the section when it applies)

- Section 4: no destructive data cleanup; inspect untracked files before overwriting them.
- Section 8 (Layer B): never treat today's constituents as the historical universe.
- Section 13 (Backtesting limitations): never report a win rate, expectancy, drawdown or
  profitability figure without a real dataset, a defined execution model and reproducible results.
- Section 16.6 and 21.16: never delete, skip or weaken a test to get green; never call
  mocked or synthetic tests integration-tested or validated; never invent test output.
- Section 21.17: stop and ask the owner only for trading-rule choices, strategy or risk
  changes, credentials or private data, paid services, destructive operations, git
  commits or pushes, broker or live execution, and claims needing unavailable evidence.
- Section 20 (with the council skill's section 9): the final report format for substantial work.

## How agents work here

- Substantial work: `gtf-autonomous-project-lead` is the governance chair (precedence,
  phase crosswalk, which specialist and which procedure skills load).
  `autonomous-gtf-project-council` staffs agents and classifies decisions A–E. It is not
  a second chair. `project-orchestrator` is the validation checklist for `nse/` and `tests/`.
- Pick the smallest set of skills for the task; agent roles and file ownership are in
  [docs/AGENT_OWNERSHIP.md](docs/AGENT_OWNERSHIP.md). One owner per file at a time.
- Separate facts, assumptions, recommendations and owner decisions in every report.
- Done means: targeted tests, then `python3 -m nse.validation.run_all`, `git diff --check`,
  protected hashes unchanged, and an honest report of what ran. Synthetic tests are not
  external validation; passing tests are not evidence of profitability.
- Repair loop: at most three targeted attempts per failure, then record the evidence and move on.
