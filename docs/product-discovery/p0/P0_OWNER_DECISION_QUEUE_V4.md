# P0 owner decision queue V4

## Update after D68 (2026-11-15)

Answered: #1 (BSE written enquiry; CDSL split test), #2 Q7 DECLINED, #3 Q10 Option A, #4 ED-57 expectations approved, #5 VBL row kept, #6 Q8 keep unparsed, #7 Q9 keep excluded, #8 CGPOWER deferred.

| Still pending | Item |
|---|---|
| A | **Send the BSE enquiry**: `P0_BSE_ENQUIRY_DRAFT.md` (not sent; no authorised mail channel). Then decide on the reply |
| B | **D66 path after the CDSL result**: CDSL matched 15 of 15 known splits but cannot prove window absence of other events (`P0_CDSL_SPLIT_COVERAGE_TEST.md`). D66 stays blocked for all 123,778 member-dates unless a source that proves window coverage is found or the owner changes D66 (owner only) |
| C | Q12 TradingView exports; Q13 R-5 wording |
| D | CGPOWER representation rule (deferred) |

The original V4 table follows unchanged.

**Date:** 2026-11-15. Only decisions still genuinely pending. Already decided and executed (D67): Q1, Q2 (enquiry only), Q3, Q4, Q5, Q6, Q11, ED-57. Silence is not approval. Ordered by member-dates blocked.

| # | Decision | Why it matters | Evidence available | Evidence missing | Options | Engineering recommendation | Member-dates | Blocks certification? |
|---|---|---|---|---|---|---|---|---|
| 1 | **D66 source path** | No qualified independent pair exists for any class or window | `P0_D66_SOURCE_DISCOVERY_REPORT.md`; BSE tariff sheet; CDSL index analysis | Any source proving window coverage; independence of upstream | (a) authorise purchase of a BSE corporate-action product, or a direct written enquiry (needs a contact channel) to obtain coverage and provenance terms first; (b) authorise a free CDSL coverage test on the 15 known in-window splits (about 15-30 specific notices); (c) stay blocked | (a)-enquiry first, plus (b) in parallel; neither changes D66 | **123,778** | Yes, all |
| 2 | Q7 OD-PX-4 shortened-session rule | 700 member-dates fail price continuity after 5 Muhurat and 2 DR sessions | `P0_PRICE_INTEGRITY_REPORT_V3.md` section 4 | - | adopt / decline | Decline until a reason to trust one-hour prints as anchors is documented | 700 | Yes (and D66) |
| 3 | Q10 OD-MEM-2/3 dummy seats | 123 member-dates; index counts include seats that are not securities | `P0_IDENTITY_FINAL_REVIEW.md`; EQ matrix | - | (a) keep excluded and report index counts minus seats; (b) count seats for index arithmetic only, never as securities | (a) | 123 | Yes for those dates |
| 4 | ED-57 changed test expectations 2 and 3 | "Rs 10 -> Rs 3" synthetic subjects now parse exactly (`SPLIT 3:10`) instead of staying unparsed | ED-57; independent re-review: justified exact reading, not a weakening | Owner sign-off (D67 authorised review of "the" changed expectation) | approve / revert to integer-only for non-VBL subjects | Approve | 0 (synthetic tests; no held subject affected) | No |
| 5 | D67 row `change:I-2024-09-12-VBL:ISIN_CHANGE:VBL:INE200M01039` | A contrary advisory verdict was not disclosed in the proposal | D67 disclosure; ED-37 ignores the API ISIN field; bhavcopy chain continuous | - | keep ACCEPTED / revert to blank | Keep | VBL 2024-09-12 onward | No (D66 blocks anyway) |
| 6 | Q8 BRITANNIA / TVSMOTOR distributions | Two in-window events unclassified | Price report section 5 | Value of distributed instruments | keep unparsed / non-price-scale rule | Keep unparsed until a rule is wanted | 2 steps (all those symbol windows stay unverified) | Yes for those symbols |
| 7 | Q9 ADANIENSOL band move | 1 member-date | Price report section 3 | NSE price-band file (not authorised) | keep excluded / exception mechanism | Keep excluded | 1 | Yes for that date |
| 8 | CGPOWER demerger representation | Pre-window event stays UNPARSED | IM: entitlement 1:1; NSE: no factor | - | keep / record as DEMERGER (no ratio) | Record as DEMERGER only with an owner rule; pre-window, low priority | 0 in window | No |
| 9 | Q12 TradingView exports | External parity | 34/34 worksheet rows blank | Exports | supply / leave pending | - | 0 | No (not a P0 data gate) |
| 10 | Q13 R-5 precedence wording | Governance | ENGINEERING_DECISIONS R-5 | - | confirm order | - | 0 | No |
