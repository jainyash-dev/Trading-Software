# Source and evidence register

Audit date: 2026-11-10. Author of this folder: the implementation audit requested in the working session. No trading rule was changed.

## Repository state

| Fact | Value |
|---|---|
| Working directory | `/Users/yash/day-trader-skill` |
| Branch | `main`, tracking `origin/main` |
| HEAD | `9e302df1a81c2b13696d8fab61f05d377481be2e` |
| HEAD subject | `latest code` |
| HEAD author date | 2026-11-03 09:32:26 +0530 |
| Staged files | none |
| Tracked files at start | 276 |
| Untracked paths at start | 161 |
| Porcelain lines at start | 117 |
| Diff stat at start | 79 files, about 10,093 insertions, 2,437 deletions |
| Python used for tests | 3.12.6 |
| Node | v22.15.0 |

The dirty tree is the owner's work, including untracked `platform/`, `docs/`, and the data files. This audit added only `docs/product-discovery/`.

Side effects of verification, not product edits:

- `npm install` in `platform/web` updated the untracked `platform/web/package-lock.json` at 2026-11-10 10:53:35 (npm reported one package added). `node_modules/` is gitignored.
- `npm run build` wrote gitignored `platform/web/dist/`.
- `python3 -m nse.validation.run_all` wrote gitignored `nse/output/validation/report.json`.

No file under `nse/sources/` was edited. The Rulebook PDF was not edited. No commit, push, reset, or clean was run.

## Source register

| Source | Purpose | Authority | Date or version | Important finding |
|---|---|---|---|---|
| Rulebook PDF at the repository root, and `nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md` | Methodology | Highest for an explicit rule | PDF hash-pinned. Markdown headings read, not re-transcribed | Sections 1-3 cover pre-trade rules, the 7-point score, and TDA. Traceability maps them to code |
| `nse/docs/TRACEABILITY.md` | Rule to code | Engineering map, dated rows through 2026-11-09 | Living table | Rows 33-35 are display-only or not implemented. Row 22's WIT branch is untested |
| `nse/docs/DECISION_LOG.md`, `DECISION_REGISTER.md` | Owner decisions | Second only to an explicit rulebook rule | Through D56 in the milestone | Not reopened |
| `docs/product/PRODUCT_REQUIREMENTS.md` | Desktop product | Product Prompt 00 | 2026-11-09 | FR-1 through FR-13 and R1-R5 via the roadmap |
| `docs/product/MASTER_PROMPT_ROADMAP.md` | Prompt order and release gates | Product Prompt 00 | 2026-11-09 | R1 open, R2 open, R3-R5 not started |
| `docs/product/DECISIONS_AND_OPEN_QUESTIONS.md` | AR-1-AR-17, OQ-1-OQ-3 | Architecture recommendations plus closed owner decisions | 2026-11-09 | AR-17 still describes a non-atomic cap that `store.py` has since locked |
| `docs/architecture/SYSTEM_ARCHITECTURE.md`, `docs/ARCHITECTURE.md` | Layers and A1-A10 | Enforced for `nse/` | Architecture check passed this audit | Platform is outside A1-A10 |
| `docs/MILESTONE_STATUS.md` | Milestone state | Authority for milestone labels, not for untracked files | 2026-11-09 | Says desktop implementation has not started. `platform/` exists |
| `PRODUCT_MASTER_STATUS.md` | Capability inventory | Stale in section 4 for corporate actions and Nifty 100 | Mixed 2026-11-02 and 2026-11-09 rows | Section 5 is closer to the tree than section 4 |
| `docs/VALIDATION_SCORECARD.md` | Historical test counts | Superseded in section 3 by later milestone numbers | 2026-11-09 | Section 3 still says 62 of 1,233 sessions |
| `nse/docs/IMPLEMENTATION_BLOCKERS.md` | Blockers | Latest parts 11-12 | 2026-11-09 | B11-R, CAL-2, B11-I, R-10 still open. Part 10's "171 periods" is older than part 11's 185 |
| `nse/docs/REAL_DATA_READINESS.md` | Data verdict | Current verdict text | 2026-11-09 | PARTIALLY_READY. Some earlier sections describe the Q1 2022 sample |
| `nse/docs/DATA_REQUIREMENTS.md` | Format notes | The 2026-11-09 paragraph supersedes the 2026-10-26 sentences under it | Mixed | Line 32 still says UDiFF is not verified |
| `nse/docs/ENGINEERING_DECISIONS.md` | ED-1 onward | Engineering, not owner decisions | Through ED-46 in the research notes | ED-3, ED-20, ED-44, ED-46 are load-bearing here |
| `nse/data/calendar/README.md` | Calendar provenance | The 2016-2025 paragraph | 2026-11-09 and an older open item | Line 79 and line 118 disagree |
| `platform/web/docs/LIMITATIONS.md` | UI honesty | Stale relative to the routes | Written with the shell | Says scan and candle routes are absent. They are not |
| `nse/research/readiness.py` | Machine-readable capability table | Stale strings | In the working tree | EOD text still says 1,233 files. P-LOC-2 still described as open |
| Code under `nse/` and `platform/` | Implementation | Outranks a status document | Working tree 2026-11-10 | See the implementation audit |

## Conflicts

Classifications are in [01_PRODUCT_DEFINITION_AND_SCOPE.md](01_PRODUCT_DEFINITION_AND_SCOPE.md). None was closed by this audit.

## Inspection log

| Stage | Inspected | Verified | Left out |
|---|---|---|---|
| Repository | `git status`, `git log`, `git diff --stat`, top-level layout | Branch, HEAD, dirty tree | Line-by-line diff of all 79 files |
| Product docs | Requirements, roadmap, decisions, milestone, scorecard, blockers, readiness, traceability headings | Conflicts listed | Every historical release snapshot under `nse/docs/release/` |
| Engine | Zone engine, overlay, qualification, scanner, risk, levels, store, backtest, execution policy, via direct reads and a read-only pass | WIT short-circuit at `scanner.py` 217-219. Cap transaction at `store.py` 811-816. `data_ready` false in `eod_coverage.py` and `app.py` | Every gate function restated line by line |
| Platform API | Routes, security, jobs, integration, tests | 24 tests passed | A live server process |
| Web | Routes, overview, scanner, watchlists, pages, chart, API client | 40 tests and the production build | A browser click-through |
| Data files | Directory roles, milestone counts, calendar README, corporate-action and universe conclusions checked against the blockers and a file inspection | `data` and `data_readiness` tests passed. `local_data` PASS for 2,478 archives | A fresh `eod-coverage` command was not started |
| Legacy `trader-*` | Inventory and the legacy test group | 304 legacy tests passed | Reading those packages as GTF code |

## Tests executed

| Test suite | Command | Executed? | Result | Failures | Limitation |
|---|---|---|---|---|---|
| Architecture module | `python3 -m nse.validation.architecture` | Yes | PASS, 50 modules, 0 violations | 0 | `nse/` only |
| Research batch | `python3 -m nse.validation.run_all` with groups `repository`, `architecture`, `zone_engine`, `mtf_freshness`, `strategy_gates`, `lookahead`, `integration`, `adversarial`, `reports`, `backtest`, `store`, `research_assistant`, `dashboard`, `risk_instruments`, `scenarios`, `health`, `hooks`, `council`, `validation_framework` | Yes | 782 passed | 0 | About 79 seconds. Does not hash the archive |
| Data batch | same runner with `data`, `data_readiness`, `acquisition`, `legacy_day_trader_skills` | Yes | 522 passed (127 + 51 + 40 + 304) | 0 | About 584 seconds. `--group` skips `local_data` |
| Platform | `PYTHONPATH=platform python3 -m pytest platform/tests -q -p no:cacheprovider` | Yes | 24 passed, 2 pydantic warnings | 0 | Fixture prices. Installed FastAPI 0.123.4 versus pin 0.121.0 |
| Frontend unit | `npm test` in `platform/web` | Yes | 40 passed | 0 | Stubbed `fetch` |
| Frontend build | `npm run build` | Yes | Success. JS bundle about 494 kB | 0 | Not a runtime check |
| Ruff | `.venv/bin/ruff check nse tests platform .claude/hooks` | Yes | All checks passed | 0 | F and E9 only |
| Docs health | `python3 -m nse.validation.docs_health` | Yes, after this folder was written | PASS, 0 findings | 0 | Also passed once before the folder existed |
| Whitespace | `git diff --check` | Yes | Clean | 0 | Untracked files have no diff |
| `local_data` | Called from `nse.validation.run_all` | Yes | PASS. 2,478 archives. Years 2016-2025. No unverified calendar source | 0 | A hash pass is not `DATA_READY` |
| `reference_comparison` | Called from `nse.validation.run_all` | Yes | PASS. 61 MATCH, 0 MISMATCH, source `YAHOO_FINANCE_SCREENSHOT` | 0 | The checker says this is not independent validation |
| Full suite in one process | `python3 -m nse.validation.run_all` with no `--group` | No | Not run as one command | - | The pieces above were run separately |
| Browser | - | No | - | - | No dev server was started |
| Two-connection journal probe | - | No | - | - | Code inspected only |

## Code anchors used in the conclusions

| Conclusion | Anchor |
|---|---|
| WIT never reaches qualification | `nse/research/scanner.py` `scan_symbol`, non-MIT return |
| Overview invents no index | `platform/gtf_platform/routes.py` overview handler, `index` is `None` |
| Health is not data-ready | `platform/gtf_platform/app.py` `data_ready` false |
| Coverage report is not data-ready | `nse/research/eod_coverage.py` `data_ready.ready` false |
| Plans, journal, fills, backtests, assistant, reports, paper have no route | `NOT_IMPLEMENTED` in `platform/gtf_platform/app.py` |
| Chart is a fixture | `platform/web/src/features/pages.tsx` Analysis branch and `platform/web/src/chart/fixtures.ts` |
| Search is the names file | `platform/gtf_platform/integration/reference.py` `_names` |
| Non-MIT scans get empty candles | `platform/gtf_platform/integration/research.py` |
| Monthly cap transaction | `nse/research/store.py` `journal_event` |
| No partial-exit kind | `EVENT_KINDS` in `store.py` |
| Placeholder routes still render | `platform/web/src/navigation/routes.ts` `available: false`, and `pages.tsx` |

## Report index

| File | Contents |
|---|---|
| [00_EXECUTIVE_SUMMARY.md](00_EXECUTIVE_SUMMARY.md) | Current state and direction |
| [01_PRODUCT_DEFINITION_AND_SCOPE.md](01_PRODUCT_DEFINITION_AND_SCOPE.md) | Scope and unresolved conflicts |
| [02_MASTER_CAPABILITY_MAP.md](02_MASTER_CAPABILITY_MAP.md) | 165 IDs |
| [03_REPOSITORY_IMPLEMENTATION_AUDIT.md](03_REPOSITORY_IMPLEMENTATION_AUDIT.md) | Status per ID |
| [04_USER_JOURNEY_ASSESSMENT.md](04_USER_JOURNEY_ASSESSMENT.md) | Journeys A-G |
| [05_ARCHITECTURE_AUDIT.md](05_ARCHITECTURE_AUDIT.md) | Boundaries and drift |
| [06_DATA_READINESS_AND_BLOCKERS.md](06_DATA_READINESS_AND_BLOCKERS.md) | Datasets and blockers |
| [07_PRODUCT_GAP_REGISTER.md](07_PRODUCT_GAP_REGISTER.md) | Gaps and labels |
| [08_PRIORITISED_IMPLEMENTATION_ROADMAP.md](08_PRIORITISED_IMPLEMENTATION_ROADMAP.md) | P0-P3 and phases |
| [09_FUTURE_SCOPE_AND_EXCLUSIONS.md](09_FUTURE_SCOPE_AND_EXCLUSIONS.md) | What not to build |
| [10_FINAL_READINESS_SCORECARD.md](10_FINAL_READINESS_SCORECARD.md) | Counts and gates |
| [11_SOURCE_AND_EVIDENCE_REGISTER.md](11_SOURCE_AND_EVIDENCE_REGISTER.md) | This file |
