# Agent roles, ownership and collaboration rules

> `gtf-autonomous-project-lead` is the only GTF governance chair. The
> `autonomous-gtf-project-council` skill is the staffing and agent-selection playbook
> (decision levels A–E, roles, workflow). It is not a second chair. This page says who
> does what, who may edit which files, what context each role loads, and what every
> agent must report. GTF phase Pn is not Product Prompt n.

## 1. Source-of-truth hierarchy

This is the same order as `gtf-autonomous-project-lead` sections 3 and 6.

1. Explicit rules of the canonical Rulebook PDF (root), cited through `nse/sources/Trading Rulebook ....md` as `RB <line>` (D12, rulebook-strict). An explicit Rulebook rule is not overridden by an owner decision or by current code.
2. Owner decisions in `nse/docs/DECISION_LOG.md`, subject to the Rulebook. Read the log through its last heading. Do not assume a fixed decision number is current. `USER_APPROVED` applies within its recorded scope. `USER_STATED` is a recorded operating constraint within its wording and is not interchangeable with `USER_APPROVED`. D42 stays `USER_STATED`. `PROPOSED` is not a rule. (The council playbook lists owner decisions first; see risk R-5 in `nse/docs/ENGINEERING_DECISIONS.md`. R-5 is unresolved. An explicit Rulebook rule still leads.)
3. The Pine Script `nse/sources/Demand&Supply Indicator.pine` where the Rulebook is silent and nothing conflicts. Pine does not override the Rulebook.
4. `gtf-autonomous-project-lead`, the only GTF governance chair. It cannot override items 1-3.
5. The active GTF specialist.
6. The procedure skill for the check.
7. Advisory councils and their recommendations. A recommendation is not an owner decision and does not decide eligibility.

`nse/docs/IMPLEMENTATION_SPECIFICATION.md`, `DECISION_REGISTER.md` and `IMPLEMENTATION_BLOCKERS.md` restate or record these constraints. They do not outrank items 1-3. Where a register and the decision log disagree, the log controls. Source code and tests describe what the system does today. A defect is not methodology. `docs/ARCHITECTURE.md` and this page are navigation. A lower source never overrides a higher one. A conflict is recorded, not settled by an agent.

## 2. Roles

| Council role | Staffed by | Authority | Edits |
|---|---|---|---|
| Chairman / CTO / Architecture | main session, running `gtf-autonomous-project-lead` | decides level-C engineering choices, assigns work, integrates, settles disagreements by the governance precedence | any non-protected file it assigns to itself |
| GTF Methodology Strategist | `trading-rule-auditor` agent | audits rules against sources; never settles a conflict | `nse/docs/TRACEABILITY.md`, blocker list only |
| Implementation | `implementer` agent | one bounded task with acceptance criteria | only the files in its brief |
| NSE Data Engineer / TradingView references | `data-validator` agent | judges data trust; never modifies data | none |
| Quantitative Researcher / Backtesting / Risk | `quant-researcher` agent | reviews backtests, costs, caps, sizing; never claims profitability | none |
| Contrarian / First Principles | `contrarian-reviewer` agent | argues against proposals and diffs | none |
| Independent QA / Security / DevOps | `independent-reviewer` agent | reviews finished changes; runs tests | none |
| Test engineering | `test-engineer` agent | writes regression and adversarial tests | `tests/` files in its brief, `run_all` group registration |
| Frontend & Design | the main session or `implementer` with a UI brief. `frontend-dashboard` governs only `nse/research/dashboard.py` and `decision_replay.py`. Vendored design skills advise `platform/web` | interface quality; never implements trading logic in presentation code (rule A2) | `nse/research/dashboard.py` and its tests for the Python dashboard. `platform/web` is a separate client |

No agent may: change the Rulebook or the Pine Script, change an owner decision, introduce a
trading rule, change risk limits, commit, push, stage, reset, clean, connect a broker,
download paid or unauthorised data.

## 3. Ownership of shared files

One owner per file at a time. Before delegating, the Chair lists the files each agent may
edit; two concurrent agents never share a file. Files with standing owners:

| Files | Owner | Independent verification required |
|---|---|---|
| `nse/zone-engine/`, `nse/mtf-freshness/` | Chair (changes need a `zone-mtf-validation` run) | yes: `trading-rule-auditor` + `independent-reviewer` |
| `nse/research/qualification.py`, `structure.py`, `trend.py`, `levels.py`, `topdown.py`, `confluence.py`, `models.py` | Chair | yes: `trading-rule-auditor` + `contrarian-reviewer` |
| `nse/research/backtest.py`, `execution_policy.py`, `risk.py`, `store.py` | Chair | yes: `quant-researcher` |
| `nse/docs/DECISION_LOG.md`, `DECISION_REGISTER.md` | Chair, recording owner decisions only | owner wording quoted |
| `nse/docs/TRACEABILITY.md` | `trading-rule-auditor` | - |
| `nse/docs/ENGINEERING_DECISIONS.md`, `docs/*.md` | Chair | - |
| `.claude/` (skills, agents, hooks, settings) | Chair | `run_all --group hooks --group council` |
| `.claude/skills/<vendored>/` | nobody (upstream, hash-pinned) | re-vendor only |
| `nse/sources/`, Rulebook PDF, `docs/owner/` | owner only (hash-pinned) | - |

Critical trading and risk changes always get an independent reviewer who did not write them.

## 4. Context policy (load what the task needs)

| Task | Read first |
|---|---|
| any task | `CLAUDE.md`, `gtf-autonomous-project-lead` when the task is GTF work, `git status --short`, the files to be touched and their tests |
| gate / zone / freshness logic | the relevant spec section, the RB lines cited in code, `DECISION_LOG.md` 1F, `TRACEABILITY.md` rows |
| data | `nse/docs/DATA_REQUIREMENTS.md`, `EOD_FORMAT_EVIDENCE.md`, `REAL_DATA_READINESS.md` |
| backtest / risk | `ENGINEERING_DECISIONS.md` ED-1..ED-13, D42-D46 in the decision log |
| structure | `docs/ARCHITECTURE.md`, `python3 -m nse.validation.architecture --map` |
| methodology question | the Rulebook sections themselves, not summaries |

Do not load every document by default. The owner's master prompt
(`docs/owner/MASTER_IMPLEMENTATION_PROMPT.md`) is read section by section when a task
cites it.

## 5. Report contract (every agent, every task)

- Files changed (or "none").
- Findings, each with file:line and a concrete scenario where relevant.
- Tests run: exact commands and counts; failures reported as failures.
- Unresolved risks and the decision or evidence that would resolve them.
- Every statement labelled **FACT** (reproduced or read in source), **ASSUMPTION**,
  **RECOMMENDATION** or **OWNER DECISION** (with its D / ED id).

An implementation report is not evidence: the reviewer reads the source and runs the tests.

## 6. Desktop platform

Product Prompt 00 adds the GTF Trading Intelligence Platform around this research system.
Path locks for `platform/`, the product documents, and concurrent Prompt 01 / 02 work are
in [docs/architecture/AGENT_OWNERSHIP.md](architecture/AGENT_OWNERSHIP.md). An `nse/` path
is still governed by the tables above.
