---
name: rulebook-compliance
description: Audit trading logic in nse/ against the Trading Rulebook, the approved decisions and the implementation specification. Use before and after any change to zone detection, scoring, freshness, invalidation, location, trend, HTF conflict, coinciding, trade levels, red flags or candidate statuses, and when asked whether the code follows the rules. Maintains nse/docs/TRACEABILITY.md.
---

# Rulebook compliance

## Authority (D12)

1. Explicit rulebook rules (`nse/sources/Trading Rulebook ...md`, cite as RB line).
2. Approved decisions in `nse/docs/DECISION_LOG.md` (USER_APPROVED only).
3. Pine Script (`PS line`) only where the rulebook is silent and does not conflict.
4. A documented engineering assumption, labelled as such (e.g. P-TREND-1 in
   `nse/docs/RESEARCH_PIPELINE.md`), only where safe.

A reading that the decision log still marks `PROPOSED` is not a rule. D40 is
`USER_APPROVED` in section 1F and is not an example of a proposed decision. The stale
sentence in decision-log section 3 that calls D40 proposed is not the status. R1–R6 are
`USER_APPROVED`. D41 is `USER_APPROVED` as a whole in section 1F for the readings that
section names. A D41 reading that entry still marks `PROPOSED`, and that section 1F does
not name, stays proposed. Do not promote it. An ambiguity is never resolved in code: it
becomes MANUAL REVIEW with the RB/PS references.

## Procedure

1. Read the changed code and the spec section it implements (spec 4-8).
2. Open each cited RB / PS line and confirm the citation is exact (line numbers drift when
   people paraphrase). `sed -n '<n>p' "nse/sources/<file>"` is read-only and allowed.
3. Check the rule has a test that would fail if the rule were broken. Run it:
   `python3 -m nse.validation.run_all --group strategy_gates --group zone_engine --group mtf_freshness`
4. Update `nse/docs/TRACEABILITY.md`: Rule, Source, Implementation, Test, Validation status.
   A rule with no implementation or no test is listed as such, never omitted.
5. Report: compliant items, gaps, conflicts (with both sources quoted), and the decision
   the user must make for each conflict.

## Non-negotiables to verify every time

- Tested (test_count > 0), invalidated or unknown-freshness zones are never candidates (D3).
- Candidates come only from the MTF overlay methods (audit M4).
- MIT: Weekly trend gate, Monthly context only (D21). WIT: Daily trend gate only (D22).
- WIT output stays BLOCKED until the 75/125-minute design is approved (audit M4b).
- Sector is never a silent pass (D6). R:R threshold is RB 82 (2:1), nothing else.
- No status approves a trade; ACTIONABLE always carries the manual checklist (spec 8).
