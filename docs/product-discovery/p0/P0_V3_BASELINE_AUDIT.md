# P0 V3 baseline audit (Phase 0)

**Date:** 2026-11-15, taken before any V3 change. The live repository is the source of truth.

| Item | Live value | Previously reported | Difference |
|---|---|---|---|
| Repository root / branch | `/Users/yash/day-trader-skill`, `main` | same | - |
| HEAD | `69858d07ccb016b74bc1d518b66b9948656ad6cf` | `69858d0` | none |
| Staged | 0 | 0 | none |
| Working tree | 235 paths: 85 modified, 150 untracked | 229 | +6; not traced path by path. 0 deleted paths (`git status` shows only M and ??). The earlier count was taken before the last programme files were written |
| Builder | `BUILD_VERSION = "1.6.0"` | 1.6.0 | none |
| D66 / ED-56 | D66 `USER_APPROVED`; ED-56 in `ENGINEERING_DECISIONS.md` and code (`corporate_actions.py`) | same | none |
| ED-57..61 | present (ED-57 `PROPOSED` held at baseline) | same | none |
| Completeness markers / `completeness.csv` | 0 / absent | same | none |
| Membership ledger | 140 ACCEPTED / 131 blank; SHA-256 `9b0fcba0...` | same | none |
| Membership member-dates (isolated build C, 1.6.0) | VERIFIED 79,151 / UNVERIFIED 44,627 | same | none |
| Identity member-dates | RESOLVED 121,323 / UNKNOWN_INSTRUMENT 2,455 | same | none |
| EQ | ACCEPTED 123,395; NON_EQ_ONLY 260; NO_EQ_ROW 123 | same | none |
| Corporate action | 0 proved windows; UNPARSED_EVENT 7,529 | same | none |
| Certified member-dates | 0 / 123,778 | same | none |

## Protected and production hashes (before)

| File | SHA-256 (first 16) |
|---|---|
| Rulebook PDF (root) | `e41cd0e7893513a4` |
| Rulebook Markdown (`nse/sources/`) | `039883be6b97ca39` |
| Pine Script (`nse/sources/`) | `14293fa5d3c8e5ba` |
| `P0_CERTIFICATION_SUMMARY.json` (production 1.5.0) | `e4304b07c2652e31` |
| `P0_CERTIFIED_RESEARCH_UNIVERSE.csv` | `8976276f648434a3` |
| `P0_EXCLUSION_SUMMARY.csv` | `af647ebbab614726` |
| `P0_RESEARCH_ELIGIBILITY_MATRIX.csv` | `c73abaa67c70d082` |
| `nifty100_review.csv` | `9b0fcba06cc57761` |
| `instrument_records.csv` | `f7ce39b0241366a6` |
| `nifty100_universe.csv` | `15775fa1262b706e` |
| `actions.csv` | `749757252b68f411` |
| `DECISION_LOG.md` | `ab748e1c2a406bf4` |

## Outstanding owner decisions at baseline

Answered in the V3 instructions (recorded as D67): Q1 pilot (done), Q2 BSE enquiry only, Q3 91 rows ACCEPTED, Q4 defer, Q5/Q6 keep unjoined, Q11 retrieval, ED-57 authorised. Pending: Q7, Q8, Q9, Q10, Q12, Q13.

## Claims checked against the live repository

All counts in the V3 instruction's section 1 matched the live state. The earlier reported "229 paths" is now 235; the difference is earlier untracked programme files, not lost work.
