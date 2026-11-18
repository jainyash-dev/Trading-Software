# P0 Batch 13 - Engineering readiness

**Date:** 2026-11-15
**Batch status:** COMPLETE. The engineering gates are ready. **Certification is not ready:** it is blocked by evidence and owner decisions, not by software (see `P0_FINAL_BLOCKER_REGISTER.md`).
**No production output was rebuilt.** Two isolated builds were written to the session scratchpad only.

## 1. Full local-data validation (verified, preserved)

| Item | Value |
|---|---|
| Command | `python3 -m nse.validation.run_all --out <scratchpad>/final_report.json` (default mode: local data, reference comparison and static lint included; not `--no-data`) |
| Environment | macOS (Darwin 25.5.0), Python 3 (system `python3`), repository HEAD `69858d07ccb016b74bc1d518b66b9948656ad6cf` with 213 pre-existing changed/untracked paths |
| Verdict | **PASS**, exit 0 |
| Totals | ran **1,475**, failures 0, errors 0, skipped 0 |
| Checks | 27 of 27 PASS: 24 test groups + `repository_checks`, `local_data`, `reference_comparison`, `static_lint`; `checks_not_run` empty |
| Duration | ~931 s of check time (~15.5 min) |
| Mode caveat | `acceptance_mode` false. In `--acceptance` mode a missing local prerequisite fails instead of skipping; this run reported 0 prerequisite skips in every check, so the outcome would not differ, but acceptance mode itself was not run |
| Preserved evidence | `evidence/validation_2026-11-15/run_all_full_local_data.log` (SHA-256 `a13aff58...`), `run_all_full_local_data_report.json` (`4b00b99f...`) |
| Per-check matrix | `P0_TEST_EXECUTION_MATRIX.csv` |

Run-integrity note: in this session several earlier overlapping invocations wrote to the same paths and were stopped, and some background notifications reported results before any run had finished. Those are discarded. The figures above come from the single clean run's own log and JSON, read directly.

Also run after the Batch 11-13 documents: `python3 -m nse.validation.docs_health` PASS (0 findings); `python3 -m nse.validation.architecture` PASS (54 modules, 0 violations); `git diff --check` clean.

Passing tests are software evidence. They are not historical-data certification.

## 2. Builder 1.6.0

| Check | Result |
|---|---|
| `BUILD_VERSION` | `"1.6.0"` (`p0_certification.py:82`); summary `build_version` 1.6.0 |
| Output safety | `--out-dir` is required (no default path); the builder writes only the four outputs there plus `--matrix` if given (`write_outputs`, `p0_certification.py:787-833`) |
| Production files untouched | SHA-256 of `P0_CERTIFICATION_SUMMARY.json`, `P0_CERTIFIED_RESEARCH_UNIVERSE.csv`, `P0_EXCLUSION_SUMMARY.csv`, `P0_RESEARCH_ELIGIBILITY_MATRIX.csv`, `nifty100_review.csv`, `DECISION_LOG.md`, both protected sources and the Rulebook PDF: identical before and after this session |
| Dual-source note wording | Corrected in code; a fresh build's summary carries "two hash-verified independent official sources ... event-by-event reconciliation ..." |

## 3. Determinism (verified)

Two consecutive isolated builds (`build_A`, `build_B`) with identical inputs:

| Output | A vs B | A vs `nse/output/p0_isolated_2026-11-15` |
|---|---|---|
| `P0_CERTIFIED_RESEARCH_UNIVERSE.csv` | identical | identical |
| `P0_MEMBERSHIP_REFERENCE_HISTORY.csv` | identical | identical |
| `P0_RESEARCH_EXCLUSION_REGISTER.csv` | identical | identical |
| `eligibility_matrix.csv` | identical | identical |
| `P0_CERTIFICATION_SUMMARY.json` | identical | differs **only** in `completeness_register.note` (corrected wording) and `inputs_sha256["nse/research/p0_certification.py"]` (the wording fix changed the builder's hash). No count differs |

Hashes: `evidence/validation_2026-11-15/isolated_build_determinism_sha256.txt`. Result: certified 0, member-dates 123,778, periods verified 85 of 185, completeness register absent, proved windows 0.

The builder's own docstring states "No output carries a timestamp, so a rebuild on the same inputs is" reproducible; this test confirms it for these inputs.

## 4. D66 / ED-56 enforcement (rechecked)

Code (`corporate_actions.py`): dual hashes required and distinct; saved API responses refused by name, `/raw/` path, hash and shape; reconciliation must be `gtf.ca_reconciliation.v1`, `RECONCILED`, no unresolved items, every event `MATCH`/`EQUIVALENT`; empty window only with `empty_window: true` and no events; acceptance marker must carry both source hashes, the reconciliation hash, symbol and window under a `USER_APPROVED` decision; the legacy single-hash marker never qualifies.

Tests that exercise it (all in the passing run):

| Requirement | Test |
|---|---|
| Single source never proves completeness | `test_one_source_alone_never_proves_completeness` |
| Identical/copied sources not independent | `test_identical_or_copied_sources_are_not_independent` |
| API response refused | `test_a_saved_api_response_is_not_completeness_proof` |
| Unresolved reconciliation fails | `test_unresolved_reconciliation_fails_closed` |
| Empty events need the empty-window flag | `test_empty_events_without_empty_window_flag_fail_closed` |
| Dual-hash marker only | `test_only_dual_hash_window_marker_items_qualify`, `test_the_decision_must_have_accepted_this_dual_window` |
| Owner decision required | `test_only_dual_source_verified_rows_with_an_owner_decision_count` |
| Empty API list not proof | `test_empty_list_is_not_proof_of_no_events`, `test_an_empty_body_stays_completeness_unknown` |
| Unparsed stays unparsed | `test_the_ten_unparsed_subjects_do_not_become_ratios` |
| End to end | `test_certified_rows_pass_every_data_gate_and_only_with_proved_completeness`, `test_without_the_completeness_register_nothing_certifies`, `test_an_unreadable_completeness_register_stops_the_build` |

Known gap (not a test failure): provenance independence (two different files from the same upstream publisher) cannot be detected by code (Batch 7 finding F-1). Control: owner review of each pair. Recommendation ENG-3.

Not separately tested: a reconciliation event with status `CONFLICT` but an empty `unresolved` list. The code rejects any event status other than MATCH/EQUIVALENT, so it fails closed; a dedicated regression test would document that (recommendation ENG-4).

## 5. Certification readiness matrix

| Gate (D63) | Engineering ready | Data/evidence ready | Owner decision pending | Member-dates passing gate (1.6.0) |
|---|---|---|---|---|
| Membership | Yes | Partly (85/185 periods verified) | 91 rows (+7 optional) | 79,151 VERIFIED |
| Identity | Yes | Partly | OD-ID-1/2 (2,332 member-dates), dummy seats | 121,323 RESOLVED |
| Calendar | Yes | Yes | none | 123,778 |
| EOD (EQ) | Yes | Yes | none (BE-only stays excluded) | 123,395 |
| Corporate action (D66) | Yes | **No: 0 proved windows** | Acquisition authorization; per-window approvals | **0** |
| Price continuity | Yes | Partly | OD-PX-3, OD-PX-4, OWN-1; ENG-1 | 122,646 CONTINUOUS |
| **All six** | Yes | **No** | - | **0 certified** |

## 6. Recommendations (engineering; none implemented)

ENG-1 fractional face-value ratios; ENG-2 backlog per-row text; ENG-3 CA source-ledger provenance fields; ENG-4 regression test for a CONFLICT event with empty `unresolved`; ENG-5 run `run_all --acceptance` once before any final certification claim.
