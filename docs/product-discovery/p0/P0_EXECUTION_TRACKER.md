# P0 execution tracker

GTF P0, the historical data foundation (Product Prompt 01, milestone MP1). This file is the persistent execution record across sessions. Update it after each coherent milestone. Do not start a second tracker. The live blocker list is `P0_REMAINING_BLOCKERS.md`.

Each statement carries one of these labels: **fact** (recomputed from files on disk), **prior report** (stated by an earlier document and not re-verified), **inference**, **recommendation** or **owner decision**.

## 1. Executive status (2026-11-15, end of Milestone 1)

| Item | Status |
|---|---|
| Overall P0 | **`P0_INCOMPLETE`**. Certified P0 data symbol-dates: **0** of 123,778 member-dates (fact). 73,366 are labelled exploratory only under D62 and are not certified. Milestone 1 (engineering) is closed with external blockers; Milestone 2 (evidence and certification) has not started (`P0_MILESTONE2_HANDOFF.md`) |
| Scope (owner decision D63) | P0 certifies six data gates. It is not GTF trade eligibility, and every output row says so |
| Active workstreams | Milestone 2: owner decisions on 24 evidence-sufficient T-001 groups; OD-CA-1 completeness source |
| Completed or validated | T-002 calendar `VALIDATED`. T-003 integrity `VALIDATED` (gaps contained). T-007 builder 1.5.0 `VALIDATED` (three independent review rounds, ED-55). R-12 `IMPLEMENTED_WITH_RESIDUAL_LIMITATIONS` (ED-52, ED-54) |
| Blocked | T-004 (OD-CA-1). T-006 (external evidence) |
| Owner decisions required | OD-CA-1 completeness source; T-001 batch 3 onward; OD-ID-1/2; optional OD-PX-3/OD-PX-4 exception rules |
| External evidence required | A corporate-action completeness source; TradingView exports; single-date ISIN notices for BAJFINANCE and GRASIM; a pre-2020 constituent baseline |
| Critical risks | OD-CA-1 (nothing can certify). R-12 residual (omitted events under 15%) |
| Last validation | 2026-11-15. See section 2A |
| Commits | None. No commit was authorised. T-001 batch 1 and every change listed here are uncommitted |

## 2. Owner decisions recorded (owner decision)

| ID | Content | Where recorded |
|---|---|---|
| D62 | Corporate-action evidence tiers. `CA_RESPONSE_PRESENT_NOT_COMPLETE` is exploratory only and never passes the gate | `DECISION_LOG.md`, ED-51 |
| D63 | P0 data certification uses six data gates and does not run the GTF pipeline | `DECISION_LOG.md`, ED-51 |
| D64 | R-12 batch authorised; T-001 batch 2 held until explicit answers (hold ended by D65) | `DECISION_LOG.md`, ED-52 |
| D65 | T-001 batch 2: 17 rows accepted on 2026-11-13 (all five cards) | `DECISION_LOG.md`, ledger |

## 2A. Milestone 1: engineering and data-foundation closure (2026-11-15)

| Task | Status | Milestone 1 work (fact) | Remaining | Owner of next step | M1 / M2 |
|---|---|---|---|---|---|
| T-001 Nifty 100 membership | `OWNER_DECISION_REQUIRED` | 140 accepted rows re-verified, 0 exceptions (batch 1: 123; batch 2: 17, D65). Conversion audited: 7 of 7 checks pass (date rules, no overlaps, counts 100 or 101 on all 1,827 days, unique keys, ISIN changes keep the seat). All 131 undecided rows classified with evidence (`P0_MEMBERSHIP_BACKLOG.csv`): 24 groups sufficient, 14 insufficient, 25 count groups not applicable | Owner decisions on 24 groups (about 175 of 185 periods if all accepted) | Owner | M2 |
| T-002 Trading calendar, incl. Dhanteras (D58) | `VALIDATED` | 211 confirmed events, 2,466 equity sessions, 12 excluded held sessions, 0 missing, 0 unresolved; 2024-01-20 hours still labelled inferred | None | n/a | M1 done |
| T-003 Raw EOD and price integrity | `VALIDATED`; gaps `CONTAINED` | 2,478 accepted archive dates, 0 hash mismatches, raw OHLC unchanged, EQ only. 25 non-EQ stretches are `SOURCE_HAS_NO_EQ_ROW` (unrecoverable); 260 member-dates excluded. BL never replaces EQ (1,312 coexisting days) | OD-PX-3, OD-PX-4 optional rules | Owner (optional) | M2 |
| T-004 Corporate actions | `BLOCKED_EXTERNAL_EVIDENCE` | Completeness register implemented and hardened (ED-54, ED-55); empty today, so nothing passes. Tiers per D62 | A completeness source and a marked owner decision (OD-CA-1) | Owner plus external | M2 |
| T-005 Identity | `BLOCKED_EXTERNAL_EVIDENCE` | Verified, dated rename policy (35 links, all verified); ambiguous or unverified renames never join; DUMMYREL never resolves to JIOFIN | GRASIM and BAJFINANCE single-date ISIN records | External | M2 |
| T-006 TradingView parity | `WAITING_FOR_EXTERNAL_EVIDENCE` | Unchanged: 34 blank worksheet rows; 29 components not externally validated | Exports listed in the handoff, section E | Owner | M2 |
| T-007 Certification builder | `VALIDATED` | Builder 1.5.0: six data gates, synthetic end-to-end fixture, independent reconciliations, rebuild byte-identical | None in engineering | n/a | M1 done |
| T-008 Independent validation | `VALIDATED` for Milestone 1 | Three review rounds by a separate read-only agent; see below | Final certification report | Milestone 2 | M2 |
| R-12 scanner safety | `IMPLEMENTED_WITH_RESIDUAL_LIMITATIONS` | Official archives and user CSV files screened; 25 adversarial tests; 26 of 125 recorded events below the band (all rights issues, small bonuses and demergers); no safe lower band | Closes only with OD-CA-1 | External | M2 |

**Independent review (T-008).** A separate read-only agent ran three rounds.
- Round 1:
  - full reconciliation of all 123,778 rows and all register intervals;
  - all six gates recomputed for every row;
  - a 60-row random sample (`random.Random(20261115)`) re-derived from raw files;
  - every identity transition in the window (24), all 260 non-EQ member-dates, all 702 steps across excluded sessions, and all 39 price-event steps;
  - 33 adversarial probes.
  - Result: 0 mismatches and no wrongly certified row. 5 medium latent fail-open paths: M-1 to M-5.
- Rounds 2 and 3 re-ran the reconciliation and the probes against the corrected builder, and found further latent residuals:
  - medium: N-1, N-3, N-3b, R-2, R2-A, R2-B;
  - low: R-1, R-3, N-2, R2-C, O-2 and others.
- Every finding was fixed (ED-55). On real data the fixes changed only:
  - 2 price steps (HDFCBANK 2024-03-04, TATACONSUM 2024-05-21), from exploratory to excluded;
  - the label on 6,432 already-failing rows.
- Final round result: see the progress history.

## 3. Workstreams

### T-001 Historical Nifty 100 membership: `IN_PROGRESS` (batch 2 applied; batch 3 next)

- State (fact, 2026-11-13): 271 review rows; 140 `ACCEPTED` (batch 1: 123 on 2026-11-12; batch 2: 17 on 2026-11-13), 131 blank. 185 periods: 85 verified, 100 not. The scope columns (25 `count_approval`, 10 `mapping_approval`) are unchanged.
- Batch 2 (D65): the owner accepted all five cards (G-E04 10 rows, G-E05 4 rows, and the JUBLFOOD, TATASTEEL and BAJAJFINSV ISIN changes).
  - Recorded on exactly those 17 rows, with reviewer `Yash Jain`, `reviewed_on` 2026-11-13 and a "T-001 batch 2" note.
  - The schema token is `ACCEPTED`.
  - The ledger SHA-256 went from `292b0e20…` to `9b0fcba0…`. Exactly 17 lines changed, and only the decision, reviewer, date and notes fields.
- Effect (fact): 14 periods newly verified, matching the dry run. 6,489 member-dates moved from failing membership to passing it, all inside those periods. The five E04 ADD periods and JUBLFOOD's new-ISIN period stay unverified until their closing rows are decided.
- Worksheets updated by the batch 1 convention: `P0_MEMBERSHIP_ROW_RECOMMENDATIONS.csv` (17 rows) and `P0_MEMBERSHIP_GROUP_REVIEW.csv` (5 groups). `nse/data/universe/README.md` is updated too.
- `tests/test_research_membership.py` `RecordedOwnerApprovals` pins the new state: the 17 keys, the batch 2 date and note, 140/131, 85/100, and the 14 periods. Rows outside both batches must stay blank.
- Next action: batch 3 evidence cards (the next five acceptance-recommended groups in date order).

### T-002 Trading calendar: `VALIDATED` (2016-2025)

- Facts (2026-11-12): 211 `CONFIRMED` events; 2,466 equity sessions; 12 excluded sessions, all with a held file; 0 missing; 0 unresolved dates in the window; D58 intact; OD-CAL-1 still labelled inferred.

### T-003 Raw EOD and price integrity: `IN_PROGRESS`

- Facts: 2,478 accepted archive dates, 0 hash mismatches. Raw OHLC unchanged. EQ-only.
- F-1 (fact): PREVCLOSE is unadjusted on ex-dates (55 of 55 events). The scanner fix is ED-52.
- Price gate: 1,130 member-dates fail. 700 are after a held excluded session; 383 have no EQ row; 39 are on a recorded price-scale ex-date; 3 are ISIN-change steps; 4 follow a BE-only session; 1 is the ADANIENSOL band move.
- ADANIENSOL 2024-11-21 (fact, investigated): a market move to the exchange's 20% price band. Details are on the blocker board under OD-PX-3. It is not a data error and not a price-scale event, and it stays excluded.

### T-004 Corporate actions: `BLOCKED` (OD-CA-1)

- D62 implemented (ED-51). The tier is reported beside the gate:
  - 108,325 member-dates `CA_RESPONSE_PRESENT_NOT_COMPLETE`;
  - 15,453 `CORPORATE_ACTIONS_UNVERIFIED`;
  - 0 `CA_COMPLETENESS_VERIFIED`.
- Every row keeps the `CORPORATE_ACTIONS_UNVERIFIED` limitation.
- Response integrity is not completeness:
  - Integrity: the bytes are the saved response, the response is non-empty, and it parsed.
  - Completeness: the API listed every event in the window.
  - Only completeness can pass the gate.
- The shared classifier now passes only `CA_COMPLETENESS_VERIFIED` or `COVERED_NO_EVENTS_PROVED` (review F4, ED-53).
- F-2 (fact): the API's `isin` field prints stale ISINs. It is not identity evidence.

### T-005 Identity: `IN_PROGRESS`

- Facts: 121,323 member-dates `RESOLVED`; 2,455 `UNKNOWN_INSTRUMENT`: GRASIM 1,234, BAJFINANCE before 2025-06-16 1,098, dummy seats 123.
- Renames joined through verified records: TELCO→TATAMOTORS→TMPV, ADANITRANS→ADANIENSOL, CADILAHC→ZYDUSLIFE, ZOMATO→ETERNAL, MCDOWELL-N→UNITDSPR, LTI→LTIM.
- Correction (review F6): the earlier line said DUMMYREL→JIOFIN resolves. It does not. DUMMYREL is `UNKNOWN_INSTRUMENT` on every one of its member-dates. JIOFIN resolves from its own listing.

### T-006 TradingView parity: `WAITING_FOR_EXTERNAL_EVIDENCE`

- Unchanged: 34 blank worksheet rows; the INFY reference rows are Yahoo screenshots; 29 components `externally_validated=false`.

### T-007 Build and integration: `IMPLEMENTATION_COMPLETE`, reviewed

- `nse/research/p0_certification.py` build 1.1.0 evaluates the six data gates. The rebuild is byte-identical.
- Reconciliation in the summary, all true:
  - member-dates equal the `Universe.members` count;
  - certified plus excluded equal the rows;
  - register sessions equal the excluded count;
  - every excluded date is in exactly one register row;
  - one row per symbol-date;
  - no order authorised.
- The certified file is empty. Exploratory rows exist only in the git-ignored matrix (`nse/output/p0/eligibility_matrix.csv`) and as register and summary labels.
- The old 38 MB `P0_RESEARCH_ELIGIBILITY_MATRIX.csv` (untracked, 2026-11-11) is superseded and was left untouched.

### T-008 Independent validation: `VALIDATION_IN_PROGRESS`

- Independent review (2026-11-13): a separate read-only agent reviewed the builder.
  - It traced 7 records from source to output: ABBOTINDIA 2021-06-15, ACC 2021-03-15, GRASIM 2024-01-10, DUMMYREL 2023-07-21, TATASTEEL 2022-07-28, ADANITRANS 2021-07-01, INFY 2024-09-16.
  - Every gate value matched its hand recomputation. No wrongly certified record was found.
- Findings and corrections (ED-53):
  - F1, a register defect in a committed output: fixed.
  - F2-F4, defects current data does not trigger: fixed.
  - F5, a tautological reconciliation check and missing tests: fixed.
  - F6, documentation drift: fixed in this file and in ED-50/ED-51.
  - F7, rows and inputs missing from the outputs: fixed.
  - F8, a duplicate definition: fixed. The `linked` symbol set is not restricted to verified renames; this is recorded and fails closed today.
- Not yet done:
  - a synthetic end-to-end `build()` fixture;
  - a reviewer reading the NSE PDFs (the reviewer relied on hashes; the batch 2 PDFs were read by this session);
  - `P0_FINAL_CERTIFICATION_REPORT.md`, deferred because it would only restate `P0_INCOMPLETE`.

### R-12 scanner safety (P0-adjacent, separate batch): `IMPLEMENTATION_COMPLETE`

- The wrong assumption: a split shows as a PREVCLOSE break. Before the fix, a hash-verified non-empty response that omitted a split passed G0, and the 10x raw gap reached zone detection.
- The fix (ED-52): `corporate_actions.price_scale_gaps`, a `marketdata` finding, and scanner and G0 handling. G0 is `MANUAL` (`PRICE_DISCONTINUITY_IN_HISTORY`) unless a recorded action explains the step.
  - Raw OHLC is untouched.
  - No zone, freshness or qualification rule changed.
- On real archives the screen flags TATASTEEL 2022-07-28 and ADANIENSOL 2024-11-21, with no PREVCLOSE finding on either.
- Residual: an omitted event below 15%; user CSV inputs are not screened.

## 4. Evidence register (sources inspected)

| Source | Path | SHA-256 | Inspected | Affects |
|---|---|---|---|---|
| NSE Indices release 2022-02-24 | `nse/data/universe/evidence/releases/ind_prs24022022_1.pdf` | `3091cf1c…fcd56` | pages 1 and 5 read | Card 1 |
| NSE Indices release 2022-07-11 | `nse/data/universe/evidence/releases/ind_prs11072022.pdf` | `dd1021f2…982e1f` | pages 1 and 2 read | Card 2 |
| Batch 2 boundary bhavcopies | ten archives, 2022-03-30..2022-09-14 (listed on the cards) | manifest-matched | EQ rows read | Cards 1-5 |
| ADANIENSOL and group sessions | UDiFF archives 2024-11-14..2024-11-26 | manifest-matched | 9 group and 7 control symbols | OD-PX-3 |
| ADANIENSOL corporate actions | `nse/data/corporate_actions/raw/ca_ADANIENSOL_2016_2025.json` | coverage-matched | 9 AGM records | OD-PX-3 |
| Recorded price events 2020-12..2025 | `actions.csv` plus bhavcopies | coverage-matched | 55 events | F-1, R-12 |
| Every certification input | `P0_CERTIFICATION_SUMMARY.json` `inputs_sha256` (now including every saved CA response and the builder source) | | | All outputs |

## 5. Validation (2026-11-13)

- Targeted modules:
  - `test_research_p0_certification`: 34 tests, OK.
  - `test_research_dataset_eligibility`: OK.
  - `test_research_price_scale_r12`: 10 tests, OK.
- Groups after the R-12 change: data_readiness 66, strategy_gates 82, integration 53, adversarial 28, scenarios 31, lookahead 13, backtest 79. All pass, 0 failures.
- `risk_instruments`: 183 tests before the review corrections, PASS.
- Full `python3 -m nse.validation.run_all --out nse/output/validation/p0-final.json`: PASS, 1,416 ran, 0 failures, 0 errors, 0 skipped. The first run failed one test (`test_project_council_skill`: ED-53 lacked its `Reversible` line). The record was fixed and the full suite re-run. `docs_health`: PASS. `git diff --check`: clean.
- Protected hashes are unchanged:
  - Pine `14293fa5…`
  - Rulebook MD `039883be…`
  - Rulebook PDF `e41cd0e7…`

## 6. Dependency graph

```
OD-CA-1 (owner / external completeness source) ──> any certified symbol-date ──> final certification report
T-001 batch 3+ (owner) ──────> membership gate (44,627 member-dates)
OD-ID-1/2 (external notice) ─> BAJFINANCE, GRASIM only
TV-1 (external) ─────────────> external parity statement only
R-12 (done, ED-52) ──────────> scanner safety; independent of certification
```

Next autonomous work:

1. A synthetic end-to-end `build()` fixture (REV-1).
2. Batch 3 evidence cards, prepared but not presented until batch 2 is answered.
3. Restrict `linked` to verified, dated renames (REV-1).

## 7. Commit grouping when authorised (none is authorised)

The three batches must stay separate, and each touches files that already have owner diffs. A commit would need non-interactive hunk isolation, or it should be deferred.

| Batch | Files |
|---|---|
| R-12 (commit first: the builder imports `price_scale_gap`) | `nse/research/corporate_actions.py` (the `price_scale_gap(s)` and docstring hunks), `nse/research/marketdata.py`, `nse/research/scanner.py`, `nse/research/qualification.py`, `tests/test_research_price_scale_r12.py`, the `run_all.py` data_readiness line, ED-52 and R-12 in `ENGINEERING_DECISIONS.md`, D64 |
| Certification builder | `nse/research/p0_certification.py`, `nse/research/dataset_eligibility.py`, `nse/research/corporate_actions.py` (the tier hunk), both test files, the `architecture.py` and `run_all.py` risk_instruments lines, ED-50/51/53, D62, D63, the four P0 outputs, `P0_EXCLUSION_SUMMARY.csv` |
| T-001 batches 1 and 2 | `nse/data/universe/nifty100_review.csv` (123 + 17 rows), `nifty100_universe.csv`, `nifty100_conversion_report.json`, `nse/data/universe/README.md`, `P0_MEMBERSHIP_ROW_RECOMMENDATIONS.csv`, `P0_MEMBERSHIP_GROUP_REVIEW.csv`, `P0_T001_MEMBERSHIP_DECISION_PACKAGE.md`, `P0_T001_BATCH2_OWNER_PACKAGE.md`, `tests/test_research_membership.py` (`RecordedOwnerApprovals` hunk), D65; the rebuilt P0 outputs go with the builder batch |

Never staged with them: D42 files (`nse/research/store.py`, `tests/test_research_store.py`).

## 8. Progress history

### 2026-11-12

- Baseline: HEAD `69858d0`, 17 ahead of origin, nothing staged. Batch 1 uncommitted.
- Built `p0_certification.py` (ED-50). Found F-1 (PREVCLOSE is unadjusted on ex-dates) and recounted OD-PX-1. Wrote the outputs and the batch 2 package. No ledger writes, no commits.

### 2026-11-13

- Recorded owner decisions D62, D63 and D64.
- Builder 1.1.0: six data gates; evidence tiers; research_use labels.
- R-12 batch (ED-52): scale-gap screen in scanner G0; 10 regression tests; verified on real archives.
- Independent review of the builder; corrections F1-F8 applied (ED-53). The register went from 1,662 to 1,667 rows. Counts are unchanged.
- ADANIENSOL 2024-11-21 investigated: a market move to the 20% band, kept excluded.
- Batch 2 evidence cards completed with a dry-run consequence. The ledger is untouched.
- No staging, no commit, no push.
- T-001 batch 2 applied (D65): 17 rows; conversion 85 of 185 periods verified; certification rebuilt and byte-identical on a second build. Certified stays 0. Exploratory goes from 68,143 to 73,368. Membership failures go from 51,116 to 44,627.
- Independent read-only audit of batch 2.
  - Scope: all 271 ledger rows, all 185 periods, all 123,778 matrix rows, all 1,667 register intervals, 14 boundary archives, both release PDFs (text extracted, not rendered) and 3 corporate-action responses.
  - Data change: correct.
  - It found three membership tests pinned to the batch 1 state, now re-pinned to batch 2, and documents still saying "held", now updated.
- No staging, no commit, no push.
- Validation for batch 2. `python3 -m nse.validation.run_all --out nse/output/validation/p0-batch2-owner-approval.json`, final run: 1,418 ran, **1 failure**, 0 errors, 0 skipped. Verdict FAIL.
  - The failure is `test_architecture.RealTree.test_the_documentation_has_no_stale_link_or_command`. It flags `docs/product-discovery/p1/P1_CERTIFICATION_REPORT.md:15`, a link to an agent-session id.
  - That file is untracked. It was written 2026-11-13 08:01-08:07 by concurrent P1/D42 work, not by this batch, and is left untouched.
  - An earlier run in the same window failed 2 `test_research_store` tests while `nse/research/store.py` and `tests/test_research_store.py` were being edited (08:05-08:06). Re-run afterwards they pass.
  - Every group covering this batch passes: risk_instruments 192 (membership, eligibility, certification), data, data_readiness, integration, adversarial, lookahead, repository and council.
  - `docs_health` reports only the P1 link. Architecture rules: 0 violations. `git diff --check`: clean.

### 2026-11-15 (Milestone 1)

- Baseline:
  - HEAD `69858d0`, nothing staged, 84 modified and 102 untracked paths;
  - ledger `9b0fcba0…` (batch 2 verified as recorded);
  - full suite 1,418 ran with 1 failure: the P1 session's broken link, outside P0, since fixed by that session.
- Investigations by separate read-only agents:
  - every undecided T-001 group, with the backlog committed as `P0_MEMBERSHIP_BACKLOG.csv`;
  - an audit of the 140 accepted rows and of the conversion;
  - the non-EQ stretches (ADANIPOWER, CGPOWER and 23 others), all `SOURCE_HAS_NO_EQ_ROW`;
  - OD-PX-4: 700 of 700 with the chain intact through the held session;
  - the R-12 residual: 26 of 125 events below the 15% band, with no safe lower band.
- Engineering:
  - ED-54: verified, dated rename policy; completeness register; R-12 screen on user CSV; synthetic end-to-end `build()` fixture.
  - ED-55: three independent review rounds.
    - Round 1: 5 medium latent paths.
    - Round 2: 3 medium and several low residuals.
    - Round 3: no critical, high or medium path remains (90 probes, 85 safe, 5 by design).
    - Every finding was fixed. The last low item (realpath) was fixed after round 3.
  - Builder 1.5.0.
- Real-data effect of Milestone 1:
  - HDFCBANK 2024-03-04 and TATACONSUM 2024-05-21 moved from exploratory to excluded (M-5);
  - 6,432 already-failing rows were relabelled `EMPTY_RESPONSE_RENAMED_TICKER` (M-3).
  - Certified 0, exploratory 73,366, register 1,671 rows.
  - The rebuild is byte-identical; the ledger and universe are unchanged.
- Documents:
  - `P0_MILESTONE2_HANDOFF.md`, `P0_MEMBERSHIP_BACKLOG.csv`;
  - blocker board updated: R-12, OD-PX-1, OD-PX-4, OD-MEM-1, REV-1 closed;
  - ED-54 and ED-55.
- No owner decision was made. No staging, no commit, no push.
- Final validation on the final source state: `python3 -m nse.validation.run_all --out nse/output/validation/p0-milestone-1.json`.
  - 1,471 ran, 1 failure, 0 errors, 0 skipped.
  - The failure is `test_architecture.RealTree.test_the_documentation_has_no_stale_link_or_command`. It flags `docs/product-discovery/p2/P2_TEST_AND_REVIEW_LOG.md:27`, a link to an agent-session id in an untracked file written 2026-11-15 08:06-08:24 by concurrent P2 work. It is outside P0 and left untouched.
  - Every P0 group passes: risk_instruments 230, data_readiness 81, data, integration, adversarial, lookahead, strategy_gates, backtest, scenarios, repository and council.
  - The previous run's council failure (the token `USER_APPROVED` in ED-55) was fixed by rewording the entry, and the suite was re-run.
  - `nse.validation.architecture`: PASS, 0 violations. `git diff --check`: clean. Protected hashes unchanged.

