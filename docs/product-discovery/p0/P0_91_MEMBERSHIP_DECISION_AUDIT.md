# P0 audit: 91 membership decisions (D67 / Q3)

**Date:** 2026-11-15
**Authority:** owner Q3 "ACCEPTED for the exact 91 evidence-sufficient rows", recorded as D67 (`nse/docs/DECISION_LOG.md`).
**Row-level before/after:** `P0_91_MEMBERSHIP_DECISION_AUDIT.csv` (91 rows: ledger line, row key, row hash, before and after decision/reviewer/date, evidence file and SHA-256, disclosure).

## 1. Pre-write checks (all passed before any write)

Record note: this file was written after the write. It transcribes the machine output of the checker script (`apply_91.py`, run in dry-run mode first and then with `--write`; the script refuses to write unless every check passes and exactly 91 lines change). The checker's JSON output with every before/after line is the source of the CSV.

| # | Check (owner section 2.3) | Result |
|---|---|---|
| 1 | Ledger read; header exact | PASS |
| 2 | Each of the 91 keys exists exactly once | PASS |
| 3 | Row hash current (recomputed with `membership.review_template`) and equal to the proposal file | PASS |
| 4 | Full source SHA-256 recomputed and unchanged | PASS (91/91) |
| 5 | Evidence files present | PASS |
| 6 | decision, reviewer and reviewed_on blank on all 91 | PASS |
| 7 | Backlog classification/status unchanged; proposal verification VERIFIED | PASS |
| 8 | Proposal holds exactly 91 rows = the 91 `EVIDENCE_SUFFICIENT` backlog keys; none of the 7 optional, 8 deferred or 25 N/A keys | PASS |
| 9 | No duplicate or conflicting entries; every proposed decision ACCEPTED | PASS |

File name: the instruction named `P0_MEMBERSHIP_DECISION_FILE_PROPOSED.csv`. The only proposal file is `P0_MEMBERSHIP_OWNER_DECISION_FILE_PROPOSED.csv` (SHA-256 `0be80251920c3dbe...`); its content passed every check above.

Check defect found and corrected before writing: the first dry run's "no optional symbol" check tested by **symbol** and failed. JIOFIN and ENRIN legitimately appear in the 91 under different rows (`change:E10:REMOVE:JIOFIN`, `change:E12:ADD:JIOFIN`, `change:E20:ADD:ENRIN`). The check was corrected to compare exact **row keys** of the 40 excluded rows. No write happened before all checks passed.

## 2. The write

| Item | Value |
|---|---|
| Ledger `nse/data/universe/nifty100_review.csv` SHA-256 | before `9b0fcba06cc57761a4adbf0a938e004fb6adf808ba7724842248977391ec1f39`, after `5c808f47fb269824040b36693f2cd0689536e89b10fd1b8cd93f57e4d8f13067` |
| Physical lines changed | 91 of 272 (271 rows + header); all other lines byte-identical |
| Fields changed on each of the 91 | `decision` ACCEPTED, `reviewer` Yash Jain, `reviewed_on` 2026-11-15, `notes` (D67 citation) |
| Unchanged on all 271 rows | `row_key`, `row_sha256`, `count_approval`, `mapping_approval` |
| Ledger totals | 231 ACCEPTED, 40 blank |
| Identity records | `instrument_records.csv` unchanged (`f7ce39b0...`) |

## 3. Recomputation after the write

| Item | Before | After |
|---|---|---|
| `nifty100_universe.csv` (regenerated with `membership.convert`; same 185 period keys; only `source_sha256` and `notes` changed on 88 periods) | `15775fa1...`, 85 periods hashed | `9520b75a...`, 173 hashed, 12 not |
| `nifty100_conversion_report.json` (regenerated; only `review` counts and `unverified_periods` changed) | accepted 140, unverified periods 100 | accepted 231, unverified 12 |
| `P0_MEMBERSHIP_ROW_RECOMMENDATIONS.csv`: `canonical_decision`/`owner_decision` mirror the ledger | 91 blank | 91 ACCEPTED |
| Member-dates, membership gate (isolated build, builder 1.6.0) | VERIFIED 79,151 / UNVERIFIED 44,627 | VERIFIED 121,156 / UNVERIFIED 2,622 |
| Certified member-dates | 0 | **0** (all 121,156 are excluded on D66 corporate-action completeness) |

The 12 periods still unverified: BAJFINANCE x2 and GRASIM (OD-ID-1/2, kept unjoined), five dummy seats (OD-MEM-2/3), and JIOFIN, ITCHOTELS, ENRIN, TMCV (the deferred optional rows).

Tests pinned to the live ledger (`RecordedOwnerApprovals`, `tests/test_research_membership.py`) were updated to the D67 state. The updated tests assert the exact 91 keys (read from the proposal file), the reviewer, the date and the D67 note, that the 7 deferred rows stay blank, the exact 12 unverified periods, and 231/40. Before the update three assertions failed against the new ledger, as expected.

## 4. Independent audit (separate agent, read-only)

Verdict for the write: **PASS_WITH_FINDINGS**. It confirmed: exactly the 91 rows changed; only the four fields; row hashes and approvals unchanged on all 271 rows; no excluded row touched; identity records unchanged; 10 release groups (77 rows) checked against the PDF texts, all 5 renames against `symbolchange.csv`, all 9 ISIN changes against the API bodies; and `completeness_decisions()` still empty.

Findings and actions:

| Finding | Action |
|---|---|
| MAJOR: row `change:I-2024-09-12-VBL:ISIN_CHANGE:VBL:INE200M01039` has a contrary advisory verdict (`INSUFFICIENT_EVIDENCE`: the API record's `isin` field is the older INE200M01013), and the proposal did not disclose it | Disclosed in D67 and in the audit CSV. Note: ED-37 deliberately ignores that field, and the INE200M01013 -> INE200M01021 step is an accepted row. **Owner may revisit this one row** (queue V4) |
| MAJOR: D67 cited this audit file before it existed | This file now exists |
| MINOR: `nse/data/universe/README.md` stale | Updated |
| NOTE: "deferred" wording for Q4 | The owner's wording was "Decision: DEFER", consistent with the ledger |
