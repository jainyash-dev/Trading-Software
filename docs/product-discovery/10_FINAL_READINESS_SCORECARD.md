# Final readiness scorecard

Audit date: 2026-11-10. Denominator for the engineering count: the 165 capability IDs in [02_MASTER_CAPABILITY_MAP.md](02_MASTER_CAPABILITY_MAP.md). Each ID has one status in [03_REPOSITORY_IMPLEMENTATION_AUDIT.md](03_REPOSITORY_IMPLEMENTATION_AUDIT.md). No weights. A verified engine rule and a verified cookie check count as one each, so the verified count is not a percent of user value.

`IMPLEMENTED_VERIFIED` means the path was read and a non-mocked test of that path passed in this audit. It does not mean TradingView parity, a certified dataset, or a browser session.

## Engineering completion

| Status | Count | Share of 165 |
|---|---|---|
| IMPLEMENTED_VERIFIED | 23 | 23/165 |
| IMPLEMENTED_PARTIAL | 109 | 109/165 |
| IMPLEMENTED_UNVERIFIED | 1 | 1/165 |
| DOCUMENTED_ONLY | 3 | 3/165 |
| NOT_IMPLEMENTED | 24 | 24/165 |
| BLOCKED | 3 | 3/165 |
| NOT_IN_SCOPE | 2 | 2/165 |
| DEPRECATED | 0 | 0/165 |

Verified IDs: SD-018, GTF-001, GTF-002, GTF-003, GTF-004, GTF-005, GTF-006, GTF-008, GTF-009, GTF-010, GTF-011, GTF-012, GTF-013, GTF-014, GTF-015, PR-011, EX-002, EX-014, AI-004, AI-005, DS-014, DS-016, DS-017.

The 23 verified rows are mostly the MIT rule engine and the safety boundary (no broker, no second cap, WIT blocked, loopback, log redaction, assistant cannot write). The 109 partial rows are real code that does not finish the requirement, usually because the desktop screen or the data certification is missing.

Blocked: GTF-017, EX-007, EX-008.

Not in scope: EX-010, UX-018.

## Product completion

These categories describe whether the owner can complete the work, not whether a function exists.

| Area | Category | Why |
|---|---|---|
| MIT zone, overlay, and G0-G8 library | Implemented but unverified on real charts | Tests passed on 2026-11-10. No TradingView reference. Not shown on the product chart |
| Nifty 100 data files | In progress | Archive, calendar, identity, and corporate actions are on disk. `DATA_READY` is not claimed |
| Certified universe and full-window EOD | Blocked | B11-R and CAL-2 |
| Overview, scanner, watchlists | In progress | API clients exist. Browser not used. Universe uncertified |
| Stock analysis | Not started as a product path | Fixture chart only |
| Trade plan | Not started in the app | Library only |
| Manual execution record | Not started in the app | CLI journal only. The app correctly sends nothing |
| Position monitoring | Blocked | No quote source |
| Journal review and performance | Not started in the app | CLI summary and backtest exist and are labelled as not a strategy result |
| Assistant | Out of scope until the owner enables a provider | The deterministic explainer is CLI-only |
| WIT, broker, multi-user | Out of scope | By decision |
| Release gates R1-R5 | Blocked or not started | R1 open. R2 open. R3-R5 not started |

No single percentage is assigned to "product completion". Journeys B-G are not usable. Journey A is a partial scan path. Calling that 40% or 70% would hide the missing middle of the workflow.

## Release gates

| Gate | Category | Evidence |
|---|---|---|
| R1 Data ready | Blocked | B11-R open. CAL-2 unresolved. Readiness verdict remains partial |
| R2 Research ready | In progress | Pipeline and tests exist. External validation and a cited real scan with matching limitations were not produced in this audit |
| R3 Application ready | Not started as a gate | Three screens exist. Prompt 14 journey log does not |
| R4 Strategy validated | Not started | No pre-registered criteria, no cited manifest, no cost schedule |
| R5 Operationally ready | Not started | No paper book, no restore rehearsal, no killed-scan certification beyond the startup interrupt test |

## Tests behind this scorecard

| Suite | Command | Executed | Result | Failures | Limitation |
|---|---|---|---|---|---|
| Research groups, first batch | `python3 -m nse.validation.run_all` with 19 groups | Yes | 782 passed | 0 | Skips `local_data`, reference, and lint |
| Data, acquisition, legacy | same runner, 4 groups | Yes | 522 passed | 0 | Same skip. Legacy group is the US skill pack, not GTF |
| Architecture | `python3 -m nse.validation.architecture` | Yes | PASS, 50 modules | 0 | Does not cover `platform/web` |
| Docs health | `python3 -m nse.validation.docs_health` | Yes, before and after this folder | PASS, 0 findings | 0 | The later run includes these pages |
| Platform API | `PYTHONPATH=platform python3 -m pytest platform/tests` | Yes | 24 passed | 0 | Fixture CSV for the MIT scan. FastAPI on the machine was 0.123.4; the pin is 0.121.0 |
| Frontend | `npm test` in `platform/web` | Yes | 40 passed | 0 | `fetch` is stubbed |
| Frontend build | `npm run build` | Yes | `tsc` and Vite succeeded | 0 | A bundle is not a journey |
| Ruff | `.venv/bin/ruff check` on `nse`, `tests`, `platform`, `.claude/hooks` | Yes | All checks passed | 0 | Rules F and E9 only |
| Whitespace | `git diff --check` | Yes | Clean | 0 | Does not review untracked files as a diff |
| `local_data` | called directly, because `--group` skips it | Yes | PASS. 2,478 archives, years 2016-2025, 0 months with issues | 0 | Twelve months have info for an excluded-session file or an unresolved date. This is not `DATA_READY` |
| `reference_comparison` | called directly | Yes | PASS. 61 MATCH, 0 MISMATCH on the Yahoo INFY sheet | 0 | The check says this is not independent validation |
| Full `run_all` as one process | `python3 -m nse.validation.run_all` with no `--group` | No | - | - | The groups and the two file checks were run separately |
| Browser | not run | No | - | - | No click-through of Overview, Scanner, or Watchlists |
| Real Nifty 100 scan | not started | No | - | - | Would be slow (TD-17) and would still be `UNIVERSE_UNVERIFIED` |

Passing these suites does not certify the methodology and does not show a profit.
