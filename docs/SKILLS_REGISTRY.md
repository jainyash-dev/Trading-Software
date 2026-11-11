# Skills and tools registry

> Every external skill, tool and repository considered for this project, with the
> decision and its evidence. Evaluated 2026-11-08 by shallow read-only clones into the
> session scratchpad (no downloaded script was executed). Our own skills are listed in
> section 4. Vendored files are pinned in `.claude/vendored-skills.json` and checked by
> `tests/test_claude_hooks.py`; never edit them, re-vendor instead (section 5).

Status: **ACTIVE** (installed and in use), **OPTIONAL** (documented; install on demand),
**REFERENCE** (ideas used, nothing installed), **REJECTED**.

## 1. External skills

| Name | Upstream | Version / commit | License | Status | Where | Purpose and reason |
|---|---|---|---|---|---|---|
| apple-design | github.com/emilkowalski/skills `skills/apple-design` | c8a79627b59d72d764d6ab6f2c87c09a48169833 (2026-11-04) | MIT | ACTIVE (vendored) | `.claude/skills/apple-design/` | Apple-style interface and motion principles, reduced motion, typography; guides the future dashboard |
| emil-design-eng | same repo `skills/emil-design-eng` | same | MIT | ACTIVE (vendored) | `.claude/skills/emil-design-eng/` | UI polish and component review; visual-design critique |
| break-ui | same repo `skills/break-ui` | same | MIT | ACTIVE (vendored) | `.claude/skills/break-ui/` | Worst-case data stress test for UI (long symbols, empty states, extreme numbers) |
| review-animations | same repo `skills/review-animations` | same | MIT | ACTIVE (vendored; upstream sets `disable-model-invocation: true`, so user-invoked only) | `.claude/skills/review-animations/` | Motion review against a strict bar |
| other emilkowalski skills (animate, animate-expo, mobile-native, write-swift, ask-sonner, pick-ui-library, prototype, choreograph, ...) | same repo | same | MIT | REJECTED | - | React / Swift / animation-library specific; the dashboard is static HTML with no animation |
| LLM Council (Ole Lehmann) | no verifiable repository. Origin: an X post by @itsolelehmann (x.com/itsolelehmann/status/2038661433626333649); GitHub user `itsolelehmann` does not exist | - | - | REFERENCE | `.claude/skills/llm-council/references/advisor-perspectives.md` | The five lenses (Contrarian, First Principles, Expansionist, Outsider, Executor) and a Chairman synthesis were already integrated in our own words; strengthened 2026-11-08 |
| aiwithremy/claude-skills-llm-council | github.com/aiwithremy/claude-skills-llm-council | 55ee36e89e0f3f780099ac50332fbb3ec8d14738 (2026-04-26) | **no license file** | REJECTED | - | Third-party copy (owner Remy Gaskell, README credits Ole Lehmann). No license, so it cannot be vendored; it also tells the agent to scan `memory/`. Ideas only |
| karpathy/llm-council | github.com/karpathy/llm-council | - | no license | REJECTED | - | A multi-model web app, not a skill, and not the requested source; would add paid external LLM calls |
| obra/superpowers | github.com/obra/superpowers | 22f0b463e7a5e579904dd6211a520321035526f7 (v7.0.2, 2026-11-03) | MIT | REFERENCE | - | TDD, systematic debugging, verification-before-completion ideas already covered by `project-orchestrator`, `test-engineer` and the repair loop. Not installed: its SessionStart hook injects text into every session and its branch/worktree skills commit and merge, which conflicts with our no-commit rule |
| anthropics/skills | github.com/anthropics/skills | 2c5958ecac7cee2b583967a2c4981d0f4a75c579 (2026-11-06) | per skill (skill-creator, docx: Apache-2.0; some without a license file) | OPTIONAL | available in Claude Code as `anthropic-skills:*` (not vendored) | `skill-creator` for authoring and validating new project skills; `webapp-testing` / `frontend-design` for future UI work |

## 2. External tools

| Tool | Upstream | Version | License | Status | Purpose and reason |
|---|---|---|---|---|---|
| ruff | astral-sh/ruff | 0.17.4 (pinned in `pyproject.toml`, installed in git-ignored `.venv`) | MIT | ACTIVE (dev) | Lint (`F`, `E9`), run by `run_all` static_lint. Formatter not enabled (no aesthetic mass diff) |
| pyflakes | PyCQA/pyflakes | 3.2.0 (present in the owner's Anaconda Python) | MIT | ACTIVE (fallback) | Used by `run_all` when ruff is absent |
| pytest | pytest-dev/pytest | 7.4.4 installed (latest 9.2.0) | MIT | ACTIVE | Alternative runner for the unittest suite; not upgraded without need |
| unittest / `run_all` | Python standard library | - | PSF | ACTIVE | The validation authority (groups, evidence, readiness) |
| uv | astral-sh/uv | latest 0.13.7, not installed | MIT or Apache-2.0 | OPTIONAL | `pyproject.toml` is uv-compatible (`[dependency-groups]`, `package = false`); the runbook gives a pip path that needs no uv |
| ty | astral-sh/ty | 0.0.99, beta | MIT | REJECTED for now | Beta type checker; the codebase is only partly annotated, so results would be noise. Revisit when it reaches a stable release (TD-6) |
| pre-commit | pre-commit/pre-commit | 4.5.0 installed (latest 4.7.0) | MIT | REJECTED | Installs git hooks; the Claude Code guard and post-edit hooks plus `run_all` already cover the checks, and the owner does not commit through agents |
| import-linter | seddonym/import-linter | 2.16 | BSD-2-Clause | REJECTED | `nse/validation/architecture.py` enforces the same layer contracts with the standard library and also covers single definitions and unsafe calls |
| bandit | PyCQA/bandit | 1.9.4 | Apache-2.0 | REJECTED for now | Rule A8 and `test_repo` cover the relevant patterns (no network, no shell, no eval/pickle); revisit if third-party code or subprocess use grows (TD-7) |
| pip-audit | pypa/pip-audit | 2.10.1 | Apache-2.0 | OPTIONAL | No runtime dependencies to audit; it queries online vulnerability databases. Run on the dev group if it grows |
| vulture | jendrikseipp/vulture | 2.16 | MIT | REJECTED | Dead-code finder with many false positives on CLI handlers registered by name |
| Graphify | github.com/Graphify-Labs/graphify (PyPI `graphifyy` 0.9.104) | 6c8002eca4acad58db6160eabcb466e61fc35afb (2026-11-08) | Apache-2.0 and MIT | REJECTED | Code graph via tree-sitter. Rejected because: about 30 non-stdlib packages; its install adds PreToolUse hooks that deny or redirect Read and Grep (conflicts with `guard.py`); docs and PDF indexing route content to an LLM provider auto-selected from environment keys; queries are logged to `~/.cache`; no local project-management features (cloud only). Replaced by `python3 -m nse.validation.architecture --map`. A manual, code-only run in a scratch directory remains possible if a graph view is ever wanted |

## 3. Project management

Graphify has no local milestone or task tracking, and no external tool was needed.
Project management is repository-native: `docs/PRODUCT_ROADMAP.md`,
`docs/MILESTONE_STATUS.md`, `docs/TECHNICAL_DEBT.md`, `nse/docs/IMPLEMENTATION_BLOCKERS.md`,
`nse/docs/DECISION_REGISTER.md`, `nse/docs/ENGINEERING_DECISIONS.md`, `docs/AGENT_OWNERSHIP.md`.

## 4. Our own skills (project-owned, `.claude/skills/`)

Every project skill names a runnable check (`tests/test_claude_hooks.py`). Grouped by use:

| Area | Skills |
|---|---|
| Orchestration and safety | `gtf-autonomous-project-lead` (sole governance chair), `autonomous-gtf-project-council` (staffing playbook, not a second chair), `project-orchestrator`, `repository-guardian`, `release-readiness`, `security-reliability` |
| GTF specialists | `gtf-p0-data-certification` (GTF P0, Product Prompt 01 and MP1: certification of membership, identity, corporate actions, calendar, EOD, continuity and the research universe), `gtf-quantitative-validation` (GTF P7: Prompt 02 backtest engine plus Prompts 09, 10 and 11; Prompt 12 is the shadow log and is not a GTF phase), `gtf-production-readiness` (GTF P11, Product Prompt 14: ten production gates mapped to `readiness.py` and to R1–R5, without collapsing them) |
| Methodology | `rulebook-compliance`, `strategy-gate-validation`, `zone-mtf-validation`, `strategy-review`, `trade-analysis`, `position-review` |
| Data | `data-quality-validation` (read-only file checks), `nse-data-engineering` (collection and custody; HELD is not certification), `reference-data-validation` |
| Testing and audit | `integration-testing`, `adversarial-testing`, `lookahead-audit`, `reporting-audit`, `nse-scenario-library`, `nse-code-review` |
| Quant | `backtest-review`, `database-engineering` |
| Interface | `frontend-dashboard` (Python SVG dashboard only: `nse/research/dashboard.py` and `decision_replay.py`; `platform/web` is a separate React client), with the vendored design skills above for that client |
| Council (advisory) | `llm-council`, `engineering-council`, `trading-council` |

GTF phase Pn is not Product Prompt n. The phase crosswalk and the standing skill set live in `gtf-autonomous-project-lead` section 7. Precedence is the Rulebook, then owner decisions, then Pine where the Rulebook is silent, then the master skill, then the active specialist, then the procedure skill, then the advisory councils. Risk R-5 stays unresolved.

Agents (`.claude/agents/`) and their roles: `docs/AGENT_OWNERSHIP.md`.

## 5. Vendoring procedure

1. Clone the upstream repository read-only into a scratch directory; verify owner, license
   and commit; read every file that will be copied (agent instructions are code).
2. Copy the skill folder unchanged into `.claude/skills/<name>/` plus the upstream LICENSE.
3. Record each file's SHA-256 in `.claude/vendored-skills.json` with upstream, path,
   commit, license and date; add a row in section 1.
4. Run `python3 -m nse.validation.run_all --group hooks --group repository`.

A local adaptation is never written into a vendored file: put project-specific guidance in
our own skill (for example `frontend-dashboard`) and reference the vendored one.
