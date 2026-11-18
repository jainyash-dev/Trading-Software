# P0 Batch 8 - Source-to-output audit

**Date:** 2026-11-15  
**Subject build:** isolated builder **1.6.0** at `nse/output/p0_isolated_2026-11-15/`  
**Production docs outputs:** left at builder **1.5.0** (SHA-256 of summary unchanged `e4304b07...913d` family; verified untouched)  
**Audit seed:** `random.Random(20261115)`  
**Verdict:** **PASS** (no unsupported certified rows)

Independent reviewer: independent-reviewer agent 9524e165-d46d-4379-aec7-253cf51e8e7a - verdict PASS (0 certified; production 1.5.0 untouched; no fail-open path). Contrarian: contrarian-reviewer agent c914a68e-0228-41c6-aab3-dbdef7e11b68 - reject any historical-certification claim; force BLOCKED (aligned).

Follow-up from independent review finding 9: summary `completeness_register.note` singular wording corrected in code to dual-source language (behavior unchanged).

---

## 1. Outputs inspected

| File | Observation |
|---|---|
| `P0_CERTIFIED_RESEARCH_UNIVERSE.csv` | Header only; **0** data rows |
| `P0_RESEARCH_EXCLUSION_REGISTER.csv` | 1,671 register intervals |
| `P0_MEMBERSHIP_REFERENCE_HISTORY.csv` | 185 periods |
| `P0_CERTIFICATION_SUMMARY.json` | `build_version` 1.6.0; `certified_symbol_dates` 0; `proved_windows` 0; D66 note present |
| `eligibility_matrix.csv` | 123,778 rows |

Summary reconciliation flags all `true` (certified+excluded=rows; one row per symbol-date; no order authorised; register coverage).

---

## 2. Certification claim checks

| Check | Result |
|---|---|
| Every certified member-date has membership evidence | N/A vacuously (0 certified) |
| Any matrix row with CERT*/ELIGIBLE | **None** (full matrix: 79,151 EXCLUDED_CORPORATE_ACTION + 44,627 EXCLUDED_MEMBERSHIP) |
| Any `CA_COMPLETENESS_VERIFIED` tier in sample+specials | **None** |
| `completeness.csv` present | **No** |
| Owner dual-hash markers | **0** |
| `authorises_order` | false |
| `rows_passing_every_data_gate` | 0 |

---

## 3. Sample and exceptional traces

- 60 random matrix rows + up to 5 rows per exceptional symbol: no false certification.
- 10/10 membership exclusions: `membership_gate=UNVERIFIED`.
- 10/10 CA exclusions: `membership_gate=VERIFIED` and corporate-action gate not completeness-verified.

| Symbol | Member-dates | Notable gates |
|---|---|---|
| BAJFINANCE | 1234 | identity UNKNOWN_INSTRUMENT 1098 / RESOLVED 136; all EXCLUDED_MEMBERSHIP |
| GRASIM | 1234 | identity UNKNOWN_INSTRUMENT 1234; CA UNPARSED_EVENT |
| VBL | 678 | CA UNPARSED_EVENT; EXCLUDED_MEMBERSHIP |
| JIOFIN | 447 | 10 NON_EQ_ONLY:BE |
| ITCHOTELS / ENRIN / TMCV | 9 / 68 / 3 | BE-only stretches |
| Dummy seats | 123 combined | NO_EQ_ROW + MISSING_COVERAGE; EXCLUDED_MEMBERSHIP |
| CGPOWER | 187 | UNPARSED_EVENT |
| ADANIENSOL | 580 | EXCLUDED_MEMBERSHIP |

---

## 4. Fail conditions

No unsupported certified record was found. Audit **PASS**.

If a future rebuild certifies a row without dual-source evidence and dual-hash approval, this audit must be failed and the build discarded.
