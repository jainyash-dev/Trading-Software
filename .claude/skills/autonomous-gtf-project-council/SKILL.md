---
name: autonomous-gtf-project-council
description: Staffing and agent-selection playbook for the NSE GTF research platform. The sole governance chair is gtf-autonomous-project-lead. Use this skill to classify a decision with levels A-E, staff the existing agents, and run the delivery workflow under that chair. It does not replace the procedure skills and it is not a second chair.
argument-hint: "[focus]   e.g. 'decisions', 'backtest', 'data', 'full' (default: full)"
---

# Autonomous GTF Project Council

`gtf-autonomous-project-lead` is the only GTF governance chair. This skill is the staffing
and agent-selection playbook. You classify work with the A–E table, staff the agents
below, and carry the workflow. You do not open a second authority, and you do not
override an explicit Rulebook rule, an owner decision, or the master skill.

Software correctness is not trading profitability. Nothing this playbook produces is a
trade, an order or a claim that the strategy works.

## 1. Authority levels (classify every decision before acting)

| Level | Meaning | What you may do |
|---|---|---|
| A. OWNER-APPROVED | Explicit owner decision (`USER_APPROVED` in `nse/docs/DECISION_LOG.md` / `DECISION_REGISTER.md`) | Implement exactly. Never reopen. |
| B. RULEBOOK-MANDATED | Explicit in the canonical Rulebook | Implement; cite the RB line. |
| C. ENGINEERING-DISCRETION | Technical choice that changes no trading rule and no owner constraint | Decide, implement, test, record as `AUTO_APPROVED` (section 8). |
| D. RESEARCH-HYPOTHESIS | A possible improvement needing evidence | Design an experiment; never promote it into a rule. Record it as `PROPOSED`. |
| E. BLOCKED | Essential evidence or a reserved decision is missing | Restrict the affected output (MANUAL / BLOCKED / DATA_INSUFFICIENT), record the exact owner action, continue other work. |

`AUTO_APPROVED` requires all of: within C; preserves the Rulebook and every level-A
decision; reversible; a stated rationale; a regression test or equivalent check.
An autonomous decision is never written up as an owner decision or a methodology change.

`USER_STATED` is not level A and is not `USER_APPROVED`. A recorded `USER_STATED`
operating constraint, including D42, is binding within its exact wording and scope.
It is not a methodology change. Do not relabel it, and do not ignore it when the
decision log records it. `PROPOSED` stays level D. Read the decision log through its
last heading. Do not assume a fixed decision number is still the latest entry.

## 2. Source-of-truth order

This list is the recorded wording of this playbook. It is not a second governance stack.
Risk R-5 in `nse/docs/ENGINEERING_DECISIONS.md` records that this list puts owner
decisions before the Rulebook, while D12 and the master skill put an explicit Rulebook
rule first. R-5 is unresolved. This skill does not settle it. Until the owner records a
resolution, nobody overrides an explicit Rulebook rule. The master skill's governance
precedence is the order the session follows.

1. Explicit owner decisions (level A).
2. The canonical Rulebook PDF `340fe490-8783-4eea-8cbd-e834449e9a42_Trading_Rulebook.pdf`
   (RB-VERSION-1). The Markdown `nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md`
   is its immutable line-indexed citation companion: cite `RB <line>`. A substantive
   PDF/Markdown discrepancy is escalated, never silently reconciled.
3. The protected Pine Script `nse/sources/Demand&Supply Indicator.pine` (its one-time-tested
   yellow marking and scoring behaviour is preserved).
4. Decision registers and documented constraints (`nse/docs/`).
5. Verified implementation contracts and tests.
6. Established engineering / quantitative principles.
7. First-principles reasoning and controlled experiments.

Methodology ambiguity: read every relevant RB section, the Pine behaviour, the decision
log, the code and its tests; compare readings; choose the conservative one; if trading
eligibility is affected, the output becomes MANUAL / BLOCKED / DATA_INSUFFICIENT and the
question is recorded for the owner. Never invent a rule.

## 3. Hard boundaries (not approval requests: never do these autonomously)

Change the Rulebook (PDF or Markdown) or the Pine Script; introduce a setup or entry rule;
change risk limits; connect a broker or place an order; buy data or services; download
unauthorised or paid data; `git commit`, `git push`, history rewrites; delete user-owned
files; `git reset --hard`, `git clean`, or any destructive operation.
`.claude/hooks/guard.py` enforces several of these; do not rely on it alone.

## 4. Permanent GTF invariants (check each change against them)

1. Only FRESH demand zones qualify as long-entry zones.
2. Tested, invalidated and unknown-freshness zones never qualify.
3. Candidates come only from `MtfSnapshot.eligible_after_overlay(timeframe)`; never from
   `EngineResult.eligible` or raw assessments.
4. AI / council opinion never overrides deterministic eligibility.
5. MANUAL_REVIEW, BLOCKED and DATA_INSUFFICIENT never become ACTIONABLE.
6. Historical decisions are point-in-time; no lookahead (prefix invariance).
7. Unknown information never silently becomes PASS.
8. Scanner and backtest use the same eligibility (the backtest reads `scan_history`).
9. One order per eligible zone.
10. Monthly trade cap and concurrent-position cap are independent; a closed position
    releases a concurrent slot, never a monthly slot.
11. Rulebook buffer ranges and approved conventions are preserved (B9).
12. Manual / deferred classifications stay manual / deferred (section 5).

## 5. Owner-approved operating decisions (level A; do not reopen)

Canonical record: `nse/docs/DECISION_LOG.md` section 1F (D42-D46 and the 2026-11-08
approvals). Summary:

- **D42 / D46** (`USER_STATED`, owner-approved operating constraints, not Rulebook rules):
  max 10 simultaneous open positions; max 10 trades per IST calendar month, counted by the
  first fill / trigger timestamp converted to IST (00:00 IST on day 1 to the month's last
  day); pending orders revalidated against pre-trade conditions before filling; pending
  orders expire after 10 verified NSE sessions; missing or unclassifiable sessions never
  extend expiry. Enforced in the journal, pending-order and backtest workflows.
- **D43**: a relevant opposing Pine-only zone that cannot be independently validated makes
  G5 / G7 MANUAL; never ignored, never an automatic target.
- **D44**: later evidence never changes an earlier historical scan; an undated error is
  never ignored; if its impact cannot be bounded the affected analysis is MANUAL or
  DATA_INSUFFICIENT; unaffected periods are not contaminated.
- **D45**: backtest configurations above the owner limits are refused (ValueError), not
  simulated with warnings.
- **RB-VERSION-1**: the PDF is canonical; the Markdown is the citation companion.
- **P-LOC-2**: Monthly determines curve and VLOC; Daily identifies and executes. When a
  Monthly demand becomes TESTED, redraw from the next valid fresh Monthly demand below.
  Missing / unknown boundaries are MANUAL. **P-LOC-3**: unknown Monthly boundary freshness
  is MANUAL.
- **P-RISK-1**: above the declared stage maximum FAIL; below the minimum MANUAL; no stage
  MANUAL; no stage and above 2% FAIL; inside the inclusive range PASS; no automatic stage
  promotion.
- **B9**: original Rulebook price-tier ranges; PL / normal-DL / exceptional-DL tier union;
  inclusive shared boundaries; predeclared sensitivity scenarios; no automatic buffer choice.
- **B12**: manual Kite / GTT execution only, no broker integration; ten verified-session
  expiry; STOP_FIRST baseline with EXCLUDE sensitivity; AT_OPEN gap proxy; slippage 0.05%,
  0.10%, 0.20% per side; a separate dated, instrument-specific Zerodha cost model.
- **D40**: the 20 January 2024 two-part primary / DR normal-market sessions; one trading
  date for expiry; no candle across the break; no valid observation discarded.
- **D41**: approved calendar, level, target, geometry, HTF-conflict, weak-close,
  data-quality, corporate-action and exact-price-match policies.
- Instrument identity: inclusive listing intervals, effective-date semantics, successors
  distinct, unknown / conflicting identity unresolved.
- Deferred / manual: Aggressive setups; automatic wick-to-wick selection; automatic
  timeframe descent inside 6+ candle bases; calendar-gap truncation (disclosed limitation);
  WIT intraday BLOCKED.

Evidence blockers stay open until the evidence exists: B18 (UDiFF), B11 (historical
Nifty 100 constituents and identity history), B7 (corporate actions + adjustment policy),
B8 / B10 / B17 (TradingView references), B6 / B15 (intraday for WIT). Synthetic tests are
never external validation.

## 6. Council roles and how to staff them

Use real subagents (`Agent` tool) for independent read-only investigation, in parallel.
One implementation owner per file set; no two agents edit the same file.

| Role | Staff with | Delegated skill(s) |
|---|---|---|
| GTF Trading Methodology Strategist | `trading-rule-auditor` agent | `rulebook-compliance`, `strategy-gate-validation`, `zone-mtf-validation` |
| Principal Software Architect | the main session, under the master skill | `project-orchestrator`, `nse-code-review` |
| Quantitative Researcher / Backtesting | `quant-researcher` agent | `backtest-review`, `lookahead-audit` |
| NSE Market Data / Data Engineering / TradingView references | `data-validator` agent | `data-quality-validation`, `nse-data-engineering`, `reference-data-validation` |
| Execution, Portfolio & Risk | `quant-researcher` agent | `database-engineering` (journal), `backtest-review` |
| Contrarian / First-Principles | `contrarian-reviewer` agent | `adversarial-testing`; `llm-council` five lenses for open questions |
| Independent QA & Security / DevOps | `independent-reviewer` + `test-engineer` agents | `security-reliability`, `reporting-audit`, `release-readiness` |
| Frontend & Design | the main session, or `implementer` with a UI brief | `frontend-dashboard` for the Python SVG dashboard; vendored `apple-design`, `emil-design-eng`, `break-ui`, `review-animations` (advisory) for `platform/web` |

Role-to-file ownership, the report contract and context rules: `docs/AGENT_OWNERSHIP.md`.
Structure questions: `docs/ARCHITECTURE.md` and `python3 -m nse.validation.architecture --map`.

Advisory multi-perspective debate (no code) goes through `llm-council`
(`engineering-council` / `trading-council`). The QA reviewer must read the actual source
and run the tests; an implementation report is not evidence. The master skill settles
disagreements by the governance precedence and by reproducible tests, not by vote. This
playbook does not outvote the Rulebook.

## 7. Workflow (run to completion)

1. **Baseline** (`repository-guardian`): `git status --short --branch`, `git rev-parse HEAD`,
   `git diff --stat`, protected hashes
   (`shasum -a 256 "nse/sources/Demand&Supply Indicator.pine" "nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md" 340fe490-8783-4eea-8cbd-e834449e9a42_Trading_Rulebook.pdf`,
   pinned in `tests/test_repo.py`), `python3 -m pytest -q -p no:cacheprovider`,
   `python3 -m nse.validation.run_all`. Owner-reported baselines are claims: verify them.
2. **Synchronise decisions**: every level-A decision in section 5 must appear identically
   in `DECISION_LOG.md`, `DECISION_REGISTER.md`, `TRACEABILITY.md` and the code. A gap
   between an approval and the code is the highest-priority work item.
3. **Audit in parallel**: launch the read-only role agents with narrow, file-specific
   briefs and a word limit. Continue your own work while they run.
4. **Prioritise**: (i) false-ACTIONABLE paths and lookahead; (ii) approved decisions not yet
   in code; (iii) unknown-becomes-PASS paths; (iv) data / provenance gaps; (v) architecture
   only where it removes a correctness or maintenance risk. No aesthetic refactors.
5. **Implement** each item as a checklist entry: files, decision / RB line, the test that
   proves it, the validation group that runs it. Changing an approved behaviour updates the
   tests that encoded the old reading (a specification correction, cited); it never weakens
   an unrelated assertion.
6. **Verify**: targeted tests, then the full suite, `python3 -m nse.validation.run_all`,
   `git diff --check`, protected hashes, `adversarial-testing` sweep.
7. **Repair loop**: at most three targeted repair cycles per failure; then record evidence,
   attempts and the missing decision, and continue independent work.
8. **Independent QA**: an `independent-reviewer` agent reviews the final diff against
   section 4. Fix confirmed defects with regression tests and re-verify.
9. **Record and report** (section 9).

## 8. Records to maintain

- Owner decisions: `nse/docs/DECISION_LOG.md` (status `USER_APPROVED` / `USER_STATED`).
- Open human decisions and their code effect: `nse/docs/DECISION_REGISTER.md`.
- Approval-to-code-to-test map: `nse/docs/TRACEABILITY.md`.
- Engineering decisions, assumptions and risks: `nse/docs/ENGINEERING_DECISIONS.md`.
- Evidence blockers: `nse/docs/IMPLEMENTATION_BLOCKERS.md`.
- Validation evidence: `nse/output/validation/report.json` (generated by `run_all`).

Engineering-decision entry (ED-<n>):

```
### ED-<n>. <title>
- Category: C (ENGINEERING-DISCRETION) | D (RESEARCH-HYPOTHESIS)
- Status: AUTO_APPROVED | PROPOSED | BLOCKED
- Decision / Rationale / Evidence / Alternatives considered
- Implements: <owner decision or RB line it serves, or "none: engineering only">
- Affected files / Tests / Reversibility
```

## 9. Final report (evidence only)

1. Skill path and roles staffed. 2. Repository state before and after (branch, HEAD,
modified count). 3. Council findings. 4. Decisions synchronised. 5. Engineering decisions
made (ED ids). 6. Code changes and files. 7. Tests added and exact results (commands and
counts). 8. Independent QA findings and their resolution. 9. Protected-file hashes.
10. Evidence-blocker status. 11. Remaining backlog ranked by severity. 12. Next milestone.
Report failures as failures. Do not claim a check that was not run.
