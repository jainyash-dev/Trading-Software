# P0 optional owner decisions (Batch 8)

**Date:** 2026-11-15
**Sources:** `P0_REMAINING_BLOCKERS.md`, `P0_EXCEPTION_RESOLUTION_REGISTER.md`, production summary `P0_CERTIFICATION_SUMMARY.json` (builder 1.5.0). Counts re-read from the summary on 2026-11-15.
**None of these unblocks certification by itself.** Every member-date still fails the corporate-action gate (D66) until completeness windows are approved. Declining any item leaves its records excluded (fail-closed).

| ID | Question for the owner | Evidence held | Count (verified) | Default if no decision | Changes a Rulebook rule? |
|---|---|---|---|---|---|
| OD-PX-4 | Adopt a rule that a session after a held Muhurat or shortened session passes the price-continuity gate when the PREVCLOSE chain is intact through the held session's EQ row? | Milestone 1 measurement | 700 member-dates (`PREVCLOSE_BREAK_ACROSS_EXCLUDED_SESSION` = 700); 7 dates | Remain price-gate failures | No (data-gate rule, D63 scope). Owner-reserved because it widens a pass condition |
| OD-PX-3 | Create a reviewed market-move exception mechanism (for example ADANIENSOL 2024-11-21, a fall to the 20% band, 0.8000 x prior close, PREVCLOSE intact)? | Investigation 2026-11-13 in `P0_REMAINING_BLOCKERS.md` | 1 member-date: the only `UNEXPLAINED_PRICE_SCALE_GAP` is ADANIENSOL 2024-11-21 (confirmed in Batch 12 from a fresh isolated 1.6.0 build matrix; see `P0_BATCH12_EXCEPTION_ANALYSIS.md`) | Excluded | No; but it introduces a human-review pass path, so owner-reserved |
| OD-PX-2 | (Evidence, not a rule) Supply or authorize official terms for CGPOWER 2016-03-15 scheme and VBL 2024-09-12 5-to-2 split | Saved API subjects only. VBL terms are in the subject text; the parser cannot represent factor 2.5 (verified Batch 7) | Those steps | Fail-closed | No. VBL is partly an engineering limitation (fractional ratio); a parser change would be ED-level, not a rule change, but the event must still be D66-reconciled |
| OD-MEM-2 / OD-MEM-3 | Accounting rule for the five non-tradable dummy seats (DUMMYREL, DUMMYITC, DUMMYSIEMS, DUMMYTATAM, DUMMYHDLVR) in full-index counts? | Index releases; no instrument records | 123 member-dates (`NO_EQ_ROW` = 123) across all five; DUMMYREL alone 21 | Excluded, non-tradable, no ISIN invented | No |
| TV-1 | Supply TradingView exports (INFY D/W/M/Q/HY/Y, SMA-50, zones, freshness, TATASTEEL adjustment on/off) or leave pending | 34 blank worksheet rows | n/a | `PENDING_EXTERNAL_EVIDENCE`; no Yahoo or other substitute | No |
| B11-P | Provide an official dated constituent list with symbols or ISINs before 2020-12-31, or confirm the D59 window stays | `IndexInclExcl.xls` is name-only | Dates before 2020-12-31 | D59 window kept | No |
| R-5 | Confirm precedence order (D12 Rulebook-first vs council skill wording) | `ENGINEERING_DECISIONS.md` risk R-5 | n/a | CLAUDE.md follows D12 | Governance wording only |

No other unresolved Rulebook decision affects P0 data certification, based on `P0_REMAINING_BLOCKERS.md` and the decision log through D66.
