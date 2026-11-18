# P0 Batch 1 - Pipeline validation report

**Date:** 2026-11-15  
**HEAD:** `69858d07ccb016b74bc1d518b66b9948656ad6cf`  
**Builder code:** `1.6.0`  
**Production rebuild:** not performed (Batch 1 rule)

---

## 1. Commands and results

| Command | Result |
|---|---|
| `python3 -c` assert `BUILD_VERSION == "1.6.0"`; parse D62/D63/D65/D66 | PASS; all four `USER_APPROVED`; `completeness_decisions({})` empty |
| `pytest tests/test_research_p0_certification.py tests/test_research_p0_build_e2e.py` | **65 passed** |
| `pytest ... corporate_actions, identity_policy, dataset_eligibility, membership, price_scale_r12` | **117 passed**, 3 subtests |
| `pytest tests/test_research_p0_certification.py::CompletenessRegister -v` | **15 passed** |
| `pytest tests/test_research_adversarial.py` | **28 passed** |
| `pytest tests/test_nse_calendar.py tests/test_nse_calendar_data.py` | **41 passed** |
| `pytest tests/test_architecture.py tests/test_repo.py tests/test_claude_hooks.py tests/test_validation_runner.py` | **69 passed** (after docs-link fix) |
| `python3 -m nse.validation.architecture` | **PASS** (54 modules, 0 violations) |
| `python3 -m nse.validation.docs_health` | **PASS** (0 findings) after fixing broken agent-id links in `P0_P4_COMPLETION_REPORT.md` |
| `python3 -m nse.validation.run_all --no-data --group architecture --group repository --group hooks --group validation_framework` | **PASS** (69 ran, 0 failures) |
| Full `run_all --no-data` (all groups) | **Not completed** - process burned CPU >15 min with buffered/no progress; superseded by targeted groups + pytest chunks |
| `tests/test_research_data.py` / full EOD coverage suite | **Not completed** - hung beyond several minutes; deferred to Batch 9 with local-data run |
| Production certification rebuild | **Not run** (Batch 1 forbids) |

**Engineering fix in Batch 1:** replaced broken markdown links to agent transcript UUIDs in `docs/product-discovery/P0_P4_COMPLETION_REPORT.md` (docs_health H1). No trading logic changed.

---

## 2. D66 / ED-56 verification matrix

| Requirement | Evidence | Result |
|---|---|---|
| Builder 1.6.0 | `BUILD_VERSION` in `p0_certification.py` | PASS |
| Dual-source requirement | `COMPLETENESS_COLUMNS` has source_a/b + recon; tests | PASS |
| Source independence | `sources_independent`; `test_identical_or_copied_sources_are_not_independent` | PASS |
| Event reconciliation | `load_reconciliation` schema `gtf.ca_reconciliation.v1` | PASS |
| Explicit dual-hash approval | marker `- **Completeness window accepted:**`; real log has **0** items | PASS (parser); no windows approved |
| Empty-window proof | `empty_window: true` required when events empty; test | PASS |
| API-shape rejection | saved API / `exDate` lists / `[]` refused | PASS |
| Single-source rejection | `test_one_source_alone_never_proves_completeness` | PASS |
| Unparsed-event rejection | covered in CA bodies / conversion unparsed path | PASS (related suites) |
| Unresolved-conflict rejection | `test_unresolved_reconciliation_fails_closed` | PASS |
| D66 status parsing | `owner_decision_status` -> D66 `USER_APPROVED` | PASS |

CompletenessRegister tests executed:

- `test_only_dual_source_verified_rows_with_an_owner_decision_count`
- `test_one_source_alone_never_proves_completeness`
- `test_only_dual_hash_window_marker_items_qualify`
- `test_identical_or_copied_sources_are_not_independent`
- `test_a_saved_api_response_is_not_completeness_proof`
- `test_empty_events_without_empty_window_flag_fail_closed`
- `test_unresolved_reconciliation_fails_closed`
- (and 8 supporting register/tier/rename tests)

---

## 3. Batch 1 acceptance

Software gates for D66/ED-56 are validated. Historical certification outputs were not rebuilt. Real-data completeness remains 0 proved windows.

**Batch 1 status:** ACCEPTED WITH LIMITATIONS (full no-data `run_all` and `test_research_data` not finished in this batch).
