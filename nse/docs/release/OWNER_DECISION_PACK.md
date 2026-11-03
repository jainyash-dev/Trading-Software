# Day Trader Skill: Owner Decision Pack

**Prepared:** 2026-11-03, Asia/Kolkata. **Status:** recommendations for review; no approvals inferred.

This pack reviews the current working tree, including existing uncommitted work, against both supplied Rulebooks. It separates source requirements, implemented behaviour, proposed interpretations and missing evidence. It does not implement any recommendation. No downloads, backtests, test runs, Rulebook/Pine edits, commits or destructive operations were performed for this report. Test citations below describe assertions inspected in source, not a fresh test result.

The starting registers are [PRODUCT_MASTER_STATUS.md, sections 1, 4 and 5][master], [UNRESOLVED_DECISIONS.md][unresolved], [DECISION_REGISTER.md, sections 1-3][register] and [D40-D41 in DECISION_LOG.md][d40]. Their historical validation claims are not independently recertified here. Already approved R1-R6 remain approved; the remaining D41 items do not acquire approval by being implemented.

## Read this before deciding

Three findings materially change how the existing questions should be presented:

1. **RB-VERSION-1 rests on a faulty PDF extraction.** The allegedly missing passages are visible on PDF page 62. A source-of-record choice remains useful, but the claimed source conflict is not established.
2. **The Rulebook supports an upper risk limit more strongly than the register suggests.** In addition to C1, its risk dashboard explicitly treats risking 2% when the stage permits 1% as a red line. Below-band risk and undeclared stage remain separate questions.
3. **A complete list of simulator inputs is not a complete execution model.** The Rulebook discusses cancelling an untriggered order when pre-trade checks become invalid. The simulator fixes the initial setup and does not fully re-evaluate those checks while waiting for a fill. Owner approval cannot make that missing behaviour exist.

Approval of methodology does not supply B7/B11/B18 records or establish TradingView agreement. Nor does a risk-plan PASS or candidate ACTIONABLE mean an order is approved.

## Source identities and citation convention

**RB** means the protected Markdown Rulebook, with exact line references. **PDF** page numbers are physical pages in the 136-page supplied PDF. Section names disambiguate page references. Links point to this checkout; code line numbers describe the current uncommitted snapshot.

| Source | SHA-256 at review |
|---|---|
| [Supplied PDF][pdf] | `e41cd0e7893513a492a39095c0f771ec67b320f1b51bc356da7c6a2c2946c2fc` |
| [Protected Markdown Rulebook][rb] | `039883be6b97ca39b00e5afe80f219a5d759dae99fa9c4179475f506a275d54b` |
| [Protected Pine Script][pine] | `14293fa5d3c8e5ba9309b45804a840bb5d8c43d47c193ebb6bca0480bc0a5519` |

Hash pins are in [protected.py:10-18][protected]. Hash equality establishes file identity, not source correctness or agreement between different formats.

## 1. RB-VERSION-1: authoritative Rulebook

**1. What is unresolved?** Which document is the source of record, and how should genuine future discrepancies be handled? The register additionally claims the PDF lacks RB 1784, 1786-1803, 1809 and 1813. That factual premise is incorrect: see [the disputed register row, line 55][version-row]. Which export was produced later is still not established.

**2. What does the Rulebook say?** PDF page 62 visibly contains the closed-leg-out requirement, section 3.4 LTF Proximity Rule, its MIT exception, and the opening of chapter 4.1. These correspond to [RB 1772-1813][rb-proximity]: DIT/WIT prefer the last 8-10 candles, older ranges carry increasing risk, and MIT Daily execution is exempt from that recency requirement. These are present in both sources. Direct PDFKit extraction and visual inspection of page 62 recovered content omitted by the earlier stdlib extraction. This check disproves the named omission; it is not a certification that every sentence in both files is identical.

**3. What does the implementation do?** Code uses Markdown RB line references. Both documents are hash-pinned. WIT recency handling is in [qualification._g1:134][g1], but WIT is independently blocked by [qualification._g0:100][g0] and M4b. The comment in `protected.py:15` describing a different revision inherits the unproven extraction conclusion.

**4-5. Interpretations and consequences**

| Choice | Consequence |
|---|---|
| PDF is canonical; Markdown is a searchable citation companion | Matches the supplied primary document; any genuine future discrepancy requires review against the PDF. No rule change follows from the page-62 finding. |
| Markdown is canonical | Convenient exact-line citations, but an explicit owner choice is needed to give it authority over a future conflicting PDF passage. |
| Both are equal authority without a conflict rule | Leaves future contradictions unresolved and invites selective interpretation. |

**6. Recommendation.** Designate the PDF as source of record and Markdown as its citation companion. Retain both immutable originals. Record an actual discrepancy before requesting a rule choice; never infer missing content from one extraction method. Correct the register's specific omission claim in a subsequent authorised documentation change. WIT stays blocked for its independent design/data reasons.

**7. Exact approval requested.** “Use the supplied PDF as canonical and the protected Markdown as a line-indexed companion. Treat the page-62 omission claim as disproven. Escalate any demonstrated substantive discrepancy; do not silently merge or edit either source.” This report does not amend the existing registers.

## 2. P-LOC-2: CMP inside a tested HTF demand zone

**1. What is unresolved?** When price first enters an HTF demand zone and freshness becomes TESTED, can it still receive VLOC treatment, or must the curve immediately move to the next fresh demand? The wording describes a touch *and bounce* without defining when the bounce is complete. R4 concerns invalidation, not this curve-boundary question.

**2. What does the Rulebook say?** [Section 4, chapter 1, sections 1.3-1.5, RB 1578-1644][rb-location]; PDF pages 54-57:

- RB 1587: the demand curve boundary must be fresh, PL untouched; tested zones create false boundaries.
- RB 1597: VLOC means price is inside the HTF demand zone, between PL and DL.
- RB 1621: after the boundary is tested by a touch and bounce, redraw using the next fresh demand below.
- RB 1639: HTF *location* quality can be slightly tested, approximately 25%. This does not explicitly waive the fresh-*curve-boundary* requirement. D15's tested but DL-untouched confluence context is another distinct role.

**3. What does the implementation do?** [structure.build_curve:129-183][curve] records `PRICE_INSIDE_TESTED_HTF_DEMAND`. It may find a lower fresh demand, but the issue remains; `positions:185` returns no position while issues exist. [qualification._g3:171-211][g3] therefore returns MANUAL with location undetermined. [G3 tests:196-226][g3-tests] distinguish unknown boundaries, skipping a tested zone outside CMP, and CMP inside tested demand.

**4-5. Interpretations and consequences**

| Choice | Consequence |
|---|---|
| Retain VLOC for the first visit until a defined bounce/exit | Preserves the intuitive inside-demand reading, but creates a freshness exception. “First visit”, permitted depth and bounce completion require definitions; no automatic threshold can be inferred. |
| Redraw as soon as authoritative freshness is TESTED | Follows the explicit fresh-boundary rule. CMP may move from VLOC to LOC/EQB/HOC, or the curve may become unavailable. It can change G3/G4 outcomes. |
| Continue MANUAL until the conflict is resolved | Avoids choosing between the passages but prevents deterministic classification for these cases. |

**6. Recommendation.** Adopt immediate redraw when the overlay establishes TESTED. Treat a tested HTF zone as context where already permitted, but not as a fresh curve boundary. Use the next valid fresh lower demand; missing or unknown boundaries remain manual. Do not invent a bounce detector. This is a proposed resolution of the timing ambiguity, not text the Rulebook explicitly supplies. It neither restores execution-zone freshness nor changes approved confluence or invalidation rules.

**7. Exact approval requested.** “Once the HTF demand is known TESTED, exclude it as a curve boundary even while CMP is inside it; redraw from the next fresh demand. Do not retain VLOC solely because CMP remains in that tested zone. Keep missing/unknown boundaries manual and preserve D15/R1-R6.”

## 3. P-RISK-1: stage risk bands and FAIL versus MANUAL

**1. What is unresolved?** Whether exceeding a declared stage's maximum should hard-fail the separate risk plan, and what to do below a stage's printed minimum or when no stage is declared. These are three different cases.

**2. What does the Rulebook say?** [C1, RB 37-75][rb-risk], PDF pages 2-3, requires calculated sizing and forbids exceeding the defined risk percentage. [Section 5, chapter 3, RB 2208-2220][rb-stage], PDF page 76, gives learning 0.5-1%, intermediate 1-1.5%, professional 1.5-2%. Crucially, [section 8, chapter 10, section 10.2, RB 3949][rb-risk-redline], PDF page 134, treats risking 2% when the stage says 1% as a red line requiring recalculation. The register's “no line says above-band = reject” is too narrow an account of the source.

Below-band risk is less settled: [section 7, RB 3298-3304][rb-small-risk], PDF page 113, discusses tiny monetary risk and reducing anxious 1% risk to 0.5%. Conversely, [the 100-trade contract, RB 3444-3472][rb-contract], PDF page 120, specifies exactly 0.5-1% without exceptions. Neither passage supplies a universal automated below-band waiver. The scaling provisions at [RB 3642-3662][rb-scaling] also do not justify automatically promoting a declared stage.

**3. What does the implementation do?** [risk.assess_config:130-172][risk-assess] returns:

| Input | Current risk-plan result |
|---|---|
| Declared stage, RPT above its maximum | FAIL |
| Declared stage, RPT below its minimum | MANUAL |
| Declared stage, within its inclusive band | PASS for this check |
| No stage, RPT greater than 2% | FAIL |
| No stage, RPT at most 2% | MANUAL |

The stage is user-declared, not proven from journal evidence. Monthly risk bands and open exposure are displayed as evidence, not enforced as an aggregate risk gate. The risk plan does not alter candidate gate outcomes; [risk tests, Config:142 and CandidatePlan:205][risk-tests] and [AuditRegressions:321][risk-audit-tests] explicitly cover these distinctions. G8's [RPT check at qualification.py:364][g8-risk] is not a substitute for stage/capital validation.

**4-5. Interpretations and consequences.** Hard-failing above-band risk implements the stated ceiling and prevents a manual acknowledgement from legitimising excessive planned risk. Making every violation MANUAL allows human review but weakens that ceiling. Passing all below-band values treats the bands as maxima only, which is plausible for reduced exposure but not universally supported, especially under the 100-trade contract. Keeping below-band/undeclared cases manual preserves those unresolved distinctions.

**6. Recommendation.** Ratify the current hard upper limits and manual lower/undeclared cases. This best fits C1 and the explicit red-line example. Keep the scope to the risk plan. Aggregate monthly exposure, stage eligibility and any below-band exception need their own defined policy; do not imply they are enforced today.

**7. Exact approval requested.** “FAIL planned RPT above the declared stage maximum, and above 2% with no stage. Keep below-band risk and undeclared stage at or below 2% MANUAL. Do not auto-promote stage or infer a below-band exception. This approves the risk-plan reading only.”

## 4. Monthly trade cap: B12-CAP

**1. What is unresolved?** The ceiling itself is not ambiguous: it is ten. The unresolved choices are when a trade consumes a slot, the month/timezone and account scope, handling pending orders and simultaneous fills, and whether noncompliant exploratory configurations may be accepted by the generic simulator.

**2. What does the Rulebook say?** [Section 5, chapter 6, RB 2388-2415][rb-cap], PDF pages 81-82: maximum ten trades per month, not a target; zero is acceptable; stop for the rest of the month after ten. Select quality setups using the priority framework. It does not explicitly define a pending order as a trade, specify timestamp normalization, or provide a numerical ranking formula for choosing the “best ten”.

**3. What does the implementation do?**

- [ExecutionModel:87-125][bt-model] defaults `monthly_trade_cap` to `None`, accepts any positive integer including 11, and leaves concurrency optional.
- [apply_portfolio_rules:352-384][bt-portfolio] counts filled trades in their recorded fill month. Unfilled orders use no slot. Fills are ordered by fill time, signal time, symbol and zone ID. [Limitations/metadata:400-418][bt-limitations] label absent enforcement or a cap above ten.
- [risk.assess_config:152][risk-assess] fails the next trade once the supplied monthly count is ten. [store.journal_event:629-665][journal] rejects an eleventh TRIGGERED trade across that journal. These are separate mechanisms, not a single shared enforcement service. Journal counting uses timestamp year/month; the backtest uses the recorded month string. Neither establishes the proposed cross-account/IST policy below.
- [Portfolio tests:322][bt-portfolio-tests] cover the eleventh fill, ordering, unfilled orders and month rollover; [CapAuditRegressions:634][bt-cap-tests] cover labels and acceptance of 11. [DECISION_REVIEW.md, A12:128][old-cap-review] saying the backtest has no cap is stale; enforcement now exists when configured.

**4-5. Interpretations and consequences**

| Counting rule | Consequence |
|---|---|
| First fill / trade trigger | Counts actual entries; expired/cancelled unfilled orders consume no trades. Requires a defined order when multiple orders could fill. |
| Placement or reservation | Prevents overbooking pending orders, but may use the allowance on orders never filled. Must define whether cancellation releases a reservation. A reservation need not itself be a completed trade count. |
| Exit/closure | Can permit more than ten new positions in one month; poorly fits the instruction to stop after taking ten trades. |
| No cap or more than ten | A strategy deviation, even if transparently labelled. It is not another interpretation of the ten-trade ceiling. |

**6. Recommendation.** For a Rulebook profile, enforce at most ten first fills in a calendar month in Asia/Kolkata, across all symbols in the same trading book. Closing a trade does not restore its monthly slot. Lower caps are acceptable. Pending-order reservations may be a separate operational control. Use current deterministic fill order only as a disclosed research proxy; it does not implement discretionary quality selection. A different selection policy must use information available before entry, never hindsight winners. Do not approve above-ten configurations as Rulebook-compliant.

**7. Exact approval requested.** “Count one trade on first fill/trigger, reset by IST calendar month, and enforce a maximum of ten across the trading book; exits do not replenish slots. Permit a lower ceiling. For research, accept the current deterministic fill ordering as a disclosed proxy, or specify a prospective selection policy.” IST normalization and consistent enforcement are proposed future work, not existing guarantees. Approval here does not set capital allocation or simultaneous-position limits.

## 5. B9: buffers, tier boundaries and stop structure

**1. What is unresolved?** A deterministic historical trade needs one entry and one stop. The Rulebook prints ranges and qualitative exceptions. It does not uniquely choose the reference price for a tier, resolve shared tier edges, pick a value inside each range, or quantify every volatility/stop-structure exception. [Approved D7, DECISION_LOG.md:115-126][d7] preserves scanner ranges and forbids silently inventing a midpoint/fixed-percent/ATR rule.

**2. What does the Rulebook say?** [Section 5, chapter 1, RB 2006-2032][rb-entry], PDF pages 70-71, and [chapter 2, RB 2088-2155][rb-stop], PDF pages 73-74:

| Printed stock-price tier | Entry buffer, rupees | SL buffer, rupees |
|---|---:|---:|
| Below 100 | 0.25-0.50 | 0.50-1 |
| 100-500 | 0.50-2 | 1-3 |
| 500-2,000 | 2-5 | 3-8 |
| Above 2,000 | 5-10 | 8-15 |

RB 2010's broad entry summary is not a replacement for the detailed tier table. RB 2022 calls the buffers guidelines requiring judgement. RB 2109 allows 50-100% more SL buffer in high volatility, without a machine-readable volatility classifier. RB 2118-2128 distinguish normal, exceptional and HTF “Shri Krishna” stop selection. The source does not reduce these structural choices to “use whichever backtests best”.

**3. What does the implementation do?** [levels.py:23-60][levels] unions all tiers applicable to PL, normal DL and exceptional DL; shared edges are inclusive on both sides. It produces entry and stop ranges. It does not implement an automatic volatility uplift or resolve every discretionary HTF stop choice. [backtest.plan:127-142][bt-plan] selects ENTRY_MIN/ENTRY_MAX and NORMAL/EXCEPTIONAL WIDE/TIGHT endpoints. It does not offer an implicit midpoint. [Levels tests:483][levels-tests] and [risk AuditRegressions:321][risk-audit-tests] exercise boundary ranges and buffer-dependent review.

**4-5. Interpretations and consequences**

| Choice | Consequence |
|---|---|
| Fixed lower, midpoint or upper buffer per tier | Reproducible but an added owner convention. Different fills, sizing and R:R result. Wider stops are not universally “conservative”: they reduce R:R but may avoid exits. |
| Price/volatility-dependent rule | Potentially closer to discretion, but requires approved inputs, thresholds, timing and exception rules. Inventing these would invent strategy. |
| Predeclared endpoint sensitivity cases | Exposes dependence on printed ranges without pretending one number is uniquely mandated. Still needs disclosure of tier union and stop-structure assumptions. |
| Defer a numerical model | Scanner ranges remain useful; a single historical trade path cannot be claimed. |

**6. Recommendation.** Preserve D7. For later exploratory research, prefer predeclared endpoint cases over an invented optimum. The existing two entry endpoints and four stop choices can form a disclosed sensitivity family, not eight equally Rulebook-approved stop decisions. Normal/exceptional/HTF applicability must still follow the source. Keep qualitative volatility/window-gap/HTF cases manual or outside a narrowly labelled experiment until defined. Results must not be used to select a winner on the evaluation period and then call it a prior rule.

**7. Exact approval requested.** Approve or amend these components separately:

- Keep scanner ranges under D7.
- Allow the existing union of PL/normal-DL/exceptional-DL tiers and inclusive shared edges **as a provisional research approximation**; otherwise supply the reference price and exact edge convention.
- Approve a predeclared endpoint sensitivity family, with structural stop choices separately labelled. If a single baseline is wanted, explicitly name `ENTRY_MIN` or `ENTRY_MAX` and the permitted stop policy.
- Leave volatility and other qualitative exceptions unresolved; do not silently treat an unadjusted model as covering them.

This is a concrete partial approval path, not a claim that B9 can be fully closed without those remaining definitions.

## 6. B12: execution, cancellation, expiry, costs and slippage

**1. What is unresolved?** How a later study should turn qualified setups into fills and exits without inventing intrabar paths or transaction costs. Required constructor fields cover some choices; pending setup validity, session completeness, order liquidity and portfolio risk remain material limitations.

**2. What does the Rulebook say?** [RB 2024-2032][rb-entry] specifies limit entries and stop-limit SL orders; [RB 2132-2155][rb-stop] distinguishes locked SL from touch-based execution. [Section 5, chapter 9.1, RB 2530-2538][rb-cancel], PDF page 86, explicitly permits cancelling before trigger if a pre-trade check becomes invalid, including a tested zone, trend shift or new HTF conflict. Chapter 9.2 restricts modifications after trigger. The Rulebook does not specify a numeric order expiry, OHLC same-bar ordering, broker fee schedule or slippage percentage. Its cancellation provision is stronger context than the register's isolated citation to RB 2141, but does not itself supply a complete event-order algorithm.

**3. What does the implementation do?** [ExecutionModel:81-125][bt-model] requires ten fields: entry, stop, target, statuses, expiry, target-first cancellation, gap policy, same-bar policy, cost and slippage. Portfolio limits remain optional. [simulate:145-228][bt-simulate] uses complete supplied candles starting after the signal, buys when low reaches entry, and uses recorded bar-end fill times. `AT_OPEN` or `AT_LEVEL` resolves gaps; `STOP_FIRST`, `TARGET_FIRST` or `EXCLUDE` resolves specified ambiguous bars. A uniform percentage per side represents costs and slippage in [r_multiple:231][bt-cost].

Important limits visible in that code:

- `MANUAL_REVIEW` is an allowed simulator input status; rejected, blocked and insufficient-data statuses are refused. ACTIONABLE itself still carries a human checklist.
- Expiry counts supplied complete candles, not independently verified exchange sessions. Missing/incomplete candles can extend the effective waiting period.
- Fill detection precedes target-first cancellation. A candle touching both entry and target does not establish which happened first; its treatment is model-dependent.
- [Historical order construction:421-460][bt-history] uses the initial allowed signal, one order per zone, with fixed levels. It does not fully rerun pre-trade qualification while the order waits. Target-first cancellation is not a substitute for the Rulebook's invalid-setup cancellation provision.
- OHLC fill proxies do not model stop-limit non-execution, queue position, partial fills, price bands or liquidity. Uniform per-side percentages are not a detailed dated fee/tax calculation.
- The release register separately records incomplete-bar skipping and an end-of-data/open-trade corporate-action exclusion limitation. These remain engineering issues; accepting a policy does not repair them.

[Model and Simulate tests:33-132][bt-tests] cover required inputs, invalid choices, expiry, future-bar use, same-bar policies and arithmetic costs. They establish intended software branches, not real execution accuracy.

**4-5. Choices, consequences and 6. recommendations**

| Component | Alternatives and consequences | Recommended approval scope |
|---|---|---|
| Candidate statuses | ACTIONABLE only; or include MANUAL, which simulates unresolved eligibility | ACTIONABLE only for a Rulebook-oriented study, retaining the manual-checklist limitation. MANUAL cases, if ever studied, must be separate experiments. |
| Gap fill | AT_OPEN captures price gaps as a proxy; AT_LEVEL can assume an unavailable favourable stop price | AT_OPEN for research, explicitly a proxy, not evidence that a stop-limit order executes. |
| Same-bar ambiguity | STOP_FIRST tends to penalise ambiguous trades; TARGET_FIRST favours them; EXCLUDE removes difficult observations and may bias the sample | STOP_FIRST baseline with EXCLUDE robustness reporting and excluded counts; no optimistic TARGET_FIRST baseline. |
| Unfilled expiry | Different positive values change fills and opportunity selection; no source value is prescribed | Owner supplies **N** verified trading sessions. Do not adopt a fixture's value as strategy. Current candle-count limitation must be resolved or bounded before claiming session expiry. |
| Target reached before entry | Cancel avoids stale targets; retaining may admit a later valid revisit | Propose `cancel_if_target_first=true` as an explicit research assumption, not a quoted Rulebook requirement. Same-bar ambiguity remains disclosed. |
| Setup becomes invalid before trigger | Re-evaluate and cancel; or freeze the initial qualification | Approve cancellation when an observed pre-trade check becomes invalid, consistent with chapter 9.1. Observation timing must respect available completed data. Current implementation does not fully do this. |
| Costs and slippage | Zero, uniform rates or a dated instrument/broker-specific model materially change net results | Require documented dated schedules and defensible slippage inputs. No invented rates or silent zero-cost baseline. Official fees alone do not establish slippage. |
| Portfolio | Cap, concurrency and capital allocation affect feasible trades | Cap per section 4. Owner supplies simultaneous-position limit or explicitly labels it unmodelled; current simulation is not proof of capital feasibility. |

**7. Exact approval requested.** Approve the proposed research protocol above, or provide replacements, **and supply**: expiry **N**, dated cost inputs and their scope, slippage assumptions/evidence, and concurrency policy. Select B9 entry/stop assumptions separately. Approve pending-order revalidation as a future requirement; do not approve the current frozen-setup simulator as a full implementation of it. Until the missing values, implementation gaps and data prerequisites are resolved, B12 is only partially decided. This report authorises no run.

## 7. D40: 20 January 2024 session hours

**1. What is unresolved?** Whether to accept 09:15-15:30 for Saturday 20 January 2024 by combining a date-specific “regular market timings” notice with a separate normal-hours circular. D40 remains PROPOSED although the calendar already uses this inference. Some underlying provenance decisions were previously approved; they do not amount to blanket approval of all D40 wording.

**2. What does the Rulebook say?** [Section 4, chapter 6, summary table, RB 1978][rb-timeframes] gives the 375-minute trading day and its division into 75/125-minute candles. It does not certify this specific session or exchange holiday history. Date-specific calendar evidence must come from the exchange, not a trading-methodology inference.

**3. What do the evidence and implementation say?** Local circulars inspected:

- [NSE/MSD/60340, page 1][notice-60340], dated 19 January 2024, withdraws the earlier DR-switch arrangements and announces regular trading on 20 January “as per regular market timings”. It does not print numeric hours.
- [NSE/CMTR/41180, page 1][notice-41180], dated 31 May 2019, prints Normal/Odd Lot market hours 09:15-15:30.
- [NSE/CMTR/65729, page 1][notice-65729], dated 23 December 2024, prints the same hours as standard for 1 February 2025. This corroborates the convention but is not a direct January 2024 timing notice or a systematic intervening-circular review.

[events.csv:61][calendar-row] records the date as CONFIRMED SPECIAL_SESSION with those inferred hours and an explicit D40 note. [nse_calendar.py:238-265][calendar-code] classifies a verified regular-hours special session as NORMAL_SPECIAL, including Saturdays, and uses it as a trading day. [Calendar evidence tests:234-260][calendar-tests] preserve the recorded source/inference. [D40:550-577][d40] explicitly leaves normal-hours review, TradingView checks and event completeness open.

**4-5. Interpretations and consequences**

| Choice | Consequence |
|---|---|
| Accept the combined evidence provisionally | Include 20 January in normal candle construction and expected sessions; retain the provenance caveat. |
| Require a date-specific numeric timing notice | Until obtained, classify the date UNRESOLVED. It must not be silently treated as a holiday. Coverage/truncation handling can restrict later replay. |
| Include every special session | Not justified by this inference; conflicts with D30's exclusion of Muhurat/shortened sessions. |

Including or excluding this day can affect its daily candle, the week ending that weekend, January and the containing Q/HY/Y aggregates, then zones, freshness and history sufficiency. Direction and magnitude are not quantified here; no replay was run.

**6. Recommendation.** Accept the narrow 20 January inference provisionally, because the date-specific notice says regular sessions and the stored normal-hours evidence provides a concrete interpretation. Keep B17 open and the missing systematic timing review visible. Preserve D30 exclusions. Do not call the whole calendar or ten-year history validated on this basis.

**7. Exact approval requested.** “Accept 20 January 2024 as a normal special session, 09:15-15:30 Asia/Kolkata, using NSE/MSD/60340 plus NSE/CMTR/41180 provisionally. Retain the inference note, D30 exclusions and B17. This does not certify calendar completeness.” If declined, the proposed disposition is UNRESOLVED, not holiday. Other D40 schema/provenance wording can be ratified separately from this date decision.

## 8. Other owner items in the registers

These are included so “every unresolved owner decision” does not silently omit the non-highlighted rows in UNRESOLVED_DECISIONS.md. Deferral is a valid disposition; it is not approval of unimplemented eligibility.

### 8.1 Remaining D41 interpretations

**Unresolved:** ratification of the engineering readings below. **Rulebook:** relevant structural, risk and RF7 requirements constrain outcomes, but do not prescribe every missing-data or comparison algorithm. **Current implementation, alternatives and consequences:**

| Item | Source and current behaviour | Alternative and consequence | Recommendation / exact approval |
|---|---|---|---|
| P-LOC-3 | RB 1587 freshness; [build_curve:129][curve] stops on unknown boundary freshness | Skip unknown and use a farther zone, potentially changing location without knowing the nearest boundary | Approve keeping MANUAL; unknown is not fresh or safely absent. |
| P-CAL-1 | Calendar is necessary to establish completed periods; [G0:100][g0] makes absent calendar MANUAL | Assume weekdays, missing special/holiday sessions | Approve current manual limitation pending verified calendar evidence. |
| P-LVL-1 | RB buffer tiers; [levels.ranges:38][levels] uses tier union | One reference price narrows ranges but adds a convention | Decide under B9; no blanket D41 approval resolves it. |
| P-LVL-2 | [RB 551-558][rb-target] specifies the nearest fresh opposing-zone target; [select_target:107][target] skips tested, stops on unknown freshness or target inside the entry range | Use tested/unknown target or skip ambiguity, changing R:R and gate outcomes | Approve current MANUAL handling and fresh-target selection as the research reading; revisit with a source-backed target exception only. |
| P-LVL-3 | Sizing requires valid entry/SL geometry (RB 2162); [levels.problems:62][level-problems], [G7:298][g7] withhold R:R for non-finite/inverted/non-positive levels | Compute misleading or undefined R:R/size | Approve withholding metrics and MANUAL diagnostics. |
| P-CONF-1 | RB 1302 measures conflict from entry; [htf_conflict:234][conflict] considers PL and entry bounds, makes outcome-changing disagreements MANUAL | Use a single point or entry range only; may change G5 | Keep manual until B9 fixes the entry convention. Approve that deferral, not a permanent new conflict threshold. |
| P-G8-1 | RF7, [RB 606][rb-rf7], involves reaction-zone context plus weak closing; [G8:333][g8] flags weak closing for manual reaction-zone review | Automate “right above”/reaction context with an invented distance | Approve manual review until owner defines contextual proximity; do not treat weak closing alone as a fully proven RF7 rejection. |
| P-DQ-1 | Rulebook does not define replay metadata clocks; [Finding.known_at:49][findings] excludes findings dated after as_of; undated findings always apply | Apply future findings to earlier decisions, breaking the intended historical view | Approve this engineering convention. It is not proof that every external event is announcement-time aware. |
| P-CA-1/2 | Rulebook has no full adjustment specification; [corporate_actions.in_history:85][ca-code] and G0 flag scale events/discontinuities; backtest excludes affected trade spans | Ignore events, or adjust with unapproved factors; either can create false geometry | Keep current restrictions pending B7. Approve neither adjustment factors nor coverage by ratifying the restriction. |
| P-REF-1 | No Rulebook CSV comparison schema; [compare_zones:41][zone-compare] matches timeframe/side/creation period, compares prices at recorded precision with default zero tolerance | Loose matching/tolerance may hide mismatches | Approve provisional matching, then confirm with the first real references; log justified precision exceptions rather than quietly widening tolerance. |
| P-BT-1 | No complete simulator prescribed; [ExecutionModel][bt-model] and [historical construction][bt-history] require assumptions and use one order per zone | Repeated opportunities from the same zone change the experiment | Approve explicit-input/one-order research convention only, with B9/B12 limitations intact. |
| M1 reporting | Closed leg-out matters (RB 1784); [scanner._fresh_zone_rows:77][fresh-report] labels `LEGOUT_WINDOW_OPEN` | Omit the label and make a still-developing score look final | Approve the diagnostic label; it does not change engine scoring or waive the closed-candle requirement. |

**Why this recommendation:** preserve observable uncertainty while avoiding invented thresholds. **Approval boundary:** approve the individual “keep/manual/diagnostic” dispositions, not a blanket statement that D41 or all gates are fully source-defined. R1-R6 are not reopened. Exact registry mapping is [RESEARCH_PIPELINE.md, section 4:89-115][d41-map] and [DECISION_LOG.md:579-594][d41].

### 8.2 Aggressive setup eligibility

1. **Unresolved:** precise HTF “area” and prior opposing-level/achievement criteria for automatic acceptance, distinct from approved R3 overlap classification.
2. **Rulebook:** [section 4, chapter 4, RB 1838-1858][rb-aggressive] requires 7/7, achievement by a close beyond an opposing level, and supporting trend; its decision table rejects the aggressive case without achievement. It does not supply a numeric area tolerance.
3. **Current:** [structure.coinciding:283][coinciding] distinguishes overlap from non-overlapping Aggressive context; [G6:263][g6] leaves Aggressive MANUAL. [G6 tests:379][g6-tests] exercise the classification. This is a restriction, not full implementation of all aggressive acceptance/rejection conditions.
4-5. **Alternatives/consequences:** define explicit area and achievement rules to automate; retain manual assessment; or disallow Aggressive in the initial research scope. Invented proximity or achievement rules change eligibility. Blanket manual handling must not be mistaken for permission when source-required achievement is known absent.
6. **Recommendation:** defer automatic Aggressive eligibility and keep it outside automatic acceptance until criteria are supplied and checked.
7. **Approval:** confirm that deferral, or specify the eligible HTF area, which prior opposing level counts and how completed-close achievement is established. No new threshold is proposed here.

### 8.3 Sector support

1. **Unresolved:** whether to begin implementing sector assessment and how to define instruments, direction/support and timing.
2. **Rulebook:** sector/market context appears at [RB 484-499][rb-sector] and [RB 851-895][rb-sector-detail]; HOC's exceptional buy discussion also invokes strong sector support at RB 1600. These passages do not specify a complete mechanical sector feed or score.
3. **Current:** [D6, DECISION_LOG.md:96-113][d6] already approves deferral; required sector checks remain manual in [matrix/G4:56,213][g4] and the checklist. No automated sector support is established.
4-5. **Alternatives/consequences:** retain manual context; define a dated index-to-stock mapping and explicit alignment method; or remove the condition, which would be a methodology change.
6. **Recommendation:** retain D6 until a separate specification is supplied. Sector support must not silently pass.
7. **Approval:** none is needed to continue the already approved deferral. Only a request to automate requires new scope and definitions; do not ask the owner to reapprove D6 as if it were absent.

### 8.4 M4b / WIT session and gap design

1. **Unresolved:** identity periods, session anchoring, last partial bar, completion and gap detection for 75/125-minute execution data.
2. **Rulebook:** [RB 1755-1770][rb-ltf] and [chapter 6 summary, RB 1978][rb-timeframes] establish timeframe roles and the 375-minute context, not the orchestrator's full intraday data contract.
3. **Current:** [audit M4b, line 283][audit-medium] records that the overlay path stops at Daily. [G0][g0] blocks WIT; [Wit tests:105][wit-tests] ensure it remains blocked.
4-5. **Alternatives/consequences:** extend the overlay with a verified session/gap design; defer WIT; or bypass the overlay, which loses required freshness/gap assurance and is unacceptable for approved output.
6. **Recommendation:** keep WIT blocked pending a concrete design and B6/B15 intraday source/depth evidence. Correcting RB-VERSION-1 does not unblock it.
7. **Approval:** no reapproval is needed to preserve the block. Future approval must address an actual 75/125-minute design and data contract; this pack does not invent one.

### 8.5 Instrument record semantics

1. **Unresolved:** ratification of the dated identity schema, not approval that missing identity records are factual.
2. **Rulebook:** no CSV/ISIN lineage semantics are prescribed; this is an engineering decision supporting D1's historical universe.
3. **Current:** [instruments.py:1-19, state_at:123][instruments] defines inclusive listing starts/ends; SYMBOL_CHANGE begins the new symbol on its effective date; ISIN_CHANGE carries the new ISIN; DELISTING/MERGER remove the old identity from that date. The implementation replaces the old ISIN on the change date: the old identity is not simultaneously active that day. MERGER does not stitch the successor into a rename. [EffectiveDates tests:85][instrument-tests] cover boundaries and changes.
4-5. **Alternatives/consequences:** inclusive versus exclusive end conventions change membership on boundary days; treating a merger as a rename can create a false price/history chain. Missing or conflicting identities can remain unknown rather than guessed.
6. **Recommendation:** ratify the implemented conventions with the ISIN transition stated explicitly; require official effective-date evidence per record. Do not infer identity from a ticker alone.
7. **Approval:** “Use inclusive listing intervals; changes take effect on effective_from with the old ISIN replaced that day; merger/delisting cease the old listing from that date; merger successor is a different instrument. Unknown/conflicting identity stays unresolved.” This does not close B11.

### 8.6 Remaining audit-register carryovers

[DECISION_REGISTER.md, section 2][register-engineering] also carries L5-L9 and audit rows 13/31. They are not new approvals hidden in the seven headline questions:

| Unresolved item | Source / current state | Interpretation and consequence | Recommended owner disposition |
|---|---|---|---|
| Wick-to-wick “as appropriate” | [Audit row 13:93][audit-rows]; RB 1263. No automatic selection rule implemented. | Always/never/conditional selection changes geometry; a conditional rule needs actual criteria. | Defer automation; supply criteria before a future implementation. |
| Drop a timeframe inside 6+ base clutter | [Audit row 31:113][audit-rows]; RB 818-820. Not implemented. | Automatic descent needs supported timeframe/data and eligibility rules; ignoring the source is not equivalent. | Keep as manual guidance pending a scoped design; no automatic descent approved. |
| L5-L8 | [Audit section 5:295-298][audit-low]: minimum-history mismatch for zero-base, custom Rules validation/labels, assumed daily timestamp convention, supply-context flag visibility | These are software/data-contract limitations, not discretionary trading rules to waive. A three-bar input cannot prove a four-bar pattern; assumed timestamps need source confirmation. | Record as unresolved engineering work/evidence. Do not label “owner approved” as a repair or certification. |
| L9 | [Audit:299][audit-low]: calendar-mode gap truncates the later HTF series; truncation is exposed | Retaining truncation loses later opportunities; segment/restart requires a design that cannot carry state across a gap silently. | Retain disclosed truncation for now; defer a restart design. No approval of data completeness follows. |

The Rulebook does not prescribe the L5-L9 software interfaces. The requested disposition is deferral/retention of disclosed limitations, not permission to weaken trading requirements. This report does not recertify every older audit claim against every module.

## 9. Evidence and data blockers: separate from owner interpretation

These blockers cannot be closed by answering “approved”. The items below specify what evidence would support closure; no evidence acquisition is performed here.

### B18: real UDiFF sample and format verification

**Current evidence:** [EOD_FORMAT_EVIDENCE.md, sections 1, 5, 7-8][eod-evidence] documents legacy-format evidence, not a verified UDiFF schema. [DATA_REQUIREMENTS.md:23-32][data-format] treats the format transition as requiring verification. Existing legacy archive coverage does not validate UDiFF.

**Code/test:** [acquisition._header_format:144 and detect_format:154][format-code] recognize an apparent UDiFF header; [ingestion quarantine at acquisition.py:369][format-quarantine] rejects it as `FORMAT_UNVERIFIED_B18`. [Acquisition tests:75-101][format-tests] use synthetic header recognition/quarantine. Recognition is not a supported parser.

**Needed:** an unchanged official sample archive, exact source URL, known download date or explicitly unknown date, SHA-256, actual header and representative rows; verified mapping for symbol/series/ISIN, OHLC, quantity, previous close, trade counts and the relevant date fields. Separately verify the transition date and schema documentation. A renamed legacy file or guessed column list is insufficient.

**Closure boundary:** retain quarantine until evidence is reviewed and a parser is implemented/validated in later work. Owner approval of a format guess cannot close B18.

### B11: historical Nifty 100 constituents and instrument identity

**Current evidence:** [Master status, sections 4-5][master] reports loaders but no historical constituent/identity records. Current index constituents must not be used as the universe for earlier years.

**Code/test:** [universe.py:23-95][universe] supports dated membership; [instruments.py:74,123,186][instruments] supports identity changes. [Universe tests:60-92][universe-tests] and [instrument EffectiveDates tests][instrument-tests] exercise synthetic histories. The universe loader's `verified` flag checks source presence and a 64-hex hash string; it does **not** read and authenticate that source file. Its Membership representation also does not retain all CSV provenance/announcement fields. Effective-date filtering alone is not proof of announcement-time correctness or complete coverage.

**Needed:** an authoritative starting membership snapshot at/before the study start, all intervening additions/removals and effective dates, publication/announcement dates, source files and verified hashes. Include delisted/merged constituents, symbol/ISIN changes, and matching historical prices/series. Resolve contradictory or overlapping intervals rather than silently accepting a convenient row. Data rights/access can be arranged later if required; no acquisition is requested here.

**Closure boundary:** official evidence must reconstruct the universe on each studied date, with identity continuity and availability checked. A present-day list, a `verified=true` label or a collection of bhavcopies alone does not close B11. Without it, historical claims retain survivorship/selection limitations.

### B7: corporate-action records and adjustment convention

**Current evidence:** records interface exists, verified event history/adjustment pipeline does not. [corporate_actions.py:33-92][ca-code] loads event records and flags non-dividend scale events within history; it does not adjust OHLC. Its verification flag, like the universe loader, checks metadata shape rather than hashing the referenced source file. [G0][g0] retains manual/unverified limitations. PREVCLOSE discontinuity detection is an anomaly signal, not proof of a particular split/bonus/rights event. [CorporateActions and PrevcloseDiscontinuity tests:60-153][ca-tests] cover those restrictions.

**Needed evidence:** official event notices with symbol/ISIN, event type, announcement/effective/ex-date distinctions, ratios/terms, source bytes and hashes, and coverage for every studied symbol/period. Demergers and rights issues must not be guessed as ordinary split factors. Dividends require an explicit price-return versus total-return treatment.

**Additional owner policy needed:** choose and document adjustment conventions, factor application dates, and as-of treatment; preserve raw data separately. Alternatives are (a) verified as-of adjustment, with validated transformed geometry, or (b) restrict/exclude affected histories and disclose the lost coverage. Ignoring scale events can manufacture zones, gaps, returns and stop hits. Recommendation: retain restrictions now and review a concrete source-backed adjustment specification later; no factors are approved by this pack.

**Closure boundary:** supplying an events CSV alone does not remove `CORPORATE_ACTIONS_UNVERIFIED` legitimately. Source authenticity, completeness and the chosen treatment must all be demonstrated. Backtest exclusions also retain the end-of-data limitation recorded in UNRESOLVED_DECISIONS.md.

### B8, B10 and B17: TradingView reference validation

The [Reference Validation Plan, sections 1-5][reference-plan] distinguishes independent computation (class A), republication such as existing Yahoo rows (class B), and recorded human judgement (class C). These are not interchangeable. The plan is prepared; it reports no TradingView observations. Synthetic comparator tests do not count as external validation.

| Blocker | Evidence required | Current tooling and exact scope |
|---|---|---|
| **B8: candles, aggregation and trend inputs** | Paired NSE TradingView D/W/M/3M/6M/12M OHLC at boundaries; holiday weeks, first partial listing periods and sufficient SMA-50 history. Record chart timezone, session, adjustment settings, export/screenshot, hash and observation date. | [nse_reference.compare_ohlc:188][ohlc-compare] and [refcheck.compare_trend:139][trend-compare]. D23's calendar-aligned construction is an approved design, not observed TradingView parity. |
| **B10: indicator/zone behaviour** | Unmodified Pine indicator output with actual input settings, including the approved max-base setting of five; D/W/M zone creation, pattern, PL/DL, first tests and invalidation. Include ambiguous timing cases. | [compare_zones:41][zone-compare]; [ZoneReference tests:334][zone-tests]. Compare owner-approved differences separately from Pine parity; do not change protected sources to force a match. WIT validation remains separately blocked. |
| **B17: calendar and sessions** | Complete the twelve prepared calendar observations and inspect boundary candles, holidays, normal special Saturdays, shortened and Muhurat sessions. Reconcile against official notices and EOD session presence across the intended study range. | [tradingview_checks.template.csv:2-13][calendar-template]; TV-CAL-09 covers 20 January 2024. Calendar hash checks authenticate held notices, not list completeness or TradingView's handling of excluded sessions. |

**What to record:** exact symbol/exchange and timeframe, Asia/Kolkata/session setting, split/dividend adjustments, indicator configuration, original export/screenshot and hash, and the specific rows compared. Start with the plan's INFY control and proposed corporate-action/listing cases only after their event dates are independently verified; the plan labels those event dates unverified. No missing observation should be filled from our own computed output.

**How to decide a mismatch:** first check observation/settings and input data; then classify intended D12 differences, unresolved methodology or an implementation defect. Default comparison tolerance is zero at recorded precision; any justified exception needs explicit evidence. Human curve/gate readings cannot be called independent algorithmic validation. A spot-check pass does not validate all years, symbols or timeframes.

**Owner action versus evidence:** the initial validation sample/settings may be approved for a later task, but actual observations and reviewed disagreements are required to close these blockers. D40 approval resolves only its inference; it does not close B17. The locally documented 2021-2025 calendar scope does not establish complete 2016-2026 coverage. Intraday B6/B15 and missing EOD history remain additional prerequisites outside these headline blockers.

## 10. Approval worksheet

No item is approved by this report. The following wording can be accepted, amended or deferred individually:

| Decision | Owner response required |
|---|---|
| **RB-VERSION-1** | PDF canonical; Markdown citation companion; accept correction of the disproven page-62 omission claim. |
| **P-LOC-2** | Redraw immediately on known TESTED; no VLOC solely from remaining inside tested demand; unknown/missing boundaries manual. |
| **P-RISK-1** | Ratify upper-band FAIL and below-band/undeclared MANUAL in the separate risk plan; no automatic stage promotion. |
| **Monthly cap** | At most ten first fills per IST calendar month across the trading book; no slot replenishment on exit; accept disclosed fill-order proxy or supply prospective selection policy. |
| **B9** | Preserve ranges; approve provisional tier/edge convention and predeclared endpoint research, or supply an explicit baseline and exception rules. |
| **B12** | Approve/amend research policies; supply expiry N, dated cost inputs, slippage and concurrency policy; require pending-order revalidation before claiming full implementation. |
| **D40** | Accept the narrow provisional 20 January 2024 09:15-15:30 inference, or mark the date unresolved; retain B17 and D30. |
| **D41 remainder / instruments** | Ratify the individual manual/diagnostic conventions and dated identity semantics in section 8; retain the listed limitations. |
| **Aggressive / audit carryovers** | Defer automatic Aggressive criteria, wick selection/timeframe descent and gap-restart design, or supply a concrete specification. Existing sector deferral and WIT block need no repeat approval. |
| **Evidence programme** | Separately approve a later reference sample/source plan if desired; actual UDiFF, constituent, corporate-action and TradingView evidence is still required. B7 adjustment policy remains to be specified from real records. |

Approving this worksheet decides policy only. Implementation, evidence collection and subsequent validation remain separate work; none was performed or implicitly authorised by preparing this pack.

[master]: /Users/yash/day-trader-skill/PRODUCT_MASTER_STATUS.md:1
[unresolved]: /Users/yash/day-trader-skill/nse/docs/release/UNRESOLVED_DECISIONS.md:1
[register]: /Users/yash/day-trader-skill/nse/docs/DECISION_REGISTER.md:1
[register-engineering]: /Users/yash/day-trader-skill/nse/docs/DECISION_REGISTER.md:57
[version-row]: /Users/yash/day-trader-skill/nse/docs/DECISION_REGISTER.md:55
[d7]: /Users/yash/day-trader-skill/nse/docs/DECISION_LOG.md:115
[d6]: /Users/yash/day-trader-skill/nse/docs/DECISION_LOG.md:96
[old-cap-review]: /Users/yash/day-trader-skill/nse/docs/DECISION_REVIEW.md:128
[d40]: /Users/yash/day-trader-skill/nse/docs/DECISION_LOG.md:550
[d41]: /Users/yash/day-trader-skill/nse/docs/DECISION_LOG.md:579
[d41-map]: /Users/yash/day-trader-skill/nse/docs/RESEARCH_PIPELINE.md:89
[pdf]: /Users/yash/day-trader-skill/340fe490-8783-4eea-8cbd-e834449e9a42_Trading_Rulebook.pdf
[rb]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:1>
[pine]: </Users/yash/day-trader-skill/nse/sources/Demand&Supply Indicator.pine:1>
[protected]: /Users/yash/day-trader-skill/nse/validation/protected.py:10
[rb-proximity]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:1772>
[rb-location]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:1578>
[rb-risk]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:37>
[rb-stage]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:2208>
[rb-risk-redline]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:3949>
[rb-small-risk]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:3298>
[rb-contract]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:3444>
[rb-scaling]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:3642>
[rb-cap]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:2388>
[rb-entry]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:2006>
[rb-stop]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:2088>
[rb-cancel]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:2530>
[rb-timeframes]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:1978>
[rb-target]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:551>
[rb-rf7]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:606>
[rb-aggressive]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:1838>
[rb-sector]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:484>
[rb-sector-detail]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:851>
[rb-ltf]: </Users/yash/day-trader-skill/nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md:1755>
[curve]: /Users/yash/day-trader-skill/nse/research/structure.py:129
[g0]: /Users/yash/day-trader-skill/nse/research/qualification.py:100
[g1]: /Users/yash/day-trader-skill/nse/research/qualification.py:134
[g3]: /Users/yash/day-trader-skill/nse/research/qualification.py:171
[g4]: /Users/yash/day-trader-skill/nse/research/qualification.py:213
[g6]: /Users/yash/day-trader-skill/nse/research/qualification.py:263
[g7]: /Users/yash/day-trader-skill/nse/research/qualification.py:298
[g8]: /Users/yash/day-trader-skill/nse/research/qualification.py:333
[g8-risk]: /Users/yash/day-trader-skill/nse/research/qualification.py:364
[g3-tests]: /Users/yash/day-trader-skill/tests/test_research_gates.py:196
[g6-tests]: /Users/yash/day-trader-skill/tests/test_research_gates.py:379
[wit-tests]: /Users/yash/day-trader-skill/tests/test_research_gates.py:105
[levels-tests]: /Users/yash/day-trader-skill/tests/test_research_gates.py:483
[risk-assess]: /Users/yash/day-trader-skill/nse/research/risk.py:130
[risk-tests]: /Users/yash/day-trader-skill/tests/test_research_risk.py:142
[risk-audit-tests]: /Users/yash/day-trader-skill/tests/test_research_risk.py:321
[levels]: /Users/yash/day-trader-skill/nse/research/levels.py:23
[level-problems]: /Users/yash/day-trader-skill/nse/research/levels.py:62
[target]: /Users/yash/day-trader-skill/nse/research/levels.py:107
[conflict]: /Users/yash/day-trader-skill/nse/research/structure.py:234
[coinciding]: /Users/yash/day-trader-skill/nse/research/structure.py:283
[bt-model]: /Users/yash/day-trader-skill/nse/research/backtest.py:81
[bt-plan]: /Users/yash/day-trader-skill/nse/research/backtest.py:127
[bt-simulate]: /Users/yash/day-trader-skill/nse/research/backtest.py:145
[bt-cost]: /Users/yash/day-trader-skill/nse/research/backtest.py:231
[bt-portfolio]: /Users/yash/day-trader-skill/nse/research/backtest.py:352
[bt-limitations]: /Users/yash/day-trader-skill/nse/research/backtest.py:400
[bt-history]: /Users/yash/day-trader-skill/nse/research/backtest.py:421
[bt-tests]: /Users/yash/day-trader-skill/tests/test_research_backtest.py:33
[bt-portfolio-tests]: /Users/yash/day-trader-skill/tests/test_research_backtest.py:322
[bt-cap-tests]: /Users/yash/day-trader-skill/tests/test_research_backtest.py:634
[journal]: /Users/yash/day-trader-skill/nse/research/store.py:629
[notice-60340]: /Users/yash/day-trader-skill/nse/data/calendar/circulars/MSD60340.pdf
[notice-41180]: /Users/yash/day-trader-skill/nse/data/calendar/circulars/CMTR41180.pdf
[notice-65729]: /Users/yash/day-trader-skill/nse/data/calendar/circulars/CMTR65729.pdf
[calendar-row]: /Users/yash/day-trader-skill/nse/data/calendar/events.csv:61
[calendar-code]: /Users/yash/day-trader-skill/nse/calendar/nse_calendar.py:238
[calendar-tests]: /Users/yash/day-trader-skill/tests/test_nse_calendar_data.py:234
[findings]: /Users/yash/day-trader-skill/nse/research/marketdata.py:49
[fresh-report]: /Users/yash/day-trader-skill/nse/research/scanner.py:77
[audit-medium]: /Users/yash/day-trader-skill/nse/docs/PHASE1_CORRECTNESS_AUDIT.md:277
[audit-low]: /Users/yash/day-trader-skill/nse/docs/PHASE1_CORRECTNESS_AUDIT.md:295
[audit-rows]: /Users/yash/day-trader-skill/nse/docs/PHASE1_CORRECTNESS_AUDIT.md:93
[instruments]: /Users/yash/day-trader-skill/nse/research/instruments.py:1
[instrument-tests]: /Users/yash/day-trader-skill/tests/test_research_instruments.py:85
[eod-evidence]: /Users/yash/day-trader-skill/nse/docs/EOD_FORMAT_EVIDENCE.md:1
[data-format]: /Users/yash/day-trader-skill/nse/docs/DATA_REQUIREMENTS.md:23
[format-code]: /Users/yash/day-trader-skill/nse/research/acquisition.py:144
[format-quarantine]: /Users/yash/day-trader-skill/nse/research/acquisition.py:369
[format-tests]: /Users/yash/day-trader-skill/tests/test_research_acquisition.py:75
[universe]: /Users/yash/day-trader-skill/nse/research/universe.py:23
[universe-tests]: /Users/yash/day-trader-skill/tests/test_research_reports.py:60
[ca-code]: /Users/yash/day-trader-skill/nse/research/corporate_actions.py:33
[ca-tests]: /Users/yash/day-trader-skill/tests/test_research_data.py:60
[reference-plan]: /Users/yash/day-trader-skill/nse/docs/REFERENCE_VALIDATION_PLAN.md:1
[ohlc-compare]: /Users/yash/day-trader-skill/nse/eod/nse_reference.py:188
[zone-compare]: /Users/yash/day-trader-skill/nse/research/refcheck.py:41
[trend-compare]: /Users/yash/day-trader-skill/nse/research/refcheck.py:139
[zone-tests]: /Users/yash/day-trader-skill/tests/test_research_data.py:334
[calendar-template]: /Users/yash/day-trader-skill/nse/data/reference/tradingview_checks.template.csv:2
