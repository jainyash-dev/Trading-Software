# P0 Batch 5 - Exception resolution register

**Date:** 2026-11-15  
**Method:** Re-read `P0_REMAINING_BLOCKERS.md`, identity notices on disk, CA conversion report, certification summary. Fail-closed where unresolved. No TradingView parity claim from substitutes. No inferred ISIN effective dates. No BE/BZ forced into EQ.

| ID | Original problem verified? | Required evidence | Current evidence resolves? | Exact next action | Fail-closed state |
|---|---|---|---|---|---|
| OD-ID-1 | Yes. BAJFINANCE ISIN change INE296A01016 to INE296A01024; MSEI/LIST/4496/2016 on disk states two dates (8 and 9 Sep 2016) | One official notice with a single effective session | No | Owner chooses one session or keep unjoined; do not agent-join | Unjoined; identity UNKNOWN_INSTRUMENT on affected dates |
| OD-ID-2 | Yes. GRASIM INE047A01013 to INE047A01021; MSEI/LIST/4581/2016 states 6 and 7 Oct 2016 | One official notice with a single effective session | No | Same as OD-ID-1 | Unjoined |
| OD-PX-2 | Yes. Unparsed subjects include CGPOWER 2016-03-15 Scheme Of Arrangement; VBL 2024-09-12 Face Value Split 5 to 2 (conversion_report.json) | Official terms the parser can represent | No | Acquire parseable terms (see CA acquisition proposal); do not invent factor | UNPARSED_PRICE_EVENT / price gate fail |
| OD-PX-3 | Yes. ADANIENSOL 2024-11-21 investigated as market move to 20% band; not CA; PREVCLOSE intact | Optional owner rule for reviewed market moves | Investigation present; no exception mechanism | Optional owner decision; otherwise remain excluded | Excluded by price screen (and other gates) |
| OD-PX-4 | Yes. 700 member-dates after Muhurat/shortened sessions fail PREVCLOSE path while chain intact through held EQ | Owner rule allowing that pattern | Measured, not adopted | Optional owner adopt/decline | Those 700 remain price-gate failures |
| OD-MEM-2 | Yes. Dummy seats lack instrument records; ISIN leakage risk from upstream rows | Owner rule for non-tradable seats if wanted | No inventable ISIN | Leave non-tradable; exclude | 123 member-dates excluded |
| OD-MEM-3 | Yes. Related dummy handling / full-index accounting | Same | No | Same | Same |
| TV-1 | Yes. Worksheet rows still pending external chart exports | TradingView (or approved) chart exports for named cases | No | Owner supplies exports; no Yahoo substitute | PENDING_EXTERNAL_EVIDENCE |
| B11-P | Yes. No constituent baseline with symbols/ISINs before 2020-12-31; IndexInclExcl.xls name-only | Official dated constituent list | No | D59 keeps research window; earlier dates warm only | Pre-window membership not certified |

### Related contained items (not reopened)

| ID | State |
|---|---|
| OD-PX-1 | Contained: BE/BZ-only stretches; EQ-only research stands |
| OD-CA-1 / D66 | Standard approved; no windows approved; acquisition proposal separate |
| OD-CAL-1 | Disclosed inference on 2024-01-20 hours; not a certification blocker by itself |

**Batch 5 status:** Register complete. No unsupported exception closed by inference.
