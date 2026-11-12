# MASTER IMPLEMENTATION PROMPT
## Build the Complete NSE Demand & Supply Trading Research System

### 1. Your role

Act as a senior quantitative developer, systematic-trading researcher, Python software architect, data-engineering specialist, and test engineer.

You are working on my existing repository:

`~/day-trader-skill`

The current working branch is expected to be:

`nse-phase1`

Your task is to transform the existing codebase into a coherent, modular, testable NSE demand-and-supply swing-trading research system.

I am using Claude Opus 5.5 because I want you to reason across the entire architecture and implement the complete system in one cohesive development effort.

**Do not limit your work to auditing the repository, creating another implementation plan, or implementing one isolated feature. Inspect the project, establish the correct architecture, implement it, integrate its components, test it, and report the actual result.**

You may implement the system in sensible internal stages, but the outcome must be a cohesive integrated implementation rather than disconnected prototypes.

Do not ask me to approve every small implementation decision. Make reasonable engineering decisions where the existing specifications support them. When a trading-rule decision is genuinely unresolved, do not invent an answer: encode the uncertainty explicitly and prevent that uncertainty from silently producing trusted trading candidates.

---

# 2. Primary objective

Build a deterministic, auditable research system that can:

1. Load and validate NSE market data.
2. Maintain a defined stock universe.
3. Process historical OHLC candles.
4. Detect demand and supply zones using the existing zone engine.
5. Analyze zones across multiple timeframes.
6. Determine whether zones are fresh, tested, breached, invalidated, or uncertain.
7. Apply the trading rulebook and candidate-qualification requirements.
8. Perform top-down analysis across the relevant timeframes.
9. Evaluate location, trend, higher-timeframe conflicts, and other specified conditions.
10. Calculate trade-analysis levels when the underlying rules and inputs permit it.
11. Generate explainable, evidence-backed research results.
12. Scan the stock universe and rank or classify research candidates using explicitly defined rules.
13. Replay historical data chronologically without lookahead leakage.
14. Export results in machine-readable formats.
15. Track data quality, unresolved decisions, validation status, and system limitations.
16. Support future historical validation and backtesting without requiring a major architectural rewrite.

The system is a **trading research and decision-support tool**, not an autonomous trading bot.

Initially, it should support long-only cash-equity swing-trading research for the Nifty 100 universe.

Do not integrate broker order placement or automated execution.

Do not claim that the strategy is profitable merely because the code passes its tests.

---

# 3. First inspect the actual repository

Before changing any files, inspect the repository and understand its current state.

At minimum, inspect:

- `git status --short --branch`
- The current branch and relevant Git diff
- The existing directory structure
- `nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md`
- `nse/sources/Demand&Supply Indicator.pine`
- `nse/docs/IMPLEMENTATION_SPECIFICATION.md`
- `nse/docs/DATA_REQUIREMENTS.md`
- `nse/docs/DECISION_LOG.md`
- `nse/docs/IMPLEMENTATION_BLOCKERS.md`
- `nse/docs/PHASE1_CORRECTNESS_AUDIT.md`
- `nse/docs/PHASE1_EXIT_CHECKLIST.md`, if present
- `nse/docs/SOURCE_COVERAGE_REPORT.md`
- `nse/docs/EOD_FORMAT_EVIDENCE.md`
- The existing zone engine
- The existing MTF freshness implementation
- The existing EOD ingestion and replay implementation
- The reference-data comparison utilities
- The calendar implementation
- Existing tests, fixtures, and test-loading utilities
- Existing project conventions, dependencies, and configuration

Inspect the actual code and data structures rather than relying on filenames or this prompt alone.

Determine which components already exist, which are partially implemented, and which are missing.

Create a concise implementation inventory for your own working reference. Then continue into implementation.

**Do not stop after the inventory.**

Do not repeatedly restart the Phase 1 audit unless you discover a specific issue that materially affects the safety or correctness of the integrated system.

---

# 4. Non-negotiable repository safety requirements

The repository contains existing uncommitted changes.

Treat every existing change as potentially important user work.

Before editing:

1. Capture the current Git status.
2. Inspect the existing diff.
3. Identify untracked files.
4. Establish which files are already modified.
5. Preserve the existing work.

Never:

- Run `git reset --hard`.
- Run `git clean`.
- Discard user modifications.
- Revert existing changes merely to make tests pass.
- Overwrite untracked files without inspecting their contents.
- Replace an existing implementation wholesale without understanding its behavior.
- Modify the Pine Script.
- Create a Git commit.
- Push changes to a remote repository.
- Perform destructive data cleanup.

Do not assume that a modified file is disposable because it is incomplete.

If an existing implementation needs modification, integrate the required changes while preserving useful existing behavior.

If a conflict cannot be resolved safely, document it and continue with independent work.

**No Git commits unless I explicitly authorize them.**

---

# 5. Authoritative trading logic

The trading rulebook is the primary authority.

The Pine Script is a secondary source that can clarify implementation details only when the rulebook is silent and the Pine behavior does not conflict with it.

The implementation specification, decision log, and blocker documents describe the current engineering interpretation and unresolved decisions.

Use the following precedence:

1. Explicit rulebook requirements.
2. Explicitly resolved decisions recorded in project documentation.
3. Non-conflicting Pine Script behavior where the rulebook is silent.
4. Explicitly documented engineering assumptions, only where safe and appropriate.

Never silently change a trading rule to make implementation easier.

If two sources conflict:

- Preserve the higher-priority rule.
- Record the conflict.
- Identify the affected behavior.
- Prevent the unresolved behavior from being treated as fully validated.
- Require manual review where appropriate.

Do not manufacture missing rulebook references, Pine references, validation evidence, or source data.

Where possible, every trading decision should include references to the rulebook, relevant implementation requirements, or supporting market-data evidence.

---

# 6. Critical freshness and zone-safety requirements

These rules are mandatory throughout the entire system.

## 6.1 Fresh demand zones only

For long-entry research, only fresh, unbreached demand zones may qualify.

A tested demand zone must never be presented as a fresh entry candidate.

Once a zone has been tested or reacted from, it must be excluded from future fresh-zone entries.

A zone that has been breached or invalidated must not qualify as an active fresh demand zone.

The system must not reset a zone to fresh simply because:

- A new scan begins.
- A new trading day starts.
- The zone appears in a different timeframe.
- The zone is loaded from a cache.
- A symbol is processed again.
- A zone is reconstructed from historical data.
- A new report is generated.

Freshness must be established from the chronological market history and the existing rule definitions.

## 6.2 Unknown freshness is not freshness

Missing candles, unresolved data gaps, ambiguous zone interactions, incomplete histories, and insufficient historical context must not be interpreted as evidence that a zone is fresh.

When freshness cannot be established, classify the zone as uncertain or blocked according to the existing model.

Never allow unknown freshness to pass silently into the candidate list.

## 6.3 Mandatory MTF overlay

The existing MTF freshness implementation has an important interface:

`MtfSnapshot.eligible_after_overlay(timeframe)`

The scanner must use this interface to obtain eligible zones.

Do not build candidate lists from:

- `EngineResult.eligible` alone.
- Raw zone-engine assessments.
- Unfiltered zone detections.
- A separately reimplemented freshness check that bypasses the MTF overlay.

The overlay accounts for higher-timeframe context, touch history, data gaps, and related restrictions.

The scanner must use the overlay-filtered results as its authoritative zone-eligibility input.

If the overlay blocks a zone, the scanner must not reintroduce it through another code path.

## 6.4 Centralize eligibility

Implement one authoritative eligibility and qualification pathway.

Reports, rankings, CSV exports, JSON exports, and historical replay must all use the same eligibility decisions.

Do not let different modules independently reinterpret freshness, invalidation, or manual-review requirements.

Add regression tests specifically designed to prevent tested, invalidated, or uncertain zones from becoming candidates.

---

# 7. Existing architecture to preserve and integrate

The repository already contains important components. Inspect their actual APIs and reuse them wherever appropriate.

## 7.1 Zone engine

Existing file:

`nse/zone-engine/zone_engine.py`

The current implementation includes concepts such as:

- `Candle`
- `Rules`
- `Zone`
- `CoreScore`
- `ScoreReading`
- `Assessment`
- `EngineResult`
- `run_engine(...)`

It implements zone detection, assessment, scoring, freshness, and eligibility-related logic.

Inspect the actual implementation before making changes.

Do not duplicate the zone engine in the scanner.

Do not create a second scoring implementation that can drift away from the existing one.

Preserve the distinction between:

- Detected zones.
- Active zones.
- Fresh zones.
- Eligible assessments.
- Assessments requiring manual review.
- Zones blocked by the MTF overlay.

## 7.2 MTF freshness

Existing file:

`nse/mtf-freshness/mtf_freshness.py`

The current implementation includes concepts such as:

- `TimedCandle`
- `HtfCandle`
- `TouchEvent`
- `DataGap`
- `ExcludedCandle`
- `ZoneTouchState`
- `HtfSeries`
- `MtfSnapshot`
- `replay(...)`

Reuse this implementation as the central source of MTF freshness and overlay eligibility.

Extend it carefully if required by the complete architecture.

Do not introduce a competing implementation that bypasses its safeguards.

## 7.3 EOD ingestion and replay

Inspect and reuse:

- `nse/eod/nse_bhavcopy.py`
- `nse/eod/nse_reference.py`
- `nse/eod/nse_replay.py`

These modules already contain work related to NSE data ingestion, reference comparisons, daily series, candle construction, and replay.

Do not replace them merely because a new architecture would be easier to write from scratch.

Integrate them through clean interfaces.

## 7.4 Calendar and reference data

Inspect:

- `nse/calendar/nse_calendar.py`
- `nse/data/calendar/`
- `nse/data/reference/`
- `nse/data/eod/manifest.csv`

Preserve existing provenance and validation metadata.

Do not pretend that a source is validated simply because a file exists.

---

# 8. Target system architecture

Implement a clean modular architecture consistent with the existing repository conventions.

Do not blindly create every suggested directory if an equivalent component already exists.

The following are logical responsibilities, not a mandate to duplicate modules.

## Layer A — Configuration and domain models

Provide shared, explicit models for:

- Symbol and security metadata.
- Market-data records.
- Timeframe identifiers.
- Data-quality findings.
- Zone assessments.
- MTF analysis results.
- Trend analysis.
- Location analysis.
- Higher-timeframe conflicts.
- Coinciding-zone analysis.
- Trade-analysis levels.
- Qualification gates.
- Candidate status.
- Manual-review requirements.
- Evidence and source references.
- Scan metadata.
- Historical replay metadata.
- System readiness and validation limitations.

Use consistent representations across modules.

Avoid passing loosely structured dictionaries everywhere when typed models would make the system safer.

Use dataclasses, enums, or the project's existing modeling conventions where appropriate.

## Layer B — Market data and universe

Implement or complete:

- Data ingestion interfaces.
- Daily OHLC normalization.
- Input validation.
- Symbol normalization.
- Duplicate detection.
- Date and chronology validation.
- Missing-data detection.
- Incomplete-bar handling.
- Historical data availability checks.
- Universe membership and filtering.
- Data provenance.
- Data-quality reporting.

The initial universe is Nifty 100.

Do not hard-code a supposedly current constituent list without recording its source and effective date.

If a reliable current or historical constituent dataset is unavailable, make the universe configurable and report that its membership is unverified.

Historical research should account for the universe applicable at the historical point being evaluated when the necessary membership data exists.

Do not silently use today's constituents as a historically correct universe.

## Layer C — Zone detection and MTF freshness

Reuse the existing zone engine and MTF overlay.

Support the documented top-down timeframes:

- Yearly (`Y`)
- Half-yearly (`HY`)
- Quarterly (`Q`)
- Monthly (`M`)
- Weekly (`W`)
- Daily (`D`)
- 125-minute (`125m`)
- 75-minute (`75m`)

Follow the existing timeframe naming conventions.

Do not fabricate candles or infer missing timeframe history without an explicit, documented rule.

Ensure that incomplete bars cannot influence confirmed decisions in ways prohibited by the existing implementation.

Preserve candle-close-time semantics and chronological processing.

## Layer D — Top-down analysis

Implement a coherent top-down analysis component that can represent the following timeframe chain:

`Yearly → Half-yearly → Quarterly → Monthly → Weekly → execution timeframe`

The output must show:

- Timeframe.
- Relevant zones.
- Zone status.
- Freshness.
- Eligibility.
- Price location relative to relevant zones.
- Available evidence.
- Missing information.
- Manual-review requirements.

The analysis must distinguish between a timeframe having no qualifying zone and the timeframe being unavailable or insufficiently validated.

Do not label missing information as a neutral or bullish condition.

## Layer E — Candidate qualification engine

Implement the complete qualification pipeline described in:

`nse/docs/IMPLEMENTATION_SPECIFICATION.md`

The specification defines gates G0 through G8.

Read the actual detailed requirements before implementing them.

Do not replace them with a generic technical-analysis strategy.

Each gate must have a clear outcome, evidence, and explanation.

Use the statuses and conventions already defined in the specification where possible.

## Layer F — Scanner and reporting

Build the universe-scanning interface around the shared qualification engine.

The scanner must:

1. Load the configured universe.
2. Load or receive market data.
3. Validate data readiness.
4. Run zone and MTF analysis.
5. Obtain eligible zones from the mandatory MTF overlay.
6. Evaluate qualification gates.
7. Generate explainable results.
8. Export results.
9. Record data limitations and scan metadata.

Support deterministic output for identical inputs and configuration.

A scan should not require a person to manually inspect raw internal objects to understand why a candidate passed, failed, or requires review.

## Layer G — Historical replay and validation

Build on the existing replay infrastructure.

The replay engine must process market data chronologically and produce point-in-time results.

Do not use future candles, future zone reactions, future constituent membership, or future corporate-action information to make earlier decisions.

Keep signal-generation time separate from subsequent outcome-evaluation time.

Provide an architecture that can support later backtesting, including transaction costs and realistic execution assumptions when those are properly specified.

Do not invent a fill model and present it as validated.

## Layer H — Outputs and auditability

Provide machine-readable output and human-readable explanations.

At minimum, support JSON and CSV for scanner results.

Use consistent schemas.

Include sufficient metadata to reproduce or audit a decision.

Avoid adding a complex dashboard or graphical interface at this stage unless one already exists and can be integrated with little risk.

Prioritize the research engine, correctness, testability, and useful reports.

---

# 9. Implement qualification gates G0–G8

Read the complete implementation specification before implementing the gates.

The following summarizes their known intent. The actual repository specification remains authoritative for details.

## G0 — Data and history readiness

Evaluate:

- Required candle history.
- Candle completeness.
- Session completeness where relevant.
- Data gaps.
- Calendar readiness.
- Chronological integrity.
- Availability of required timeframe data.
- Any other data-readiness conditions specified in the implementation specification.

If data is insufficient, return the appropriate blocked or insufficient-data status.

Do not continue to an actionable candidate status when required inputs are missing.

## G1 — Fresh, unbreached execution-timeframe demand zone

Require a fresh, unbreached demand zone according to the existing zone engine and MTF overlay.

A tested zone must not pass.

A breached zone must not pass.

Unknown freshness must not pass.

The overlay must be the authoritative source of eligible zones.

Apply the specified WIT recency requirements only where they are defined and sufficiently unambiguous.

## G2 — Core scoring

Use the existing core-scoring implementation and the rulebook's definitions.

The implementation specification describes a core score of 7/7 as a qualification requirement.

Do not duplicate the scoring formula.

If an assessment reaches the numerical threshold but has unresolved flags or mandatory manual checks, preserve those restrictions.

Do not treat a numerical score as proof that every qualitative condition has been satisfied.

## G3 — Location and curve

Implement the location logic defined in the specification and rulebook.

Known timeframe requirements:

- MIT: Monthly curve.
- WIT: Weekly curve.

Do not invent curve thresholds or zone-selection rules where they remain unresolved.

If the required location cannot be established confidently, report the uncertainty and apply the appropriate restriction.

## G4 — Trend requirements

Follow the documented distinction between MIT and WIT.

Known requirements:

- MIT: Weekly trend gate, with Monthly context mandatory but not itself a gate.
- WIT: Daily trend gate only.

Do not accidentally impose the MIT trend requirements on WIT.

Do not treat an unavailable trend calculation as a passing trend condition.

## G5 — Higher-timeframe conflict

Implement the documented higher-timeframe conflict checks.

Distinguish between:

- No identified conflict.
- Confirmed conflict.
- Insufficient data.
- Ambiguous or unresolved conflict.

Do not silently treat missing higher-timeframe data as absence of conflict.

## G6 — Coinciding and aggressive setups

Implement the definitions in the specification and rulebook.

Do not invent a definition for coinciding zones or aggressive setups when the project has not resolved it.

Where necessary, create an explicit unresolved-rule state and a manual-review restriction.

## G7 — Entry, stop-loss, target, and risk/reward

Implement trade-analysis levels only when the relevant rule definitions and input data support them.

Use the specified methods for:

- Entry.
- Stop-loss.
- Target.
- Risk/reward ratio.

Do not manufacture levels from generic trading conventions if those conventions are not authorized by the rulebook or resolved specifications.

If a calculation cannot be made reliably, report why it is unavailable.

Do not silently use an arbitrary risk/reward threshold.

## G8 — Red flags and essential checks

Implement the documented red-flag and essential-check logic.

Represent unresolved essential checks explicitly.

Never turn a mandatory manual check into an automatic pass.

---

# 10. MIT and WIT must remain distinct

The specification distinguishes MIT and WIT trade types.

Read the actual definitions and requirements in the repository.

Preserve the known distinctions:

### MIT

- Daily execution timeframe.
- Weekly trend gate.
- Monthly context is mandatory but is not itself a gate.
- Monthly curve/location requirements apply.
- Weekly trend opposing Monthly location bias requires the documented caution or manual-review treatment.

### WIT

- 75-minute or 125-minute execution timeframe.
- Daily trend gate only.
- Weekly curve/location requirements apply.
- Do not apply Weekly or Monthly trend gates as though they were WIT requirements.

If any detail differs in the authoritative specification, follow the specification and document the discrepancy.

**Intraday 75-minute and 125-minute outputs must remain blocked or explicitly deferred until the session-completeness and gap-handling design has been validated and approved.**

Build the interfaces and tests needed for future support, but do not falsely label unvalidated intraday outputs as trusted candidates.

---

# 11. Candidate statuses must be explicit

Implement a clear status model.

Use existing specification terminology wherever possible, including the known concepts:

- Rejected.
- Data insufficient.
- Manual review.
- Actionable candidate: manual checks pending.

The precise final enum names should follow existing project conventions.

The important distinction is between:

1. A candidate that fails a mandatory requirement.
2. A candidate whose required data is unavailable.
3. A candidate that has unresolved trading-rule ambiguity.
4. A candidate that passes the implemented automated checks but still requires manual verification.
5. A candidate that is fully validated for the specific research purpose.

Do not conflate these states.

**The scanner must never automatically approve a trade.**

If the specification requires a manual check, the system must preserve it in the final output.

If a feature has not passed the relevant validation, represent that limitation in its readiness state.

A score, ranking, or favorable chart pattern must never override a failed safety gate.

---

# 12. Evidence-backed reporting

Implement structured decision evidence.

For each scanned symbol and relevant candidate, include as much of the following as the source data supports:

- Symbol.
- Company or security identifier where available.
- Scan timestamp.
- Historical as-of timestamp.
- Trade type.
- Execution timeframe.
- Zone identifier.
- Zone side and pattern.
- Zone proximal and distal boundaries.
- Zone creation time.
- Zone freshness and test status.
- Zone invalidation or breach status.
- Zone-engine assessment.
- Core score.
- MTF overlay result.
- Yearly analysis.
- Half-yearly analysis.
- Quarterly analysis.
- Monthly analysis.
- Weekly analysis.
- Execution-timeframe analysis.
- Location or curve result.
- Trend result.
- Higher-timeframe conflicts.
- Coinciding/aggressive classification.
- Entry, stop-loss, target, and risk/reward when validly calculable.
- G0–G8 gate outcomes.
- Reasons for rejection or blocking.
- Manual-review checklist.
- Missing data.
- Unresolved trading rules.
- Validation limitations.
- Relevant rulebook and implementation references.
- Relevant source-data provenance.
- System and engine versions.

Use the exact output structure specified in the implementation specification where it exists.

Do not add fake evidence to fill empty fields.

If an item cannot be determined, represent it as unknown, unavailable, or not applicable as appropriate.

## Required report categories

Support at least:

1. **Fresh-zone report:** identifies fresh, unbreached zones supported by the authoritative overlay.
2. **Candidate qualification report:** shows qualification outcomes and gate-by-gate explanations.
3. **Data-quality report:** describes missing, incomplete, inconsistent, or unverified inputs.
4. **Scan summary:** shows the number of symbols processed and the resulting status counts.
5. **Validation/readiness report:** identifies which capabilities are implemented, tested, externally validated, deferred, or blocked.

Use deterministic JSON and CSV serialization.

Reports must not hide rejected or blocked outcomes merely to make the scanner appear successful.

---

# 13. Historical replay and lookahead prevention

Historical replay is an important architectural capability.

Build on the existing replay modules rather than starting over.

Requirements:

- Process candles in chronological order.
- Maintain a well-defined as-of timestamp.
- Ensure every decision uses only information available at that timestamp.
- Prevent future zone tests from changing the historical classification of a zone.
- Prevent future data from changing earlier trend or location results.
- Preserve point-in-time universe membership where reliable data exists.
- Keep signal-generation data separate from future outcome data.
- Track missing dates and unresolved calendar coverage.
- Make replay deterministic.
- Support reproducible test fixtures.

Add explicit regression tests for lookahead leakage.

For example, a historical candidate evaluated at time T must not change merely because candles after T were added to the dataset, except where the later dataset reveals that the original data itself was incomplete and the system explicitly reports that limitation.

Where the existing implementation has unresolved behavior, preserve it as a documented restriction rather than pretending the issue is solved.

## Backtesting limitations

Create the interfaces needed for future backtesting, but do not claim that backtesting validates profitability by itself.

Do not report invented win rates, expectancy, drawdown, or profitability figures.

Only calculate performance metrics when there is a genuine historical dataset, a defined execution model, appropriate cost assumptions, and actual reproducible results.

Keep research signal generation separate from the backtesting execution simulator.

---

# 14. External validation must not block the entire implementation

I do not want to spend the entire development cycle repeatedly auditing Phase 1.

The goal is to build the complete system now and refine it afterward.

Therefore:

- Continue implementation even if TradingView parity has not been fully established.
- Continue implementation even if some EOD source details require later confirmation.
- Continue implementation even if historical corporate-action handling requires further validation.
- Continue implementation even if external market-data comparisons are incomplete.
- Continue implementation even if some strategy decisions require my future confirmation.

However, these limitations must be tracked honestly.

Create or update the relevant documentation so that every important unresolved issue has:

- A unique identifier.
- A description.
- The affected component.
- The potential consequence.
- The current restriction.
- The evidence needed to resolve it.
- A proposed validation method.
- A clear readiness status.

Use the project's existing blocker and decision-log structure where practical.

Do not invent a resolution for an unresolved strategy decision.

Do not repeatedly reopen already documented questions unless new evidence requires it.

**The distinction is simple: implementation can proceed, but unsupported conclusions must remain restricted.**

Build the interfaces and architecture now. Validate uncertain behavior later.

---

# 15. Data integrity and readiness states

Implement a consistent way to communicate readiness.

At minimum, distinguish between:

- Implemented.
- Unit-tested.
- Integration-tested.
- Validated against reference data.
- Externally validated.
- Deferred.
- Blocked.
- Requires manual review.

Do not claim external validation simply because synthetic tests pass.

Do not claim integration testing if only isolated mocks were used.

Do not claim that a dataset is complete unless the available evidence supports that conclusion.

Do not interpret a passing software test as proof of trading-strategy validity.

When a component is unvalidated, its output must carry a suitable limitation or be blocked from trusted candidate generation.

Avoid unnecessarily blocking unrelated components. For example, an unresolved intraday-session issue should not prevent development of a daily research workflow if the daily workflow has its own valid data and readiness conditions.

---

# 16. Testing requirements

Build a robust test suite around the complete system.

Inspect the existing tests and reuse the project's conventions.

Do not weaken existing tests simply to make the new implementation pass.

## 16.1 Unit tests

Cover:

- Market-data parsing.
- Input validation.
- Candle chronology.
- Incomplete candles.
- Timeframe aggregation where implemented.
- Zone-engine integration.
- Freshness preservation.
- Zone invalidation.
- MTF overlay behavior.
- Core scoring integration.
- Qualification-gate outcomes.
- MIT/WIT differences.
- Location calculations.
- Trend calculations.
- Higher-timeframe conflicts.
- Trade-level calculations.
- Data-quality restrictions.
- Manual-review propagation.
- Report serialization.
- Configuration validation.
- Readiness-state behavior.

## 16.2 Integration tests

Cover the full path:

`Input data → validation → zone engine → MTF overlay → top-down analysis → qualification gates → candidate result → report export`

Verify that the final candidate output uses the same eligibility decisions as the MTF overlay.

Test both successful and blocked workflows.

## 16.3 Freshness regression tests

Explicitly test that:

- A fresh demand zone can proceed only if every required gate permits it.
- A tested demand zone cannot qualify.
- An invalidated zone cannot qualify.
- Unknown freshness cannot qualify.
- A data gap cannot silently establish freshness.
- An MTF-blocked zone cannot reappear in scanner results.
- Repeated scans do not reset zone history.
- Historical replay does not use future touches.
- Manual-review flags survive every pipeline stage.

## 16.4 Gate tests

For each G0–G8 gate, test:

- Passing conditions.
- Failing conditions.
- Missing inputs.
- Ambiguous inputs.
- Manual-review cases.
- Interaction with other gates.

## 16.5 Determinism and reproducibility

Verify that identical input data, configuration, and as-of time produce equivalent outputs.

Avoid nondeterministic ordering, timestamps unrelated to the requested replay time, or unstable identifiers.

## 16.6 Test integrity

Do not fabricate test results.

Do not silently skip critical tests.

If a test requires unavailable external data, report that limitation explicitly.

Use mocks for isolated unit tests where appropriate, but do not mistake mocked integration tests for validation against real NSE data.

Run the complete existing test suite after integration.

If a test fails, investigate the underlying cause.

Do not remove or weaken an assertion merely to get a green test run.

---

# 17. Implementation quality requirements

Use the following engineering principles.

### Single source of truth

There should be one authoritative implementation for:

- Zone detection.
- Core scoring.
- MTF freshness eligibility.
- Candidate qualification.
- Status interpretation.
- Report schemas.

Avoid duplicated business logic.

### Separation of responsibilities

Keep the following responsibilities distinct:

- Data ingestion.
- Data validation.
- Zone detection.
- MTF analysis.
- Top-down analysis.
- Qualification.
- Candidate reporting.
- Historical replay.
- Backtesting and outcome evaluation.

### Explicit uncertainty

Use explicit result states rather than implicit booleans when the difference between false, missing, and unknown matters.

Do not default unknown values to passing conditions.

### Traceability

Important decisions should be explainable from recorded inputs and rule references.

### Maintainability

Prefer clear, testable functions and cohesive modules.

Avoid unnecessary abstraction, speculative infrastructure, and overengineering.

### Compatibility

Preserve existing public interfaces unless there is a compelling reason to change them.

When changing an interface, update every relevant caller and test.

### Dependency management

Inspect the project's existing dependency and runtime conventions before adding dependencies.

Prefer the Python standard library where it is sufficient.

Do not introduce a heavyweight framework solely for convenience.

---

# 18. Suggested implementation sequence

You may organize the work into internal stages, but continue through the full implementation rather than stopping after each stage.

### Stage 1 — Repository understanding

Inspect the current implementation, Git state, rulebook, specifications, blockers, and tests.

Identify existing functionality and missing integration points.

### Stage 2 — Shared domain and interfaces

Define or refine shared models, status enums, configuration, data-quality representations, and stable interfaces.

### Stage 3 — Complete the core pipeline

Integrate market data, zone detection, MTF freshness, top-down analysis, and qualification gates.

### Stage 4 — Scanner and outputs

Implement universe scanning, candidate qualification reports, fresh-zone reports, JSON/CSV exports, and scan summaries.

### Stage 5 — Replay and point-in-time safety

Integrate historical replay and add regression coverage for chronology, freshness, and lookahead leakage.

### Stage 6 — Testing and integration

Run unit tests, integration tests, repository tests, and any relevant static or type checks supported by the existing project.

Fix genuine implementation issues.

### Stage 7 — Documentation and readiness

Update implementation documentation, decision logs, blocker records, readiness states, and usage instructions.

### Stage 8 — Final verification

Inspect the final diff and Git status.

Confirm that existing user changes remain intact, the Pine Script was not modified, and no commits were created.

**Do not stop at Stage 1 or Stage 2. Complete as much of the integrated implementation as the available repository and execution environment support.**

---

# 19. Definition of done

The task is complete when the following are true to the extent supported by the repository and environment.

## Architecture

- The major responsibilities are separated into cohesive modules.
- Existing components are reused rather than duplicated.
- Interfaces between components are consistent.
- The end-to-end scanner pipeline is integrated.
- The implementation is maintainable and testable.

## Trading correctness

- The rulebook remains authoritative.
- Tested demand zones cannot become fresh entry candidates.
- Invalidated zones cannot qualify.
- Unknown freshness cannot qualify.
- MTF overlay eligibility is mandatory.
- MIT and WIT requirements remain distinct.
- Unresolved rules remain explicit.
- Manual-review requirements cannot be silently bypassed.
- No candidate is automatically approved for trading.

## Data integrity

- Missing or incomplete data is reported.
- Data provenance is retained where available.
- Validation status is honest.
- Historical replay is point-in-time aware.
- No lookahead leakage is introduced by the implementation.

## Usability

- A user can run the scanner through documented commands or interfaces.
- The scanner can process the configured universe when the required inputs are available.
- Outputs explain why a candidate passed, failed, or requires review.
- JSON and CSV reports are available.
- Readiness and validation limitations are visible.

## Testing

- New unit tests cover important business rules.
- Integration tests exercise the end-to-end pipeline.
- Existing tests are preserved.
- The complete available test suite has been run, or every inability to run it is explicitly reported.
- Actual results are reported without fabrication.

## Repository safety

- Existing user modifications are preserved.
- No destructive Git operation was used.
- No commit was created.
- The Pine Script remains unchanged.

Do not claim the project is fully validated if external data comparisons, TradingView parity, or other required validation work remains incomplete.

---

# 20. Final response format

After implementation, give me a concise but technically meaningful report using the following sections.

## A. Executive summary

Explain what was actually implemented and how the components work together.

Clearly distinguish completed implementation from planned or deferred work.

## B. Architecture implemented

Show the final module structure and describe the responsibility of each major component.

## C. End-to-end workflow

Explain the actual workflow from input data to final candidate reports.

## D. Trading-rule safeguards

Explicitly confirm how tested zones, invalidated zones, unknown freshness, MTF overlay restrictions, and manual-review requirements are enforced.

If any safeguard is incomplete, say so prominently.

## E. Tests and verification

List the exact commands executed and the actual results.

Distinguish:

- Unit tests.
- Integration tests.
- Repository tests.
- Reference-data validation.
- External validation.

Do not claim a test category passed unless it was actually executed successfully.

## F. Unresolved issues

List the important remaining blockers, their impact, and what is needed to resolve them.

Separate engineering blockers from trading-rule decisions and external validation.

## G. How to run it

Provide the actual commands for the implemented scanner and report generation, based on the real interfaces you created.

Do not invent commands for features that do not exist.

## H. Changed files

Summarize the important modified, added, and deleted files.

Explicitly confirm whether the Pine Script changed and whether any Git commit was created.

## I. Recommended next steps

Give me the smallest practical set of next steps required to move from the implemented system toward validated research.

Do not recommend another broad audit if a specific, targeted validation step would suffice.

---

# Final instruction

Think across the whole repository, preserve the existing work, and implement the system cohesively.

Do not merely tell me how to build it.

Do not return only an architecture diagram.

Do not stop after writing a checklist.

Do not keep postponing implementation until every external validation question has been answered.

**Inspect the real code, make the necessary changes, integrate the complete system, test what can actually be tested, and document what remains uncertain.**

Be ambitious about implementation and conservative about claims.

Build the system now. Refine and validate it afterward.

# 21. Build an Autonomous Engineering and Validation System

## Objective

In addition to implementing the NSE trading research system, build a project-specific autonomous engineering framework that can implement, test, validate, audit, and maintain the codebase with minimal routine human intervention.

The objective is to eliminate the need for me to manually supervise every implementation step, run every test, discover every defect, and repeatedly ask whether the system is correct.

I want the repository to contain the instructions, skills, automated checks, validation scripts, and development workflow necessary for Claude Code to carry out substantial engineering tasks independently.

Do not merely document this idea. Inspect the capabilities available in the actual environment and implement the appropriate infrastructure.

## 21.1 Inspect the available agent capabilities first

Before creating any skills, inspect the actual Claude Code environment, supported skill formats, project-level configuration, hooks, subagents, and available execution mechanisms.

Use the native capabilities supported by the installed version.

Do not assume that every feature is available or create invalid configuration based on outdated syntax.

Where supported, use project-local skills and specialized subagents. Where deterministic automation is more appropriate, implement executable scripts and test commands.

Keep all project-specific instructions version-controlled in the repository.

Prefer a structure similar to the following, adapting it to the actual environment:

.claude/
    skills/
        project-orchestrator/
            SKILL.md
        repository-guardian/
            SKILL.md
        rulebook-compliance/
            SKILL.md
        data-quality-validation/
            SKILL.md
        zone-engine-validation/
            SKILL.md
        mtf-freshness-validation/
            SKILL.md
        strategy-gate-validation/
            SKILL.md
        lookahead-audit/
            SKILL.md
        integration-testing/
            SKILL.md
        adversarial-testing/
            SKILL.md
        reference-data-validation/
            SKILL.md
        reporting-audit/
            SKILL.md
        release-readiness/
            SKILL.md
    agents/
        implementer.md
        independent-reviewer.md
        data-validator.md
        trading-rule-auditor.md
        test-engineer.md

scripts/
    validate/
        validate_repository.py
        validate_data.py
        validate_zones.py
        validate_mtf.py
        validate_gates.py
        validate_replay.py
        validate_reports.py
        validate_readiness.py

Adapt filenames and directory locations to the actual Claude Code conventions.

Do not create empty skills, placeholder agents, or scripts that merely print success.

Every implemented component must have a defined responsibility and an executable or otherwise verifiable outcome.

Do not introduce duplicate implementations of existing validators when suitable scripts or tests already exist.

## 21.2 Project Orchestrator skill

Create a project orchestrator that manages substantial development tasks.

It must:

1. Read the project instructions and relevant specifications.
2. Inspect the current repository state.
3. Identify relevant modules, tests, and dependencies.
4. Break work into tasks with explicit acceptance criteria.
5. Select the appropriate specialized skills and validators.
6. Implement or delegate independent tasks where supported.
7. Integrate the results.
8. Run the appropriate verification sequence.
9. Diagnose and fix implementation defects.
10. Repeat verification after corrections.
11. Update documentation and readiness records.
12. Produce a final evidence-based report.

The orchestrator must not stop after generating a plan.

It must continue through implementation and verification unless a genuine blocker prevents further progress.

It should use the smallest reasonable set of skills needed for each task rather than invoking every skill for every trivial change.

For substantial changes, maintain an explicit task checklist so that work is not forgotten between stages.

## 21.3 Repository Guardian skill

Create a dedicated skill responsible for repository safety.

Before changes:

- Record the branch and working-tree status.
- Inspect the relevant Git diff.
- Identify modified and untracked files.
- Identify protected files and important user changes.
- Record the baseline for later comparison.

After changes:

- Inspect the complete diff.
- Identify unintended modifications.
- Check whether protected files changed.
- Confirm that no user changes were discarded.
- Confirm that generated files are appropriate.
- Confirm that no unauthorized commits were created.

Never use destructive Git operations to manufacture a clean workspace.

Never silently overwrite untracked files.

Never modify the Pine Script.

Never commit, push, or rewrite Git history without explicit authorization.

If a test failure is caused by pre-existing work, investigate it without discarding that work.

## 21.4 Rulebook Compliance skill

Create a specialized trading-rule auditor.

It must read the authoritative trading rulebook and relevant project specifications before evaluating changes to trading logic.

It must verify:

- Zone detection and scoring behavior.
- Freshness rules.
- Invalidation rules.
- MIT/WIT differences.
- Timeframe requirements.
- Location and trend requirements.
- Qualification gates.
- Manual-review requirements.
- Candidate-status semantics.
- Evidence and report consistency.

It must check that rulebook requirements have corresponding implementation and regression tests.

Where practical, maintain a traceability matrix connecting:

`Rule → Specification → Implementation → Test → Validation status`

Flag rules that lack an implementation or adequate tests.

Do not invent missing trading rules to complete the matrix.

Where a requirement is ambiguous, preserve the ambiguity and apply the project's manual-review or blocked-state conventions.

## 21.5 Data Quality Validator skill

Create an independent validator for market-data inputs.

It should verify, as applicable:

- Input format and required fields.
- Valid numeric OHLC values.
- OHLC consistency.
- Chronological ordering.
- Duplicate records.
- Missing records.
- Timestamp interpretation.
- Candle completeness.
- Session coverage.
- Calendar coverage.
- Symbol and series consistency.
- Data provenance.
- Reference-data consistency.
- Availability of sufficient historical context.

It must distinguish a verified defect from an unverified assumption.

It must not assume that a missing candle means there was no trading activity.

It must not assume that a source is trustworthy merely because the file exists.

Where external data is unavailable, complete the validations possible with local data and explicitly report the missing external verification.

## 21.6 Zone Engine Validator skill

Create a validator for the existing zone engine.

Use synthetic fixtures with known expected outcomes and preserve existing tests.

Cover:

- Zone detection.
- Zone creation and chronology.
- Freshness.
- Zone touches.
- Invalidations.
- Core scoring.
- Manual-review flags.
- Boundary conditions.
- Incomplete candles.
- Historical replay.
- Determinism.

Test the existing public interfaces rather than creating a separate scoring implementation.

When a defect is discovered, identify the smallest appropriate fix and run regression tests afterward.

Do not change the trading rule to make a failing test pass.

## 21.7 MTF Freshness Validator skill

Create a dedicated validator for multi-timeframe freshness.

It must verify the relationship between:

- Base-timeframe candles.
- Higher-timeframe candles.
- Zone creation.
- Zone touches.
- Data gaps.
- Excluded candles.
- Timeframe boundaries.
- Overlay eligibility.
- Historical as-of timestamps.

The validator must verify that candidate generation uses:

`MtfSnapshot.eligible_after_overlay(timeframe)`

It must explicitly test that zones blocked by this overlay cannot re-enter the candidate list through another module.

Include regression tests for:

- Tested zones.
- Invalidated zones.
- Missing touch history.
- Ambiguous freshness.
- Missing timeframe history.
- Data gaps.
- Repeated scans.
- Historical replay.
- Incomplete candles.
- Timeframe-boundary conditions.

Treat uncertain freshness as a restriction, not a passing result.

## 21.8 Strategy Gate Validator skill

Create a specialized validator for G0–G8.

For every gate, maintain test cases for:

- Valid passing conditions.
- Valid failing conditions.
- Missing data.
- Ambiguous rules.
- Manual-review requirements.
- Interactions with other gates.

Verify that the final candidate status reflects all mandatory restrictions.

A later passing gate must never override an earlier mandatory failure.

An unresolved rule must never become an automatic pass.

MIT and WIT must have separate regression tests where their rules differ.

Intraday outputs must remain restricted according to the documented session-completeness and gap-validation requirements.

## 21.9 Lookahead Auditor skill

Create a specialized historical-replay auditor.

It must attempt to detect:

- Future candles influencing earlier decisions.
- Future zone touches changing earlier freshness.
- Incorrect use of completed higher-timeframe candles.
- Incorrect as-of timestamps.
- Future information leaking into trend or location calculations.
- Retrospective universe membership.
- Outcome data being used to generate a signal.
- Nonchronological processing.

Use adversarial historical fixtures.

Include a prefix-invariance test: where the data available through time T is unchanged, adding later candles must not change the decision that was validly made at T.

If a later data addition reveals that the earlier dataset was incomplete, the system may report that newly discovered data-quality limitation, but it must not silently rewrite the historical decision as though future information had been available at T.

Document any limitation that cannot be fully tested.

## 21.10 Integration Test Engineer skill

Create an integration-focused skill that validates the complete system:

`Market data → Data validation → Zone engine → MTF overlay → Top-down analysis → G0–G8 → Candidate output → JSON/CSV reports`

It must verify:

- Consistent data and timeframes between modules.
- Correct propagation of restrictions.
- Stable identifiers and statuses.
- Correct error handling.
- No candidate bypasses the authoritative eligibility pathway.
- Reports accurately reflect internal results.
- Identical inputs produce equivalent outputs.

Use actual repository components for integration tests wherever possible.

Mocks are appropriate for isolated unit tests, but must not be misrepresented as full integration verification.

## 21.11 Adversarial Testing skill

Create a skill whose purpose is to find ways the system could be wrong.

It should actively attempt to violate system invariants rather than simply rerun ordinary happy-path tests.

Examples:

1. Can a tested zone appear in the fresh-zone report?
2. Can an invalidated zone become a candidate?
3. Can missing history be interpreted as proof of freshness?
4. Can a raw engine assessment bypass the MTF overlay?
5. Can a manual-review requirement disappear during serialization?
6. Can a failed G0 gate be overridden by G2?
7. Can an intraday candidate appear while its readiness status is blocked?
8. Can future candles change an earlier point-in-time decision?
9. Can missing higher-timeframe data be interpreted as no conflict?
10. Can a report claim external validation when only unit tests were executed?
11. Can a missing reference dataset produce a false successful validation?
12. Can an unresolved trading-rule decision silently acquire a default value?
13. Can two equivalent scans produce inconsistent candidate classifications?
14. Can a test pass because its setup never exercised the intended code path?

Turn every confirmed defect into a regression test.

Prioritize defects that can produce false-positive candidates, bypass safety gates, or misrepresent validation.

## 21.12 Reference Data Validator skill

Build a validator that compares system outputs against approved reference data when available.

Reuse the existing reference-data utilities and formats.

It should:

- Verify reference-file formats.
- Validate required fields.
- Check provenance.
- Compare expected and actual OHLC values.
- Compare expected and actual zone results where reference data supports that comparison.
- Identify mismatches.
- Distinguish exact matches, tolerance-based matches, missing references, and unresolved comparisons.
- Produce a discrepancy report.

Never manufacture reference values.

Never treat an absent reference as a successful match.

Never treat a synthetic fixture as external market-data validation.

When the relevant reference data is unavailable, mark the validation as unavailable rather than failing unrelated software tests.

## 21.13 Reporting Auditor skill

Create a skill that verifies that reports faithfully represent the system's decisions.

Check that:

- Blocked candidates remain blocked in exports.
- Manual-review flags remain visible.
- Missing data is not hidden.
- Scores are consistent with their source assessments.
- Zone identifiers match the underlying objects.
- Gate outcomes match the qualification engine.
- Report timestamps are correct.
- As-of timestamps are not replaced with current timestamps.
- Validation limitations are preserved.
- Candidate counts reconcile with individual records.
- JSON and CSV exports do not silently omit important restrictions.

Use round-trip serialization tests where appropriate.

## 21.14 Release Readiness skill

Create a final readiness auditor.

It must evaluate each major component independently.

Use explicit states such as:

- Implemented.
- Unit-tested.
- Integration-tested.
- Reference-validated.
- Externally validated.
- Deferred.
- Blocked.
- Requires human decision.

Do not collapse these states into one generic green checkmark.

The auditor must inspect actual evidence, including test output and validation records.

It must not accept an implementation's self-reported success without checking the relevant evidence.

Generate a readiness report that identifies:

- What is complete.
- What has been tested.
- What has been validated against references.
- What remains externally unverified.
- Which trading rules remain unresolved.
- Which outputs remain restricted.
- What human decisions are required.

## 21.15 Build an autonomous validation runner

Create a single documented command that runs the appropriate repository validation workflow.

For example, use a project-appropriate command such as:

`python -m nse.validation.run_all`

This is a suggested interface; inspect the repository conventions before choosing the final command.

The runner should orchestrate the applicable checks:

1. Repository and configuration validation.
2. Unit tests.
3. Data-format and local-data validation.
4. Zone-engine tests.
5. MTF freshness tests.
6. Strategy-gate tests.
7. Replay and lookahead tests.
8. Integration tests.
9. Report-schema tests.
10. Reference-data comparisons where reference data exists.
11. Readiness report generation.

Do not duplicate existing test execution unnecessarily.

Separate required checks from optional checks that depend on unavailable data or external access.

Return a meaningful process exit code.

A mandatory test failure must produce a nonzero exit code.

An unavailable external reference must not be reported as a successful validation.

If the environment lacks a required dependency, identify the missing dependency and report the resulting verification limitation.

The runner must not silently skip a mandatory check.

## 21.16 Bounded autonomous fix-and-retest loop

Implement or document a reliable workflow for autonomous repair.

When a test or audit fails:

1. Capture the exact failure.
2. Identify the affected component.
3. Inspect the relevant implementation and test.
4. Determine whether the issue is a genuine defect, an incorrect test assumption, missing prerequisites, or an unresolved specification.
5. Fix the implementation if the requirements are clear.
6. Add a regression test for a confirmed defect.
7. Rerun the failing test.
8. Rerun the relevant component suite.
9. Rerun the complete required suite.
10. Reinspect the final diff.

Use a bounded retry budget, such as three targeted repair cycles for a particular failure before escalating.

The limit is not permission to stop all unrelated work. If one area is blocked, continue independent tasks where safe.

If the same failure persists after the repair budget is exhausted, stop repeatedly changing code without a clear diagnosis. Record the evidence, the attempted fixes, and the specific decision or missing information required to proceed.

Never:

- Delete failing tests to obtain a green result.
- Weaken assertions without a justified specification correction.
- Change trading rules to make tests pass.
- Skip failed checks and report overall success.
- Invent test output.
- Treat a lack of errors as proof that a feature is correct.

## 21.17 Human intervention policy

The system should operate autonomously by default.

Claude may independently perform ordinary, reversible engineering work, including:

- Inspecting files.
- Editing implementation code.
- Creating appropriate tests.
- Fixing defects.
- Running local tests.
- Updating technical documentation.
- Generating local reports.
- Improving error handling.
- Refactoring code while preserving behavior.
- Creating regression tests.
- Repeating validation.
- Documenting blockers.

Human intervention is required when the next step involves a decision or permission that cannot safely be inferred.

Examples include:

- Choosing between conflicting trading rules.
- Approving a change to the trading strategy.
- Accepting a previously unresolved financial-risk assumption.
- Obtaining credentials or private data.
- Approving a paid external service.
- Authorizing destructive operations.
- Authorizing a Git commit or push.
- Enabling broker integration or live order execution.
- Approving a claim that requires external evidence that is unavailable.
- Resolving a decision explicitly reserved for the project owner.

When human intervention is necessary:

1. Complete all independent work that can safely continue.
2. Document the exact blocker.
3. Explain why it cannot be resolved autonomously.
4. Present the available options and their consequences.
5. State the minimum decision required from me.
6. Do not repeatedly ask for information already available in project documentation.

Do not ask for approval for every ordinary implementation detail.

## 21.18 Optional automation and hooks

Where supported by the installed Claude Code environment, implement project-level hooks for appropriate deterministic checks.

Examples include:

- Detecting protected-file changes.
- Running formatting or lightweight checks after edits.
- Running targeted tests after relevant code changes.
- Checking for unauthorized Git operations.
- Verifying that required validation commands are available.
- Preventing known dangerous commands from running automatically.

Do not make every file edit trigger the entire slow test suite.

Use a layered approach:

- Fast checks during development.
- Targeted tests after a component change.
- Full required validation before completion.

Hooks must be compatible with the installed environment and must not perform destructive actions.

Do not rely on natural-language instructions alone for critical deterministic protections when executable checks can enforce them.

## 21.19 Keep the system maintainable

The purpose of these skills is to reduce supervision, not to create an unnecessarily complicated agent framework.

Before adding a skill, agent, script, or hook:

- Check whether equivalent functionality already exists.
- Reuse established interfaces.
- Keep each responsibility clear.
- Avoid duplicate validation logic.
- Make outputs machine-readable where useful.
- Document how to invoke the component.
- Add tests for critical executable behavior.

Do not create a skill simply to increase the skill count.

Every component must provide measurable value.

## 21.20 Definition of done for the autonomous engineering framework

The framework is complete when:

1. Project-local skills exist in the correct supported format.
2. Their responsibilities and activation conditions are clear.
3. The orchestrator can direct substantial work through implementation and validation.
4. Repository safety is checked before and after changes.
5. Trading-rule compliance has explicit verification.
6. Data, zone, MTF, qualification, replay, and reporting checks are integrated.
7. Adversarial tests target critical failure modes.
8. Confirmed defects produce regression tests.
9. A single command runs the available validation workflow.
10. Failures produce meaningful exit codes and reports.
11. Autonomous repair is bounded and evidence-driven.
12. Readiness claims distinguish tests from external validation.
13. Human intervention is requested only for genuine decisions or permissions.
14. All skills, scripts, and hooks are documented and tested to the extent supported by the environment.
15. Existing user changes remain intact.
16. The Pine Script remains unchanged.
17. No unauthorized Git commit or push occurs.

Implement this framework as part of the larger NSE research-system project.

Do not stop after creating skill files. Test that the actual commands and checks work.

If the installed environment prevents a capability from being implemented, document the limitation and implement the closest reliable alternative without pretending the missing capability exists.

## Autonomous Engineering, Decision Boundaries, and Evidence Requirements

### 1. Engineering autonomy
Operate independently on implementation, debugging, refactoring, test creation, documentation, and validation when these actions are consistent with the approved specifications.

Do not stop for routine engineering decisions or ask for approval after every implementation step.

### 2. Trading-strategy authority
Never invent, silently modify, or independently approve a material trading rule.

The Trading Rulebook is authoritative for trading methodology. The Implementation Specification defines the intended software behavior. Pine Script may supplement the rulebook only where the rulebook is silent and no conflict exists.

If a material rule remains ambiguous, record the ambiguity, explain its consequences, and prevent the affected decision from being automatically approved. Continue implementing unaffected components.

### 3. Evidence-based completion
Distinguish clearly between:
- Implemented
- Unit-tested
- Integration-tested
- Adversarially tested
- Reference-validated
- Historically evaluated
- Production-ready

Never use one status as evidence that another has been achieved.

Do not claim that the strategy is profitable, validated, or production-ready without the evidence required to support that claim.

### 4. Independent validation
Create tests from approved requirements and expected behaviors, not merely from the current implementation.

Include negative tests, boundary cases, historical replay checks, and tests for lookahead bias, zone freshness, invalidation, incomplete candles, missing data, calendar assumptions, and multi-timeframe eligibility.

Where independent reference data is unavailable, identify the limitation explicitly. Do not manufacture expected results or treat synthetic fixtures as independent validation.

### 5. Safe autonomous repair
Investigate failures, identify root causes, implement bounded fixes, and rerun relevant tests.

Do not make a test pass by weakening a requirement, deleting a meaningful test, suppressing a failure, or changing approved strategy behavior.

If repeated attempts fail, preserve the evidence, explain the root cause and impact, and continue with independent tasks where safe.

### 6. Fail-closed candidate eligibility
Only use candidates permitted by the approved rules and the existing multi-timeframe freshness overlay.

Never bypass MtfSnapshot.eligible_after_overlay(timeframe) by reading raw EngineResult.eligible for candidate generation.

A zone that has been tested, invalidated, or cannot be reliably classified as fresh must not appear as an eligible fresh-zone candidate.

Missing, ambiguous, incomplete, or contradictory evidence must not be interpreted as proof of eligibility.

Manual-review requirements must remain visible and cannot be automatically approved.

### 7. Repository protection
Preserve all existing user modifications and untracked files.

Do not perform destructive Git operations, commit, push, modify the protected Pine Script, or execute broker orders without explicit authorization.

Inspect the actual repository state before making changes and before reporting completion.

### 8. Honest completion report
At completion, report:
- What was implemented
- Files changed
- Tests executed and their actual results
- Known failures and unresolved issues
- Unvalidated assumptions and missing reference data
- Commands needed to reproduce the validation
- Remaining blockers and their practical impact

Do not report success for checks that were not executed or for capabilities that were not verified.