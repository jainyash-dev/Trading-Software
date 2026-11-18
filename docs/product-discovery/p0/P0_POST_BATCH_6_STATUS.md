# P0 post-Batch-6 status

**Date:** 2026-11-15  
**HEAD:** `69858d07ccb016b74bc1d518b66b9948656ad6cf`  
**Programme status:** `P0_CERTIFICATION_BLOCKED`  
**CA acquisition:** not authorized (owner has not approved new source downloads)

This note consolidates independent reviews, validation re-checks, and pointers to the owner decision packs. It does not authorize acquisition, membership decisions, or a production rebuild.

---

## 1. Independent reviews (retrieved; not assumed)

Reviews were retrieved from completed agent transcripts (status success). Findings below are from those results, then cross-checked against the repository.

### 1.1 Independent reviewer - agent `9524e165-d46d-4379-aec7-253cf51e8e7a`

| Field | Value |
|---|---|
| Verdict | **PASS** (isolated build fail-closed; historical certification not complete) |
| Scope | Isolated `nse/output/p0_isolated_2026-11-15/`, production summary, D66/ED-56 code paths |
| Tests they ran | 23 passed (completeness/D66/fail_open filter on P0 modules) |

**Agreed facts (re-verified here):**

- Isolated `build_version=1.6.0`, `certified_symbol_dates=0`, matrix only `EXCLUDED_*`, certified CSV header-only.
- `completeness.csv` absent; `completeness_decisions` empty; D66 does not approve any window.
- Production summary remains `build_version=1.5.0`, different file from isolated (not overwritten).
- No fail-open path found that certifies without dual-source evidence under current inputs.

**Disagreement / correction:**

| Item | Reviewer said | Repository check | Disposition |
|---|---|---|---|
| DUMMYREL member-dates | 123x EXCLUDED_MEMBERSHIP | **DUMMYREL alone = 21**; all five `DUMMY*` symbols sum to **123** | Treat as aggregation slip; use per-symbol counts. Correction required in any citation that attributes 123 solely to DUMMYREL. |
| Finding 9 note wording | Singular "a ... independent source" lag | **Already corrected** in `p0_certification.py` to dual-source language after that review | Closed. Isolated summary file still has the old note text until a future isolated rebuild (not run here). |

### 1.2 Contrarian reviewer - agent `c914a68e-0228-41c6-aab3-dbdef7e11b68`

| Field | Value |
|---|---|
| Verdict | **reject** any claim of P0 *historical* certification |
| Forced status | `P0_HISTORICAL_CERTIFICATION_BLOCKED` / programme `P0_CERTIFICATION_BLOCKED` |
| Rejected labels for certification | `COMPLETE_WITH_EXPLICIT_LIMITATIONS`, `PARTIALLY_COMPLETE` (as certification claims) |

**Agreed facts:** 0 certified is the only honest certification outcome; D66 unmet; exploratory CA must not be read as certified; isolated != production; empty API `[]` does not prove completeness today; membership 85/185 is not a partially certified universe.

**No disagreement on status.** Anti-misread rules already recorded in `P0_CERTIFICATION_FINAL_REPORT.md`.

### 1.3 Required corrections from reviews

| ID | Action | Status |
|---|---|---|
| R-NOTE | Dual-source completeness note wording | Done in code; isolated JSON note stale until rebuild |
| R-DUMMY | Cite DUMMY seats as 123 combined / DUMMYREL 21 | Documented here |
| R-CLAIM | Never claim COMPLETE/PARTIAL certification | Status remains BLOCKED |

---

## 2. Validation snapshot (this session)

| Check | Result |
|---|---|
| Builder code `BUILD_VERSION` | **1.6.0** |
| D66 status | `USER_APPROVED`; 0 dual-hash markers; dual-source columns + marker enforced |
| ED-56 | Implemented (`load_completeness` / `sources_independent` / `load_reconciliation`) |
| CompletenessRegister + D66-filtered tests | **23 passed**, 42 deselected |
| Full P0 certification + e2e after wording change | **65 passed** |
| Production summary | **1.5.0**, certified 0 |
| Isolated summary | **1.6.0**, certified 0 |
| Full local-data `run_all` | **Not run** - last `nse/output/validation/report.json` is a targeted group-only invocation (69 tests PASS); `checks_not_run` includes local_data, reference_comparison, and static_lint because only selected groups were requested |

---

## 3. Owner packs prepared (this preparation)

| Deliverable | Path |
|---|---|
| Owner decision pack (all queues) | `P0_OWNER_DECISION_PACK.md` |
| CA provider comparison | `P0_CA_PROVIDER_COMPARISON.md` |
| Membership decision summary | `P0_MEMBERSHIP_DECISION_SUMMARY.md` |
| Identity blockers OD-ID-1/2 | `P0_IDENTITY_BLOCKER_DECISIONS.md` |

**No downloads. No ACCEPTED/REJECTED. No approval markers. No production rebuild. No P5. No git staging/commits.**

---

## 4. Stop for owner review

Outstanding owner actions (order suggested):

1. Read CA provider comparison; decide whether to authorize acquisition (still **not** authorized).
2. Decide membership groups (24 sufficient first).
3. Decide OD-ID-1 / OD-ID-2 (join session or keep unjoined).
4. After CA evidence exists: dual-hash completeness markers only for exact windows.

Until then: **`P0_CERTIFICATION_BLOCKED`**.
