# P0 Historical Data Certification - Final report

**Date:** 2026-11-15  
**HEAD:** `69858d07ccb016b74bc1d518b66b9948656ad6cf`  
**Role:** Autonomous P0 technical lead  
**Final status:** `P0_CERTIFICATION_BLOCKED`

This status reflects **historical evidence and owner approvals**, not software progress alone.

---

## 1. Executive verdict

D66/ED-56 dual-source corporate-action completeness is implemented and tested (builder **1.6.0**). An isolated rebuild produced **0** certified member-dates out of **123,778**. No completeness windows exist, no dual-hash owner markers exist, and acquisition of non-API official sources was **not** authorized.

Therefore P0 historical certification is **blocked**. Software validation of the certification gates is complete. No P5 work was started. Nothing was staged, committed, or pushed.

Independent review (independent-reviewer agent 9524e165-d46d-4379-aec7-253cf51e8e7a): **PASS** on isolated 1.6.0 fail-closed build. Contrarian review (contrarian-reviewer agent c914a68e-0228-41c6-aab3-dbdef7e11b68) agrees: force `BLOCKED` for any historical-certification claim; do not use `COMPLETE_WITH_EXPLICIT_LIMITATIONS` or `PARTIALLY_COMPLETE` for the certified dataset. Gate implementation is not proof. Exploratory CA tiers and isolated outputs must not be read as certification.

**Anti-misread rules (binding for citations of this programme):**

1. Isolated path `nse/output/p0_isolated_2026-11-15/` is not production certification; docs summary remains builder 1.5.0 with 0 certified.
2. `CA_RESPONSE_PRESENT_NOT_COMPLETE` / exploratory-only labels (~73k rows) are not certified and do not enter the certified universe (D62).
3. Membership 85/185 verified periods are not a partially certified universe; those rows still fail the CA gate.

---

## 2. Distinguish four layers

| Layer | State |
|---|---|
| Software validation | PASS for D66/ED-56 unit/e2e/adversarial suites; architecture PASS; docs_health PASS after link fix; targeted `run_all --no-data` groups PASS (69) |
| Real historical data coverage | EOD archives 2016-2025 held; calendar confirmed; membership 85/185 periods verified; CA API custody for 145 symbols (not D66-complete) |
| Owner-approved evidence | D62/D63/D65/D66 standards approved; **0** per-window CA approvals; **131** membership ledger cells still blank |
| Certified / excluded member-dates | Certified **0**; excluded **123,778** (isolated 1.6.0) |

---

## 3. What was delivered

| # | Deliverable | Path |
|---|---|---|
| 1 | Data inventory | `docs/product-discovery/p0/P0_DATA_INVENTORY_REPORT.md` |
| 2 | Pipeline validation | `docs/product-discovery/p0/P0_PIPELINE_VALIDATION_REPORT.md` |
| 3 | Coverage matrix | `docs/product-discovery/p0/P0_HISTORICAL_COVERAGE_MATRIX.csv` |
| 4 | Missing evidence | `docs/product-discovery/p0/P0_MISSING_EVIDENCE_REGISTER.md` |
| 5 | CA reconciliation register | `docs/product-discovery/p0/P0_CA_RECONCILIATION_REGISTER.csv` (0 proved) |
| 6 | CA acquisition proposal | `docs/product-discovery/p0/P0_CA_SOURCE_ACQUISITION_PROPOSAL.md` (**stop at auth**) |
| 7 | Membership decision pack | `docs/product-discovery/p0/P0_MEMBERSHIP_OWNER_DECISION_PACK.md` |
| 8 | Exception register | `docs/product-discovery/p0/P0_EXCEPTION_RESOLUTION_REGISTER.md` |
| 9 | Isolated certification outputs | `nse/output/p0_isolated_2026-11-15/` |
| 10 | Source-to-output audit | `docs/product-discovery/p0/P0_SOURCE_TO_OUTPUT_AUDIT.md` |
| 11 | This final report | `docs/product-discovery/p0/P0_CERTIFICATION_FINAL_REPORT.md` |
| + | Owner approval queues | `docs/product-discovery/p0/P0_OWNER_APPROVAL_QUEUES.md` |

Production certification files under `docs/product-discovery/p0/P0_CERTIFICATION_SUMMARY.json` remain builder **1.5.0** and were **not** overwritten.

---

## 4. Isolated build 1.6.0 (safe)

Command:

```
python3 -m nse.research.p0_certification \
  --out-dir nse/output/p0_isolated_2026-11-15 \
  --matrix nse/output/p0_isolated_2026-11-15/eligibility_matrix.csv
```

| Metric | Value |
|---|---|
| Member-dates | 123,778 |
| Certified | **0** |
| EXCLUDED_CORPORATE_ACTION | 79,151 |
| EXCLUDED_MEMBERSHIP | 44,627 |
| Membership periods verified | 85 |
| Proved CA windows | 0 |
| `authorises_order` | false |

---

## 5. Owner pauses (do not infer approval)

1. **Authorize CA acquisition scope** (providers, symbols, windows) - see acquisition proposal.
2. **Approve completeness windows** only after dual sources + reconciliation hashes exist (D66 marker form).
3. **Membership ACCEPTED/REJECTED** on backlog groups - see decision pack (24 sufficient / 14 insufficient / 25 N/A).
4. **OD-ID-1 / OD-ID-2** single effective session or keep unjoined.
5. Optional: OD-PX-4, OD-PX-3 exception mechanism, OD-MEM-2/3, TV-1 exports.

---

## 6. Remaining external blockers

| Blocker | Blocks certification? |
|---|---|
| Dual-source CA evidence + owner dual-hash approvals | **Yes - every member-date** |
| Membership blank ledger rows | Yes - 44,627 member-dates today |
| OD-ID-1 / OD-ID-2 | Yes - BAJFINANCE/GRASIM identity |
| OD-PX-2 unparsed events | Affected symbols/dates |
| TV-1 | External parity only |
| Full local-data `run_all` | Validation completeness (not a certification substitute) |

---

## 7. Test evidence (Batch 1 / 9 partial)

| Suite | Result |
|---|---|
| P0 certification + e2e | 65 passed |
| CompletenessRegister | 15 passed |
| Related membership/CA/identity/R12 | 117 passed |
| Adversarial | 28 passed |
| Calendar | 41 passed |
| architecture + repo + hooks + validation_framework via `run_all --no-data --group ...` | 69 passed |
| docs_health / architecture modules | PASS |
| Full local-data `run_all` | **Not completed** this programme |
| `test_research_data` / full EOD soak | **Not completed** (hang risk); deferred |

---

## 8. Why not COMPLETE_WITH_EXPLICIT_LIMITATIONS?

That status requires a certified historical sample with exclusions documented. The largest defensible certified sample today is **empty**. Excluding everything while gates work is correct engineering; it is not a completed certification of a research universe.

**Partial** would describe engineering readiness. The required single status for the certification programme outcome is:

# `P0_CERTIFICATION_BLOCKED`

Unblock path: owner-authorized dual official CA sources -> reconcile -> dual-hash approvals -> membership decisions -> isolated rebuild -> re-audit -> then reassess status.

---

## 9. Repository safety

- Working tree preserved (~197 prior dirty paths + this programme's docs/output).
- No staging, commit, push, reset, clean, or destructive checkout.
- No Rulebook/Pine/`nse/sources/` edits.
- No broker integration. No P5.
