# Engineering Decisions, Assumptions and Risks

Autonomous decisions made by the `autonomous-gtf-project-council` skill. **None of these is
an owner decision or a methodology change.** Category C = engineering discretion
(`AUTO_APPROVED` only if reversible, rule-preserving and tested); D = research hypothesis
(`PROPOSED`, never promoted to a rule). Owner decisions live in `DECISION_LOG.md`.

## Decisions (2026-11-08)

### ED-1. Owner limits are the defaults of the backtest portfolio fields
- Category C. Status `AUTO_APPROVED`.
- Decision: `ExecutionModel.monthly_trade_cap` and `max_open_positions` default to 10 instead of None. A model file written without them gets the owner limits.
- Rationale: D45 forbids "unlimited". A default equal to the owner limit is not an invented assumption; the B9 / B12 execution assumptions stay required inputs.
- Alternatives considered: make both fields required (this breaks every older model file for no safety gain); keep None and refuse it (the same safety, worse usability).
- Affected files: `nse/research/backtest.py`, `models.py`. Tests: `test_research_backtest.Model`, `Portfolio`.
- Reversible: yes.

### ED-2. A backtest without a calendar is refused
- Category C (it implements D42 / D45). Status `AUTO_APPROVED`.
- Decision: `_from_history` raises `ValueError` when `scan_config.calendar is None`.
- Rationale: without a calendar, expiry counts candles, so a missing session silently extends a pending order. The owner forbids that.
- What is unchanged: `simulate()` keeps candle counting as a labelled primitive for unit tests.
- Alternatives considered: keep the `EXPIRY_COUNTS_CANDLES_NO_CALENDAR` label. D45 rejects "warnings only".
- Tests: `test_research_execution_policy.D45Refusals`, the CLI tests in `test_research_backtest`.
- Reversible: yes.

### ED-3 (revised 2026-11-08, second milestone). One order per zone counts submitted orders
- Category C. Status `AUTO_APPROVED`. It implements the owner brief's rule: "a research plan that was never submitted as an order must not consume the one-order-per-zone allowance; once an actual order has been submitted, cancellation, expiry, stop-out or closure does not release it". This supersedes the first ED-3 below.
- Decision:
  - Additive migration 2 adds the append-only table `journal_orders` (one row per entry), set by `store.journal_order_submitted` / CLI `journal-order-submitted`. It is the owner's record of a manual Kite / GTT order; nothing is sent.
  - `store._holds_zone`: an earlier entry holds the zone if it has a submission, or it TRIGGERED (OPEN / CLOSED), or it EXPIRED, or it is still PLANNED. Only CANCELLED without a submission frees the zone.
- Conservative choice: an EXPIRED entry without a submission row still holds the zone. Expiry belongs to a live order, and pre-v2 journals have no submission rows; a plan never submitted is recorded as CANCELLED.
- QA re-review fixes (2026-11-08), in additive migration 3 (v2 is never edited):
  - an INSERT guard: `INSERT OR REPLACE` bypassed the append-only triggers;
  - `journal_legacy_entries`, a snapshot of the entries that existed before submissions could be recorded. A legacy CANCELLED entry keeps its zone used, because whether it was submitted is unknown.
  - Separately, a journal event dated before the order's submission time is refused.
- Tests: `test_research_store.JournalAuditRegressions20261106.test_ed3_*` (9).
- Reversible: yes (the migrations are additive; the rule is one function).

### ED-3 (first version, superseded). One journal order per zone, including after CANCELLED / EXPIRED
- Category C, restrictive. Status: superseded by the revised ED-3 above.
- Decision: `store.journal_add` refuses any second entry on the same symbol, zone and trade type.
- Rationale: the owner invariant is "one order per eligible zone", and the backtest already never places a second order on a zone. Before this change the journal allowed one after CANCELLED / EXPIRED, which made the two inconsistent.
- Consequence: a journal entry cancelled by mistake uses up the zone.
- Reversible: yes. Reverse if the owner says a cancelled *plan* (no order ever placed) should free the zone.
- Tests: `test_research_store.JournalAuditRegressions20261106.test_a_cancelled_or_expired_entry_still_uses_up_the_zone`.

### ED-4. D43 relevance definitions
- Category C (it implements D43). Status `AUTO_APPROVED`.
- G5: a Pine-only supply is relevant if any of PL, ENTRY_MIN or ENTRY_MAX lies inside it, or its PL lies at most 10% above that reference (`structure._band`, the same bands as validated zones).
- G7: a Pine-only supply is relevant if it lies on the target timeframe, above ENTRY_MIN and below the structural target's PL.
- Exclusions, on positive evidence only:
  - Pine deleted the zone (completed close beyond DL, PS 2613; RB 1313): excluded from G5 and G7.
  - Pine recorded a PL touch: excluded from G7 only, because a tested zone cannot be the fresh target (RB 551-558, as `levels.select_target`). It stays relevant for G5, where a tested opposing zone is MANUAL.
- A record without these fields is relevant.
- Not applied to the WIT Monthly-location check (WIT is BLOCKED) or to the G7 reference timeframe (validated M zones do not affect G7 either).
- Tests: `test_research_gates.PineOnlyD43`.
- Reversible: yes (each exclusion is one condition in `_g5` / `_g7`).

### ED-5. BAD_DATE bound
- Category C (it implements D44). Status `AUTO_APPROVED`.
- Decision:
  - The lower bound is the previous valid row's date, inclusive, because the bad row may duplicate it.
  - The bound is used only when the neighbouring valid rows are in order **and** the file has no OUT_OF_ORDER or DUPLICATE_DATE finding anywhere. A file that contradicts its own order cannot bound a lost row. The independent QA review (2026-11-08) reproduced the looser local-only rule dating the error too late in an unsorted file.
  - `verified=False`, plus an `ERROR_DATE_BOUND_INFERRED` warning.
- Assumption: the file is in date order around the bad row. If that assumption is wrong, an earlier scan could have used a file with a lost earlier row. The warning makes this visible.
- Tests: `test_research_lookahead.FutureDataQuality.test_d44_*`.
- Reversible: yes (drop the date to restore whole-input blocking).

### ED-6. `recorded_on` is not used to filter evidence
- Category C (restrictive). Status `AUTO_APPROVED`.
- Decision: corporate-action, universe and instrument records stay filtered by their effective / ex dates, not by when they were entered.
- Rationale: a split with ex-date before as_of happened before as_of. Hiding it from an earlier re-run because it was typed in later would loosen G0 (P-CA-1). D44's "later evidence must not affect earlier scans" is applied to evidence *about later dates*.
- Risk: re-running an old scan after adding records can change its output in the restrictive direction. Scan outputs are not frozen (`store.import_scan` keeps the original).
- Reversible: yes, but only with an owner decision.

### ED-7. Execution policy module
- Category C (it implements B9 / B12). Status `AUTO_APPROVED`.
- `nse/research/execution_policy.py` holds the owner values (AT_OPEN, STOP_FIRST + EXCLUDE, slippage 0.05 / 0.10 / 0.20, 10 / 10 / 10).
- `CostSchedule` refuses any lookup that is undated, spans a period change, or names an unknown instrument.
- The owner fixed no baseline slippage, so all three run and none is called the baseline.
- `cancel_if_target_first`, statuses and the entry/stop scenarios stay user inputs.
- Tests: `test_research_execution_policy`.
- Reversible: yes (a new module; nothing else depends on it).

### ED-8. IST conversion as a fixed +05:30 offset
- Category C. Status `AUTO_APPROVED`.
- IST has no DST, so `models.IST` is a fixed offset and needs no tzdata. Naive times are exchange-local IST, as every candle and journal time already is.
- The journal still refuses to mix naive and aware times.
- Reversible: yes.

### ED-9. Walk-forward pooled OUT trades obey the caps across folds
- Category C (it implements D42 / D45). Status `AUTO_APPROVED`.
- Decision: `run_walk_forward` re-applies `apply_portfolio_rules` to the pooled OUT copies, so OUT windows that split one IST month share its 10-trade cap. The per-fold records are unchanged.
- Found by the independent QA review (2026-11-08) as a plausible defect; the unit test reproduces it.
- Tests: `test_research_execution_policy.WalkForwardPooledCap` (unit level: `_segment` is patched).
- Reversible: yes.

### ED-10. Two-window primary/DR sessions in the backtest (D40)
- Category C (it implements D40 after the evidence resolution, `REAL_DATA_READINESS.md` §1). Status `AUTO_APPROVED`.
- Decision:
  - An `EXCLUDED_SHORTENED` date (2 Mar, 18 May 2024) counts as one verified session toward expiry.
  - Its daily bar spans the DR break, so it is never a fill or exit bar (D30). Its high/low only show whether a level could have been reached:
    - when no level could have been reached, the record continues;
    - when one could, the record ends `DATA_EXCLUDED_SESSION`;
    - a missing bar is `DATA_MISSING_SESSION`.
  - Muhurat is unchanged.
- Rationale: the owner's D40 wording ("one trading date for expiry; no candles across the break; do not discard valid observations"). Using the bar as a bound discards nothing and creates no candle.
- Alternatives considered: keep ending every record that meets the date (it discards valid observations); treat the bar as a normal candle (it creates a candle across the break).
- QA re-review fixes:
  - pending-order revalidation is checked before the two-window branch, so an invalid setup is `CANCELLED_SETUP_INVALID`, not a data stop;
  - a carried-over open trade records `SHORTENED_SESSION_CARRIED_OVER` with `zone_check: NOT_APPLIED` and whether the close was beyond the DL (the bar is not a candle, so no invalidation is applied, but the skip is never silent).
- Tests: `test_research_execution_policy.D40TwoWindowSessions` (9, including the real calendar).
- Reversible: yes.

### ED-11. Per-file EOD coverage report
- Category C. Status `AUTO_APPROVED`.
- Decision: `nse/research/eod_coverage.py` (CLI `eod-coverage`) gives each raw file its own verdict and reports:
  - duplicates (`IDENTICAL_CONTENT` / `CONFLICTING`);
  - missing calendar sessions; uncovered weekdays are UNVERIFIED, never holidays;
  - UDiFF files;
  - symbol gaps.
- Rationale: `inventory` loads the archive set at once, so one bad file would hide the rest.
- Tests: `test_research_eod_coverage`.
- Reversible: yes.

### ED-12. Execution realism gaps are listed on every backtest result
- Category C (disclosure, restrictive). Status `AUTO_APPROVED`.
- Decision: `backtest.EXECUTION_REALISM_GAPS` is added to every result's limitations. It lists symmetric-percentage costs only, no flat / minimum / capped charges, price bands, partial fills, tick size, GTT trigger semantics, liquidity and capital.
- Rationale: the cost review (2026-11-08) found that `flat_charges_modelled: false` stayed in the grid metadata and never reached results.
- Reversible: yes.

### ED-13. Universe integrity: overlaps refused, members without data reported
- Category C (restrictive). Status `AUTO_APPROVED`.
- Decision:
  - `universe.load` refuses overlapping membership periods for one symbol. Ends are inclusive, so a shared day overlaps; before this, the last row won silently.
  - `scanner.scan` reports a member at as_of with no input as `DATA_INSUFFICIENT` (`NO_INPUT_FOR_UNIVERSE_MEMBER`) instead of dropping it (survivorship visibility, B11).
- Tests: `test_research_reports.Universe`.
- Reversible: yes.

## Decisions (2026-11-08, foundation milestone, Master Prompt 0)

None of these changes a gate, an eligibility rule, a status or a limit. The trading
modules (`qualification`, `scanner`, `reports`, `structure`, `trend`, `topdown`,
`levels`, `confluence`, `marketdata`) are byte-identical to the pre-milestone tree;
`mtf_freshness` and `models` differ only by removed unused `typing` names (independent
QA, 2026-11-08).

### ED-14. Shared input adapters move out of the CLI
- Category C. Status `AUTO_APPROVED`.
- Decision: `nse/research/inputs.py` holds `parse_as_of` and the local input loader (`load`, `from_args`), formerly `cli._as_of` / `cli._inputs` plus a copy in `scenarios.parse_as_of`. `backtest.py` and `decision_replay.py` no longer import `cli`.
- Rationale: a portfolio-layer module importing the CLI was a hidden cycle (lazy imports) and made domain code depend on presentation.
- Evidence: line-for-line equivalence confirmed by independent QA; `cli._as_of`, `cli._inputs`, `scenarios.parse_as_of` kept as aliases; full suite unchanged.
- Alternatives: move every command handler into the application layer (TD-1; 13 modules for no behavioural gain).
- Implements: none (engineering only). Files: `inputs.py`, `cli.py`, `backtest.py`, `decision_replay.py`, `scenarios.py`. Tests: existing CLI, backtest, dashboard, scenario tests.
- Reversible: yes.

### ED-15. Architecture is enforced by a standard-library checker, not by moving files
- Category C. Status `AUTO_APPROVED`.
- Decision: `nse/validation/architecture.py` (rules A1-A10: layers, dependency direction, cycles, CLI isolation, stdlib only, single engine copy, single definitions, unsafe calls) and `nse/validation/docs_health.py` (links, CLI commands, `run_all` groups, modules named in docs), both run by the `architecture` validation group.
- Rationale: the code already had clear responsibilities; renaming the hyphenated engine folders or splitting large modules would disturb owner evidence and tests for no correctness gain. import-linter, Graphify and bandit were evaluated and not adopted (`docs/SKILLS_REGISTRY.md`).
- Evidence: every rule has a planted-violation test (`tests/test_architecture.py`), including the evasions independent QA found in the first version (relative imports, `import_module` literals, other path-loading spellings, `from os import system`, `getattr(os, ...)`, non-literal `shell=`, concatenated status literals).
- Implements: owner prompt addition 1 and 5.
- Reversible: yes.

### ED-16. Concise root CLAUDE.md; the owner's master prompt archived verbatim
- Category C. Status `AUTO_APPROVED`.
- Decision: the 65 KB master implementation prompt moves byte-identically to `docs/owner/MASTER_IMPLEMENTATION_PROMPT.md` (SHA-256 `c6c8cd91...ba8f`, pinned in `tests/test_repo.py`); `CLAUDE.md` becomes a short index that states it remains binding and keeps the safety rules and invariants. New root entries (`docs/`, `pyproject.toml`, `.env.example`) are added to the root whitelist test.
- Rationale: owner prompt 5.1 asks for a concise root file with detail elsewhere; loading 65 KB into every agent context crowds out task context.
- Alternatives: `@import` the archived prompt from CLAUDE.md (would load it all again).
- Reversible: yes (copy the archived file back). No owner text is lost or edited.

### ED-17. Development toolchain: Python 3.10+, no runtime dependencies, ruff for lint only
- Category C. Status `AUTO_APPROVED`.
- Decision: `pyproject.toml` declares `requires-python >= 3.10`, `dependencies = []`, a `dev` dependency group with `ruff==0.17.4`, ruff rules `F` and `E9` only (no formatter), and pytest settings. `run_all` adds an optional `static_lint` check: ruff from `.venv` or `PATH`, else pyflakes, else `UNAVAILABLE`; findings FAIL; `--acceptance` refuses `--no-lint`; skipped optional checks are listed in the report (`checks_not_run`).
- Evidence: the full suite passes on Python 3.10.20 and 3.12.7; 16 pre-existing unused imports were removed to start lint at zero (one legacy `trader-scanner` redefinition is an intentional pattern, and `trader-*` is excluded).
- Alternatives: ty (beta, rejected for now), pre-commit (git hooks; rejected), formatter (aesthetic mass diff; rejected).
- Reversible: yes.

### ED-18. Research-run manifests
- Category C. Status `AUTO_APPROVED`.
- Decision: `nse/research/run_manifest.py` writes `run_manifest.json` beside `scan` outputs and `<file>.manifest.json` beside a `backtest` result. It records a content-addressed `run_id`, input file hashes and a dataset hash (only the files the command read), methodology versions and protected-source hashes, code identity (git HEAD plus the SHA-256 of `git diff HEAD`), parameters, declared assumptions (the execution model), limitations and output hashes. The wall-clock `recorded_at` is excluded from `run_id`, and the reports themselves stay byte-deterministic.
- Rationale: owner prompt addition 3 (reproducible research) without a heavyweight experiment tracker.
- Limits: untracked files are not in the code identity (stated on every dirty run); `backtest-walk-forward` / `backtest-sensitivity` handlers live in the portfolio layer and cannot call the application-layer writer (TD-4).
- Tests: `tests/test_research_run_manifest.py`; `test_research_backtest` CLI test.
- Reversible: yes.

### ED-19. Third-party skills are vendored verbatim and hash-pinned
- Category C. Status `AUTO_APPROVED`.
- Decision: four MIT skills from `emilkowalski/skills` at commit c8a79627 (apple-design, emil-design-eng, break-ui, review-animations) are copied unchanged with the upstream LICENSE; `.claude/vendored-skills.json` pins every file. Tests exempt them from our project-skill rules (runnable check, no em dash) only by exact folder, and require byte identity instead.
- Rationale: the owner asked for these design principles; editing third-party text to satisfy our style tests would misrepresent it as upstream.
- Reversible: yes (delete the folders and the manifest entry).

### ED-20. One EOD source per trade date: legacy to 2024-07-05, UDiFF from 2024-07-08
- Category C. Status `AUTO_APPROVED` (MP1, 2026-11-09).
- Decision:
  - `nse_bhavcopy` parses both verified formats. It accepts exactly the two UDiFF header variants seen in official samples (`UDIFF_2024A`, `UDIFF_2024B`) and refuses any other.
  - `selected_format(trade_date)` is legacy up to 2024-07-05 and UDiFF from 2024-07-08.
  - `load_many`, which builds every research dataset, refuses a file in the other format (`SourceSelectionError`). Acquisition quarantines it (`FORMAT_NOT_SELECTED_FOR_DATE`).
  - `load()` still parses either format for any date, so `cross_check` can compare the two on overlap dates.
  - `acquire-plan` and the inbox provider name the selected format's file for each date.
- Rationale:
  - NSE/MSD/62424: legacy available "till July 05, 2024", discontinued July 08, 2024.
  - On four official overlap dates the two formats agree exactly, row by row (`EOD_FORMAT_EVIDENCE.md` §9).
  - The prompt forbids combining sources without explicit selection.
  - Legacy is kept for the overlap because it is the longer-verified format.
- Alternatives considered:
  - Accept either format on overlap dates: rejected, because one date could then have two sources.
  - Switch at 2024-01-01, the first UDiFF file served: rejected, because there is no evidence UDiFF was published then.
- Implements: none (data engineering); serves D31 provenance and B18.
- Affected files: `nse/eod/nse_bhavcopy.py` (`LOADER_VERSION` 2.0.0), `nse/research/acquisition.py`, `manifest_tool.py`, `eod_coverage.py`, `inventory.py`, `inputs.py`, `instruments.py`, `run_manifest.py`, `marketdata.py`, `nse/validation/run_all.py`.
- Tests: `tests/test_nse_eod_evidence.py` (24, of which 6 use real evidence); `test_research_acquisition.SourceSelection` (6).
- Specification correction: synthetic legacy fixtures dated 2025 were moved back 364 days (same weekday and ISO week), because no legacy file exists after 2024-07-05. Affected: `test_nse_replay`, `test_research_acquisition`, `test_research_data`, `test_research_instruments`.
- Reversible: yes. Change the two dates, or drop the check in `load_many`.

### ED-21. Instrument identity checked on every bhavcopy input
- Category C. Status `AUTO_APPROVED` (MP1).
- Decision:
  - `inputs.load` passes every bhavcopy input through `instruments.apply_to_input`, using records from `--instruments` when given (scan, scan-history, backtest, replay-decision).
  - Each of the following is a dated ERROR, so the scanner's G0 makes the input DATA_INSUFFICIENT from that date and earlier scans are unchanged (D44):
    - an ISIN change no record explains;
    - an ISIN the records contradict;
    - a symbol reused for another ISIN (two instruments' prices joined);
    - a symbol the supplied records do not cover;
    - `SYMBOL_HISTORY_SPLIT`: the symbol's ISIN traded under another symbol before its first row, so its series starts mid-history. This applies even when a record explains the rename, until histories are joined by ISIN (TD-13).
  - Without verified records for the symbol, the input carries `IDENTITY_UNVERIFIED` but is not blocked.
  - The limitation and the provenance summary depend only on the records file, never on market data after an as-of (prefix invariance).
  - Review corrections, same day:
    - the contrarian found the rename gap;
    - independent QA found the reuse WARNING, the label leak across dates, and `scenarios` HISTORICAL_REAL skipping the check.
    - All four are fixed, with regression tests.
- Rationale:
  - Approved instrument-identity policy: unknown or conflicting identity is unresolved, and successors are distinct.
  - Closes risk R-2.
  - Blocking every scan without records would make the scanner unusable until B11 closes, and adds no safety over the label. A spliced history across an ISIN change is what produces wrong zones, and that case is now blocked.
- Implements: owner instrument-identity decision (`DECISION_LOG.md` 1F).
- Affected files: `nse/research/instruments.py`, `inputs.py`, `models.py` (`IDENTITY_UNVERIFIED`), `cli.py`, `backtest.py`, `decision_replay.py`.
- Tests: `test_research_instruments.InputIdentityIntegration` (8, including one through `scanner.scan_symbol`), `RenameRegression` (3), `QaRegressions20261109` (3).
- Reversible: yes.

### ED-22. Nifty 100 membership converter; declared member-count exceptions
- Category C. Status `AUTO_APPROVED` (MP1).
- Decision:
  - `nse/research/membership.py` converts a dated baseline plus reconstitution events (schema in `REAL_DATA_READINESS.md` §5) into `universe.py` rows. It checks provenance by hash and identity optionally, and refuses to convert partially.
  - By default the converter requires N members and equal ADD / REMOVE counts per event. A date with an official count other than N is accepted only when declared in `count_exceptions`, and only at exactly that count.
  - `Universe.balance` reports the count; `Membership` stores the ISIN.
- Rationale:
  - The 17 Aug 2023 NSE Indices release has 6 NIFTY 100 inclusions against 5 exclusions (TATAMTRDVR), so "always 100" would reject official data.
  - An undeclared deviation still catches transcription omissions.
- Implements: D1 and the B11 requirements.
- Tests: `tests/test_research_membership.py` (35, synthetic).
- Reversible: yes.

### ED-23. Evidence retrieval: small official evidence files only; research data unchanged
- Category C. Status `AUTO_APPROVED` (MP1).
- Decision: during MP1 the council fetched only small official evidence files, each kept separate from the research dataset:
  - 9 bhavcopy samples and 3 format circulars, in `nse/data/eod/evidence/`;
  - the 3 withdrawn D40 circulars, in `nse/data/calendar/circulars/`;
  - 11 NSE Indices releases, a dated constituent archive and an inclusion workbook, in `nse/data/universe/evidence/`;
  - 2 corporate-action API responses, in `nse/data/corporate_actions/raw/`.

  Every file is recorded with its URL, retrieval date and SHA-256. Press-release URLs were confirmed by an independent byte-identical re-fetch. Nothing was added to `nse/data/eod/raw/` or its manifest, and no network code was added to `nse/` (D31).
- Rationale:
  - This follows the 2026-10-28 practice of retrieving circulars with their URL recorded.
  - The owner's earlier script-download approval covered one batch. A bulk backfill of 1,171 sessions is a separate owner action, given precisely in `REAL_DATA_READINESS.md` §9.
- Reversible: yes. Delete the evidence folders.

### ED-24. Coverage file states and research readiness
- Category C. Status `AUTO_APPROVED` (MP1).
- Decision: `eod-coverage` (report 2.0.0) records four cumulative states per file:
  - DOWNLOADED;
  - PARSED;
  - VALIDATED (provenance matches);
  - ACCEPTED_FOR_RESEARCH: an archive in the selected format, on an official trading day, with no conflicting or refused duplicate.

  It also records:
  - `dataset.dataset_id`, a SHA-256 over the accepted (date, file hash) pairs, plus the manifest hash and loader version;
  - `eod_ready`, with its blockers;
  - per-date `coverage_pct`.

  A standalone CSV byte-identical to an accepted archive's member stays VALIDATED and is not a blocker.
- Rationale: the MP1 requirement to separate downloaded, parsed, validated and accepted, and never to claim coverage because files exist.
- Tests: `test_research_eod_coverage` (4 new; one assertion updated, cited ED-20).
- Reversible: yes.

### ED-25. Scripted EOD backfill under D47
- Category C (implements owner decision D47). Status `AUTO_APPROVED`.
- Decision: `.claude/skills/nse-data-engineering/scripts/eod_backfill.py`. It lives outside `nse/`, so D31's no-network rule for product code and `test_repo`'s network-import ban still hold.
  - **download:**
    - only the plan's MISSING calendar trading days within 2021-2025;
    - URL equal to `nse_bhavcopy.official_url(date)` on `nsearchives.nseindia.com`;
    - a pause before every request, three attempts with exponential backoff, and HTTP 404 recorded as NOT_SERVED;
    - files staged under their official name and verified (single member, strict parse) before they enter the inbox;
    - never overwrites a file, and resumes from the download log.
  - **ingest:** one file at a time through `acquisition.ingest`, with its own URL as `source_page`, the actual download date, and the same owner-approved script-download provenance status as the Q1 2022 batch. That path applies quarantine, source selection, duplicate and revision checks, manifest rows and the ledger.
  - **report:** a JSON summary of the download log and the ledger.
- Rationale: the conditions of D47, mapped one to one.
- Reversible: yes. Delete the script; ingested files are kept, as they are raw evidence.

### ED-26. Calendar 2016-2020 under D48
- Category C (implements D48). Status `AUTO_APPROVED`.
- Decision: the 2016-2020 base holiday circulars, amendments and session notices are added to `nse/data/calendar/` in the existing format. A row is `CONFIRMED` only where the printed circular states it; otherwise it is `UNRESOLVED`, and the calendar raises for that date. The 2021-2025 rows are unchanged; tests compare both ranges with the printed circulars. Results: section 0 of `REAL_DATA_READINESS.md`.
- Reversible: yes.


### ED-27. Human review gate for membership (D49)
- Category C (implements D49). Status `AUTO_APPROVED`.
- Decision:
  - `membership.convert(..., review_path=)` verifies a period only with exactly one ACCEPTED review row naming a reviewer and a date, and the SHA-256 of the exact baseline and changes files.
  - An edit after review voids it (HASH_MISMATCH). REJECTED, INVALID or missing reviews leave every period unverified (`UNIVERSE_UNVERIFIED`).
  - Agents never write an ACCEPTED row.
  - Count exceptions (ED-22) carry D49's "never force 100".
- Tests: `test_research_membership.ReviewGate` (5). The rows-focused tests pass an explicit review (specification correction, D49).
- Reversible: yes.


### ED-28. Corporate-action event store (D50)
- Category C (implements D50). Status `AUTO_APPROVED`.
- Decision:
  - `corporate_actions.from_nse_json` converts saved NSE corporate-action responses into the existing `corporate_actions.py` records file (`nse/data/corporate_actions/actions.csv`), with the source JSON hash-verified.
  - Terms come from exact whole-subject patterns: `Bonus a:b`; a face-value split or consolidation with an integral ratio; `Rights a:b` and `Demerger`, recorded with their terms but no scale ratio; dividends.
  - Combined or unrecognised price events are returned as UNPARSED for manual review, never guessed.
  - Prices are never adjusted; a price-scale action inside a replayed history keeps G0 MANUAL (unchanged).
- Tests: `test_research_data.CorporateActionStoreD50` (3).
- Reversible: yes.


### ED-29. Rename continuity through verified ISIN lineage (D51)
- Category C (implements D51). Status `AUTO_APPROVED`. Resolves TD-13.
- Decision: `instruments.lineage` walks back through VERIFIED SYMBOL_CHANGE records. It joins a predecessor only when, in the bhavcopies:
  - every predecessor row carries the record's ISIN;
  - every successor row in its segment carries it too;
  - the predecessor has no row on or after the effective date, and the successor none before it.

  `inputs.load` relabels the predecessor rows (copies only; prices, ISIN and file provenance unchanged) so that one series spans the rename, and `apply_to_input` checks identity over the lineage. Any failed condition stops the join, records `LINEAGE_NOT_JOINED`, and keeps `SYMBOL_HISTORY_SPLIT` (DATA_INSUFFICIENT). A shared ticker or a similar name never joins. ISIN changes and mergers are never joined.
- QA correction, same day (prefix invariance): only evidence dated before the change can refuse a join. A contradiction on or after it (the old symbol still trading the same ISIN, or the new symbol's first row under another ISIN) is a dated `LINEAGE_CONFLICT` ERROR. A later ISIN change of the new symbol is a separate dated event. The old ticker's rows under another ISIN after the change are never joined.
- Tests: `test_research_instruments.LineageD51` (7, including `test_the_join_does_not_depend_on_later_files`).
- Reversible: yes.


### ED-30. Invalid non-EQ rows are isolated; EQ rows and format failures still refuse the file
- Category C. Status `AUTO_APPROVED` (MP1 backfill, 2026-11-09).
- Evidence: during the D47 backfill, 112 official files failed the whole-file rule because of rows outside EQ. 210 rows in all, in two kinds:
  - T0 (same-day settlement, from 2024-03-28): CLOSE is not a T0 trade price and lies outside the T0 high/low, e.g. SBIN T0 on 2024-04-08 at O/H/L 762, C 768.3;
  - E1 (partly paid) on 2021-02-16: ISIN printed as `DUMMY`.

  No EQ row in any of the 1,233 files is invalid.
- Decision:
  - A row of a series other than EQ that fails a *value* check (MalformedFileError) is rejected and listed in `BhavcopyFile.rejected_rows` with its line and reason; the file is kept.
  - An invalid EQ row, an unreadable series, a duplicate, or any format-level failure still refuses the whole file.
  - The coverage report lists the rejected rows per file.
- Rationale: research reads EQ only (DATA_REQUIREMENTS §2.2). Refusing 112 sessions for rows no scan uses would have cost real coverage without adding safety. The rejection is recorded, never silent.
- QA correction, same day: only `RowValueError` (prices, OHLC order, quantities, ISIN) is isolated, and only on a row whose structure is intact and whose series is an uppercase code (`[A-Z0-9]{1,4}`). Structural failures always refuse the whole file: field count, a non-empty 14th column, a TIMESTAMP or TradDt of another day (now checked before any value), and a lowercase or unreadable series. This also refuses a comma inside an EQ symbol. The 112 affected official files still load, isolating only their T0 and E1 rows.
- Tests: `test_nse_eod_evidence.NonEqRowIsolation` (5).
- Reversible: yes.

### ED-31. Unresolved calendar dates block only the timeframes whose range contains them
- Category C. Status `AUTO_APPROVED`.
- Decision: `inventory` readiness per timeframe counts unresolved dates inside that timeframe's required range only. The old global check made the four 2016-2019 UNRESOLVED Dhanteras rows (D48) block even Daily readiness in 2022.
- Fail-closed where it applies: the Yearly range that contains them stays not ready.
- Tests: `test_research_data.UnresolvedDateScope`.
- Reversible: yes.


### ED-32. Universe transcription build and identity records
- Category C (implements D49 and D51). Status `AUTO_APPROVED`.
- Decision:
  - **Universe files:** `nse/data/universe/nifty100_baseline.csv` (official list as of 31 Dec 2020), `nifty100_changes.csv` (23 events, 123 rows, plus 9 `RENAME` rows), `nifty100_count_exceptions.csv` (19 dated counts, each citing its one-sided release) and the converted `nifty100_universe.csv` (171 periods).
  - **How they were built:** mechanically from the primary agent transcription. The independent cross-check agreed on 122 of 123 rows; the exception is the JIOFIN symbol on 2023-07-20, which the release does not print and which is recorded as an inference.
  - **ISINs:** taken from the held bhavcopy at each date. Five pre-listing entities (Jio Financial, four "DUMMY" demerger placeholders) take the ISIN of the security that later listed, and each is flagged.
  - **Identity records:** `instrument_records.csv` holds LISTING and SYMBOL_CHANGE rows taken only from NSE `EQUITY_L.csv` and `symbolchange.csv`. 17 member ISINs have no current listing record and stay unresolved: 4 are absent from the list (HDFC, MINDTREE, PEL, TATAMTRDVR), and 13 trade under a later ISIN whose cause is not established.
  - **Review gate:** `nifty100_review.csv` has a header and no row, so every period is UNVERIFIED (D49). `membership.RENAME` keeps the seat across a symbol change.
- Verification: the rolled universe equals the independently transcribed official lists of Mar 2021, Sep 2021 and Mar 2022. All cited releases are byte-identical between the two agents' downloads. Every holiday date is in its circular's text.
- Tests: `test_research_membership.Renames` (2). The one-off formatting script is not product code. The artifact under review is the transcription files; conversion is reproducible from repository files (`nse/data/universe/README.md`).
- Superseded in part (2026-11-09): identity records by ED-37, review by ED-35.
- Reversible: yes.

### ED-33. D52: a PREVCLOSE discontinuity explained only by an excluded session without a file
- Category C (implements D52). Status `AUTO_APPROVED` (2026-11-09).
- Evidence: NSE serves bhavcopies for the Muhurat sessions of 2016-2025 and the two DR-switch sessions of 2024 (HTTP 200, strict parse). So the discontinuity that R-9 described is removed at source by holding those files (ED-34). The D52 rule therefore applies only where such a file is still not held.
- Decision: `scanner._explained_by_excluded_session` reclassifies a discontinuity as the INFO finding `PREVCLOSE_EXPLAINED_BY_EXCLUDED_SESSION` only when every one of these holds:
  - the official calendar classifies every date between the two held files;
  - none of those dates is a trading day;
  - at least one is `EXCLUDED_MUHURAT` or `EXCLUDED_SHORTENED`;
  - `corporate_action_coverage` (the hash-verified `coverage.csv` beside `actions.csv`) covers the symbol over the gap;
  - no recorded price-scale action, including `UNPARSED_PRICE_EVENT`, has its ex-date in the gap.

  Otherwise the discontinuity stays a detected `PRICE_DISCONTINUITY_IN_HISTORY` (G0 MANUAL).

  The finding is never called a corporate action. No candle is created. Recorded actions, identity findings and other warnings are unchanged.
- Sequence-dependent audit: D33 checks touches during an excluded session. A session with no candle cannot be checked, so `scanner._unobserved_excluded_sessions` lists them. Each adds an `EXCLUDED_SESSION_UNOBSERVED` warning and limitation. G1 is MANUAL when one falls inside the zone's span (leg-in or start candle to as_of), checked before any PASS. Nothing becomes ACTIONABLE through D52.
- QA hardening, same day:
  - the rule refuses when a file is held for the excluded session but lacks the symbol (a `NO_ROW_IN_FILE` finding on that date: not "no EOD file");
  - it also refuses when the action records are absent (coverage alone proves nothing).
  - The test of a missing trading day now calls the rule directly, because the scan-level version could pass with no candidates.
- Tests: `test_research_data.ExcludedSessionD52` (7).
- Reversible: yes.

### ED-34. Excluded-session bhavcopies are held in their own role
- Category C (implements D52 / D33). Status `AUTO_APPROVED`.
- Decision:
  - `eod_backfill.py download --include-excluded` fetches official files for calendar-excluded sessions.
  - They are ingested like every other file.
  - `eod_coverage` accepts them as `EXCLUDED_SESSION_D33`: held for the D33 touch check and PREVCLOSE continuity, never a candle (the overlay sets them aside, H1), and never counted as trading-day coverage.
  - Files on UNRESOLVED dates are held as evidence and stay VALIDATED, never ACCEPTED. (The four Dhanteras files were the case under D54; since D58, 2026-11-10, those dates are confirmed sessions and their files are ACCEPTED_FOR_RESEARCH.)
- Tests: `test_research_data` coverage tests and `ExcludedSessionD52`.
- Reversible: yes.

### ED-35. Row-level membership review (D53)
- Category C (implements D53; supersedes the single-row review of ED-27). Status `AUTO_APPROVED`.
- Decision:
  - `nifty100_review.csv` has one row per baseline row, change row and count exception (`row_key`, `row_sha256` of that row's exact content, `decision`, `reviewer`, `reviewed_on`, `notes`).
  - A period is verified only when its start row, its end row and every count exception it relies on are ACCEPTED with a matching hash. ED-48 adds a count-only approval that does not replace this `decision`.
  - Editing a row voids its own acceptance only (`stale_hash`).
  - `membership.review_template` writes the blank template; agents never fill a decision.
- Tests: `test_research_membership.ReviewGate` (7) and `ReviewCoversExceptions` (2).
- Reversible: yes.

### ED-36. Membership action ISIN_CHANGE
- Category C (implements D51 / D56). Status `AUTO_APPROVED`.
- Decision: an index seat that continues under a new ISIN, with the same symbol, is `ISIN_CHANGE` with `replaces_isin`. The old ISIN must be a member at that date; the period closes and a new one opens with the same seat. This makes no claim that prices are continuous: the identity layer treats an ISIN change as a separate dated event and never joins histories across it (ED-29).
- Tests: `test_research_membership.IsinChanges` (2).
- Reversible: yes.

### ED-37. When an ISIN change counts as evidenced
- Category C (implements D56). Status `AUTO_APPROVED`.
- Decision: an ISIN change seen in the bhavcopies (last session under the old ISIN, first under the new) counts as evidenced only through an official NSE corporate-action record. The record must:
  - be a price-scale or face-value action (`SPLIT`, `BONUS`, `CONSOLIDATION`, or an `UNPARSED_PRICE_EVENT` whose text is such an action);
  - belong to the instrument, under its symbol or a symbol of its official rename chain;
  - have its ex-date or record date equal to the first session under the new ISIN.

  The record's own `isin` field is not used: it often holds an older ISIN. Without such a record the change gets no `ISIN_CHANGE` record. The identity check then reports `ISIN_CHANGED_WITHOUT_RECORD` (DATA_INSUFFICIENT across the change). Names are never matched.
- QA correction, same day: a second rule ("the ex-date is the last session under the old ISIN, and the new ISIN starts the next trading day") was first applied and then withdrawn. It is a convention, not evidence. The independent review found that the two records it matched print record dates on the Saturday after the change, so D56 ("ambiguous evidence stays DATA_INSUFFICIENT") applies.
- Evidence:
  - 30 ISIN changes of member symbols are visible in the 2016-2025 bhavcopies.
  - 27 match, including MCDOWELL-N 2018 through its official rename to UNITDSPR.
  - Unevidenced, never joined: BAJFINANCE 2016-09-09 and GRASIM 2016-10-07 (record dates Saturday 2016-09-10 and 2016-10-08) and YESBANK 2020-03-16 (no official price event).
  - All 15 changes since 2021 match: 13 during index membership, plus IRCTC and MAZDOCK outside it.
  - Records: `nse/data/universe/instrument_records.csv` (219, all source-verified) and `identity_report.json`.
- Identity rebuild (same day):
  - An instrument with an ISIN change gets a LISTING on its earliest observed ISIN from its first held session (source: that bhavcopy archive), then one `ISIN_CHANGE` per evidenced change.
  - A member ISIN missing from EQUITY_L (HDFC, MINDTREE, PEL, TATAMTRDVR, KOTAKBANK's pre-2026 ISIN, YESBANK's post-2020 ISIN) gets a LISTING from its first held session; its end is not recorded without official evidence.
  - A SYMBOL_CHANGE takes the ISIN traded on both sides of the rename (SRTRANSFIN to SHRIRAMFIN 2022-12-20: INE721A01013, not the later EQUITY_L ISIN).
  - PROMPT-01 audit correction: five SYMBOL_CHANGE records for renames before 2016 carried today's EQUITY_L ISIN: TISCO to TATASTEEL, JSWSTL to JSWSTEEL, CHOLADBS to CHOLAFIN, SOLAREX to SOLARINDS and BAJAUTOFIN to BAJFINANCE. In point-in-time state that made two ISINs active under one symbol, an escalated UNKNOWN_INSTRUMENT that would have blocked those scans. A pre-history rename now keeps its record only when its ISIN is the one traded on the new symbol's first held session; otherwise it is dropped and reported (`identity_report.json` `pre_history_renames_dropped`), never guessed. Regression test: `test_research_instruments.RealIdentityRecords`.
  - Reproducible: `.claude/skills/nse-data-engineering/scripts/identity_collect_obs.py`, then `identity_build_records.py`, from the raw archives, `nse/data/universe/build/instrument_records_base.csv` and `actions.csv`. The re-run reproduced the file byte-identical.
  - Result: the identity check over every member observation 2016-2025 leaves exactly three findings, the unevidenced changes above. Each is a dated `ISIN_CHANGED_WITHOUT_RECORD` ERROR.
- Reversible: yes.

### ED-38. Legacy bhavcopy variants found by the 2016-2020 backfill
- Category C. Status `AUTO_APPROVED`.
- Evidence (D55 download): 2 of 1,242 official files differ from the verified LF / 14-column layout.
  - `cm10JUL2017bhav.csv.zip`: CRLF on every line and a 13-column header (no trailing empty column).
  - `cm13JUL2020bhav.csv.zip`: the same, plus its single member stored as `cm13JUL2020bhav.csv/cm13JUL2020bhav.csv`, and every TIMESTAMP written `13-Jul-20`.
- Decision: three explicit, exact variants:
  - schema `LEGACY_13_CRLF`: CRLF on every line with no other CR, exactly the 13-column header;
  - schema `LEGACY_13_CRLF_SHORTDATE`: inside `LEGACY_13_CRLF` only, every TIMESTAMP exactly the file date as `DD-Mon-YY`;
  - archive layout `<name>/<name>` as the only member (`nse_bhavcopy.archive_layout_ok`).

  `SourceInfo.member_name` records the real stored path. Everything else is still refused: LF with 13 columns, CRLF with 14, mixed endings, a stray CR, another short date, mixed date forms, another folder, two members.
- Tests: `test_nse_eod_evidence.LegacyCrlfSchema` (2) and `LegacyShortDateAndNestedMember` (2).
- Reversible: yes.

### ED-39. Corporate-action collection and coverage rules (D56)
- Category C (implements D56 / D50). Status `AUTO_APPROVED`.
- Decision:
  - `.claude/skills/nse-data-engineering/scripts/collect_corporate_actions.py` fetches NSE's corporate-action records for every historical member over 2016-2025. It is rate limited, resumable and never overwrites a file. Each raw response is saved and logged with its SHA-256.
  - `coverage.csv` lists a symbol only when its response was a non-empty list whose bytes still match the log. An empty response cannot be told apart from "no events": NSE files events under the current symbol, so former tickers return `[]`.
  - Price events whose terms do not match an exact pattern are stored as `UNPARSED_PRICE_EVENT`, a price action that keeps G0 MANUAL. They are never dropped.
- Limitation: NSE does not document the API's completeness. Coverage means "an official response was held", not "complete"; the PREVCLOSE discontinuity check stays active.
- Audit correction, same day:
  - Two official abbreviated splits ("Fv Splt Frm Rs 10 To Re 1", JSWSTEEL 2017; SOLARINDS 2016) were classified as "no price event" and dropped.
  - Classification is now fail-closed: a part is skipped only when it matches a known non-price form (AGM, including three printed misspellings; EGM; buyback; change of registrar). A dividend spelling ("Int Div", "Divdend") is a dividend. Anything else unrecognised is `UNPARSED_PRICE_EVENT`.
  - `actions.csv` regenerated: 2,064 events, 12 added, none removed.
- Tests: `test_research_data.CorporateActionStoreD50` (including `test_abbreviated_splits_and_unknown_subjects_are_never_skipped`).
- Reversible: yes.

### ED-40. `--corporate-actions` on scan, scan-history, backtest and replay-decision
- Category C. Status `AUTO_APPROVED`.
- Decision: one flag loads `actions.csv` and its sibling `coverage.csv` (`inputs.corporate_action_config`) into `ScanConfig`. The scanner, backtest and decision replay share one path. Without the flag there is no coverage, so D52 explains nothing. A missing file is not evidence that no events occurred.
- Superseded in part by ED-46: the loader return is still `(None, None)` when the flag is absent, but G0 is MANUAL (`CORPORATE_ACTION_COVERAGE_UNKNOWN`) instead of the previous pass.
- Reversible: yes.

### ED-41. Full validation, bounded memory: load_many(keep=)
- Category C. Status `AUTO_APPROVED`.
- Evidence: with 2,478 archives (2016-2025), holding every row (about 5 million `BhavRow` objects with Decimal fields) exceeded the 8 GB machine. The process swapped, so four real-data tests took 42 minutes.
- Decision:
  - `nse_bhavcopy.load_many(paths, manifest, keep=)` still parses and validates every row of every file. `series_counts` and `non_eq_only_symbols` still describe the whole file; only the rows `keep` accepts stay in memory.
  - `inputs.load` keeps the requested symbols and their SYMBOL_CHANGE chains. A first pass builds a compact (ISIN, symbol) to first/last-date index. A second pass, over those dates only, adds the rows of any other symbol that traded one of their ISINs, which is exactly what `apply_to_input` reads for renames and reused ISINs.
  - `run_all` keeps no rows (dates only) or only INFY. `inventory` keeps the requested symbols. `instruments-check` keeps observations, not rows.
- Tests:
  - `test_research_instruments.FilteredLoadingEquivalence`: four identity cases give byte-identical inputs with and without filtering. A mutant without the second pass fails it.
  - The real-data inventory tests now take 6m40s.
- Reversible: yes.

### ED-42. An UNRESOLVED calendar date is listed, not a calendar-vs-EOD disagreement
- Category C (implements D54: "do not block unrelated readiness"). Status `AUTO_APPROVED`.
- Decision: `run_all.check_local_data` lists a month's UNRESOLVED dates under `info`. A required window that contains one still fails (fail-closed); one that does not is unaffected. Before this change, the four Dhanteras dates of 2016-2019 failed every window, including 2022 Q1.
- Tests: `test_research_data.RealWindow` (`test_unresolved_dates_outside_a_window_do_not_fail_it`, and the CAL-2 window in `test_runner_required_window`).
- Reversible: yes.

### ED-43. A first period that starts before calendar coverage is partial, not a replay failure
- Category C. Status `AUTO_APPROVED`.
- Evidence: with history from Friday 2016-01-01, every real scan became DATA_INSUFFICIENT (`CALENDAR_COVERAGE: 2015-12-28`). The overlay asked the calendar about the days of the first Weekly period before the first held candle, and the calendar covers 2016 onwards only.
- Decision (`mtf_freshness._build_series`, rule H2a in the module docstring):
  - A day of the first period before the first held candle that the calendar does not cover (`COVERAGE_ERRORS`, declared by `NseCalendar`) counts as an expected session. That first period is therefore `partial_first_period`, which is the restrictive reading.
  - The same applies to a pre-history day the calendar cannot classify (UNRESOLVED), which happens when ED-44 restarts history after such a date in the same period. Inside the history an UNRESOLVED day still truncates (L10), and every other coverage error still stops the replay.
- Tests: `test_mtf_freshness` (three H2a cases, including the in-history L10 control).
- Reversible: yes.

### ED-44. History used by a scan starts after the last UNRESOLVED calendar date
- Category C (implements D54: "do not block unrelated readiness"). Status `AUTO_APPROVED`.
- Evidence: after D55, every 2025 scan was DATA_INSUFFICIENT. The four UNRESOLVED Dhanteras dates of 2016-2019 end every series (L10: a series never runs across a date whose sessions are unknown), so no candle after October 2016 was usable.
- Decision: `scanner.scan_symbol` replays only the candles after the latest UNRESOLVED date between the first candle and as_of. The cut is a dated WARNING finding and a limitation, both `HISTORY_STARTS_AFTER_UNRESOLVED_DATE`.
  - Nothing is stitched across the date. Timeframes that need older history lose it, which is fail-closed (ED-31's scope rule).
  - Identity and data-quality errors dated before the cut still apply.
  - The cut depends only on the calendar and as_of, so it is point in time; a scan before the date is unchanged.
- Real effect (scan 2025-12-26, `nse/output/scan-d52-d56-2025-12-26-v4`): INFY, RELIANCE, HDFCBANK, TMPV and ETERNAL are evaluated on all six timeframes. The excluded-session G0 MANUAL of R-9 is gone. BAJFINANCE and YESBANK stay DATA_INSUFFICIENT (unevidenced ISIN changes). No candidate is ACTIONABLE.
- Tests: `test_research_data.ExcludedSessionD52.test_history_starts_after_the_last_unresolved_date`.
- Reversible: yes. Owner question CAL-2 / D54: classifying the four dates would remove the cut.
- Status (2026-11-10): D58 classified the four dates (option A). No UNRESOLVED row remains, so the cut does not apply to any current scan (a real 2025-12-26 scan replays from 2016-01-01). The rule stays in force for any future UNRESOLVED date; tests inject one.

### ED-45. Research runs orchestrate the scanner; they do not restate the gates
- Category C. Status `AUTO_APPROVED`.
- Decision: `nse/research/pipeline.py` is the research-run entry. It calls `scanner.scan` and `risk.plans_for_scan`, copies every symbol status, candidate status and blocked zone, and writes `research.json`, `trade_plans.json` and `research_report.md` beside the existing scan reports.
  - Candidate status is never replaced by a plan status. `authorises_order` is false and `selected_quantity` is null on every plan. Buffer combinations are omitted so a range is not read as one order.
  - Monthly trades, open positions and the one-order allowance are three checks. A missing count is `NOT_SUPPLIED`. One supplied count does not pass the other two. Journal counts come from `store.portfolio_at`, which ignores events after `as_of`. A research run does not write the journal.
  - `research.json` embeds the scan, so `generated_at` is whatever the caller passed. The research JSON does not read a clock. `run_manifest.json` records the wall clock and the code revision (ED-18).
  - `run_history` accepts no portfolio, or a function of `as_of`. One snapshot is refused, because a later cancellation would clear an earlier date. `--journal` is opened read-only and is re-read at each as-of. A caller count passed with `--as-of-list` is labelled `CALLER_PORTFOLIO_REUSED`.
  - The trade-plan section prints blocking and unknown constraints beside any quantity range. A range next to a blocking constraint is not a size to place.
  - Report rows are sorted by symbol, zone creation time and zone id. `pre_entry_score` is not a rank.
- Implements: the existing scanner, qualification, risk and journal contracts. No trading rule is added.
- Affected files: `nse/research/pipeline.py`, `nse/research/store.py` (`portfolio_at`), `nse/research/cli.py` (command registration), `tests/test_research_pipeline.py`.
- The envelope adds a stable zone reference (symbol, timeframe, side, start time, created time). The engine index id is unchanged. `compare_zone_identity` does not treat a new dataset id as a new zone. An ambiguous or unresolved reference withholds the plan and the quantity. `completeness` is `COMPLETE`, `PARTIAL`, or `FAILED` as already named in the architecture contract. `UNIVERSE_UNVERIFIED` stays a limitation on a complete run, and `full_universe_scan` is false.
- Tests: `python3 -m nse.validation.run_all --group integration`
- Reversible: yes. Removing the module and the command registration restores the previous `scan` command. `scan` itself is unchanged.

### ED-46. Monthly TRIGGERED insert is atomic; G0 requires verified corporate-action coverage
- Category C. Status `AUTO_APPROVED`.
- Decision:
  - `journal_event` for `TRIGGERED` counts the IST month and inserts the row inside one `BEGIN IMMEDIATE` transaction. A second connection waits, then sees the committed row. This closes the two-connection probe that reached 11 trades (P01 audit, 2026-11-09). The API lock is not a substitute.
  - G0 is `MANUAL` with `CORPORATE_ACTION_COVERAGE_UNKNOWN` when no coverage file is supplied, and `CORPORATE_ACTION_COVERAGE_UNVERIFIED` when the symbol's replayed history is outside a hash-verified window. An empty event list or an empty official response is not that window (P01-H1). A verified window with no recorded price-scale action can still pass this check.
  - `run_manifest.scan_input_paths` fingerprints `--instruments` and `coverage.csv` beside the corporate-action file (P01-H2).
  - A backtest of an unverified universe file, not only an ad-hoc list, carries `SURVIVORSHIP_UNCONTROLLED` (P01-H4).
- P01-H3 review (code re-read 2026-11-09, no behaviour change to those four):
  - ED-33: `scanner._explained_by_excluded_session` still requires the calendar, coverage and action records, no trading day in the gap, an excluded session, no held file for that session, and no price-scale ex-date in the gap. Otherwise the discontinuity stays `PRICE_DISCONTINUITY_IN_HISTORY`. `qualification._g1` stays MANUAL on `EXCLUDED_SESSION_UNOBSERVED`.
  - ED-40: `inputs.corporate_action_config` still returns no coverage when the flag or the sibling `coverage.csv` is absent. It does not treat that absence as "no events". ED-46 changes only the G0 result of that absence, recorded on ED-40 as a partial supersession.
  - ED-43: `mtf_freshness._build_series` `day_state` treats a pre-history uncovered or unclassifiable day as an expected session (`partial_first_period`) and does not stop the replay. An UNRESOLVED day inside the history still truncates.
  - ED-44: `scanner.scan_symbol` drops candles on or before `_last_unresolved_date` and records `HISTORY_STARTS_AFTER_UNRESOLVED_DATE`. It does not join the two sides.
- Tests: `test_research_store.Journal.test_two_connections_cannot_both_commit_an_eleventh_trigger`, `test_research_gates.G0.test_corporate_action_coverage_unknown_unverified_and_covered`, `test_research_run_manifest.Manifest.test_identity_and_coverage_files_change_the_dataset_fingerprint`, `test_research_backtest.EndToEnd.test_a_synthetic_trade_from_a_point_in_time_signal`.
- Reversible: yes.
- Alternatives considered: folding plans into `scanner.py` (mixes presentation and portfolio reads into the qualification path); a second gate implementation (rejected; A9).

## Assumption register

| ID | Assumption | Where | Risk if wrong | Check |
|---|---|---|---|---|
| A-1 | Naive timestamps are IST | candles (`marketdata._session`), journal | Month and day boundaries shift | ED-8; journal refuses mixes |
| A-2 | A CSV is date-ordered around a BAD_DATE row | `marketdata._bad_date` | An earlier scan used a file with a lost row | `ERROR_DATE_BOUND_INFERRED` warning |
| A-3 | Pine's detector on the same completed candles is the right source for Pine-only breach / touch state | `structure.pine_only_zones` | A Pine zone deleted by data the engine never saw | Gaps never delete a zone; only observed closes do |

### ED-47. Provisional membership research window (D59)
- Category C.
- Status `AUTO_APPROVED`.
- Decision: a non-ad-hoc universe whose as-of is before 2020-12-31 carries `MEMBERSHIP_BEFORE_PROVISIONAL_WINDOW`. An ad-hoc list does not, because it is already `UNIVERSE_UNVERIFIED` and is not a Nifty 100 membership study. Candles before the date stay available as indicator history. No membership row is marked accepted, and no pre-2020 constituent is invented.
- Implements: D59
- Affected files: `nse/research/universe.py`, `nse/research/models.py`, `nse/research/backtest.py`, `tests/test_research_reports.py`, `tests/test_research_backtest.py`
- Tests: `test_research_reports`, `test_research_backtest.ProvisionalWindow`
- Reversible: yes. Removing the limitation and the constant restores the previous labels. The review file is untouched.

### ED-48. Membership review scopes do not certify a period
- Category C.
- Status `AUTO_APPROVED`.
- Decision: `nifty100_review.csv` may add `count_approval` and `mapping_approval` after the D53 columns. A six-column file still reads as before. `decision` `ACCEPTED` remains full approval of that row and is never copied into the new columns.
  - `count_approval` `APPROVED` is valid only on an `exception:` row. It passes the count gate and does not verify a period.
  - `mapping_approval` `APPROVED` is valid only on a `change:` row. It records the symbol and the add or remove direction. It does not verify a period, including an open-ended addition.
  - A period is verified only when its source verifies, its start row and its end row (if any) have `decision` `ACCEPTED` with a matching hash, the count gate passes, and any identity check is clear. `REJECTED` on `decision` or on `count_approval` fails the count gate.
  - A scope on the wrong kind of row, a bad token, a missing reviewer or a non-ISO date is a problem and approves nothing. Agents still never write `decision` `ACCEPTED`.
- Implements: D60 and D61 (owner Yash Jain, 2026-11-11). The stored scope value is `APPROVED`, not `decision` `ACCEPTED`. The 25 exception rows and the ten E03 rows are recorded in `nifty100_review.csv`. Their `decision` cells stay blank. 236 other rows have no reviewer. `decision` stays blank on all 271 rows.
- Affected files: `nse/research/membership.py`, `tests/test_research_membership.py`, `nse/data/universe/README.md`
- Tests: `test_research_membership.ApprovalScopes`
- Reversible: yes. A reader that ignores the two columns restores the single decision field. Existing `ACCEPTED` rows keep their meaning either way.

### ED-49. Symbol-date eligibility does not borrow another symbol's failure
- Category C.
- Status `AUTO_APPROVED`.
- Decision: `dataset_eligibility.certify_members` classifies each symbol-date from its own gates. A failed identity or membership gate names that symbol and date and does not change another row. Passing rows are `CERTIFIED_SUBSET`. `COMPLETE_NIFTY100` is returned only when the caller passes `index_evidence_resolved=True` and every required member passes. The real Nifty 100 ledger does not pass that flag while any membership `decision` is blank or any identity finding remains. `authorises_order` is false.
- Implements: D60 and D61 stay limited approvals. This does not accept a membership period.
- Affected files: `nse/research/dataset_eligibility.py`, `tests/test_research_dataset_eligibility.py`, `nse/validation/architecture.py`, `nse/validation/run_all.py`
- Tests: `test_research_dataset_eligibility`
- Reversible: yes. Deleting the module removes the label. Scanner statuses are unchanged.

### ED-50. Reproducible P0 certification build; PREVCLOSE does not show a price-scale event
- Category C (GTF P0, gtf-p0-data-certification sections 12-14). Status `AUTO_APPROVED`. 2026-11-12.
- Problem: `classify_symbol_date` and `certify_members` had no production caller. The 2026-11-11 counts (123,778 excluded member-dates), `P0_RESEARCH_ELIGIBILITY_MATRIX.csv` and `P0_EXCLUSION_SUMMARY.csv` were produced outside any committed tool, and that matrix records price continuity as `NOT_RESCANNED_THIS_PASS`.
- Decision: `nse/research/p0_certification.py` derives every gate for every Nifty 100 member-date 2020-12-31..2025-12-31 from the files on disk and classifies it with `dataset_eligibility`. It writes `P0_CERTIFIED_RESEARCH_UNIVERSE.csv`, `P0_RESEARCH_EXCLUSION_REGISTER.csv` (one row per run of identical gates), `P0_MEMBERSHIP_REFERENCE_HISTORY.csv` and `P0_CERTIFICATION_SUMMARY.json` (input hashes, reconciliation) in `docs/product-discovery/p0/`, and optionally the per-symbol-date matrix (kept out of git under `nse/output/`). Outputs carry no timestamp; a rebuild on the same inputs was byte-identical.
- Gate rules that are new here:
  - Corporate action: no saved response proves the API's completeness (R-10), so `COVERED_WITH_VERIFIED_EVENTS` is reported as `EVENTS_VERIFIED_COMPLETENESS_NOT_PROVED` and does not pass. The build never emits `COVERED_NO_EVENTS_PROVED`. This is stricter than `dataset_eligibility`'s passing set, which is unchanged for a future source that proves completeness.
  - Price continuity, per step: a recorded price-scale action in the step (looked up under every symbol the verified instrument records link, because NSE files events under the current symbol), an ISIN change, a PREVCLOSE break, or a session range wholly outside 15% of the prior close each fail. The 15% band is a screen: it names no event and no ratio.
  - GTF: `NOT_EVALUATED_IN_P0`, fail closed. The pipeline is not run per member-date.
- Evidence for the price rule: every recorded split, bonus, rights issue and demerger with an EQ row on both sides in 2020-12-01..2025-12-31 (55 events, 32 legacy and 23 UDiFF files) has PREVCLOSE equal to the unadjusted prior close. Example: TATASTEEL 1:10 split, `cm28JUL2022bhav.csv.zip`, PREVCLOSE 959.4, open 98.1. A PREVCLOSE-only check called that step continuous; the regression test is `test_a_split_with_an_intact_prevclose_chain_is_not_continuous`.
- Result on the 2026-11-12 inputs: 123,778 member-dates, 0 certified, label `NO_CERTIFIED_SYMBOL_DATES` on all 1,234 sessions. 72,662 member-dates pass membership; every member-date fails the corporate-action gate. One unexplained scale gap (ADANIENSOL 2024-11-21, range 697.25..724.00 against 871.55) stays excluded pending investigation; it is not called an error or a corporate action.
- Limitations: the gate is per step, so a study over a window needs every step in it to pass. A small event (a rights issue moves the price a few percent) is not visible to the screen. A break across the seven held Muhurat or shortened sessions is not D52 (D52 requires that no file is held) and fails closed.
- Alternatives considered: trusting the PREVCLOSE chain (rejected on the 55-event evidence); passing `COVERED_WITH_VERIFIED_EVENTS` as the eligibility module allows (rejected: a non-empty body does not prove completeness, P0 master prompt Part 8); writing over the untracked 38 MB matrix (rejected: kept, now superseded).
- Affected files: `nse/research/p0_certification.py`, `tests/test_research_p0_certification.py`, `nse/validation/architecture.py`, `nse/validation/run_all.py`, the four outputs above.
- Tests: `test_research_p0_certification` (19 unit tests on SYNTHETIC rows plus 4 consistency checks on the committed outputs).
- Not changed: the scanner, G0, `corporate_actions.load_coverage`, `dataset_eligibility`, any methodology gate. R-12 records the scanner consequence.
- Reversible: yes.
- Superseded in part by ED-51 (2026-11-13): the GTF gate is no longer evaluated by the P0 build (D63).

### ED-51. P0 build: six data gates and corporate-action evidence tiers (D62, D63)
- Category C. Status `AUTO_APPROVED`, implementing owner decisions D62 and D63. 2026-11-13.
- Decision:
  - `dataset_eligibility.DATA_GATES` names the six data gates. `classify_symbol_date` and `certify_members` take an optional `required_gates`. The default is still all seven gates, so every existing caller and test is unchanged. An unknown or empty list is refused. This is the one classifier, not a second gate architecture.
  - `p0_certification` (build 1.1.0) classifies with `required_gates=DATA_GATES`. Every output row carries `certification_scope=P0_DATA` and `gtf_trade_eligibility=NOT_EVALUATED_NOT_A_P0_GATE`.
  - `corporate_actions.evidence_tier(body_status, price_integrity_passed)` returns `CA_RESPONSE_PRESENT_NOT_COMPLETE` for a hash-verified, non-empty body with no unparsed price subject on a symbol-date whose EOD and price-continuity gates pass, and `CORPORATE_ACTIONS_UNVERIFIED` otherwise. It never returns `CA_COMPLETENESS_VERIFIED`: no source proves completeness. The tier sits beside the gate and never changes it. Every row keeps the `CORPORATE_ACTIONS_UNVERIFIED` limitation.
  - `research_use`: `CERTIFIED_P0_DATA` only when every data gate passes. `EXPLORATORY_ONLY_NOT_CERTIFIED` when only the corporate-action gate fails and the tier is the weaker one. `EXCLUDED` otherwise. Exploratory rows appear only in the git-ignored matrix and in the summary counts, never in the certified file.
- Integrity is not completeness. Integrity means these bytes are the saved response, it is not empty, and it parsed. Completeness means the API listed every event in the window. Only completeness can pass the gate.
- Result on the 2026-11-13 inputs: 123,778 member-dates; 0 certified; 108,325 carry `CA_RESPONSE_PRESENT_NOT_COMPLETE`; 68,143 are exploratory-only; 72,173 fail only the corporate-action gate.
- Tests: `test_research_dataset_eligibility.DataGateScope`, `test_research_p0_certification.EvidenceTier` and `CommittedOutputs`.
- Reversible: yes.

### ED-53. Corrections from the independent review of the P0 build (2026-11-13)
- Category C. Status `AUTO_APPROVED`. The review was a separate read-only agent, which traced 7 sample records from source to output. It found no wrongly certified record. These are minimal corrections, not a rewrite.
- F1 (in a committed output): register runs were keyed on the symbol's own member-dates, so a run spanned sessions on which the symbol was not a member, and its evidence cited the wrong period (BANKBARODA, PNB, JIOFIN, JINDALSTEL, ZYDUSLIFE). Runs now use the window's session index, and the key includes the membership period, the evidence tier and the research use. The register gained `membership_period_from`, `corporate_action_evidence_tier`, `research_use` and `limitations`. 1,662 rows became 1,667.
- F2: a second `coverage.csv` row for one symbol silently replaced the first and could hide an unparsed subject. It is now refused.
- F3: a date the calendar cannot classify dropped out of the build, and a step across it could pass. Such a member-date now gets a row with calendar `UNRESOLVED`, and a step across it is `CALENDAR_UNRESOLVED_ON_STEP` (D54). There are none in the window today.
- F4: `dataset_eligibility` still passed `COVERED_WITH_VERIFIED_EVENTS`, which is the D62 middle tier. The corporate-action gate now passes only `CA_COMPLETENESS_VERIFIED` or `COVERED_NO_EVENTS_PROVED`. `required_gates` must include all six data gates. This is stricter; no current output changes.
- F5: `member_dates_equal_certified_plus_excluded` was a tautology. It is replaced by an independent count from `Universe.members`, plus a check that every excluded date is in exactly one register row. New tests cover `identity_value`, `corporate_action_bodies` (hash mismatch, `[]`, retry, duplicate, unparsed) and the register across gaps.
- F7: `inputs_sha256` now includes a digest of every saved corporate-action response and the builder's own source.
- F8: `scale_gap` delegates to `corporate_actions.price_scale_gap` (one definition, ED-52).
- Not changed (recorded): `linked` symbols come from `instruments.history` over all records. That fails closed today because `identity_value` rejects an unverified record (F8). There is no synthetic end-to-end `build()` fixture yet (F5).
- Result: certified 0 and every gate count unchanged; the rebuild is byte-identical.
- Tests: `test_research_p0_certification` (34 tests), `test_research_dataset_eligibility` (adds F4 cases).
- Reversible: yes.

### ED-54. Milestone 1: verified-rename policy, completeness register, CSV screen, end-to-end fixture (2026-11-15)
- Category C. Status `AUTO_APPROVED`. Implements D51, D62 and D63 and closes review residual REV-1. No owner decision is made here.
- Verified-rename policy (`nse/research/instruments.py`):
  - `rename_links()` publishes every SYMBOL_CHANGE record with its evidence file, hash, line and status.
  - `verified_rename_names()` joins tickers only through VERIFIED records along a single-ISIN chain.
  - `verified_rename_into(records, symbol, after, on_or_before)` is the dated join for one step. Two candidates are ambiguous and give none.
  - The P0 builder uses only these. The prior close of a step may sit under another ticker only on the step of that verified rename. Before, `instruments.history()` linked over all records, including unverified rows and later renames.
- Completeness register (`nse/research/corporate_actions.py`, D62, OD-CA-1):
  - `nse/data/corporate_actions/completeness.csv` (`COMPLETENESS_COLUMNS`). A row proves a window only when its cited source hashes to the recorded SHA-256 and `owner_decision` is a decision id (`D<n>`). Any other row is ignored. A malformed file is refused.
  - With a proved window, a hash-verified response with no unparsed subject gives `CA_COMPLETENESS_VERIFIED`, and `[]` gives `COVERED_NO_EVENTS_PROVED`. Without one, nothing passes.
  - The file does not exist; 0 windows.
  - The builder (1.2.0) reports `completeness_register` and `rename_links` in the summary and fingerprints the register in `inputs_sha256`.
- User CSV inputs (`marketdata.from_csv`) run the same R-12 price-scale screen as official archives, whatever the file states about adjustment. The scanner holds G0 on the finding. There is no source-specific bypass.
- Tests:
  - `test_research_p0_build_e2e`: synthetic end-to-end `build()` through every gate state, determinism, and refusal of a tampered archive, a duplicate coverage row or an unreadable register. 11 tests.
  - `test_research_identity_policy`: 10 tests.
  - `test_research_p0_certification.CompletenessRegister`: 5 tests.
  - `test_research_price_scale_r12`: 25 tests, including 5:1 split, bonus 1:2, consecutive events, a mis-dated action, duplicate actions, missing evidence and user CSV.
- Result on real data: the certified file, register, history and matrix were byte-identical to build 1.1.0's. The summary changed only by its version, input fingerprint and two new keys. None of these outputs is committed. Certified 0, because the register is empty.
- Measured, not changed: the 15% band. Over 123,352 member steps with no recorded action, false positives are 1 / 3 / 4 / 21 / 97 at 15 / 12 / 10 / 8 / 5%. Recorded events missed at 15% are 26 of 125 (all rights issues, 3 small bonuses, 4 demergers, 6 unparsed). No price-only rule separates them from ordinary moves.
- Reversible: yes.

### ED-55. Milestone 1 independent review: latent fail-open paths closed (2026-11-15)
- Category C. Status `AUTO_APPROVED`. Fail-closed hardening only; no gate is relaxed and no owner decision is made.
- The review was a separate read-only agent. It checked all 123,778 rows and all 1,667 register intervals, and re-derived all six gates on a 60-row random sample from raw files (`random.Random(20261115)`): 0 mismatches. It found no wrongly certified row, and 0 rows are certified. It ran 33 adversarial probes and found 5 medium latent fail-open paths. Corrections, builder 1.3.0:
  - M-1: a saved body is JSON-parsed. Anything other than a list of objects with a text `subject` is `MALFORMED_RESPONSE` and never reaches the middle tier.
  - M-2: an empty body that exists only in `raw/` is hash-verified against `collection_log.jsonl`. Disagreeing retries are `CONFLICTING_RESPONSES`. An unverified body never passes, even with a register window.
  - M-3: an empty body of a ticker joined by a verified rename is `EMPTY_RESPONSE_RENAMED_TICKER` and never passes, because NSE files events under the current ticker (ED-39). 6,432 member-dates on 10 tickers were relabelled; all already failed.
  - M-4: a completeness-register row counts only when its `owner_decision` is owner-approved (the log's approved status) in DECISION_LOG.md and its source is not a saved API response.
  - M-5: a step containing an excluded session fails even when PREVCLOSE happens to equal the prior regular close (`STEP_ACROSS_EXCLUDED_SESSION`). HDFCBANK 2024-03-04 and TATACONSUM 2024-05-21 moved from exploratory to excluded.
  - L-1: renames under two ISINs on one ticker join nothing, and a step's rename join needs the record's ISIN to equal the period's.
  - L-3: the input fingerprint includes the deciding modules, the collection log and the decision log.
  - L-4: the builder refuses a universe file that differs from a fresh ledger conversion.
  - L-5: a stronger e2e overlap check.
- Result: certified 0, exploratory 73,366, price-gate failures 1,132, register 1,671 rows. Two rebuilds are byte-identical.
- Second review round, builder 1.4.0 (the same reviewer re-ran its probes against 1.3.0 and reported residual and new latent paths). Corrections:
  - N-1 and R-1: `rename_state()` classifies a ticker from ALL SYMBOL_CHANGE records as NONE, CURRENT, OLD or AMBIGUOUS. Only NONE and CURRENT can pass the corporate-action gate. An empty body of any renamed ticker never passes. An OLD or AMBIGUOUS ticker's response is `RESPONSE_OF_RENAMED_AWAY_TICKER`. An AMBIGUOUS ticker's price gate is `AMBIGUOUS_RENAME_HISTORY`.
  - R-2: a decision qualifies for the completeness register only when it is owner-approved (the log's approved status) and its DECISION_LOG entry carries a completeness acceptance marker naming the source and windows. A general approval (D57, D62...) never qualifies. Today none qualifies. **Superseded for marker shape by ED-56 / D66:** the qualifying marker is now `- **Completeness window accepted:**` with two source hashes and a reconciliation hash; the legacy single-hash `- **Completeness source accepted:**` never qualifies.
  - R-3: a register source is refused when its bytes match any saved API response or its content has the API's shape.
  - N-2: the real build refuses to run when the ledger check cannot be made.
  - N-3: a price-type entry with an unreadable ex-date or a non-EQ series counts as unparsed, and an empty subject is malformed. All 2,326 real entries are EQ with readable ex-dates.
  - L-3: `membership.py` is fingerprinted.
- Real-data effect of the second round: none. Certified file, register, history and matrix are byte-identical to 1.3.0.
- Third review round, builder 1.5.0:
  - N-3b: the unparsed-entry count now uses the parser's own predicates, with no stripping or defaulting. A price-type or unrecognised entry the parser drops is always counted.
  - R2-A and R2-B: a decision qualifies only through a marker bullet inside its own entry, `- **Completeness source accepted:** <sha256> <SYMBOL> <from>..<to>[; ...]`. A register row must match one item exactly: bytes, symbol and window. This also closes R3-A, other forms of the same data, because the owner names the exact bytes.
  - R2-C: the ledger check is required whenever the real universe file is used, however its path was passed.
  - O-2: a renamed-away or ambiguous ticker's response earns no exploratory tier.
  - Real-data effect: none. Row-level outputs are byte-identical to 1.4.0. Tests: 178 across the seven P0 modules.
- Tests: `test_research_p0_build_e2e` (12), `test_research_p0_certification`, `test_research_identity_policy`, `test_research_corporate_actions`, `test_research_dataset_eligibility`, `test_research_price_scale_r12` and `test_research_membership`: 177 together.
- Reversible: yes.

### ED-52. R-12: G0 holds on an unexplained price-scale gap (D64)
- Category C. Status `AUTO_APPROVED`, implementing owner decision D64. 2026-11-13.
- Wrong assumption found: `marketdata.from_bhavcopy` labelled a PREVCLOSE break "possible unadjusted corporate action", and R-10 relied on that break to reveal an event the API omits. NSE prints the unadjusted prior close on an ex-date (ED-50), so a split or bonus never produces that break. The existing synthetic test models a split as an adjusted PREVCLOSE; the real files do not. Consequence before this change: a symbol whose hash-verified, non-empty response omits a split passed G0's coverage check, and the raw scale break reached zone detection with G0 `PASS`.
- Decision:
  - `corporate_actions.price_scale_gaps()` screens each held EQ session. A session whose whole range lies more than `SCALE_GAP_BAND` (15%) from the last held close is a `PRICE_SCALE_GAP`. `price_scale_gap()` is the single definition of the band test.
  - `marketdata.from_bhavcopy` emits a `PRICE_SCALE_GAP` finding.
  - `scanner.scan_symbol`: a gap inside the replayed history becomes a detected discontinuity, unless a recorded price-scale action has its ex-date in the same step (then `CORPORATE_ACTION_IN_HISTORY` already holds G0, and an INFO finding records the match). D52 does not explain a scale gap.
  - `qualification._g0` counts `PRICE_SCALE_GAP` with `PREVCLOSE_DISCONTINUITY` as `PRICE_DISCONTINUITY_IN_HISTORY`, so G0 is `MANUAL` and the status can never be actionable.
  - Raw OHLC is not adjusted. No zone, freshness or qualification rule changed. Backtest and decision replay use the same `scan_symbol`.
- Limitations: an event smaller than the band (rights, a small demerger) is visible only through a recorded action. User CSV inputs (`marketdata.from_csv`) are not screened; they already carry `PRICE_ADJUSTMENT_UNKNOWN` unless stated. A genuine market move of more than 15% across the whole session (ADANIENSOL 2024-11-21) also holds G0. That is fail-closed by design.
- Tests: `test_research_price_scale_r12` (10 tests: the TATASTEEL 2022-07-28 shape, bonus, large and small demerger, rights, band edges, G0 with and without recorded actions and with verified coverage, prefix invariance).
- Affected files: `nse/research/corporate_actions.py`, `nse/research/marketdata.py`, `nse/research/scanner.py`, `nse/research/qualification.py`, `tests/test_research_price_scale_r12.py`, `nse/validation/run_all.py`.
- Reversible: yes.

### ED-54. Journal reservations, prints and charges share one SQLite write transaction
- Category C. Status `AUTO_APPROVED`. 2026-11-13. GTF P1 application hardening. Not an owner decision and not a methodology change. Renumbered from a colliding "ED-51" draft id; ED-51 remains the P0 data-gates entry.
- Problem: `journal_add` checked the one-order rule and then inserted in a later deferred transaction, so two connections could both reserve one zone. A `TRIGGERED` event was already counted inside `BEGIN IMMEDIATE` (ED-46). Partial fills had no row of their own, and a missing charge was indistinguishable from zero.
- Decision:
  - `journal_add`, `journal_order_submitted`, `journal_event` and `journal_execution` take `BEGIN IMMEDIATE` before the reservation, the monthly count or the open-position count, and commit the decision with the insert. A refused body rolls back. Closing the connection before commit leaves no row.
  - Open-position refusal uses the peak open count at the fill time and every later TRIGGERED/EXIT time (`_peak_open_from`), so a backdated fill cannot sit under later opens and exceed the cap.
  - After `journal_orders` submission, a missing calendar refuses the fill (`ORDER_EXPIRY_UNRESOLVED`). A configured but unloadable calendar raises on the desk path. Missing calendar never extends a submitted order.
  - There is no permanent unique index on the zone. A plan that was never submitted and is `CANCELLED` still releases the zone (ED-3). A submitted order, an expiry, a stop-out or a close does not.
  - Migration 4 adds `journal_executions`, `journal_charges` and `journal_idempotency`. The first ENTRY print inserts the one `TRIGGERED` event. Later prints of that order are not a second trade and not a second position (RB 2140). Unfilled quantity is not a fill. A legacy `TRIGGERED` with no prints remains a fill of the whole planned quantity.
  - Charges are stored only from an owner-entered amount or from `charges.quote` on a dated schedule the caller supplies. The module contains no brokerage, STT, exchange, SEBI, GST or stamp rate. Absent charges stay `ABSENT`. Schedule output is `ESTIMATED`. Owner-entered lines are `ACTUAL`. `gross_pnl` stays gross. `actual_net_pnl` is set only when every closed trade in the month has actual lines.
  - A repeated event with the same body, or the same `request_key`, returns the first result. Plan approval passes `request_key` `approve:<plan_id>` so a retry after a lost response does not create a second journal entry.
  - Platform backup uses the SQLite backup API, refuses to overwrite an existing copy or the live file, and `restore_copy` checks integrity and row counts in a new directory. It does not swap the live database. The copy does not include `nse/data/eod/raw/`. No backup schedule is installed.
- Alternatives considered: a unique index on `(symbol, zone_id, trade_type)` (rejected: a cancelled unsubmitted plan could not release the zone); hardcoding a Zerodha card (rejected: no dated source is in the repository); treating one `TRIGGERED` price as the partial-fill list (rejected: the prints cannot be reconstructed).
- Affected files: `nse/research/store.py`, `nse/research/charges.py`, `platform/gtf_platform/integration/desk.py`, `platform/gtf_platform/routes.py`, the web hash query reader, and the tests named in the P1 report.
- Reversible: yes. The migration is additive. Removing the call sites restores the previous journal calls. Existing journals keep their rows.

### ED-56. Dual-source corporate-action completeness gate (D66 / OD-CA-1 Option A)
- Category C. Status `AUTO_APPROVED`. Implements owner decision D66. 2026-11-15. Not an owner decision and not a methodology change.
- Problem: the completeness register (ED-54/ED-55) could mark a symbol/date window complete from one hash-verified non-API source plus a matching single-hash acceptance line. D66 requires two independent official sources reconciled event-by-event.
- Decision:
  - `COMPLETENESS_COLUMNS` now carries `source_a`/`source_b` paths and hashes plus `reconciliation_file`/`reconciliation_sha256`.
  - Acceptance marker is `- **Completeness window accepted:** <sha_a> <sha_b> <recon_sha> <SYMBOL> <from>..<to>`. The legacy single-hash marker never qualifies.
  - `sources_independent` requires distinct hashes, distinct non-identical files, and refuses saved API responses.
  - `load_reconciliation` requires schema `gtf.ca_reconciliation.v1`, status `RECONCILED`, empty `unresolved`, and every event `MATCH` or `EQUIVALENT`.
  - A single source, even hash-verified and individually approved, never establishes completeness.
- Not changed: D62 evidence tiers; acquisition of any source; approval of any specific completeness row (still owner-reserved); certified count remains 0 until real dual-source evidence and per-window approvals exist.
- Builder version: 1.6.0. Tests: `CompletenessRegister` dual-source adversarial cases; e2e fixture updated to two sources + reconciliation.
- Reversible: yes.

### ED-57. ENG-1: fractional face-value split ratios (VBL 2024-09-12)
- Category C. Status `AUTO_APPROVED`, implementation **authorised by the owner in D67** (2026-11-15). Earlier the same day it was recorded as `PROPOSED` (held); the original text is kept below.
- Implemented semantics (documented before the code change):
  - Face values are parsed from the subject text with `decimal.Decimal`, then `fractions.Fraction`. No float is used in parsing (see the precision note below for `load()`).
  - SPLIT: factor = old/new and must be > 1. CONSOLIDATION: factor = new/old and must be > 1. The row is `(action, ratio_from, ratio_to)` = old:new **share counts**: SPLIT `(factor.denominator, factor.numerator)`, CONSOLIDATION `(factor.numerator, factor.denominator)`, always integers in lowest terms. Whole-number factors give the same rows as before on every held subject (`10 -> 2` is `SPLIT 1:5`; `1 -> 10` is `CONSOLIDATION 10:1`). Exception, fail-closed direction: a face value written with a trailing or leading point ("10.", ".5") used to be accepted and is now unparsed. No held subject has one. VBL `5 -> 2` is `SPLIT 2:5`.
  - Fail closed (`UNPARSED_PRICE_ACTION`): an equal face value (factor 1; previously emitted `SPLIT 1:1`), a zero or negative value, a direction that contradicts the action word (a "split" to a larger face value), an unreadable number (previously `float()` could raise), or a ratio term above 10,000.
  - Abbreviated "Fv Splt Frm Rs a To Re b" follows the same rule.
- Changed regression expectations (three; the first draft of this entry disclosed only one and the independent review found the other two):
  1. `test_the_ten_unparsed_subjects_do_not_become_ratios` (`tests/test_research_corporate_actions.py`): the VBL subject left the must-not-parse list; `ExactFaceValueRatio` asserts exactly `SPLIT 2:5`. The other five subjects in that test still must not parse.
  2. `CorporateActionStoreD50.test_combined_or_unclear_price_events_are_never_guessed` (`tests/test_research_data.py`): the synthetic subject "From Rs 10/- Per Share To Rs 3/- Per Share" was asserted unparsed; it now reads exactly as `SPLIT 3:10`. The other four subjects (combined "And", "Scheme Of Arrangement", "Bonus issue", combined rights+bonus) stay `UNPARSED_PRICE_EVENT`; unparsed count 5 -> 4.
  3. `CorporateActionStoreD50.test_abbreviated_splits_and_unknown_subjects_are_never_skipped`: the synthetic "Fv Splt Frm Rs 10 To Rs 3" now reads `SPLIT 3:10` (still never skipped); "Capital Restructuring" stays unparsed.
  Rationale: a fully stated face-value change gives an exact share ratio, so reading it is not a guess (D56 forbids guessing, not exact reading). The inputs of the tests were not changed. These expectation changes need the owner's review under D67 ("review the existing regression test and its changed expectation") and were sent back to the independent reviewer.
- Hardening after review: `face_value_ratio` accepts only plain decimal text (`\d+(\.\d+)?`). Exponent notation, signs, `Infinity`/`NaN` and non-string input return None. Held-data parity was re-run after hardening: 2,064 of 2,064 rows identical to the stored `actions.csv`.
- Precision of the "no float" claim: no float is used in **parsing** or in the stored text. `Action.ratio_from`/`ratio_to` are typed float and `load()` reads them with `float()`. The values are small integers, so they are exact, and nothing reads them arithmetically (R-12).
- Effect on tiers (review finding): VBL's raw body now has 0 unparsed subjects. In the builder VBL's response status can move from `UNPARSED_EVENT` to a parsed-response status, which can move VBL symbol-dates from `CORPORATE_ACTIONS_UNVERIFIED` to the exploratory tier `CA_RESPONSE_PRESENT_NOT_COMPLETE` (D62). That tier never certifies; the certified count is unaffected.
- Not changed: OHLC (never adjusted), the classification of any non-face-value event, D66, the certified count.
- Correction (2026-11-15, same day): an earlier version of this entry said the builder would reclassify VBL from the raw body. That was wrong: the builder counts parsed and unparsed events from the stored `nse/data/corporate_actions/actions.csv`. Verification and change made:
  - All 2,064 rows were re-derived from the 189 held raw bodies with the new parser. Exactly **one** row differed (VBL 2024-09-12 `UNPARSED_PRICE_EVENT 0:0` -> `SPLIT 2:5`); 2,063 rows were byte-identical (whole-number backward compatibility on all held data).
  - That single line was updated (`recorded_on` 2026-11-15; the note says it was reclassified by ED-57). `actions.csv` SHA-256 `749757252b68...` -> `ec50d805d07a...`.
  - `conversion_report.json`: the VBL entry moved from `unparsed` (10 -> 9) to a new `reclassified_ed57` record; SHA-256 -> `a9f5612bd981...`.
- Original proposal text follows.
- Problem: `_part_row` emits SPLIT/CONSOLIDATION only for whole-number factors. VBL's "From Rs 5/- Per Share To Rs 2/- Per Share" (factor 2.5) falls through to `UNPARSED_PRICE_ACTION`, although its terms are fully stated and the bhavcopy step (1,569.15 -> 645.60) is consistent with them.
- Proposal: represent the factor as a reduced integer fraction parsed from the decimal text (`Fraction(old)/Fraction(new)` = 5/2 -> `("SPLIT", 2, 5)`), matching the existing BONUS convention `(b, a+b)`. Nothing outside `corporate_actions.py` reads the ratio values, and OHLC is never adjusted (R-12).
- Why held: it changes the expectation of `test_the_ten_unparsed_subjects_do_not_become_ratios` (VBL is one of the ten) and the classification of a recorded event. The owner's 2026-11-15 instructions authorised ED entries but said that retrieval work does "not authorize ... changing parser behaviour". Needs explicit owner go-ahead and independent review before it is implemented.
- Effect if implemented: VBL 2024-09-12 moves from `UNPARSED_EVENT` to `PRICE_SCALE_EVENT_ON_STEP:SPLIT`. The certified count is unchanged (D66).
- Reversible: yes.

### ED-58. ENG-2: per-row text in `P0_MEMBERSHIP_BACKLOG.csv`
- Category C. Status `AUTO_APPROVED`. Implemented 2026-11-15. Documentation only.
- Problem: the two `G-BASELINE-2020-12-31` insufficient rows carried one group-level `reason`/`missing_evidence` text, so the GRASIM row's reason described BAJFINANCE (Batch 11).
- Decision: split the existing text per symbol; no wording added or removed beyond the split. Only physical lines 2-3 changed (verified); the other 131 lines are byte-identical. SHA-256 before `bbaaa727134fb8b5148d02f04efe54466ea577444be4b42fa8cab3f33a91d0e7`, after `6fe5e18931d7d35a08d7b3511becebad51cca8f5d84dfaff112e39673aeeb458`. Status fields unchanged; no ledger decision touched.
- Reversible: yes (pre-change copy kept in the session scratchpad).

### ED-59. ENG-3: provenance fields in the corporate-action source ledger
- Category C. Status `AUTO_APPROVED`. Implemented 2026-11-15 as a process/document change (no code).
- Problem: `sources_independent()` proves byte-distinctness, not provenance independence (Batch 7 F-1). Two files from the same publisher pass the code check.
- Decision: `docs/product-discovery/p0/P0_CA_SOURCE_LEDGER.csv` carries `publisher` and `upstream_chain` for every source. A pair whose publishers coincide (for example NSE/CML and NSE/FAOP) is not proposed to the owner as Source A/B. The owner's dual-hash marker remains the control point.
- Not changed: builder code, completeness schema, D66.
- Reversible: yes.

### ED-60. ENG-4: regression test for a CONFLICT event with an empty `unresolved` list
- Category C. Status `AUTO_APPROVED`. Implemented 2026-11-15.
- Test: `CompletenessRegister.test_a_conflict_event_fails_closed_even_with_empty_unresolved` (`tests/test_research_p0_certification.py`). A reconciliation that says `RECONCILED` with `unresolved: []` but carries an event with status `CONFLICT`, `MISSING_IN_A`, `MISSING_IN_B`, empty or unknown is refused. A positive control (`MATCH`) is accepted, so the path is exercised. No production code changed; behaviour already failed closed.
- Reversible: yes.

### ED-61. ENG-5: acceptance-mode validation before any certification claim
- Category C. Status `AUTO_APPROVED`. 2026-11-15.
- Decision: `python3 -m nse.validation.run_all --acceptance` (missing local prerequisites FAIL instead of SKIP) is run with `--out` pointing outside the repository before any final P0 claim. Its side effects were inspected: it sets `NSE_PHASE1_ACCEPTANCE=1` and writes only the `--out` report.
- Result: recorded in `docs/product-discovery/p0/P0_OWNER_INSTRUCTIONS_EXECUTION_REPORT.md` with the preserved log and report.
- Reversible: yes.

## Risk register

| ID | Risk | Severity | Current control | Owner of next step |
|---|---|---|---|---|
| R-1 | The synthetic fixtures carry a Pine-only W supply, so D43 makes several synthetic paths MANUAL | Low (test only) | The scenario and e2e expectations are updated and cite D43 | none |
| R-2 | ~~Instrument identity is not wired into the scanner~~ Resolved 2026-11-09 by ED-21: every bhavcopy input is checked; without records it carries IDENTITY_UNVERIFIED | Low (residual: a rename that keeps the ISIN shortens history, never splices it) | ED-21 | none |
| R-3 | A per-file bhavcopy error blocks every as-of (unbounded) | Low (restrictive) | Fail-closed | engineering backlog |
| R-5 | Precedence wording differs: D12 (an owner decision, `DECISION_LOG.md`) puts explicit Rulebook rules first; the `autonomous-gtf-project-council` skill section 2 lists owner decisions first. No current owner decision contradicts an explicit Rulebook rule, so no output differs today | Low (no behaviour difference found) | `CLAUDE.md` follows D12; nothing overrides an explicit Rulebook rule | owner: confirm the order, then align the council skill wording |
| R-4 | D40-Q1: the owner's 20 Jan 2024 description differs from the registered evidence | Low (evidence trail closed 2026-11-09: NSE/MSD/59999 planned the two-window session, NSE/MSD/60340 withdrew it) | The data is unchanged; excluded sessions end backtest records | owner: acknowledge the factual correction |
| R-6 | UDiFF format drift on unsampled dates (a third header variant) | Low (fail-closed) | Strict parser refuses any other header; the file is quarantined with the line | engineering: add the variant with a sample when one appears |
| R-7 | NSE serves archives today that may differ from what was published on the trade date | Medium (unknowable) | Provenance records retrieval date, URL and hash; `KNOWN_LIMITATIONS` in every coverage report | none possible locally |
| R-8 | NSE re-zips archives: `cm05JUL2024bhav.csv.zip` fetched twice on 2026-11-09 gave two archive SHA-256 values with a byte-identical CSV member | Low (fail-closed) | The data identity is the member hash, which tests compare. A re-download of a held session is quarantined as a revision for review, never silently replacing the file | none |
| R-9 | A Muhurat or DR session without a held file leaves a PREVCLOSE discontinuity for every stock. ~~NSE publishes no Muhurat bhavcopy~~ Corrected 2026-11-09: NSE serves them for 2016-2025, and they are now held (ED-34) | Low (fail-closed) | Owner decision D52 (ED-33): explained only under strict conditions; unobserved sessions make G1 MANUAL | none |
| R-10 | NSE's corporate-action API has undocumented completeness; an event it omits is invisible except through a PREVCLOSE discontinuity | Medium | The detection finding is always kept. Coverage changes G0 only through the narrow D52 rule: excluded sessions with no held file, no missing trading day, action records present and none in the gap (ED-33). Everywhere else a discontinuity keeps G0 MANUAL | owner: an independent CA source, if one is wanted |
| R-11 | Legacy layout variants on unsampled dates (2 of 1,242 in 2016-2020) | Low (fail-closed) | Exact variants only (ED-38); anything else is quarantined | engineering |
| R-12 | R-10's control assumes an omitted event shows as a PREVCLOSE discontinuity. It does not for price-scale events: on 55 of 55 recorded 2021-2025 ex-dates NSE printed the unadjusted prior close (ED-50). A symbol whose non-empty corporate-action body omits a split passes the G0 coverage check, and the raw scale break reaches zone detection undetected | Medium after ED-52 (was High) | ED-52: G0 holds on a whole-range gap over 15% unless a recorded action explains it. Residual: an omitted event smaller than the band, and user CSV inputs | engineering: an omitted small event needs a completeness source (OD-CA-1) |
