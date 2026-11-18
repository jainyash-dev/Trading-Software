# Skill architecture audit

Date: 2026-11-11. Read-only. No skill was edited, renamed, merged, or deleted. P0 implementation was not started.

Source of this audit: the four GTF skills in full; the description and operating instructions of every other skill under `.claude/skills/`; `CLAUDE.md`; `docs/SKILLS_REGISTRY.md`; `docs/AGENT_OWNERSHIP.md`; `docs/PRODUCT_ROADMAP.md`; `docs/product/MASTER_PROMPT_ROADMAP.md`; and the known precedence note R-5 in `nse/docs/ENGINEERING_DECISIONS.md`.

## Verdict

The four GTF skills can become one engineering and research organization. They are not that organization yet.

The three specialists already refuse to change the Rulebook, qualification, risk limits, or `authorises_order`. That part of the design holds. What does not hold is governance. The repository still names `autonomous-gtf-project-council` as the operating authority, while `gtf-autonomous-project-lead` claims the same chair and never mentions the council, the orchestrator, or the repository guardian. Loading both produces two chairs.

A second break is the phase vocabulary. GTF phases P0–P11 exist only inside the four new skills. The owner's issued plan is Product Prompts 00–14, and the repository milestones are MP0 and MP1. The numbers do not match. GTF phase P0 is Prompt 01. GTF phase P11 is Prompt 14. Product Prompt 11 is robustness and stress testing. An agent that treats "P11" as one thing will certify the wrong work.

No existing skill is redundant enough to remove. The vendored design skills stay byte-for-byte untouched. The procedure skills (data, gates, zones, lookahead, backtest review, security, release readiness) stay independent and are invoked under the specialist that owns the phase.

## Answers to the ten checks

| Check | Result |
|---|---|
| 8. The master skill is the project-wide governance authority | Claimed by the master and by all three specialists. Not installed. `CLAUDE.md`, `docs/AGENT_OWNERSHIP.md`, `docs/SKILLS_REGISTRY.md`, and `docs/PRODUCT_ROADMAP.md` still name the council. The master never cites those skills. |
| 9. Specialists cannot override the Rulebook, approved methodology, or risk limits | The procedures hold. All three forbid methodology changes, the 10/10 caps, and automated orders. One sentence does not: P0 section 3 ranks the master skill, then owner decisions, then the Rulebook. That order can override an explicit Rulebook rule. |
| 10. P0, P7, and P11 specialists have clear activation conditions | Clear inside their own glossaries. Unsafe against Product Prompt numbers. P7's description omits GTF phase P11; the production skill is what pulls it in. The production skill also activates on any new log line or file writer. |
| 11. The right skills can be loaded together without contradiction | Not today. After the corrections in section 6, the bundles in section 4 can. |
| 12. A single activation architecture for P0–P11 | Section 7. Do not apply it by editing skills until these findings are accepted. |

## 1. Existing skill inventory

34 `SKILL.md` files. 4 GTF skills, 26 project procedure skills, 4 vendored design skills. Vendored files are hash-pinned in `.claude/vendored-skills.json` and must not be edited.

### 1.1 GTF skills (new)

| Skill | Lines | What it claims to own | What it explicitly refuses |
|---|---|---|---|
| `gtf-autonomous-project-lead` | 1200 | All GTF phases P0–P11. Autonomous technical lead. "Apply whenever working in the GTF trading repository." | Changing Rulebook, Pine, qualification, risk limits, broker permissions. Fabricating evidence. Setting `authorises_order` true. |
| `gtf-p0-data-certification` | 536 | Membership, identity, corporate actions, calendar, EOD, price continuity, certified universe, exclusion register. Primary on GTF P0. Consumer on GTF P2, P7, P11. | Zone rules, gates, risk limits, orders. Writing `ACCEPTED` or `REJECTED` in `nifty100_review.csv`. Guessing a second effective session. Adjusted prices as the research price. |
| `gtf-quantitative-validation` | 418 | Study design, bias, costs, walk-forward, robustness, prospective log, acceptance language. Primary on GTF P7. Also GTF P0 when data will be quoted as performance, and GTF P6 so the journal stays separate from the simulator. | Changing zones, gates, freshness, buffers, caps. Parameter search. `TARGET_FIRST` as baseline. Inventing a Zerodha tariff. Authorising trading. |
| `gtf-production-readiness` | 419 | Ten production gates, security, both SQLite stores, backup and restore, monitoring, performance evidence, the local journey. Primary on GTF P11. Also GTF P1, P5, P8, P9, P10. | Automated execution. Public bind. Tauri or Electron. Inventing a performance bar and then treating it as policy. Weakening host checks or the monthly cap. |

Each specialist says the master is mandatory and that the specialist cannot override it.

### 1.2 Project procedure skills

| Skill | Role today | Disposition |
|---|---|---|
| `autonomous-gtf-project-council` | Second chair. Decision levels A–E, agent staffing, hard ban on autonomous commits. Source order lists owner decisions before the Rulebook (R-5). | Keep. Demote to the staffing playbook once the master is the chair. Do not load it as a competing authority. |
| `project-orchestrator` | Checklist for a substantial `nse/` or `tests/` change. Repair loop of three. No commit unless the conversation authorises it. Still says read decisions D1–D46. | Keep as the `nse/` execution checklist, under the master. Correct the decision-log range. |
| `repository-guardian` | Baseline, protected hashes, dirty-tree rule. No commit, push, reset, clean, or amend without authorisation in the current conversation. | Keep. Its git rule wins until the master is corrected. |
| `rulebook-compliance` | Rulebook, then `USER_APPROVED` decisions, then Pine where the Rulebook is silent. Maintains `TRACEABILITY.md`. Still calls D40 proposed. | Keep. It is the methodology audit. Correct the D40 sentence. |
| `strategy-gate-validation` | G0–G8 and `derive_status` in `qualification.py`. | Keep. Independent. The GTF skills correctly refuse to reimplement gates. |
| `zone-mtf-validation` | Zone engine and MTF overlay, including `eligible_after_overlay`. | Keep. Independent. |
| `strategy-review` | Proposed rule changes stay `PROPOSED` until the owner approves. Routes through `trading-council`. | Keep. Independent. Only the owner approves a methodology change. |
| `trade-analysis` | One setup. Status words are BUY CANDIDATE, WAIT, AVOID, INSUFFICIENT DATA, capped by the evidence pack. | Keep for case work. The canonical status remains `derive_status`. |
| `position-review` | An open position. SL is locked after trigger. REDUCE has no Rulebook basis (RB 2343). | Keep. Independent. |
| `data-quality-validation` | Bhavcopy, calendar, and manifest checks before a scan. "Never fix data in place. Report it; the user decides." Every result carries `CORPORATE_ACTIONS_UNVERIFIED` until a corporate-action source is approved. | Keep as the checker. It does not own certification. The "never fix" line conflicts with P0 transcription repair. |
| `nse-data-engineering` | Offline acquisition, inbox, quarantine, ledger, D47/D55/D56 scripts. "Verified when `acquire-plan` shows the sessions HELD." | Keep. Owns collection. "Held" is not certification. |
| `reference-data-validation` | TradingView and other recorded comparisons through `nse_reference.py`. A mismatch is never auto-resolved. | Keep. Owns external parity. |
| `lookahead-audit` | Prefix invariance, higher-timeframe completeness, `Universe.members(as_of_date)`. | Keep. The quant skill already names it. |
| `backtest-review` | Audit of design, assumptions, and claims. Routes a combined council review. Separates a green suite from a performance claim. | Keep. The quant skill already names it. |
| `release-readiness` | Per-capability states from `nse/research/readiness.py`. Triggers on "is it ready". | Keep as the research-tree statement. It is not the ten production gates. |
| `security-reliability` | No network, broker, or order code under `nse/`. No secrets. Guard hooks. No unauthorised commit. Triggers on a new dependency, command, hook, file writer, or data path. | Keep. The production skill already names it. |
| `database-engineering` | `nse/research/store.py`: additive migrations, idempotent import, journal rules, `store-backup`. Description says "paper-trade journal". | Keep for the research store. It does not own `platform/gtf_platform/db.py`. |
| `integration-testing` | Real pipeline from data through CLI reports. Synthetic end-to-end tests are labelled synthetic. | Keep. Independent. |
| `adversarial-testing` | False-positive candidates, lost manual flags, lookahead, overstated validation. | Keep. Independent. |
| `reporting-audit` | Scanner exports match the pipeline, including limitation codes. | Keep. Independent. |
| `nse-scenario-library` | Rule-cited scenarios through the real pipeline. Synthetic cases are software evidence only. | Keep. Independent. |
| `nse-code-review` | Diff review. Does not edit unless asked. Does not commit. | Keep. Independent. |
| `llm-council` | Advisory only. Rulebook and deterministic eligibility outrank opinion. Still says D40, D41, and R1–R6 stay unresolved. Forbids stage, commit, push, and download. | Keep as the advisory coordinator. Correct the stale decision sentence. |
| `engineering-council` | Thin router into `llm-council` Mode A. Recommends. Does not authorise commits or downloads. | Keep as an entry point. Not a second engineering authority. |
| `trading-council` | Thin router into `llm-council` Mode B. One line allows EXIT/REDUCE to be discussed. A later line says REDUCE has no Rulebook basis. | Keep as an entry point. Align the REDUCE lines. |
| `frontend-dashboard` | Static HTML and SVG from `nse/research/dashboard.py` and `decision_replay.py`. "No frontend stack." "Use for any dashboard or chart change." | Keep, scoped to those two Python modules. It does not govern `platform/web`. |

### 1.3 Vendored design skills

| Skill | Invocation | Disposition |
|---|---|---|
| `apple-design` | UI and motion principles for the web | Advisory for `platform/web`. Do not edit. Eligibility display rules outrank visual preference. |
| `emil-design-eng` | Polish and component critique | Same. |
| `break-ui` | Worst-case data on a screen | Same. Useful on GTF P3, P4, P5, P6, and P10 screens. |
| `review-animations` | `disable-model-invocation: true`. User-invoked only. | Stays user-invoked. |

`docs/SKILLS_REGISTRY.md` section 4 does not list the four GTF skills, and it still calls the council the central authority. `tests/test_claude_hooks.py` already requires every non-vendored skill to name a `python3 -m nse.validation.run_all`, `unittest`, or `nse.research.cli` command. The four GTF skills do name those commands.

### 1.4 Three phase vocabularies

These are different series. An agent must not translate by number.

| GTF skill phase | Meaning inside the four skills | Owner's product prompt with the same number | Actual product prompt for that work |
|---|---|---|---|
| P0 | Historical data foundation | Prompt 00, the blueprint | Prompt 01, real NSE data readiness. Also MP1. |
| P1 | Application hardening | Prompt 01, data readiness | Defects inside Prompt 03 and later, not a named prompt of its own. |
| P2 | Charts and stock analysis | Prompt 02, research pipeline | Prompt 06. |
| P3 | Opportunity intelligence | Prompt 03, local API | Prompt 05. |
| P4 | Trade planning | Prompt 04, web shell | Prompt 07, plans half. |
| P5 | Portfolio and risk | Prompt 05, scanner UI | Prompt 07, portfolio half. |
| P6 | Journal and performance reporting | Prompt 06, charting | Prompt 08. |
| P7 | Backtesting and quantitative validation | Prompt 07, plans and portfolio | Prompt 02 for the engine, Prompts 09, 10, and 11 for the study. |
| P8 | Monitoring and automation | Prompt 08, journal | No single prompt. Platform jobs and `daily-update`. |
| P9 | AI research assistant | Prompt 09, historical backtesting | Prompt 13. |
| P10 | Professional UI/UX | Prompt 10, quantitative validation | Prompt 04 plus the visual pass across feature screens. |
| P11 | Final production certification | Prompt 11, robustness and stress testing | Prompt 14. Release gates R1–R5. |

Product Prompt 12 (shadow testing and paper trading) has no GTF phase. The master skill lists "unapproved paper-trading engines" as out of scope. The quant skill says the prospective log is not a paper engine. Prompt 12 is an owner-issued prompt. Leaving this unmapped will make a later phase refuse work the owner already scheduled, or build a broker path the skills forbid.

## 2. Responsibility overlap matrix

Rows are capabilities. Cells say who leads. "Procedure" means the existing skill still runs. "Consumes" means the skill reads the result and does not redo the investigation.

| Capability | Master | P0 skill | Quant skill | Production skill | Existing skill that still runs |
|---|---|---|---|---|---|
| Who decides and in what order | Claims the chair | Defers to the master | Defers to the master | Defers to the master | Council also claims the chair |
| Git and protected files | Section 9 orders a commit after every successful batch | Follows master section 9 | Follows master section 9 | Follows master section 9 | Guardian, council, orchestrator, security skill, code review, and llm-council forbid an unauthorised commit |
| Rulebook, gates, freshness | Restates the invariants. Level C forbids changes | Does not reimplement gates | Does not re-score zones | Displays the canonical envelope | `rulebook-compliance`, `strategy-gate-validation`, `zone-mtf-validation`, `strategy-review` |
| Risk limits, 10 fills and 10 open positions | Restates D42, D45, D46, ED-3 | Does not change them | Refuses to change them | Reconciles them across API and databases | `database-engineering` states the monthly ceiling. Council section 4 states both caps |
| Acquisition and inbox | P8 mentions downloads | Points at `nse-data-engineering` | - | Monitoring reads the ledger | `nse-data-engineering` leads |
| File-level data checks | - | Certification judgement over the checks | Reads the certification label | Gate 1 reads the label | `data-quality-validation` leads the checks |
| External chart parity | Listed under P0 | `EXTERNAL_PARITY_PENDING` until a recorded comparison | Leaves `NOT_EXTERNALLY_VALIDATED` | - | `reference-data-validation` leads |
| Certified universe and exclusions | P0 section | Leads | Consumes. Uncertified runs are `NOT_PERFORMANCE_EVIDENCE` | Gate 1 consumes | No existing skill certifies. Do not let acquisition "HELD" or a green `local_data` group stand in |
| Look-ahead | Prefix invariance | Point-in-time membership | Section 7 | - | `lookahead-audit` leads the hunt |
| Backtest claims | P7 section | Data prerequisite | Leads study design and acceptance language | Gate 3 quotes the study. It does not rerun a private backtest to confirm a feeling | `backtest-review` leads the focused audit |
| Research readiness statement | - | P0 labels in section 15 | Section 15 acceptance words | Says to copy `readiness.py` and also defines ten gates and five final statuses | `release-readiness` leads the capability table. Product gates are R1–R5 |
| Security and local data | Section 12 | No network inside `nse/` | No broker | Leads | `security-reliability` leads the research-tree checklist |
| Research journal | P6 | - | Journal fills are not simulated trades | Reconciles both databases | `database-engineering` leads `nse/research/store.py` |
| Platform database, backup, restore | P1 and P11 | Backup of bhavcopies is a different store | - | Leads `platform/gtf_platform` | No existing skill owns the platform database. `database-engineering` must not be stretched over it without saying so |
| Scanner reports | Canonical pipeline | - | - | Counts must match the envelope | `reporting-audit` |
| End-to-end research path | Names the pipeline | Does not replace it | Simulator is not a second strategy | Journey in section 11 | `integration-testing` |
| False-positive and leakage sweeps | Testing section | Named regression cases | Named groups | Named groups | `adversarial-testing` |
| One stock or one open position | P4 and P5 | - | - | Caps on screen | `trade-analysis`, `position-review` |
| Advisory debate | Not mentioned | - | - | P9 explanations are not an eligibility engine | `llm-council` and its two routers |
| Python SVG dashboard | - | - | - | - | `frontend-dashboard` |
| React application UI | P2 and P10 assume React 19, Vite, Lightweight Charts. `platform/web` already exists | Charts that claim history use the certified series | - | P10 polish does not close a reliability gate | Vendored design skills, advisory. `frontend-dashboard` currently contradicts this surface |

Duplicate capabilities, and the one that should remain:

- Two chairs. Keep the master as the chair after the precedence correction. Keep the council as staffing and as the level A–E classification, rewritten so it does not lead.
- Two "is it ready" skills. Keep both, with different outputs: `release-readiness` writes the `readiness.py` capability rows; `gtf-production-readiness` writes the Prompt 14 gate table and maps it onto R1–R5.
- Two data judgements. Keep all three layers: `nse-data-engineering` collects, `data-quality-validation` checks a file, `gtf-p0-data-certification` certifies symbol-dates.
- Two backtest reviewers. Keep `backtest-review` and `lookahead-audit` as the focused audits. The quant skill is the operating procedure around them.
- Two councils named "council". `llm-council` is advisory. `autonomous-gtf-project-council` is a delivery chair. They are not duplicates. Only one of them may decide.
- `engineering-council` and `trading-council` are routers into `llm-council`. Keep them so a named request still lands in the right mode.

Nothing in this list should be deleted.

## 3. Conflicting instructions

These are the conflicts that change what an agent will do. Stale wording that merely lags the decision log is included where it would reopen a closed decision.

### 3.1 Blocking if the skills are loaded together

1. **Commits.** The master, section 1 and section 9, says the owner expects a commit after each successful coherent batch, and tells the agent to stage and commit. The three specialists follow "master-skill section 9" for commits. `repository-guardian`, the council section 3, `project-orchestrator` section 7, `security-reliability`, `nse-code-review`, `llm-council`, `CLAUDE.md`, and `docs/AGENT_OWNERSHIP.md` forbid `git commit` unless the current conversation authorises it. `.claude/hooks/guard.py` blocks the recognisable forms. A standing sentence inside a skill is not that authorisation.

2. **Who is the chair.** `CLAUDE.md` sends substantial work to the council and the orchestrator. `docs/AGENT_OWNERSHIP.md` says the council is the operating authority. The master says to apply it whenever working in this repository, and its section 17 says not to stop at planning. The master does not mention the council. The council does not mention the master. Neither yields.

3. **Rulebook precedence inside the P0 skill.** P0 section 3: if the specialist and the master disagree, follow the master, then owner decisions, then the explicit Rulebook rule. `CLAUDE.md`, `docs/AGENT_OWNERSHIP.md`, and `rulebook-compliance` put an explicit Rulebook rule first (D12). The council puts owner decisions first; that difference is already recorded as R-5, and `CLAUDE.md` says nobody overrides an explicit Rulebook rule. The quant skill is safer: "Explicit Rulebook rules outrank this skill." The production skill says Rulebook rules and owner decisions outrank a convenience fix, and also says to follow the master when the two disagree.

4. **Phase numbers.** GTF P0, P7, and P11 are not Product Prompts 00, 07, and 11. See section 1.4. This is an activation conflict, not a wording nit.

5. **Editing data.** `data-quality-validation` says never fix data in place, and the user decides. The P0 skill says correct a transcription when the authentic source disagrees, correct a parser that mis-reads a documented schema, and do not ask the owner whether an unsupported record should be guessed. `docs/AGENT_OWNERSHIP.md` says the `data-validator` agent never modifies data. Those can coexist only if the main session performs a sourced transcription repair and the data-validator agent stays read-only. Loaded as written, they contradict.

6. **What "verified" means for EOD files.** `nse-data-engineering` says the work is verified when `acquire-plan` shows sessions HELD and `run_all` local data passes. The P0 skill says a held file is not a certified symbol-date, and an empty corporate-action body is not `COVERED_NO_EVENTS_PROVED`. The code still attaches `CORPORATE_ACTIONS_UNVERIFIED` on the replay path (`nse/eod/nse_replay.py`). A P0 certification label must not be used to delete that limitation.

7. **Which UI the chart skills govern.** `frontend-dashboard` says there is no frontend stack and that it applies to any dashboard or chart change. The master, sections 4.2 and P2, specifies the React application that already lives in `platform/web`, including `platform/web/src/chart/CandleChart.tsx`. Loading both on a chart task forbids the client the product already has.

8. **Three readiness languages.** `release-readiness` uses the `readiness.py` states. The production skill defines ten gates and the statuses `NOT_READY`, `FAILED`, `READY_WITH_LIMITATIONS`, `READY_FOR_CONTROLLED_USER_ACCEPTANCE`, and `PRODUCTION_READY`, and also says not to create a second scheme beside `readiness.py`. The product roadmap uses R1–R5. Prompt 10 writes strategy-acceptance criteria that the quant skill still treats as `PROPOSED_OWNER_DECISION`. An agent can close "ready" in one vocabulary and leave it open in the others.

### 3.2 Real, and smaller

9. **Stale decision status.** `llm-council` section 0 says D40, D41, and R1–R6 stay unresolved. `rulebook-compliance` still says a proposed decision, "D40 today", is not a rule. The decision log marks D40 `USER_APPROVED`, D41 `USER_APPROVED` as a whole with the remaining readings still proposed, and R1–R6 approved. The council skill section 5 already treats D40 and D41 as level A. An agent that loads `llm-council` will reopen decisions the council skill tells it never to reopen.

10. **Orchestrator decision range.** `project-orchestrator` tells the agent to read approved decisions D1–D46. P0 work depends on D47 onward, including D58, D59, D60, and D61, which the P0 skill names. Stopping at D46 drops the membership and calendar decisions.

11. **Trade-analysis status words.** BUY CANDIDATE, WAIT, AVOID, and INSUFFICIENT DATA are not `derive_status` values. The evidence pack's `verdict_cap` is supposed to cap them. The canonical pipeline status is still the status a report may quote. The gloss must not be written back as qualification.

12. **REDUCE.** `position-review` forbids recommending a reduction (RB 2343). `trading-council` says EXIT/REDUCE may be discussed, and later says REDUCE has no Rulebook basis. The later line and `position-review` agree. The earlier line does not.

13. **Pine ranked with the Rulebook.** Master section 6, methodology, puts "owner-approved Rulebook and Pine methodology" in one tier. D12 and `rulebook-compliance` use Pine only where the Rulebook is silent and nothing conflicts.

14. **Paper trading.** The master excludes unapproved paper-trading engines. `database-engineering` describes a paper-trade journal. The quant skill's prospective log is a manual shadow log. Product Prompt 12 is the owner's shadow-testing prompt. These name one journal three ways, and they can be read as either forbidding Prompt 12 or authorising a paper engine.

15. **Master section 6, code behaviour, ranks the current implementation above approved specifications.** That is the right order for "what does the code do today". It is the wrong order for "what should the code do". The methodology list in the same section is the right order for the second question. An agent that applies the code list to a trading rule will keep a bug because the code exists.

### 3.3 Aligned, and worth keeping aligned

These do not conflict. They are the reason the specialists can sit on top of the old skills.

- Fresh, untested demand only. Tested, invalidated, and unknown freshness never qualify. Candidates come only from `MtfSnapshot.eligible_after_overlay`. WIT stays blocked. Unknown is not PASS.
- One qualification path: `pipeline.run` → `scanner.scan` → `scan_symbol` → `qualification.evaluate_symbol`.
- `authorises_order` stays false. No broker. No network inside `nse/`.
- Monthly cap of 10 fills and open-position cap of 10 are independent. Closing a position releases a seat, not a monthly fill. ED-3: one actual order per eligible zone.
- Raw unadjusted OHLC is canonical. Prices are not silently adjusted, filled, or spliced across an unresolved identity.
- Agents do not write `ACCEPTED` or `REJECTED` on Nifty 100 review rows.
- Synthetic tests are not market validation. A backtest is not a forecast and is not permission to trade.
- Protected inputs stay untouched: the Rulebook PDF, `nse/sources/`, and vendored skills.
- The quant skill already defers to `backtest-review`, `lookahead-audit`, and the `quant-researcher` agent. The P0 skill already defers to `nse-data-engineering`, `data-quality-validation`, and `reference-data-validation`. The production skill already defers to `release-readiness`, `security-reliability`, and `database-engineering`.

## 4. Recommended skill combinations by roadmap phase

Load the standing set on every implementation batch. Add the phase set. Do not also load the council as a chair.

**Standing set**

- `gtf-autonomous-project-lead`, after correction C1 and C2.
- `repository-guardian` at the start and the end.
- `project-orchestrator` when the edit is in `nse/` or `tests/`. It runs the validation loop. It does not choose a different authority order.

**Do not load together until C2 is written:** `gtf-autonomous-project-lead` and `autonomous-gtf-project-council` as two chairs. After C2, load the council only to staff subagents.

| GTF phase | Product work it actually is | Lead specialist | Also load | Leave independent, do not let them lead |
|---|---|---|---|---|
| P0 | Prompt 01, MP1 | `gtf-p0-data-certification` | `nse-data-engineering`, `data-quality-validation`, `reference-data-validation` when a comparison is in scope, `lookahead-audit` if membership or as-of code changes, `adversarial-testing` if an eligibility flag changes | Council data role stays read-only. `release-readiness` at the end for the capability row. Quant skill only if someone is about to quote a performance number |
| P1 | Hardening defects, mostly Prompt 03 | `gtf-production-readiness`, limited to the P1 defect list, not a `PRODUCTION_READY` claim | `security-reliability`, `database-engineering` if the journal is touched, `nse-code-review`, `integration-testing` | P0 skill when a real scan is shown, so the screen stays labelled uncertified |
| P2 | Prompt 06, and the existing Python dashboard when that file is the task | Master for the phase. No GTF specialist leads chart code | `frontend-dashboard` only for `dashboard.py` and `decision_replay.py`. Vendored `apple-design`, `emil-design-eng`, `break-ui` for `platform/web`. `zone-mtf-validation` if overlay behaviour changes. P0 skill as a consumer of labels | `review-animations` unless the user invokes it. Production skill does not sign off on a chart |
| P3 | Prompt 05 | Master | `reporting-audit`, `integration-testing`, `adversarial-testing`, `break-ui` on the scanner screen. `strategy-gate-validation` only if a gate file is actually edited | The UI must not recompute qualification |
| P4 | Prompt 07, plans | Master | `strategy-gate-validation`, `rulebook-compliance`, `trade-analysis` for a single setup, `database-engineering` if a plan is stored | Quant skill does not choose the entry or the stop after seeing results |
| P5 | Prompt 07, portfolio | `gtf-production-readiness` for reconciliation of the two caps | `database-engineering`, `position-review` for one open position, `security-reliability` | A position review does not place or modify an order |
| P6 | Prompt 08 | Master, with the quant skill's journal rule | `database-engineering`, `gtf-quantitative-validation` so realised fills are not mixed with simulated trades, `reporting-audit` if an export changes | Prompt 12's shadow log, when that prompt starts, stays a separate column |
| P7 | Prompt 02 backtest engine, plus Prompts 09, 10, and 11 | `gtf-quantitative-validation` | `gtf-p0-data-certification` before any number is called evidence, `backtest-review`, `lookahead-audit`, `adversarial-testing`, `strategy-review` if a rule change is proposed | `trading-council` may challenge a claim. It does not pick a model. Acceptance hurdles stay proposed until a decision-log entry exists |
| P8 | Jobs and `daily-update`. No matching prompt number | `gtf-production-readiness` section 9 | `nse-data-engineering`, `security-reliability`, `data-quality-validation` on the files that arrived | A monitor that submits, modifies, or cancels an order fails the gate |
| P9 | Prompt 13 | `gtf-production-readiness` for the assistant boundary | `llm-council` as advisory colour, `trade-analysis` only to read a scan and an evidence pack | The assistant does not qualify and does not authorise |
| P10 | Prompt 04 and the visual pass. This is not product Prompt 10 | Master | Vendored design skills, `break-ui`, `frontend-dashboard` only for the Python dashboard, production skill section 11 for empty, error, and loading states | Design preference does not hide a blocked or manual status |
| P11 | Prompt 14. This is not product Prompt 11 | `gtf-production-readiness` | P0 skill for gate 1, quant skill for gate 3, `release-readiness`, `security-reliability`, `database-engineering`, `integration-testing`, `adversarial-testing`, `reporting-audit` | `nse-code-review` and the independent-reviewer agent read the diff. They do not get a second vote on eligibility |

Prompt 02 research-pipeline work that is not a backtest uses the standing set plus `strategy-gate-validation`, `zone-mtf-validation`, `rulebook-compliance`, `lookahead-audit`, `integration-testing`, `adversarial-testing`, and `nse-scenario-library`. It does not load the quant skill unless a metric will be quoted.

Prompt 12, when it starts, uses the quant skill's prospective-log rules and `database-engineering`. It does not become a broker integration. The master needs a sentence that says this prompt is in scope as a shadow log.

## 5. Missing capabilities

No new specialist is required before P0. These gaps are real, and they are reasons to keep the existing procedure skills rather than to write another 1,200-line skill.

- The master has no load list. It never names the council, the orchestrator, the guardian, or the procedure skills. An agent that reads only the master will ignore the checks those skills run.
- No skill owns `platform/web` chart, scanner, plan, portfolio, or journal implementation. `frontend-dashboard` owns a different UI. P2, P3, P4, and P6 have a phase description in the master and no procedure skill.
- No skill owns the platform SQLite database as its own procedure. The production skill describes it. `database-engineering` describes the research store, including checksummed migrations, which are not the same mechanism as `platform/gtf_platform/db.py`.
- No skill owns P8 monitoring beyond the production skill's section 9 and `daily-update` in `nse-data-engineering`.
- No skill owns P9 grounding beyond one section of the production skill and the advisory council.
- The registry, `CLAUDE.md`, and agent ownership do not mention the four GTF skills, so a new session can still be staffed entirely by the council.
- GTF phases, product prompts, repository milestones, `readiness.py` states, the ten production gates, and R1–R5 are not mapped in any skill.

P0 itself is not missing a procedure. The P0 skill plus the three data skills cover membership, identity, corporate actions, the calendar, EOD, continuity, provenance, exclusions, and external parity.

## 6. Required corrections

Do not apply these until they are accepted. None of them delete a skill. Vendored skills are not in this list.

| Id | File | Change |
|---|---|---|
| C1 | `gtf-autonomous-project-lead` sections 1 and 9 | A commit happens only when the current conversation explicitly authorises it. Remove the standing order to commit every successful batch. The specialists inherit this because they follow section 9. |
| C2 | Master, then one paragraph each in `CLAUDE.md`, `docs/AGENT_OWNERSHIP.md`, `docs/SKILLS_REGISTRY.md`, and `docs/PRODUCT_ROADMAP.md` | Install the precedence stack in section 7. The council remains the staffing playbook and stops being the chair. Record that R-5 is unchanged until the owner confirms the council's source order. |
| C3 | `gtf-p0-data-certification` section 3, and the matching sentence in the production skill | On a disagreement, an explicit Rulebook rule leads, then owner decisions, then the master, then the specialist. The specialist cannot win a methodology or risk-limit question. |
| C4 | Master section 7, and the description of each specialist | Add the crosswalk in section 1.4, in the skill text. State that GTF phase Pn is not Product Prompt n. |
| C5 | `data-quality-validation`, `nse-data-engineering`, and one sentence in the P0 skill | The data-quality skill reports and does not edit. A sourced transcription repair belongs to the P0 skill, recomputes the hash, and does not edit a price to close a gap. "Sessions HELD" is called file custody, not verification. `CORPORATE_ACTIONS_UNVERIFIED` stays on scan results until the code and the decision log remove it. |
| C6 | `frontend-dashboard` description | Scope it to `nse/research/dashboard.py` and `decision_replay.py`. State that `platform/web` is a different client. |
| C7 | `llm-council`, `rulebook-compliance`, `project-orchestrator` | D40 is `USER_APPROVED`. D41 is `USER_APPROVED` as a whole, and the readings the decision log still marks proposed stay proposed. R1–R6 are approved. The orchestrator reads the decision log through the latest entry, not through D46. |
| C8 | Master, new short section | Name the standing set and the phase table in section 4, so the master loads the existing skills instead of replacing them. |
| C9 | `gtf-production-readiness` section 13 and 15 | Map the ten gates and the five final statuses onto R1–R5 and onto the `readiness.py` rows. One open critical gate keeps R5 open. A P0 label is R1 evidence, not R4. A quant status is R4 evidence, not an execution approval. |
| C10 | Master section 4.1 and the quant skill section 14 | Product Prompt 12 is the prospective shadow log. It is in scope when that prompt starts. It is not a broker and not a paper-trading engine that places orders. |
| C11 | `trading-council` | Remove the line that allows REDUCE to be discussed as an action. Keep the line that REDUCE has no Rulebook basis. |
| C12 | `trade-analysis` | The quoted status is the canonical pipeline status. BUY CANDIDATE and the other glosses are council language and must pass `verdict_cap`. |
| C13 | Master section 6 | Split Pine out of the Rulebook tier, matching D12. State that the "code behaviour" list answers what the code does, and the methodology list answers what the code should do. |
| C14 | `docs/SKILLS_REGISTRY.md` section 4 | Add the four GTF skills and the one-line role of each. Leave vendored rows unchanged. |

C1, C2, C3, and C4 are the corrections that should land before P0 implementation. The others can land in the same edit or immediately after. P0 data work does not need C6, C11, or C12.

## 7. Final recommended skill architecture

One stack. Lower layers do not override higher layers.

1. Explicit Rulebook rule, cited as `RB <line>`.
2. Owner decisions, `USER_APPROVED` or `USER_STATED`, in `nse/docs/DECISION_LOG.md`.
3. Pine, only where the Rulebook is silent and nothing conflicts.
4. `gtf-autonomous-project-lead` for phase order, autonomy, evidence, and repository safety.
5. The one GTF specialist for the active GTF phase, using the crosswalk so the phase is not a product-prompt number.
6. The existing procedure skill for the check being run.
7. `llm-council`, `engineering-council`, and `trading-council`, advisory only.

The master is the only chair. It decides level-C engineering questions, assigns file ownership, and stops at level-C boundaries: trading rules, risk limits, broker permissions, and irreversible actions. The council's level A–E table is the classification vocabulary the master should adopt, because it is sharper than the master's Level A–D list and it already matches the decision log. Adopting that vocabulary is a documentation edit, not a second chair.

Specialists add procedure. They do not widen eligibility, choose a friendlier execution assumption, or declare a later phase complete.

Procedure skills stay independent. They are how a specialist proves a claim. Removing them would force every check into the 1,200-line master, which is how the instructions drift.

Vendored skills stay advisory and hash-pinned. They apply to `platform/web` presentation. They lose to any rule about showing blocked, manual, and data-insufficient states.

Agents stay in their current write boundaries from `docs/AGENT_OWNERSHIP.md`. The main session implements a P0 transcription repair. `data-validator` audits and does not edit data. `quant-researcher` reviews backtest diffs and does not declare profitability. `trading-rule-auditor` audits and does not settle a Rulebook conflict. `independent-reviewer` reviews the finished diff.

Activation rule, once C4 is in the skill text:

- A task about historical NSE files, membership, identity, corporate actions, the calendar, or whether a dataset is certified loads the P0 specialist, even during a later phase.
- A task that will quote win rate, expectancy, drawdown, profit factor, CAGR, or "the strategy works" loads the quant specialist, and loads the P0 specialist first if the dataset is historical.
- A task about production certification, backup, recovery, or "is the application ready" loads the production specialist, which then reads the P0 label and the quant status instead of redoing those studies.
- A task that only adds a log line loads `security-reliability`. It does not open the ten-gate certification.
- "Is it ready" loads `release-readiness` and, when the question is about the local application, the production specialist. The answer uses both vocabularies, mapped, and does not collapse them into one tick.

That is the coordinated organization: one chair, one precedence stack, one phase crosswalk, and the existing skills kept as the checks that chair is not allowed to skip.

## What this audit did not do

No skill file was modified. No test suite was run, because no code changed. P0 implementation was not started. The decision log was read far enough to check D40, D41, and the R1–R6 header, not re-audited entry by entry.
