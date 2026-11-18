# GTF P0-P4 completion report

**Date:** 2026-11-15  
**Governance chair:** `gtf-autonomous-project-lead`  
**Final status:** `P0_P4_COMPLETE_WITH_EXPLICIT_LIMITATIONS`

This report is the acceptance deliverable for the P0-P4 completion programme. It treats the current repository as source of truth. Prior phase certification reports are evidence of intent, not proof that the tree is complete.

---

## 1. Executive summary

The approved **software** scope through P4 is in a defensible `COMPLETE_WITH_EXPLICIT_LIMITATIONS` state: P1-P4 platform features pass their available suites with preserved authority boundaries (`authorises_order` always false; journal owns caps/ED-3; P3/P4 cannot elevate blocked candidates). Under D66, the P0 corporate-action completeness **gate** now requires two independent sources plus event reconciliation; the single-source certification path is removed (ED-56, builder `1.6.0`).

What is **not** complete: historical data certification. `completeness.csv` is absent, **0** of **123,778** member-dates are certified, membership still needs owner decisions on the remaining backlog groups, and full local-data `run_all` plus an automated visual screenshot matrix were not executed.

Do not start P5 from this report.

---

## 2. Phase-by-phase completion status

| Phase | Software status | Data / evidence status |
|---|---|---|
| P0 | Gate + backlog architecture updated for D66 / four-field backlog | **Incomplete:** 0 certified; no completeness windows; open OD-ID/PX/MEM/TV items |
| P1 | `COMPLETE_WITH_LIMITATIONS` (prior + revalidated) | N/A (fixtures) |
| P2 | `COMPLETE_WITH_LIMITATIONS` (prior + revalidated) | Charts label non-certified data; OD-P2-1 deferred |
| P3 | `COMPLETE_WITH_LIMITATIONS` (prior + revalidated) | CERTIFIED discovery refused while P0=0 |
| P4 | `COMPLETE_WITH_LIMITATIONS` (prior + revalidated) | CERTIFIED planning demoted; P4-IR-04 accepted |

---

## 3. Requirements-to-implementation traceability (summary)

| Requirement | Implementation evidence |
|---|---|
| Canonical path `pipeline → scanner → qualification` | Unchanged; P3/P4 consume stored envelopes only |
| Fresh unbreached demand only; fail closed on unknown | Preserved in `nse/`; platform does not recompute eligibility |
| Caps 10/10 independent; ED-3 | `nse/research/store.py` + P1 desk; platform preview advisory |
| `authorises_order` false | Asserted across platform APIs/UI/tests |
| D66 dual-source CA completeness | `corporate_actions.load_completeness` / `load_reconciliation` / dual-hash marker |
| Membership ≠ identity ≠ EQ | `P0_MEMBERSHIP_BACKLOG.csv` four status fields |
| No broker / no auto execution | No order endpoints; OpenAPI omits unimplemented writes |

---

## 4. Owner decisions verified and outstanding

### Verified (binding)

| ID | Status | Scope used |
|---|---|---|
| D62 | `USER_APPROVED` | Three CA evidence tiers |
| D63 | `USER_APPROVED` | Six P0 data gates |
| D65 | `USER_APPROVED` | T-001 batch 2 membership rows only |
| D66 | `USER_APPROVED` | OD-CA-1 Option A dual-source + reconciliation bar |
| D42 | `USER_STATED` | Caps / expiry operating constraints (unchanged) |

Decision-log SHA-256 at Batch 0 verification: `ab748e1c2a406bf4304d9402a285747841a00b400f49028677bb6195e79c913d`.

### Outstanding (owner-reserved; not decided here)

1. Per-window `- **Completeness window accepted:**` items (D66 explicitly does **not** approve any row or source file).
2. Membership `ACCEPTED`/`REJECTED` for remaining blank ledger rows (24+ sufficient groups; dummy/identity groups still deferred).
3. OD-ID-1 / OD-ID-2 (BAJFINANCE, GRASIM).
4. OD-PX-2 / OD-PX-3 / OD-PX-4; OD-MEM-2/3; TV-1; B11-P.
5. R-5 precedence wording.
6. Optional later: platform plan state sync after journal cancel (P4-IR-04); auto `EXPIRED` production.

---

## 5. Defects discovered and fixed (this programme)

| ID | Severity | Finding | Remediation | Retest |
|---|---|---|---|---|
| A-SINGLE-SOURCE | Critical | One approved source could certify | Dual-source schema + marker (ED-56) | P0 CompletenessRegister + e2e PASS |
| IR-P0-01 | High | Empty `events: []` recon could prove a window | Require non-empty events or `empty_window: true` | New adversarial test PASS |
| IR-P0-02 | Medium | Stripped API JSON / `[]` not always detected as API | Shape detection on `exDate` lists and `[]` | Extended API-shape test PASS |
| REPO-EMDASH | Low | Em-dashes failed `test_repo` | ASCII replacements in product-discovery docs | repository group PASS |

Independent review: independent-reviewer agent transcript 07d0bf6f-9f3f-441e-8e2f-aa6a32555c25. Contrarian: contrarian-reviewer agent transcript eeaa7239-8551-4f4b-b168-6e8357dfa0c8.

---

## 6. Known accepted limitations

1. **P0 certified count = 0.** Engineering gate ≠ historical certification.
2. On-disk `P0_CERTIFICATION_SUMMARY.json` still reports builder **1.5.0** (last safe rebuild). Code is **1.6.0**. No production rebuild was run (would rewrite outputs; certified would remain 0 without real dual-source evidence).
3. No backup schedule; app backup excludes raw EOD archives (P1).
4. In-memory sessions (D57); restart needs re-bootstrap.
5. OD-P2-1: no standalone chart without stored scan.
6. Weekly/Monthly volume not aggregated.
7. P3: OI-007 omitted; no sector filter (D6); null `zone_id` collapses desk rows.
8. P4-IR-04: platform `APPROVED` may remain after journal cancel; journal remains authority.
9. P4 `EXPIRED` modeled but not auto-produced.
10. Full `run_all` with local_data **not run** this programme.
11. Automated visual screenshot matrix **not run**; component/vitest coverage used instead.
12. Charge tariffs not verified against official PDFs.

---

## 7. P0 certification state

| Metric | Value |
|---|---|
| Member-dates (summary) | 123,778 |
| Certified member-dates | **0** |
| Completeness register file | **absent** |
| Proved windows | **0** |
| Code builder version | **1.6.0** |
| On-disk summary builder | 1.5.0 (stale vs code; counts still 0) |
| Membership periods verified | 85 of 185 |
| Ledger | 140 `ACCEPTED`, 131 blank |

---

## 8. Test commands and exact results

| Command | Result |
|---|---|
| `python3 -m pytest -q -p no:cacheprovider tests/test_research_p0_certification.py tests/test_research_p0_build_e2e.py` | **66 passed** (after IR fixes + em-dash) |
| `python3 -m unittest discover -s platform/tests` | **58 passed** |
| `cd platform/web && npm test -- --run` | **48 passed** (12 files) |
| `cd platform/web && npm run build` | **PASS** |
| `python3 -m pytest -q -p no:cacheprovider tests/test_research_store.py tests/test_architecture.py` | **108 passed** |
| `python3 -m pytest -q -p no:cacheprovider platform/tests/test_api_security.py tests/test_research_store.py` | **93 passed** (2 pydantic deprecation warnings) |
| `python3 -m nse.validation.architecture` | **PASS** (54 modules, 0 violations) |
| `python3 -m nse.validation.docs_health` | **PASS** |
| `python3 -m nse.validation.run_all --no-data --group architecture --group repository --group hooks --group validation_framework` | **PASS** (69 ran, 0 failures) |
| Full `run_all` with local_data | **NOT RUN** (limitation) |
| Automated visual screenshot matrix | **NOT RUN** (limitation) |

---

## 9. Visual QA evidence

No automated screenshot capture environment was exercised end-to-end in this programme.

Proxy evidence (not a substitute for a full visual matrix):

- Web vitest covers overview, scanner, watchlists, opportunities navigation, plans navigation, chart zone helpers, shell navigation (48 tests).
- Production build succeeds.
- Known empty/loading/error paths covered in unit/UI tests for dashboard and scanner.

**Limitation:** desktop/narrow viewport screenshot matrix remains outstanding for a stricter P2 visual claim.

---

## 10. Security and recovery review

| Area | Result |
|---|---|
| Session cookie logging | Tested: logs do not keep session cookie |
| Expired session rejection | Tested |
| OTP/password logging | `logsafe` path retained; security suite PASS |
| Backup restore | Restore-check leaves live files; interrupted restore cleans partial |
| OpenAPI | Cookie auth; unimplemented writes omitted |
| Dependency / CVE full audit | Not re-run as a standalone SCA product in this programme; platform security tests PASS |
| `authorises_order` | False on all checked paths |

---

## 11. Cross-phase integration findings

Verified authority chain:

`P0 data labels → stored scanner envelope → P3 opportunity metadata → P4 plan → P1 journal`

- P3 cannot SHORTLIST blocked/rejected/data-insufficient canonical statuses.
- P4 refuses blocked candidates; approve path keeps `authorises_order: false`.
- Charts never claim P0 CERTIFIED for fixture/exploratory candles.
- Dual-state P4 plan vs journal cancel remains an accepted UI desync, not an eligibility elevation.

---

## 12. Independent-review register

| Finding ID | Phase | Severity | Disposition |
|---|---|---|---|
| A-SINGLE-SOURCE | P0 | Critical | Fixed (ED-56) |
| IR-P0-01 | P0 | High | Fixed |
| IR-P0-02 | P0 | Medium | Fixed |
| IR-P0-03 | P0 | Low | ED-55 annotated superseded |
| IR-P0-05 | P0 | Medium (process) | Documented; legacy `recommendation_on_file` retained beside four fields |
| P4-IR-04 | P4 | Medium | Accepted limitation |
| Contrarian C1 | Programme | Critical (packaging) | Accepted as explicit limitation: software ≠ certified data |
| Contrarian C2 | P0 evidence | Critical (external) | Outstanding; 0 certified |

No unresolved Critical/High **software** defects remain after Batch 8 remediation. External-evidence Critical items remain open and are listed as limitations, not fixed by code.

---

## 13. Git branch, HEAD, working-tree status

| Item | Value |
|---|---|
| Branch | `main` |
| HEAD | `69858d07ccb016b74bc1d518b66b9948656ad6cf` |
| Staged | **none** |
| Commits this programme | **none** |
| Pushes | **none** |
| Working tree | Dirty (~196 paths); pre-existing P0-P4 work preserved |

---

## 14. Remediation-owned files (this programme)

- `nse/research/corporate_actions.py`
- `nse/research/p0_certification.py` (builder 1.6.0 + summary note)
- `nse/docs/ENGINEERING_DECISIONS.md` (ED-56; ED-55 marker note)
- `tests/test_research_p0_certification.py`
- `tests/test_research_p0_build_e2e.py`
- `docs/product-discovery/p0/P0_MEMBERSHIP_BACKLOG.csv`
- `docs/product-discovery/p0/P0_MILESTONE2_REMEDIATION_BLOCKER.md`
- `docs/product-discovery/P0_P4_COMPLETION_REPORT.md` (this file)
- Em-dash ASCII cleanup across selected `docs/product-discovery/**` files (repo hygiene)

Unrelated dirty/untracked files outside this list were inspected only as needed and left as owner/other-session work.

---

## 15. Explicit confirmation: no commits, pushes or staging

Confirmed at programme end:

- `git rev-parse HEAD` → `69858d07…` (unchanged from Batch 0 baseline).
- `git diff --cached` → empty.
- No `git add`, `git commit`, `git push`, reset, clean, or history rewrite.

---

## 16. Remaining blockers and external evidence dependencies

1. Acquire and owner-approve dual-source CA completeness windows (D66 per-window markers).
2. Owner membership decisions for remaining blank ledger rows (do not auto-ACCEPT).
3. OD-ID-1/2, OD-PX-2/3/4, OD-MEM-2/3, TV-1, B11-P as recorded in P0 blockers.
4. Optional: rebuild P0 outputs under builder 1.6.0 into an isolated out-dir (expect certified still 0).
5. Optional: full local_data `run_all` when owner bhavcopies are available and safe.
6. Optional: automated visual screenshot matrix.
7. Optional: P4 dual-state sync / auto-EXPIRED (needs requirements confirmation).

---

## Conclusion

**Is the approved P0-P4 software scope genuinely complete?**

**Yes, with explicit limitations:** `P0_P4_COMPLETE_WITH_EXPLICIT_LIMITATIONS`.

The software through P4 is integrated, tested under available suites, and respects trading/authority invariants. The P0 **data** foundation is **not** certified (0 member-dates). Calling the programme "fully complete" without those limitations would be false. Do not start P5 until the owner accepts this status and prioritises remaining external-evidence work separately.
