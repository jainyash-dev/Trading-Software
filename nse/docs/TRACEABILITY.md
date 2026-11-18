# Traceability: Rule, Source, Implementation, Test, Validation

**Dated 2026-11-02; rows 51-56 added 2026-11-06; rows 57-63 added 2026-11-08; rows 64-68 added 2026-11-08 (real-data milestone).** "Validation" is external evidence only (TradingView, reference data);
synthetic tests are listed under Test. A row with no implementation or no test says so.
R1-R6 are product-owner approved in `DECISION_REGISTER.md`; other D41 interpretations
remain PROPOSED (`RESEARCH_PIPELINE.md` section 4, `DECISION_LOG.md` D41).

| # | Rule | Source | Implementation | Test | Validation |
|---|---|---|---|---|---|
| 1 | Strong candle = body > 50% | RB 402; D12 | `zone_engine._Detector.strong_bull/bear` | `test_zone_engine` | None (B10) |
| 2 | Leg-in / base / leg-out, max 5 bases, 6+ no zone | RB 404, 739, 786-787; PS 10, 1386-1439; D35 | `zone_engine.cluster_step` | `test_zone_engine` | None (B10) |
| 3 | Body-to-wick PL/DL; exceptional DL | PS 1464-1511; RB 337-339, 542-544 | `zone_engine.create` | `test_zone_engine` | None (B10) |
| 4 | Zero-base zones, score tagged ZB-PINE-REF | PS 1717-1762; D5, D13 | `zone_engine.zero_base_step`, `base_points` | `test_zone_engine` | None |
| 5 | Core 7/7 (freshness 3, strength 2, base 2) | RB 661, 675-677, 728-730, 785-787, 829 | `zone_engine.core_score`, `_assess`; G2 `qualification._g2` | `test_zone_engine`; `test_research_gates.G1G2` | None |
| 6 | Any PL touch after the leg-out = tested; tested never an entry | RB 264, 683-697; D3 | engine `state_step`; overlay `_overlay`; G1 | `test_mtf_freshness`; adversarial q1, q2 | None |
| 7 | Close beyond DL invalidates permanently | PS 2613; RB 1627, 1741; D24 | engine `state_step`; overlay | `test_zone_engine`, `test_mtf_freshness`; q2 | None |
| 8 | HTF zones tested by finer completed candles | RB 292, 1508; D24-D28 | `mtf_freshness.replay` | `test_mtf_freshness` | None (B8) |
| 9 | Missing data never establishes freshness | D27, D33, D34, D36-D39 | overlay statuses; G0; blocked dispositions | `test_mtf_freshness`; q3; integration missing session | None |
| 10 | Candidates only from the overlay | audit M4 | `MtfSnapshot.eligible_after_overlay`, `manual_review_after_overlay`; `qualification.evaluate_symbol` | `test_repo` safety boundaries; q4; sweep | n/a |
| 11 | Long-only; supply is context | D2 | engine CONTEXT_ONLY; fresh-zone report label | `test_research_reports` | n/a |
| 12 | Completed candles only; as_of cuts input | D23; spec 9 | engine `_completed`; `replay` step 1 | `test_research_lookahead` | n/a |
| 13 | Curve from nearest fresh HTF DZ below / SZ above; 0 / 33.33 / 66.66 / 100 | RB 1586-1591, 1597-1601 | `structure.build_curve`, `positions` | `test_research_gates.G3` | None |
| 14 | Tested boundary -> redraw; broken boundary -> redraw | RB 1617-1628 (situations 3, 4) | `build_curve` skips tested, ignores invalidated | `G3.test_tested_boundary_is_skipped` | None |
| 15 | ATH: no curve | RB 1605-1609 | `build_curve` issue -> G3 MANUAL | `G3.test_incomplete_curve_needs_review` | None |
| 16 | VHOC no buy; HOC only in extreme circumstances | RB 1600-1601; spec 7.2; P-MAT-2 | `_g3`, `matrix_long` | `G3.test_vhoc_is_rejected`; `Trend.test_matrix_rows` | None |
| 17 | SMA-50 clock, Pine thresholds, 55 candles | RB 1672-1711, 1748; PS 252-291; D14, D23 | `trend.reading_from_closes` | `test_research_gates.Trend` | None (B8) |
| 18 | MIT: Weekly trend gate, Monthly context only; RB 1232 caution | D21; RB 1232 | `ROLES[MIT]`; `_g4`; `_evidence` | `Trend.test_monthly_trend_is_context_not_a_gate`, `test_weekly_sideways_at_vloc_is_extreme_caution` | None |
| 19 | WIT: Daily trend gate only; Weekly curve | D22; RB 1394-1395, 1574, 1668 | `ROLES[WIT_*]` | `Wit.test_wit_ignores_a_falling_weekly_trend_that_rejects_mit` | None |
| 20 | Alignment matrix (long rows) | RB 1889-1903; spec 7.6; P-MAT-1, P-TREND-1 | `qualification.matrix_long` | `Trend.test_matrix_rows`, `test_weekly_trend_cases` | None |
| 21 | HTF conflict: inside / <= 5% reject; 5-10% manual; W/Y and tested manual; broken opposing zone clears | RB 601, 1302-1316; spec 7.4; RF2; P-CONF-1 | `structure.htf_conflict`; `_g5` | `test_research_gates.G5`; q9 | None |
| 22 | WIT weekly DZ inside Monthly SZ toxic | RB 1402 | `_g5` WIT branch | none (WIT BLOCKED; branch untested) | None |
| 23 | Coinciding / invalid / aggressive geometry; DL-untouched HTF zone | RB 1826-1856; D15; P-COIN-1, P-COIN-2 | `structure.coinciding`; `_g6` | `test_research_gates.G6` | None |
| 24 | Entry = PL + buffer; SL = DL - buffer; printed tiers; ranges only | RB 2010-2022, 2097-2110; D7; B9; P-LVL-1 | `levels.ranges` | `G7.test_ranges_use_every_tier_that_could_apply` | None |
| 25 | Target = nearest fresh ITF opposing PL; R:R >= 2 (RF8) | RB 82, 551-558, 2268-2328; spec 6.4; P-LVL-2 | `levels.select_target`, `rr_range`; `_g7` | `test_research_gates.G7` | None |
| 26 | Quantity = floor(RPT / (entry - SL)) | RB 42, 2162, 2203-2204 | `levels.quantity_range` | `G7.test_ranges_use_every_tier_that_could_apply` | n/a |
| 27 | Red flags RF1-RF10; Essential Checks 1-10 | RB 594-631; P-G8-1 | `_g8` (RF1, RF2, RF3, RF6, RF7, RF8, EC1, EC5-7 automated; RF4, RF5, RF9, RF10, EC10 checklist) | `test_research_gates.G8` | n/a |
| 28 | WIT recency 8 / 9-10 / >10 / >20 | RB 1403, 1788-1801; D16 | `_g1` | `Wit.test_wit_recency_bands` | None |
| 29 | Statuses; never auto-approve; checklist on actionable | spec 8 | `models.derive_status`; `CHECKLIST` | `StatusDerivation`; `Reference` | n/a |
| 30 | Sector never a silent pass | D6 | matrix LOC + Sideways, HOC -> MANUAL; checklist SECTOR | `Trend.test_weekly_trend_cases`; q12 | n/a |
| 31 | Intraday blocked until M4b approved | audit M4b; user decision 2026-10-28 | G0 BLOCKED; scanner BLOCKED | `Wit`; q7; `Cli.test_wit_scan_is_blocked_without_reading_data` | n/a |
| 32 | Top-down Y -> HY -> Q -> M -> W -> execution | D11; spec 7.1 | `topdown.tda` | integration (TDA in every result) | None |
| 33 | HTF EMA20, crossover, RSI/Stochastic, gap application (+points to /14) | RB 500-583, 896-987; spec 5.1, 5.3 | `confluence.score14` (display only: EMA20, crossover, gap PROVISIONAL; sector, RSI/Stoch NOT_EVALUATED); no gate reads it | `test_research_confluence` (incl. no-gate-depends mutation) | None (B8) |
| 34 | "Coming from" analysis, LOTL, authenticity, garbage chart | RB 1316; RF4; spec 8 | checklist only (manual) | `Reference` (checklist present) | n/a |
| 35 | Wick-to-Wick PL/DL (audit row 13); drop a timeframe in a 6+ base mess (row 31) | audit section 3.1 | **not implemented** | none | n/a |

## Gate summary (G0-G8)

Implementation: `nse/research/qualification.py` unless noted. Unit tests:
`tests/test_research_gates.py` (class named after the gate). Real-replay tests:
`tests/test_research_e2e.py`. Every gate reports evidence and source references in its result.

| Gate | Inputs | Approved rule | PASS | FAIL | MANUAL | Missing data | E2E coverage |
|---|---|---|---|---|---|---|---|
| G0 | snapshot, data findings, calendar, corporate actions | spec 8 G0; D23, D28, D33, D34 | complete execution series, calendar given | (none) | no calendar (P-CAL-1), unresolved dates, corporate action in history (P-CA-1) | DATA_INSUFFICIENT: data error dated <= as_of, truncated or short execution series; BLOCKED for WIT | missing session, no calendar, WIT |
| G1 | overlay-kept zone | D2, D3; audit M4; WIT recency RB 1403, 1788-1801 | fresh demand, test_count 0, overlay FRESH | (zone never reaches G1) | WIT recency > 8 | (overlay blocks it) | tested, invalidated, leg-out day |
| G2 | engine assessment | RB 661, 829; D12 | ELIGIBLE 7/7 | (not evaluated below 7/7) | engine MANUAL_REVIEW (source disagreement) | (n/a) | 6/7 then 7/7 |
| G3 | location TF zones (M for MIT, W for WIT), CMP | spec 7.2; RB 1586-1601; approved R1 | VLOC / LOC / EQB at CMP only | VHOC | HOC; incomplete curve; unknown boundary; CMP in tested HTF DZ | DATA_INSUFFICIENT if the series is unavailable | reference (LOC); CMP-only and tested-boundary cases |
| G4 | trend gate TF (W for MIT, D for WIT), CMP positions, coinciding class | spec 7.3, 7.6; D14, D21, D22; RB 1889-1903; approved R1/R2/R5 | matrix PASS for every reading and CMP position; 12 o'clock maps to STRONG_UP | matrix FAIL for every reading and CMP position | readings disagree; RB 1232 caution; < 55 candles | DATA_INSUFFICIENT if truncated / unavailable | reference (12 o'clock); EQB + Down; HOC outcomes; 53 of 55 weeks |
| G5 | supply zones on M, Q, HY (reject) and W, Y (evidence) | spec 7.4; RB 1302-1316; RF2 | none within 10% | fresh M/Q/HY inside or <= 5% | 5-10%; W/Y; tested or unknown; measuring point | DATA_INSUFFICIENT for M/Q/HY; MANUAL for W/Y | Weekly supply near entry; Y and HY missing |
| G6 | location TF and execution demand-zone ranges | spec 7.5; D15; RB 1826-1856; approved R3/R6 | actual range overlap with qualifying DL-intact HTF demand; known absence passes as Standard | execution zone wholly below HTF DL | execution zone wholly above the HTF demand range is distinct Aggressive; unknown freshness / DL status is MANUAL | DATA_INSUFFICIENT | overlapping, non-overlap, boundary, unknown and known-absence cases |
| G7 | levels (`levels.py`), target TF supply | spec 6; RB 82, 2010-2022, 2097-2110, 2268-2328; RF8 | R:R >= 2 for all choices | R:R < 2 for all choices | depends on buffer; no / unknown target; invalid levels (P-LVL-3) | DATA_INSUFFICIENT if target TF unavailable | reference (PASS_ALL) |
| G8 | trend gate, positions, zone, G5, G7, TDA, risk per trade | RB 594-631; approved R5 | RF1-3, 6-8, EC1, 5-7 pass | RF3 clear down not at VLOC | RF3 ambiguous; RF7 poor closing; EC1 TDA incomplete; EC7 no RPT | (via EC1) | no risk per trade |

Precedence (`models.derive_status`): BLOCKED > REJECTED > DATA_INSUFFICIENT > MANUAL_REVIEW
> ACTIONABLE (manual checks pending). Tests: `StatusDerivation`, adversarial q6, mutation runs.

## Product-owner approvals and focused regression coverage (2026-11-02)

| ID | Approved rule | Implementation | Focused regression coverage |
|---|---|---|---|
| R1 | CMP alone determines curve position; execution PL cannot override HOC at CMP | `qualification._g3`, `structure.positions` | CMP/PL disagreement; HOC CMP with LOC execution PL; exact curve boundaries |
| R2 | 12 o'clock maps to STRONG_UP while diagnostics/reports retain Extreme Uptrend | `trend.READINGS`, trend/gate evidence | 12 o'clock matrix result; threshold; preserved diagnostic label |
| R3 | Inclusive actual price-range overlap of execution and relevant HTF demand is COINCIDING; Aggressive remains distinct; preserve D15 DL qualification | `structure.coinciding`, `qualification._g6` | overlap, non-overlap, exact boundary, tested-but-DL-intact, DL-touched and unknown states |
| R4 | Completed own-timeframe close beyond demand DL invalidates; wick-only and pending HTF close stay distinct; SL touch is a separate trade event | Zone Engine, MTF overlay, research backtest | wick-only/no invalidation; close/invalidation; HTF pending/resolution; SL-only, invalidation-only and both |
| R5 | HOC + Up long rejects; HOC + Sideways is manual; HOC + Down follows RF3 | `qualification.matrix_long`, `_g3`, `_g8` | direct matrix cases and full final-status outcomes |
| R6 | Known absence passes G6 as Standard; unknown freshness or DL-touch status stays manual; G3 independently controls curve qualification | `structure.coinciding`, `qualification._g6` | G6 pass with G3 manual; unknown freshness and DL status; no actionable bypass |

## Additional rows (2026-10-29, second pass)

| # | Rule | Source | Implementation | Test | Validation |
|---|---|---|---|---|---|
| 36 | Unadjusted price-scale corporate action in the history is not silently used | B7; P-CA-1 | `corporate_actions.py`, `_g0` | `test_research_data.CorporateActions` | None (no data) |
| 37 | Invalid trade levels never produce an R:R | spec 6; P-LVL-3 | `levels.problems`, `_g7` | `test_research_gates.Levels` | n/a |
| 38 | History sufficiency per timeframe; acquisition spec | D23, D29, D31 | `inventory.py` | `test_research_data.RequiredHistory`, `RealInventory` | Local files only |
| 39 | Zone reference comparison | B10; P-REF-1 | `refcheck.py` | `test_research_data.ZoneReference` (hand-derived synthetic rows) | None (no TradingView rows) |
| 40 | Backtest: point-in-time signals, user execution model, no performance claim | B9, B11, B12; P-BT-1 | `backtest.py` | `test_research_backtest` | None |
| 41 | Leg-out window still open is visible in the report | audit M1 | `scanner._fresh_zone_rows` | e2e `test_before_the_leg_out_closes_there_is_no_candidate` | n/a |
| 42 | Unexplained price-scale change (PREVCLOSE discontinuity) is not silently used | B7; P-CA-2 | `corporate_actions.prevclose_discontinuities`; `marketdata.from_bhavcopy`; `_g0`; `backtest.run` | `test_research_data.PrevcloseDiscontinuity`, `RealDiscontinuities`; `test_research_backtest` | Local Q1 2022 files: one occurrence (SETFGOLD), event unverified |
| 43 | Required data window is complete before acceptance | D29, D31; B17, B18 | `run_all --require-window`; `inventory --window-start` | `test_research_data.RealWindow` | Local files only |
| 44 | Provenance rows for new EOD files, nothing inferred | D31 | `manifest_tool.py`; `cli manifest-rows` | `test_research_data.ManifestRows` | n/a |
| 45 | Q/HY/Y OHLC and SMA 50 references can be compared | D23; B8; D14 | `nse_reference` (TIMEFRAMES), `refcheck.compare_trend` | `QuarterlyReference`, `TrendReference` | None recorded (`REFERENCE_VALIDATION_PLAN.md`) |

## Additional rows (2026-11-02, integrated build)

| # | Rule | Source | Implementation | Test | Validation |
|---|---|---|---|---|---|
| 46 | Quantity = floor(RPT / (Entry - SL)), exact; RPT within stage band; never average down; F&O refused; 10 trades/month ceiling | RB 37-75, 2157-2214, 2140, 2388-2408 | `risk.py` (separate risk plan; never changes a status); `levels.quantity_range` (exact decimals, regression for float off-by-one) | `test_research_risk` (RB worked examples exact); `G7`/`Levels.test_quantity_uses_exact_prices_regression` | n/a |
| 47 | Monthly 10-trade cap (IST month of first fill) and 10 concurrent positions are enforced in backtests; None or above 10 is refused (D45, superseding "unset = limitation"); cap selection by fill order is recorded, "best 10" stays a human choice | RB 2392, 2400, 2408, 2414; B12; D42, D45, D46 | `backtest.ExecutionModel`, `apply_portfolio_rules`, `models.ist_month` | `test_research_backtest.Portfolio`; `test_research_execution_policy.IstMonth`, `D45Refusals` | None |
| 48 | Journal: SL locked after trigger; no add-to-position; SL hit and zone invalidation separate; no entries for failed gates | RB 2139, 2140, 2380; R4 | `store.journal_add`, `journal_event` | `test_research_store` | n/a |
| 49 | Scenario regression library through the real pipeline | spec 10.2 spirit; every rule cited per scenario | `nse/research/scenarios.py`, `nse/scenarios/` | `test_research_scenarios` (19 SYNTHETIC scenarios) | None (synthetic) |
| 50 | Rulebook revision: an earlier extraction said the PDF lacks RB 1784, 1786-1803; the owner pack (2026-11-03) reports PDF page 62 contains them (disputed, not re-checked) | RB-VERSION-1 | code cites the Markdown | `test_repo` pins both hashes | Owner decision |
| 51 | An in-progress candle that has reached a fresh zone's PL is not freshness: G1 MANUAL | spec 6.2; D23; RB 264, 683-697 | `MtfSnapshot.incomplete_touches`; `qualification._g1` (`INCOMPLETE_CANDLE_TOUCH`) | `test_research_adversarial.AuditRegressions20261106` | None (synthetic) |
| 52 | Coinciding HTF zone: an excluded-session touch, or a gap after its first test, leaves its DL status unknown (never "untouched") | D15, D30 H1, R6 | `structure._dl_hidden`, `zone_views` | `test_research_adversarial.AuditRegressions20261106` | None (synthetic) |
| 53 | Pending order cancelled when a later point-in-time scan no longer allows the setup; nothing re-evaluated after the fill | RB 2530-2538, 2540-2551; D42 | `backtest.simulate` (`revalidation`), `_from_history`; `store.journal_event` (TRIGGERED) | `test_research_backtest.AuditRegressions20261106`, `test_research_store.JournalAuditRegressions20261106` | None |
| 54 | Expiry in verified sessions; missing, excluded or unclassifiable sessions and incomplete bars fail closed; chosen entry/stop must give 2:1 | RB 82 RF8; D30; D42 | `backtest._sessions`, `plan` | `test_research_backtest.AuditRegressions20261106` | None |
| 55 | One journal order per zone; 10 simultaneous positions; monthly ceiling independent | P-BT-1; RB 2392; D42 | `store.journal_add`, `journal_event`, `_open_positions` | `test_research_store.JournalAuditRegressions20261106`, `Journal.test_monthly_summary_and_ceiling` | n/a |
| 56 | Provenance is a matching file hash, not a hash-shaped string | D31; B7, B11 | `models.source_verified` (universe, corporate actions, instruments); `run_all._evidence_hashes` | `test_research_reports.Universe`, `test_research_data.CorporateActions`, `test_validation_runner.ReferenceEvidence` | Local INFY screenshots re-hashed: 5/5 match (not independent validation) |

## Additional rows (2026-11-08, owner approvals; `DECISION_LOG.md` 1F)

| # | Rule | Source | Implementation | Test | Validation |
|---|---|---|---|---|---|
| 57 | Price inside a TESTED Monthly demand: redraw from the next fresh Monthly demand below; unknown boundary MANUAL; other TFs / supply stay MANUAL | RB 1621; P-LOC-2, P-LOC-3 | `structure.build_curve` (`redrawn_past`); `_g3` evidence `redrawn_past_tested` | `test_research_gates.G3.test_price_inside_a_tested_monthly_demand_redraws_from_the_next_fresh_zone`, `test_redraw_*`; adversarial `CouncilRegressions20261108` | None (synthetic) |
| 58 | Relevant opposing Pine-only zones make G5 / G7 MANUAL; never ignored, never a target | D43; D12; PS 2613; RB 1313, 551-558 | `zone_engine` (Pine-only `invalidated_index`, `test_count`); `structure.pine_only_zones`; `_g5`, `_g7` | `test_research_gates.PineOnlyD43`; adversarial `test_a_d43_restriction_survives_every_export` | None (B10) |
| 59 | Undated errors: bounded by neighbouring rows when possible, otherwise block every scan; later-dated findings never reach earlier scans | D44; P-DQ-1 | `marketdata._bad_date`, `Finding.known_at` | `test_research_lookahead.FutureDataQuality` | None |
| 60 | Backtest configurations above owner limits are refused, not labelled; a backtest needs a calendar | D45; D42 | `ExecutionModel.__post_init__`; `backtest._from_history` | `test_research_execution_policy.D45Refusals`; adversarial `test_dataclasses_replace_cannot_bypass_the_d45_limits` | n/a |
| 61 | Journal monthly ceiling by IST month; closed position frees a slot, not a monthly trade; one order per zone even after CANCELLED / EXPIRED | D42, D46; RB 2392; ED-3 | `store.journal_add`, `journal_event`, `journal_summary` | `test_research_store.JournalIstMonth20261108`, `JournalAuditRegressions20261106` | n/a |
| 62 | Owner execution policy: AT_OPEN, STOP_FIRST + EXCLUDE, slippage 0.05 / 0.10 / 0.20, dated per-instrument costs, predeclared B9 scenarios, nothing selected | B9, B12 | `execution_policy.owner_grid`, `CostSchedule` | `test_research_execution_policy` | None (no Zerodha schedule held) |
| 63 | Rulebook PDF canonical; Markdown citation companion; discrepancies escalated (D40-Q1 escalated, not reconciled) | RB-VERSION-1; D40 | protected hashes; `DECISION_REGISTER.md` open items | `test_repo` | Owner decision |

## Additional rows (2026-11-08, real-data readiness milestone)

| # | Rule | Source | Implementation | Test | Validation |
|---|---|---|---|---|---|
| 64 | Two-window primary/DR sessions: one trading date for expiry, never a fill / exit bar, daily high/low as a bound | D40, D30; NSE/MSD/60677, 61893 | `backtest._sessions`, `_Shortened`, `simulate` | `test_research_execution_policy.D40TwoWindowSessions` | Two independent reviews of the held circulars (hash-verified) |
| 65 | A plan never submitted does not use the zone's one order; a submitted order always does | ED-3 (owner brief); P-BT-1 | `store.journal_orders` (migration 2), `journal_order_submitted`, `_holds_zone` | `test_research_store` `test_ed3_*` | n/a |
| 66 | Per-file EOD coverage; a missing session is never a holiday without the calendar | D31, D30; B17, B18 | `eod_coverage.py` (`eod-coverage`) | `test_research_eod_coverage` | Local files only |
| 67 | Universe: overlapping periods refused; a member without data is reported | B11; survivorship | `universe.load`, `scanner.scan` | `test_research_reports.Universe` | None (no membership file) |
| 68 | Execution realism gaps are disclosed on every backtest result | B12 | `backtest.EXECUTION_REALISM_GAPS` | `test_research_backtest`, `test_research_execution_policy` | n/a |

## Additional rows (2026-11-09, MP1 real NSE data readiness)

| # | Rule | Source | Implementation | Test | Validation |
|---|---|---|---|---|---|
| 69 | One EOD source per trade date: legacy to 2024-07-05, UDiFF from 2024-07-08; only verified schemas; never mixed for one date | D31; B18; NSE/MSD/62424; ED-20 | `nse_bhavcopy.selected_format`, `load_many`, `cross_check`; `acquisition._ingest_one` (`FORMAT_NOT_SELECTED_FOR_DATE`); `manifest_tool.rows_for` | `test_nse_eod_evidence`; `test_research_acquisition.SourceSelection` | 4 official overlap dates identical (`EOD_FORMAT_EVIDENCE.md` §9); no external source |
| 70 | Instrument identity on every bhavcopy input: an unexplained ISIN change, a contradicting record, a reused symbol, an uncovered symbol (with records) and a split history are dated ERRORs (DATA_INSUFFICIENT from that date); otherwise `IDENTITY_UNVERIFIED` without verified records | Owner instrument-identity approval (1F); D44; ED-21 | `instruments.apply_to_input` via `inputs.load` and `scenarios._inputs` | `test_research_instruments.InputIdentityIntegration`, `RenameRegression`, `QaRegressions20261109` | None (B11) |
| 71 | Point-in-time Nifty 100 from a dated baseline and releases; effective date = first session; declared count exceptions only | D1; B11; ED-22 | `membership.convert`, `universe.Universe.balance` | `test_research_membership` | None: no reviewed transcription yet |
| 72 | Coverage distinguishes downloaded, parsed, validated and accepted; coverage counts accepted files only | MP1 brief section 4; ED-24 | `eod_coverage._states` | `test_research_eod_coverage` | Real report 2021-2025: 62 of 1,233 accepted |
| 73 | 20 Jan 2024 is one regular primary-site session; the withdrawn NSE/MSD/59999 plan is not a session | D40 (owner approval kept; factual correction) | `nse/data/calendar/events.csv`, `sources.csv` | `test_nse_calendar_data.Tables.test_d40_twentieth_january_is_one_primary_session_not_the_withdrawn_dr_plan` | Official circulars, hash-verified |

## Additional rows (2026-11-09, owner decisions D47-D51)

| # | Rule | Source | Implementation | Test | Validation |
|---|---|---|---|---|---|
| 74 | Scripted backfill only for the approved window and official URLs; rate-limited, resumable, never overwriting, ingested through quarantine | D47; ED-25 | `.claude/skills/nse-data-engineering/scripts/eod_backfill.py` | acquisition tests (ingest path) | 1,171 real files, 0 quarantined |
| 75 | Calendar 2016-2020 from official circulars; unresolved dates flagged, never inferred | D48; ED-26, ED-31 | `nse/data/calendar/` | `test_nse_calendar_data` (2016-2020 block, Dhanteras test); `test_research_data.UnresolvedDateScope` | text re-check of every date |
| 76 | No universe period is verified without an accepted human review of the exact files; counts other than 100 only when declared from a release | D49; ED-22, ED-27, ED-32 | `membership.review_status`, `load_count_exceptions`, `RENAME` | `test_research_membership.ReviewGate`, `CountExceptions`, `Renames` | checkpoints Mar 2021, Sep 2021, Mar 2022 |
| 77 | Raw OHLC canonical; events stored separately; no adjustment; unparsed terms never guessed | D50; ED-28 | `corporate_actions.from_nse_json` | `test_research_data.CorporateActionStoreD50` | INFY / RELIANCE records |
| 78 | Renames joined only through verified ISIN continuity and dates; otherwise DATA_INSUFFICIENT | D51; ED-29 | `instruments.lineage`, `join_files`, `inputs.load` | `test_research_instruments.LineageD51` | none (B11-I) |
| 79 | Invalid non-EQ rows isolated; EQ and format failures refuse the file | ED-30 | `nse_bhavcopy._parse` | `test_nse_eod_evidence.NonEqRowIsolation` | 112 official files |

## Additional rows (2026-11-09, owner decisions D52-D56)

| # | Rule | Source | Implementation | Test | Validation |
|---|---|---|---|---|---|
| 80 | A PREVCLOSE discontinuity is "explained" only across calendar-excluded sessions with no file, no missing trading day, verified CA coverage and no recorded price action in the gap; never a corporate action; no candle created | D52; ED-33 | `scanner._explained_by_excluded_session` | `test_research_data.ExcludedSessionD52` | 12 excluded-session files held, so real data rarely needs it |
| 81 | An excluded session with no candle inside a zone's span makes G1 MANUAL (D33 touch check impossible); never ACTIONABLE | D52, D33; ED-33 | `scanner._unobserved_excluded_sessions`, `qualification` G1 | `test_research_data.ExcludedSessionD52` | none |
| 82 | Excluded-session files are accepted only in their own role; never candles, never trading-day coverage; UNRESOLVED-date files never accepted | D52, D54; ED-34 | `eod_coverage._states`, overlay H1 / L10 | `test_research_eod_coverage`, `test_research_data` | real report 2016-2025 |
| 83 | Universe periods are verified only through human, row-level, hash-matched decisions; agents never accept | D53; ED-35 | `membership.convert`, `review_template`, `read_review` | `test_research_membership.ReviewGate`, `ReviewCoversExceptions` | 271 rows verified by independent agents; human review pending |
| 84 | Unresolved calendar dates block only ranges that contain them | D54, D58; ED-31, ED-42, ED-44 | `inventory`, `run_all.check_local_data`, `scanner._last_unresolved_date` | `test_research_data.UnresolvedDateScope`, `RealWindow` | 0 unresolved dates after D58; the rule remains for any future one |
| 85 | 2016-2020 official EOD files, strictly verified; exact layout variants only | D55, D58; ED-38, ED-41 | `nse_bhavcopy` (`LEGACY_13_CRLF*`, `archive_layout_ok`, `load_many(keep=)`), `acquisition._header_format` | `test_nse_eod_evidence.LegacyCrlfSchema`, `LegacyShortDateAndNestedMember`; `test_research_acquisition`; `test_research_instruments.FilteredLoadingEquivalence` | 1,242 real files; 2,466 of 2,466 equity sessions accepted after D58 |
| 86 | Official CA records for every historical member; an unrecognised subject is an UNPARSED price event, never skipped; empty responses are not coverage | D56, D50; ED-39 | `collect_corporate_actions.py`, `corporate_actions._part_row`, `load_coverage` | `test_research_data.CorporateActionStoreD50` | 189 symbols, 145 covered, 2,064 events |
| 87 | An ISIN change counts as evidenced only through an official price-scale CA record dated at the change; otherwise never joined | D56, D51; ED-37 | `instrument_records.csv` (build script in the MP1 report), `instruments.isin_consistency` | `test_research_instruments` | 27 of 30 changes evidenced; the identity check over every member observation leaves 3 dated findings (the unevidenced changes) |

## Additional rows (2026-11-13, GTF P1 journal hardening)

| # | Rule | Source | Implementation | Test | Validation |
|---|---|---|---|---|---|
| 88 | Monthly cap and open-position cap are independent and enforced in one write transaction; IST month; a closed position frees only a slot | D42, D46; RB 2392; ED-46, ED-51 | `store._Immediate`, `journal_event`, `_refuse_new_trigger`, `_open_positions` | `test_research_store.P1JournalIntegrity`, `Journal`, `JournalIstMonth20261108` | Synthetic journal only |
| 89 | One order per zone; cancel before submission releases it; submission, stop-out and close do not; the check and the insert commit together | ED-3; P-BT-1; ED-51 | `journal_add`, `_holds_zone`, `journal_order_submitted` | `test_research_store` `test_ed3_*`, `test_two_connections_cannot_both_reserve_one_zone`, `test_stop_and_close_do_not_release_a_submitted_zone` | Synthetic journal only |
| 90 | A print is not a second order; unfilled quantity is not a fill; charges exist only when entered or scheduled | RB 2140; ED-51; B12 | `journal_execution`, `journal_record_charges`, `charges.quote` | `P1JournalIntegrity.test_partial_prints_*`, `test_absent_charges_*`, `test_research_execution_policy.ItemisedCharges` | No statutory tariff is stored |
