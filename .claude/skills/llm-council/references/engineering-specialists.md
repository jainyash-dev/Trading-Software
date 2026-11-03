# Engineering Council: specialist briefs (Mode A)

Each specialist runs in its own subagent with the brief below. It gets the request, the scope
(files, diff or proposal), and this file. It does not see other specialists' findings.

**Subagents cannot invoke skills** (the project agents have no Skill tool). The coordinator's
prompt must name the files, and the specialist must read them before working:
`.claude/skills/<skill>/SKILL.md` for each skill in the "Reads skill file" column.

| Specialist | Agent (existing) | Reads skill file |
|---|---|---|
| A. Architecture Reviewer | `independent-reviewer` | `project-orchestrator` (module map) |
| B. Code Quality Reviewer | `independent-reviewer` | `nse-code-review` |
| C. Data Integrity Reviewer | `data-validator` | `data-quality-validation`, `lookahead-audit` |
| D. Security Reviewer | `independent-reviewer` | `repository-guardian` |
| E. Adversarial Testing Reviewer | `independent-reviewer` (proposes tests; `test-engineer` writes them only when the user asks for changes) | `adversarial-testing`, `zone-mtf-validation`, `strategy-gate-validation` |

All are read-only in council mode. Every council specialist runs as an agent without Edit,
Write or MultiEdit (`independent-reviewer`, `data-validator`); `tests/test_llm_council.py`
enforces this. A specialist may run tests and read-only commands. It edits nothing, stages
nothing and commits nothing.

## Output contract (every engineering specialist)

```
SPECIALIST: <A-E name>
SCOPE REVIEWED: <files / diff / proposal, with paths>
COMMANDS RUN: <exact commands and their real result lines, or "none">
FINDINGS:
  - id, severity (CRITICAL | HIGH | MEDIUM | LOW | INFO), file:line, claim,
    evidence (quote, test output or reproduction), confidence (CONFIRMED | PLAUSIBLE | QUESTION)
REQUIRED TESTS: <failing scenario to add, per finding>
ASSUMPTIONS AND MISSING EVIDENCE: <explicit list>
VERDICT FOR THIS AREA: APPROVE | APPROVE WITH CONDITIONS | REJECT | CANNOT ASSESS (why)
WHAT WOULD CHANGE MY VERDICT: <specific evidence>
```

Severity means:
- **CRITICAL:** a path to a false candidate, an overlay bypass, lookahead, a protected-file or
  history-destroying operation, or a credential or broker exposure.
- **HIGH:** a wrong result or lost restriction under realistic input.
- **MEDIUM:** a fragile or untested path.
- **LOW / INFO:** maintainability.

A finding with no reproduction or exact quote is at most PLAUSIBLE.

## A. Architecture Reviewer
- **Scope:** boundaries and dependencies between `nse/zone-engine`, `nse/mtf-freshness`,
  `nse/eod`, `nse/calendar`, `nse/research`, `nse/validation`; single sources of truth
  (zone detection, scoring, overlay eligibility, qualification, report schema).
- **Inspect:** imports (`nse/research/deps.py` loads each module once); new modules against
  `nse/docs/RESEARCH_PIPELINE.md` section 1; duplicated business logic; speculative layers.
- **Must flag:**
  - a second eligibility path beside `qualification.evaluate_symbol`;
  - a module that recomputes freshness;
  - a network import;
  - a new dependency outside the standard library.
- **Evidence commands:** `python3 -m nse.validation.run_all --group repository`;
  `grep -rn "run_engine(\|\.eligible\b" nse/research`.

## B. Code Quality Reviewer
- **Scope:** correctness of the changed lines and their callers; interfaces and types;
  error handling (fail closed: unknown never becomes PASS); duplication; regression risk.
- **Inspect:** the diff (`git diff`, `git status --short`), the surrounding functions, and
  the tests that cover them (name each). A test that cannot fail is a finding.
- **Evidence commands:** `python3 -m nse.validation.run_all --group <group of the changed module>`;
  `cd tests && python3 -B -m unittest -v <module>`.

## C. Data Integrity Reviewer
- **Scope:** lookahead (as_of cut, in-progress periods, findings dated after as_of),
  survivorship (universe per date), leakage (outcomes feeding signals), missing sessions
  (calendar, D27/D37), corporate actions (B7; PREVCLOSE discontinuities), point-in-time
  correctness of every input, and provenance (manifest SHA-256).
- **Inspect:** `nse/mtf-freshness/mtf_freshness.py replay`, `nse/research/scanner.py`,
  `marketdata.py`, `backtest.py`, `inventory.py`; any code that reads "the last" value of a
  series.
- **Evidence commands:**
  - `python3 -m nse.validation.run_all --group lookahead --group data --group data_readiness`
  - `python3 -m nse.research.cli inventory --as-of <date>`
- **Must flag:** any read of data dated after the decision time; a gap treated as no
  activity; unadjusted prices across a price-scale event used without a restriction.

## D. Security Reviewer
- **Scope:**
  - secrets and credentials;
  - unauthorised operations (git writes, destructive git, recursive deletes);
  - protected files (`nse/sources/*`, pinned in `nse/validation/protected.py`);
  - external data access (no network code under `nse/`, D31);
  - broker restrictions (D10, D17, D32).
- **Inspect:** the diff for `subprocess`, `os.remove`, `shutil.rmtree`, network modules,
  `kiteconnect`, order verbs, `.env`, keys. Check proposals against `.claude/hooks/guard.py`.
- **Evidence commands:**
  - `git status --short`, `git diff --cached --name-only` (must be empty);
  - `python3 -m nse.validation.run_all --group repository` (compares the protected sources
    with the SHA-256 pins in `nse/validation/protected.py`; do not hash or print them by hand);
  - `python3 -m nse.validation.run_all --group hooks`.
- **Must reject:**
  - any proposal to reset, clean, stash, restore, rebase, amend, force-push or commit
    without authorisation;
  - any edit to the Rulebook or Pine Script;
  - any broker or order call.

## E. Adversarial Testing Reviewer
- **Scope:**
  - edge cases;
  - invalid inputs (non-finite or non-positive prices, inverted geometry, duplicates,
    out-of-order dates);
  - fail-closed behaviour;
  - attempts to bypass deterministic eligibility: engine-eligible but overlay-tested zones,
    a later gate overriding G0, manual items lost in export.
- **Method:** state the invariant, build the smallest scenario that would break it, and say
  which existing test catches it (name it) or that none does. For a claimed safeguard, ask
  for or run a mutation: switch the check off and show the outcome changes (pattern:
  `TestsExerciseTheirPath` in `tests/test_research_adversarial.py`).
- **Evidence commands:** `python3 -m nse.validation.run_all --group adversarial --group strategy_gates --group integration`.
