---
name: gtf-p0-data-certification
description: "Autonomous NSE historical market-data research, point-in-time Nifty 100 reconstruction, instrument identity resolution, corporate-action verification, exchange-calendar validation, EOD integrity, price continuity, source provenance, historical exclusions and research-universe certification. Use when a task materially involves NSE historical data, Nifty 100 membership, instrument identity, corporate actions, the exchange calendar, EOD files, price continuity, exclusions, or research-universe certification, including roadmap phases P0, P2, P7, and P11."
---

# GTF P0 Data Certification

## 1. Mission and scope

Act as the independent historical market-data research and certification lead for the GTF Trading Intelligence Platform.

Establish the largest defensible historical NSE cash-equity research dataset. Correctness and source traceability outrank dataset size. A smaller certified subset with an explicit exclusion register is a successful result. A larger file that hides an unresolved identity, an empty corporate-action response, or a name-only membership claim is not.

Investigate and decide evidence-based data questions. Do not ask the owner to approve routine transcription, parsing, classification, or exclusion decisions that the rules below already settle. When the evidence is insufficient, exclude the affected symbol-dates and continue with every unrelated symbol.

This skill covers point-in-time Nifty 100 reconstruction, instrument identity, corporate actions, the exchange calendar, end-of-day integrity, price continuity, provenance, and research-universe certification. It does not change GTF zone rules, qualification gates, risk limits, or execution policy. It does not place orders. `authorises_order` stays false on every eligibility result.

Chart work (P2), quantitative studies (P7), and production certification (P11) consume this skill's outputs. They do not replace this investigation.

## 2. Activation

Read this skill before any task that materially changes or relies on historical NSE market data.

| Roadmap phase | How this skill applies |
|---|---|
| P0 Historical data foundation | Primary owner of membership, identity, corporate actions, calendar, EOD, price continuity, the certified universe, and the exclusion register |
| P2 Stock analysis and charting | A chart that claims historical prices or historical index membership uses the certified series and prints every exclusion. Labelled fixtures stay labelled |
| P7 Backtesting and quantitative validation | Historical performance may cite only symbol-dates this skill has certified. Read `gtf-quantitative-validation` as well |
| P11 Final production certification | The data-integrity gate uses this skill's certification label and exclusion register |

Also load this skill when new bhavcopies, calendar circulars, identity files, corporate-action responses, or index notices arrive, when a scan is `DATA_INSUFFICIENT` for a data reason, or when someone asks whether a dataset is certified.

Acquisition mechanics (inbox, quarantine, approved download scripts) stay with `.claude/skills/nse-data-engineering/SKILL.md`. Content validation of a file already on disk also uses `.claude/skills/data-quality-validation/SKILL.md`. External chart comparison uses `.claude/skills/reference-data-validation/SKILL.md`. This skill is the certification judgement over those checks. It does not replace them.

## 3. Master skill dependency

Before starting work, read `.claude/skills/gtf-autonomous-project-lead/SKILL.md` in full.

`gtf-autonomous-project-lead` remains mandatory. It governs project-wide authority, autonomy, repository safety, owner interaction, and Git policy. This specialist skill adds data-certification procedures. It cannot override the master skill. It cannot change approved GTF methodology. It cannot authorize automated order execution. It cannot weaken project safety, fail-closed eligibility, or validation requirements.

If this file and the master skill appear to disagree, follow the master skill, then the owner decisions in `nse/docs/DECISION_LOG.md`, then the explicit Rulebook rule. Record the disagreement. Do not invent a resolution that enlarges eligibility.

Repository safety and commits follow master-skill section 9. Do not use `git reset`, `git clean`, destructive checkout, a broad revert, history rewriting, or `git commit --amend`. Do not stage unrelated owner work. Do not push unless the owner asks. Treat the dirty working tree as the owner's. The master skill file itself is not edited by this skill.

Protected inputs stay untouched: the Rulebook PDF, the files under `nse/sources/`, and vendored third-party skills. Hashes of protected sources are part of the evidence, not something to regenerate in order to match a parse.

## 4. Authority model for data decisions

### 4.1 Decisions you make independently

You may, and should, do these without asking:

- Read official circulars, datasets, saved API bodies, and local evidence files, and compare them with the canonical tables.
- Correct a transcription when the authentic source document disagrees with the typed field. Recompute that row's hash. A previous review approval of the old hash is void. Do not copy an old `ACCEPTED` onto the new hash.
- Correct a parser that mis-reads a documented schema. Add a regression test that uses the real failing subject. Do not loosen a check so that an unrecognised subject becomes "no event".
- Resolve a symbol or ISIN mapping when one authoritative record names the old identity, the new identity, and one effective session.
- Set a membership `effective_date` when the notice's wording and the converter's date rule agree, and record the wording in `notes`.
- Classify a corporate action, an empty response, a calendar session, an EOD defect, or a price gap using the categories in this skill.
- Exclude unsupported symbol-dates and write the exclusion with its evidence.
- Produce reconciliation reports from source rows through certified and excluded rows.
- Continue other symbols while one symbol is excluded.

Do not ask the owner whether an unsupported record should be guessed. Exclude it.

### 4.2 Decisions that stay with the owner

Ask only when the established rules cannot settle the question, and only with the master skill's single consolidated decision request.

Owner authorization is required for:

- A change to GTF methodology, the Rulebook, qualification, risk limits, or the manual-execution rule.
- Writing `decision` `ACCEPTED` or `REJECTED` in `nse/data/universe/nifty100_review.csv`. D49, D53, ED-27, ED-35, and ED-48 reserve human review. Agents never write those tokens. Count approval and mapping approval are not substitutes.
- Choosing one effective session when two authentic official dates remain in the same notice and a join is wanted. Until that choice exists, do not join. Exclusion is the autonomous result, not a question.
- A new download or collection scope outside the approvals already recorded (D47, D55, D56, and any later decision you re-read). `nse/` does not gain network access.
- Destructive cleanup of `nse/data/`, overwriting an accepted raw bhavcopy, or deleting an evidence file.
- Treating BE or BZ rows as EQ research prices. That is OD-PX-1 and is not approved.
- Building a derived adjusted price series as the research price. D50 keeps raw OHLC canonical. A separate adjusted dataset needs a documented policy the owner has accepted.
- Any claim that would mark `DATA_READY` or full historical Nifty 100 certification while a required baseline or review gate is open.

Prepare the evidence, the recommended exclusion, and the consequence. Keep working on every symbol the open question does not affect.

### 4.3 What you must re-read

Examples in this skill were grounded in the repository's decisions through D61 and the P0 blocker board. Before acting, re-read:

- `nse/docs/DECISION_LOG.md` from D49 onward
- `nse/docs/ENGINEERING_DECISIONS.md` from ED-20 onward
- `docs/product-discovery/p0/P0_REMAINING_BLOCKERS.md`
- `docs/architecture/DATA_ARCHITECTURE.md`
- `nse/docs/DATA_SOURCE_REGISTRY.md` and `nse/docs/REAL_DATA_READINESS.md`
- `nse/data/universe/README.md`

A dated example that a later owner decision has closed is history. Do not reopen a closed decision, and do not treat this skill's examples as a newer approval.

## 5. Evidence hierarchy

Use the highest source that actually identifies the fact you need. "Official" is not one bucket.

1. Official NSE circulars and notices, held locally, identified by circular number and SHA-256 in the relevant `sources.csv`.
2. Official NSE datasets: accepted CM bhavcopies (legacy and UDiFF), and index or corporate-action files whose rows carry symbols or ISINs and a proved coverage window.
3. Official issuer filings and corporate-action announcements, used when the exchange extract is silent or unparsed. They can supply terms. They do not rewrite an accepted bhavcopy.
4. Official instrument and ISIN records, including depository records when they are the identity source on file.
5. Other authoritative exchange or regulatory records, cited with the document id.
6. Secondary corroboration: vendor screens, news, reconstructed spreadsheets, and name-only change logs. Corroboration cannot create an ISIN, a ratio, a membership period, or a price.

### 5.1 Authenticity and transcription are different checks

Authenticity asks whether this file is the document it claims to be: URL or circular number, byte size, and SHA-256 matched to `sources.csv` or the manifest. A matching hash proves file identity. It does not prove the economic content was read correctly.

Transcription correctness asks whether the canonical CSV or parser output matches the text of that authentic file: the symbol, ISIN, ex-date, ratio, effective date, and session hours. Check the cell against the page, not against a previous CSV.

Both checks are required before a row is source-verified. A beautiful canonical table built from an unverified spreadsheet is still unverified. A hash-matched PDF that was typed into the wrong column is a transcription defect, which you correct.

### 5.2 Conflicting evidence

- Two primary sources disagree on a date, ratio, symbol, or ISIN: keep both citations, do not average them, and exclude the affected symbol-dates.
- A primary source disagrees with a secondary source: the primary controls. Record the secondary source as contradictory evidence. Do not delete it to tidy the register.
- A later official document supersedes an earlier one only when the later document says so. Keep the earlier file in the evidence store.
- A name-only index log never creates a symbol or an ISIN, and it never outranks a record that has them.
- A price jump never creates a corporate-action ratio.

Do not silently discard the losing source.

## 6. Historical Nifty 100 membership

The research universe is point-in-time NSE cash equity, initially Nifty 100 (D1). Today's constituents are not the historical index. D59 restricts membership-based Nifty 100 research to 2020-12-31 onward. That window is not certification. Dates before 2020-12-31 may warm indicators. A non-ad-hoc study whose as-of is earlier carries `MEMBERSHIP_BEFORE_PROVISIONAL_WINDOW`. Do not invent a 2016-2020 constituent list from a later snapshot. `IndexInclExcl.xls` is a name-only change log through 2020-07-31 and is not a pre-2020 baseline (B11-P).

### 6.1 Files and date rules

The converter in `nse/research/membership.py` reads:

- `nse/data/universe/nifty100_baseline.csv` — a composition actually in force on `as_of_date`. Nothing before `as_of_date` is inferred.
- `nse/data/universe/nifty100_changes.csv` — `effective_date` is the first date the new composition is in force. An ADD is a member from `effective_date`. A REMOVE is a member through the calendar day before `effective_date`.
- `nse/data/universe/nifty100_count_exceptions.csv` — official counts other than the nominal size, only when declared.
- `nse/data/universe/nifty100_review.csv` — human gate. `decision` is the only full row approval.
- `nse/data/universe/evidence/baseline/IndexInclExcl.xls` — name-only corroboration.
- `nse/data/universe/evidence/sources.csv` — provenance for the files that were actually read.

The converter rolls forward from the earliest baseline. It refuses a change on or before that baseline. Do not implement a backward roll from a later constituent file.

Map a notice's phrase, such as "with effect from the close of the previous day", onto `effective_date` explicitly in `notes`. The converter does not read free text. If the phrase and the typed date disagree, fix the transcription or exclude the row. Do not leave a silent mismatch.

### 6.2 What a membership period needs

A period is verified only when its source file verifies, the row that starts it and the row that ends it (if any) have `decision` `ACCEPTED` with a matching hash, every count exception the conversion uses passes the count gate, and any identity check is clear. You do not write `ACCEPTED`.

These do not verify a period:

- `count_approval` `APPROVED` (D60). It passes the count-arithmetic gate only. Documented counts of 101 stay 101. Never force the count to 100.
- `mapping_approval` `APPROVED` (D61). It records a symbol and a direction. It does not start or end a certified period.
- A matching company name in `IndexInclExcl.xls`.
- A symbol that exists in a later bhavcopy.
- An agent recommendation in a review packet.

Dummy seats (`DUMMYREL`, `DUMMYITC`, `DUMMYSIEMS`, `DUMMYTATAM`, `DUMMYHDLVR`, and any later non-tradable placeholder you confirm in the source) are not tradable research names. Do not invent ISINs for them. They cannot fill out a "full index" claim.

Symbol changes and ISIN changes keep a seat only through the identity rules in section 7. A RENAME is not an ADD. An ISIN change is not a new company merely because the ticker looks familiar.

### 6.3 Reconstruction procedure

1. State the date range and whether it sits inside the D59 window.
2. Hash-check every source file the baseline and the changes cite.
3. Read the notice, not only the CSV, for each addition, removal, and ad-hoc change that the claimed periods depend on.
4. Confirm `effective_date` against the notice wording and the inclusive/exclusive rule above.
5. Walk the membership. An ADD of someone who is already a member, a REMOVE of someone who is not, or an undeclared count is a transcription defect or a missing notice. Repair it from the source or exclude the dates the walk cannot support.
6. Leave `decision` blank. Record your evidence conclusion in the decision record and in the exclusion register.
7. One symbol's missing notice excludes that symbol's affected dates. It does not blank the rest of the index.

Confidence in a period is `HIGH` only when the authentic document was read, the hash matches, the symbol and ISIN are on that document or on a joined identity record, and no contradictory primary source is on file. Anything weaker stays unverified and out of the certified universe.

## 7. Symbol and ISIN identity

Renames join only through verified ISIN continuity and effective dates (D51, ED-29). Two companies that share a ticker or a similar name are never joined. If continuity cannot be established, the symbol-dates stay `DATA_INSUFFICIENT` or excluded. Never infer an ISIN.

Evidence to inspect, not to trust blindly:

- `nse/data/universe/instrument_records.csv`
- `nse/data/universe/build/instrument_records_base.csv`
- `nse/data/universe/evidence/identity/symbolchange.csv`
- `nse/data/universe/evidence/identity/EQUITY_L.csv`
- `nse/data/universe/identity_report.json`
- the bhavcopy ISIN on the session, checked by `instruments-check` (ED-21)

### 7.1 When a mapping is resolved

A mapping is `RESOLVED` only when one authoritative record states all of:

- the old symbol or old ISIN
- the new symbol or new ISIN
- one effective session
- that both sides are the same security, or the official successor relationship the research rule already allows

A circular that names only the new ISIN does not prove the old ISIN. Leave them unjoined. Conflicting effective dates in one notice stay unjoined. The BAJFINANCE `INE296A01016` / `INE296A01024` pair and the GRASIM `INE047A01013` / `INE047A01021` pair were in that state: one notice stating two sessions. Re-read the blocker board before assuming they are still open, and do not pick a session in order to extend a history.

Mergers, demergers, and schemes join only on the official terms: the successor ISIN, the ratio if one is required for continuity, and the effective session. A shared promoter or a similar name is not a join. Duplicate identities stay duplicate until a source shows they are the same security. Do not merge them to simplify a chart.

### 7.2 Identity procedure

1. For each symbol-date in scope, record the bhavcopy symbol, series, and ISIN.
2. Find the instrument interval that contains that date.
3. If the bhavcopy ISIN and the interval ISIN disagree, stop the join for that date. Look for an ISIN-change notice. If none resolves it, exclude the date for identity.
4. Across a rename, require the same ISIN on both symbols and the symbol-change effective date. Do not splice prices across a gap the identity record does not cover.
5. Write the source file and hash on the decision record. A spreadsheet inference is not a source.

## 8. Corporate-action research

Corporate actions explain prices. They do not rewrite them (D50, ED-28). Verified terms live in the event store. Raw OHLC stays canonical. An unverified ratio is never used in zone detection, scanning, or backtesting.

Events in scope: splits, bonuses, rights issues, mergers, demergers, schemes of arrangement, symbol changes, ISIN changes, and any other official event that breaks or explains a price series. Rights issues and schemes matter when they change the traded instrument or the price scale, even when they are not a simple integer split.

### 8.1 Coverage is a window, not a vibe

`nse/data/corporate_actions/coverage.csv` records a requested symbol and date window, the saved body, and its SHA-256. `nse/research/corporate_actions.py` classifies a saved body:

| Status | Meaning |
|---|---|
| `MISSING_COVERAGE` | No body to read |
| `EMPTY_RESPONSE_COMPLETENESS_UNKNOWN` | The saved body is `[]`. This is not proof that no corporate action occurred |
| `UNPARSED_EVENT` | A price-type subject the parser cannot read. Stored as `UNPARSED_PRICE_EVENT` with ratio 0,0. G0 is MANUAL |
| `COVERED_WITH_VERIFIED_EVENTS` | The body parsed into price events. Completeness of the API is still not proved by a non-empty body alone. The events that parsed are verified as events present in that body |
| `RESPONSE_PRESENT_COMPLETENESS_NOT_PROVED` | A non-empty body with no parsed price event and no unparsed price event. This is not "no events" |

`load_coverage` does not treat `[]` as a covered window. G0 is `MANUAL` with `CORPORATE_ACTION_COVERAGE_UNKNOWN` when no coverage file is supplied, and `CORPORATE_ACTION_COVERAGE_UNVERIFIED` when the replayed history falls outside a hash-verified window (ED-46). An empty event list inside a proved window is a different fact from an empty HTTP body. Do not collapse them.

`nse/research/dataset_eligibility.py` will accept `COVERED_NO_EVENTS_PROVED` as a passing corporate-action gate. Emit that value only when a source affirmatively establishes both the window and the absence of events. The saved NSE API body `[]` is not that source. Passing `COVERED_NO_EVENTS_PROVED` for `[]` is a false certification.

### 8.2 Six labels you must keep distinct

Use these words in the decision record. They match the judgement, and the code statuses above are the implementation of the first, third, fourth, and sixth.

- **Verified event.** The official subject parsed, the terms are the terms in the source, and the ex-date is the source ex-date.
- **Verified no-event evidence.** A source proves the window was complete and that no relevant event occurred. Rare. Do not invent it to clear a gate.
- **Missing evidence.** The window was not retrieved, the hash does not match, or the body is `[]`.
- **Unparsed event.** The source shows a price event and the parser cannot represent the ratio without invention. Leave the ratio unset. Do not round 5-for-2 into an integer the parser likes.
- **Conflicting event.** Two primary sources disagree. Exclude the continuity across that ex-date.
- **Unverified coverage.** A response exists and its completeness is not proved, including `RESPONSE_PRESENT_COMPLETENESS_NOT_PROVED`.

Never infer a split, bonus, or scheme ratio from the size of a price gap.

### 8.3 Procedure

1. Recompute SHA-256 of each `raw/*.json` the coverage row cites. A mismatch quarantines the window.
2. Confirm the symbol and the from/to dates on the row are the request that produced the body.
3. Classify the body with `response_status`. Do not hand-edit the status to a passing value.
4. For each parsed event, read the subject, ex-date, ISIN, and ratio back against the JSON.
5. For each unparsed subject, record the subject string and exclude price continuity across that ex-date.
6. Regenerate `actions.csv` only through the existing writer after a real collection change. Do not hand-write a ratio into the CSV.
7. A symbol with unknown coverage fails its own dates. Neighbouring symbols with proved windows keep their own results.

New collection outside D56's recorded scope needs a new owner approval. The data-engineering skill owns the resumable collector. This skill owns whether the result certifies anything.

## 9. Exchange calendar

The calendar is `nse/data/calendar/events.csv`, built from hash-matched circulars in `nse/data/calendar/circulars/` and indexed by `sources.csv`. `nse/calendar/nse_calendar.py` is the reader. Weekdays are not "expected sessions" until the calendar classifies them.

Classify every date in the claimed range as one of: normal session, special session, Muhurat session, closed session, shortened session, holiday, or unresolved. Trading hours are an attribute of that class, not a default you may fill in.

### 9.1 Preserved Dhanteras decision

D58, which supersedes D54 for four dates only, stands unless a later owner decision says otherwise. Re-read it before touching these rows:

- 2016-10-28, NSE/CMTR/33442
- 2017-10-17, NSE/CMTR/36003
- 2018-11-05, NSE/CMTR/39215
- 2019-10-25, NSE/CMTR/42455

Each is `CONFIRMED`, classified `NORMAL_SPECIAL`, with regular equity hours 09:15-15:30. The Gold ETF and SGB evening extension stays in the note and builds no equity candle. Do not return these dates to `UNRESOLVED`. Do not treat D58 as a licence to infer any other date.

D54 remains the rule for every other unresolved date: do not infer session status or hours, keep the date flagged, and do not treat it as a verified session. ED-31, ED-42, and ED-44 stay in force. An unresolved date blocks the histories whose range contains it. It does not block a scan that does not need that date. A future unresolved date must not be waved through because the four Dhanteras dates were later confirmed.

### 9.2 Sourced hours and inferred hours

Sourced hours are the hours printed in the circular for that session. Inferred hours are a copy of the ordinary 09:15-15:30 session taken from a circular that does not itself print the hours. Inferred hours stay labelled inferred. The 2024-01-20 hours were inferred from NSE/CMTR/41180 and disclosed as OD-CAL-1. Re-read that disclosure. Do not relabel an inference as a quotation.

A Muhurat or shortened session takes its hours from its own circular. A holiday circular's weekday list is the closed set only after the amending circulars for that year are applied. A special session that is not the cash-equity regular market does not become an equity candle because a bhavcopy exists for a different segment.

### 9.3 Calendar-to-EOD reconciliation

For the claimed range:

- Every equity trading session has an accepted EOD file, or an explicit documented reason that no file is expected.
- Every accepted research EOD file falls on a confirmed equity session.
- A file for an excluded or non-equity session is held only in the role D52 and ED-34 already allow. It is not a research candle.
- A bhavcopy dated on a holiday is a finding. Do not relabel the holiday to absorb the file.
- Report missing equity dates and unexpected archive dates separately. A previous "no missing trading day" line is not a universe certification.

D52 explains a previous-close gap across an excluded session only when three facts all hold: an authoritative circular confirms the excluded or special session, the session is recorded as excluded from the accepted EOD dataset, and no EOD file is expected for it. That explanation is not a split. It does not fabricate a candle. It does not clear unrelated corporate-action or identity warnings. It does not make a candidate actionable.

## 10. EOD integrity

Research prices are accepted official NSE CM bhavcopies, unadjusted (D50, ED-20). One source per trade date: legacy through 2024-07-05, UDiFF from 2024-07-08. A verified file in the other format is quarantined. An unseen header is refused. A revised file for a session that is already accepted is quarantined. The accepted raw file under `nse/data/eod/raw/` is not overwritten.

The canonical row is the EQ series (ED-30). Invalid non-EQ rows are isolated. They do not delete the EQ rows, and they do not become EQ rows. Do not backfill BE or BZ observations into EQ. Where a name traded only on BE for a stretch, those sessions are missing EQ sessions until the owner approves a different series policy. An intact previous-close chain on BE does not change that.

### 10.1 Fields to check

For every accepted file in the claimed range, check:

- trade date matches the session and the file's identity
- symbol, series, and ISIN are present and consistent with the instrument interval
- open, high, low, close are numerically ordered (low ≤ open, close ≤ high, and low ≤ high) and positive
- traded quantity is present and non-negative
- previous close is present
- number of trades, when the schema version contains it
- no duplicate symbol-series-ISIN inside the file
- the archive member and any standalone copy share the recorded hash
- the manifest row's SHA-256 matches the bytes
- the session is on the calendar as a tradable equity session, or the file is in the excluded-session role

Manifest columns and the acquisition ledger (`nse/data/eod/manifest.csv`, `acquisition_ledger.jsonl`, `download_log.jsonl`) are the provenance. `eod-coverage` is the report. Do not replace it with a hand count you did not reconcile to that command.

A hash match proves the bytes. It does not prove the exchange's print was free of corporate-action or identity problems. Those are later gates.

## 11. Price continuity

Preserve raw unadjusted OHLC as the canonical series. Do not silently fill, interpolate, forward-fill, or adjust prices. A derived adjusted series, if one is ever built, is a different dataset id with its own policy. Scans and backtests on the research price read the raw series.

On the EQ series only, walk sessions in calendar order:

1. Compare this session's previous close with the prior EQ session's close.
2. If they match within the file's own precision, the chain is continuous for that step. Continuity is not a corporate-action clearance.
3. If they differ, classify the gap. Do not smooth it.
   - D52's three conditions: an explained calendar gap. Keep the missing-session marker.
   - A verified price-scale event on that ex-date, with a parsed ratio: a corporate-action discontinuity. Record the event. Leave the OHLC raw. The backtest already excludes a trade that stays open across a recorded price-scale event. Do not "fix" the candle so the trade can stay in the sample.
   - A series change onto BE or BZ: a missing EQ stretch. Do not import the BE prices.
   - An ISIN or symbol change without a resolved identity join: an identity break. Do not splice the two histories.
   - Otherwise: an unexplained gap. Exclude the affected continuity. G0 or the price gate fails closed for those dates.

Unparsed ratios stay unresolved. Do not compute a factor from the two closes around the ex-date.

`PRICE_CONTINUOUS` in `dataset_eligibility.py` means this investigation passed for that symbol-date. Do not stamp it because the file parsed.

## 12. Research-universe eligibility

Evaluate symbol-dates, not the index as a single boolean. `nse/research/dataset_eligibility.py` is the classifier. One unresolved symbol does not change another symbol's gates (ED-49).

Passing values are:

| Gate | Passing value |
|---|---|
| membership | `VERIFIED` |
| identity | `RESOLVED` |
| corporate_action | `COVERED_WITH_VERIFIED_EVENTS` or `COVERED_NO_EVENTS_PROVED` |
| calendar | `TRADING_DAY` |
| eod | `ACCEPTED` |
| price_continuity | `CONTINUOUS` |
| gtf | `PASS` |

A missing gate is `UNKNOWN` and fails. The first failure in that order is the blocking gate. Every failed gate is named. Unknown evidence fails closed. There is no "probably eligible".

`certify_members` returns:

- `COMPLETE_NIFTY100` only when the caller passes `index_evidence_resolved=True` and every required member on that date passes. You may pass that flag only after the full-index conditions in section 14 hold. A count approval, a mapping approval, or a set of passing rows does not set the flag by itself.
- `CERTIFIED_SUBSET` when at least one symbol-date passes and the full-index condition does not.
- `NO_CERTIFIED_SYMBOL_DATES` when none pass.

The GTF gate is the canonical pipeline's result for that symbol-date (`pipeline.run` → `scanner.scan` → `scan_symbol` → `qualification.evaluate_symbol`, candidates only from `MtfSnapshot.eligible_after_overlay`). This skill does not reimplement the gates and does not let a data pass override a methodology fail. WIT stays blocked. Tested, invalidated, and unknown-freshness zones never qualify.

`authorises_order` is false on every classification.

## 13. Three mandatory outputs

Every certification task produces or updates three traceable artifacts. Extend the existing files. Do not create a second unofficial universe beside them, and do not delete prior exclusions to enlarge the certified set.

1. **Historical reference membership dataset.** The baseline, the change list, and the intervals the converter emits, each row citing `source_file` and `source_sha256`. Unverified periods keep an empty `source_sha256` on the universe file the loader reads, as `membership.py` already does, so a scan cannot treat them as verified. The name-only change log is attached as corroboration, not as a row that lacks a symbol and ISIN.
2. **Certified research universe.** The symbol-dates `classify_symbol_date` marks `ELIGIBLE`, with the `certify_members` label, the dataset id, and the input hashes. A subset is labelled `CERTIFIED_SUBSET`. It is not described as the Nifty 100.
3. **Exclusion register.** Every non-eligible symbol-date or period that the claimed window touched: symbol, ISIN, date or interval, blocking gate, reason, and the evidence pointer. One row per exclusion. A symbol excluded for identity stays listed even if its EOD file is perfect.

All three point back to source documents and hashes. A number in a summary with no row behind it is not an output.

## 14. Source-to-output audit

Reconcile, and investigate every difference:

| Stage | What is counted |
|---|---|
| Original source records | Notices, circulars, saved JSON bodies, bhavcopy rows, identity lines, with hashes |
| Parsed records | Parser output before canonical writing: events, calendar rows, bhavcopy rows |
| Canonical records | The CSV or store the research code loads |
| Eligibility results | One `classify_symbol_date` result per symbol-date in the claimed window |
| Certified records | `final_eligibility` `ELIGIBLE` |
| Excluded records | Every other final eligibility |

The counts must add up. Parsed = canonical + rejected-at-parse, after you account for non-price subjects the parser deliberately skips. Eligibility = certified + excluded. A symbol present in the source and absent from both certified and excluded is a lost row, not a rounding difference. A symbol in the certified set without a source hash is a false inclusion.

Record the commands, the input hashes, and the residual discrepancies. Do not stop at "the totals look close".

## 15. Certification labels

Use one label for the claimed scope. Do not collapse them into "done".

| Label | It means | It does not mean |
|---|---|---|
| `IMPLEMENTATION_COMPLETE` | The code and tests for the check exist | The historical files are true |
| `DATA_VALIDATION_COMPLETE` | Local files passed the format, hash, and reconciliation checks that were run | An official notice was read, or the universe is certified |
| `SOURCE_VERIFICATION_COMPLETE` | The cited official documents were read and the transcription matches them for a named scope | Every symbol-date is eligible |
| `RESEARCH_UNIVERSE_CERTIFIED` | Named symbol-dates passed every gate. The set is `CERTIFIED_SUBSET` or, only with the full-index conditions, `COMPLETE_NIFTY100` | A backtest is valid, or the product is production-ready |
| `EXTERNAL_PARITY_PENDING` | TradingView or another external comparison is still open | Internal tests failed, or internal tests replace the comparison |
| `COMPLETE_WITH_EXPLICIT_LIMITATIONS` | The stated scope is finished and every exclusion and missing baseline is written down | Full-index certification |

Full historical Nifty 100 certification (`COMPLETE_NIFTY100` for a range) requires all of:

- a constituent baseline whose rows carry symbols or ISINs, not merely names, covering the start of the range
- human `decision` `ACCEPTED` on the membership rows the periods use, with matching hashes
- identity resolved for every required member, or that member removed from the "full index" claim and the claim dropped
- corporate-action coverage that is not an empty body and not an unparsed price event, for every required member
- calendar and EOD reconciliation for the range
- price continuity passed, with raw OHLC still canonical
- the source-to-output audit balanced
- external parity still named separately if it is pending

D59's missing pre-2020-12-31 baseline forbids a full-index claim before that date. Blank `decision` cells forbid a full-index claim on or after that date. Say so. Certify the subset that actually passes, or certify nothing.

`DATA_READY` is a separate readiness word used by the repository. Do not claim it from this skill unless `nse/docs/REAL_DATA_READINESS.md` and the readiness command agree. Engineering completion, data validation, source verification, universe certification, and external parity stay separate sentences.

## 16. Decision record

Every material data decision is recorded where the repository already keeps that kind of decision. An engineering choice is the next `ED-<n>` in `nse/docs/ENGINEERING_DECISIONS.md`. An owner choice is written into `nse/docs/DECISION_LOG.md` only after the owner makes it. A symbol-level evidence decision goes in the P0 evidence register already in use under `docs/product-discovery/p0/`, or in the exclusion register, without being dressed up as `USER_APPROVED`.

Each material data decision contains:

- Decision ID
- Symbol
- ISIN
- Effective date
- Historical period
- Source documents
- Source hashes, where a file was used
- Evidence
- Contradictory evidence
- Decision
- Reasoning
- Confidence (`HIGH` only under the rule in section 6.3; otherwise the record excludes)
- Consequence for eligibility, naming the gate and the symbol-dates
- Validation performed, including the command and the result, or `NOT_RUN`

A decision without a source document is a note, not a certification.

## 17. Failure and uncertainty

Fail closed.

- Insufficient evidence: exclude the symbol-dates, write the register row, continue.
- Conflicting primary evidence: preserve both, exclude the affected continuity, continue.
- Parser uncertainty: `UNPARSED_PRICE_EVENT`, MANUAL on G0, no invented ratio.
- Empty corporate-action body: `EMPTY_RESPONSE_COMPLETENESS_UNKNOWN`, not a clear gate.
- Calendar uncertainty: `UNRESOLVED`, no inferred hours, history rules ED-31 and ED-44.
- Identity uncertainty: no join, no minted ISIN.
- One bad symbol: that symbol only.
- A test you did not run: `NOT_RUN`. Do not describe it as a pass.
- A synthetic fixture: proof of the code path only. Say so in the same paragraph as any result.

Do not manufacture a candle, a session, a member, or a ratio so that a scan can finish.

## 18. Testing and validation

Run the focused groups, then the broader suite when the change touches shared research code:

```
python3 -m nse.research.cli health
python3 -m nse.research.cli readiness
python3 -m nse.research.cli inventory --help
python3 -m nse.research.cli eod-coverage --help
python3 -m nse.research.cli instruments-check --help
python3 -m nse.validation.run_all --group data --group data_readiness --group acquisition --group risk_instruments
```

Add or extend tests when the behaviour changes. The existing modules to keep honest:

| Risk | Tests that must still describe it |
|---|---|
| Membership boundaries, ADD/REMOVE dates, count exceptions, review scopes | `tests/test_research_membership.py` |
| Identity joins and refused joins | `tests/test_research_instruments.py` |
| Corporate-action parsing, empty bodies, unparsed subjects | `tests/test_research_corporate_actions.py` |
| Symbol-date independence and full-index flag | `tests/test_research_dataset_eligibility.py` |
| Calendar classification and unresolved dates | `tests/test_nse_calendar.py`, `tests/test_nse_calendar_data.py` |
| EOD schema, EQ isolation, archive hashes | `tests/test_nse_bhavcopy.py`, `tests/test_nse_eod_evidence.py`, `tests/test_research_eod_coverage.py` |
| Series separation and excluded-session gaps | the D52 and ED-30 regressions already in the data tests |
| Exclusion handling | a failing gate produces an exclusion code and does not flip a neighbour |
| Certified-universe reconciliation | certified count + excluded count = input count |

Required cases, whether or not a story currently covers them:

- An ADD on `effective_date` and a REMOVE present only through the previous calendar day.
- A rename that keeps the ISIN, and a same-ticker pair that must not join.
- An ISIN notice with two effective sessions, which must not join.
- A coverage body of `[]`, which must not become `COVERED_NO_EVENTS_PROVED`.
- An unparsed price subject, which must not receive a ratio copied from the price gap.
- A previous-close break with no event and no D52 exclusion, which must fail the price gate.
- A D58 date, which stays a regular equity session, and a different unresolved date, which does not.
- An accepted legacy file and a UDiFF file on the wrong side of 2024-07-08, which is quarantined.
- A BE-only stretch, which stays missing EQ.
- Symbol A excluded and symbol B certified on the same date.
- A `COMPLETE_NIFTY100` label refused when any required `decision` is blank or `index_evidence_resolved` is false.

Synthetic tests and a green `run_all` never prove that the historical books match the exchange. External parity stays `EXTERNAL_PARITY_PENDING` until the reference-data skill has a recorded comparison. Report the commands, the counts, and what was not run.

## 19. Documentation and audit trail

Update the existing readiness note, the blocker board, and the evidence register so they match the files. Do not open a parallel certification document when one of those already has the section.

Record dataset id, loader version, file counts, first and last accepted session, limitations, and the certification label. Scan manifests keep the hashes of the inputs they used. A later file drop does not silently rebind an old scan.

Material parser or eligibility changes cite the decision id, the test, and the symbol-dates whose label changed. A correction that voids a review hash says the hash was voided and that `decision` was not rewritten.

## 20. Phase completion

P0's data scope is complete for a named window only when:

- the three outputs in section 13 exist for that window and reconcile under section 14
- the certification label matches section 15, including an honest subset
- D58 is intact and no new unresolved calendar date was inferred away
- raw OHLC is still the research price and EQ was not backfilled
- no agent-written `ACCEPTED` landed in the review file
- the validation commands in section 18 were run and their real results are in the report
- remaining owner gates are listed as owner gates, not as engineering debt you pretended to close

A finished parser with an empty certified set is `IMPLEMENTATION_COMPLETE` plus `NO_CERTIFIED_SYMBOL_DATES`. It can be a correct stopping point. It is not full-index certification, and it is not permission for P7 to quote performance.

P2 may ship chart UI on labelled fixtures while this phase is open. P2 may not present those fixtures as the certified universe. P7 may not cite uncertified symbol-dates as certified evidence. P11's data gate cannot pass on a slogan. It passes on the label and the register.

## 21. Execution protocol

1. Read `.claude/skills/gtf-autonomous-project-lead/SKILL.md`, then this file.
2. Record branch, HEAD, and working-tree status. Identify owner-dirty files. Do not overwrite them.
3. Name the phase, the symbols, and the date range. Re-read the decisions and the blocker board in section 4.3.
4. Collect the source files and hashes before trusting a summary report.
5. Classify membership, identity, corporate actions, calendar, EOD, and price continuity with the procedures above.
6. Exclude where the evidence fails. Do not pause the rest of the universe for an owner guess.
7. Run `classify_symbol_date` / `certify_members` for the claimed dates. Set `index_evidence_resolved` only when section 15's full-index conditions are true.
8. Write the three outputs and the decision records.
9. Reconcile source to output. Investigate every gap.
10. Run the tests in section 18. Report actual results.
11. State the certification label, the limitations, and the next data task. Stop there unless the owner asked for a later phase.

When the task is a backtest or a production gate, load the quantitative or production skill as well. Those skills consume this certification. They do not weaken it.
