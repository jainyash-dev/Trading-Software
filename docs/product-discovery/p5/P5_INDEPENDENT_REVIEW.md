# P5 Independent Review

**Date:** 2026-11-16  
**Reviewer role:** independent-reviewer (did not author the batch)  
**Closure review agent id:** 875edce0-a70b-4385-9951-2a6850514ad1  
**Earlier review agent id:** 2a0fa66a-b184-4bf6-b94d-460136cebb5d

## Verdict

**PASS** after closure remediations (STALE aggregate honesty, dedicated Portfolio UI tests, repository hygiene, documented EOD policy).

Prior mid-batch verdict was PASS_WITH_LIMITATIONS; Important findings from that pass were remediated and re-tested.

### Critical defects

None.

### Important findings and disposition

| # | Finding | Disposition |
|---|---|---|
| 1 | DQ ERROR on a later bar blocked an earlier accepted close | Fixed earlier; prior close remains STALE. Test: `test_later_error_does_not_discard_earlier_accepted_close` |
| 2 | Portfolio UI omitted `research_use` | Fixed earlier |
| 3 | `_price` could raise on NaN | Fixed earlier. Test: `test_price_rejects_nan` |
| 4 | Portfolio aggregate labelled AVAILABLE while position marks were STALE | **Fixed in closure:** aggregate `valuation_state` / `exposure_state` become STALE when any open mark is STALE. Test: `test_portfolio_aggregate_stays_stale_when_marks_are_stale` |
| 5 | Status doc lagged closure remediations | Updated in this closure package |

### Minor findings (accepted residual)

1. Portfolio UI does not render an `authorises_order` Fact (API still forces false; page copy states no order).
2. Empty open book reports valuation UNAVAILABLE with an explicit reason.
3. No maximum-age cutoff for STALE marks (documented; owner decision reserved).

### Confirmations

- Journal sole authority for caps/quantities; platform schema has no second counter
- D42 monthly/open independence preserved; 10th race and 11th dual-refuse PASS
- ED-3 separate; zone refusal does not change D42 counts
- `authorises_order` false on portfolio paths
- Sector/drawdown UNAVAILABLE
- Marks never invent quotes; missing -> UNAVAILABLE; STALE keeps `price_date`
- Dedicated Portfolio UI vitest (10) PASS
- Repository reel includes `GTF_ENGINEERING_FIRST_ROADMAP.md`; em-dash scan PASS

### Status

Independent review: **INDEPENDENTLY_REVIEWED**  
Unresolved critical/important findings: **none**  
P5 owner acceptance: reserved for the owner (`ACCEPTANCE_READY` recommendation only)
