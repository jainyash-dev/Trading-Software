# Scenario library

Each `*.json` in this folder is one scenario: candle data, an as-of time, a trade type, a
calendar and the outcome the rules require, with rule references and an explanation of
why. `nse/research/scenarios.py` runs every scenario through the REAL pipeline
(`marketdata.from_csv` or `from_bhavcopy` -> `scanner.scan` -> G0-G8) and compares; it has
no gate, freshness or eligibility logic of its own.

```
python3 -m nse.research.cli scenarios-validate                     # schema + data provenance
python3 -m nse.research.cli scenarios-run                          # report in nse/output/scenarios/
python3 -m nse.research.cli scenarios-run --only mit_fresh_7of7_actionable --out /tmp/x
python3 -m nse.scenarios.generate --check                          # data/ matches its generator
```

`scenarios-run` exits 1 if any scenario is FAIL or INVALID, 2 on a usage error. UNAVAILABLE
(inputs absent) is reported in the summary and the verdict (`PASSED_WITH_UNAVAILABLE`) and
is never counted as a pass.

## Data kinds

| data_kind | What it is | Where |
|---|---|---|
| `SYNTHETIC` | **Invented prices.** Not market data, not TradingView parity, never external validation. Software regression evidence only. | `data/*.csv`, each listed with its sha256 in `data/MANIFEST.json`; written by `generate.py` |
| `HISTORICAL_REAL` | Official NSE legacy bhavcopies held locally (git-ignored, D31). Named by repository path and sha256; an absent or different file makes the scenario UNAVAILABLE. | `nse/data/eod/raw/` |
| `OWNER_CHART` | A chart case the product owner transcribed. None is shipped and none may be invented. | start from `templates/owner_chart.template.json` |

**Every CSV in `data/` is SYNTHETIC.** The runner refuses (INVALID) a SYNTHETIC scenario whose
CSV is not in `data/MANIFEST.json` or whose sha256 differs, and an OWNER_CHART scenario that
points at a SYNTHETIC file. `generate.py` copies the long SYNTHETIC history of
`tests/_research.py` (`long_mit_candles`, `extend`) because `nse/` never imports `tests/`;
`data/MANIFEST.json` records each file's recipe.

Calendars: `WEEKDAYS_SYNTHETIC` (every weekday trades; allowed only with SYNTHETIC data),
`NSE` (`nse/data/calendar`; UNAVAILABLE if it does not load), `NONE` (CALENDAR_UNVALIDATED,
D28 / P-CAL-1). SYNTHETIC CSVs are loaded with price adjustment NONE (invented prices have no
corporate actions); OWNER_CHART CSVs with UNKNOWN.

## Schema (unknown keys are rejected at every level)

Top level, all required: `id` (equals the file name), `title`, `description`, `rule_refs`
(non-empty; forms `RB 1896`, `RB 683-697`, `PS 2613`, `R5`, `D3`, `P-CAL-1`, `spec 7.4`,
`spec 8 G0`, `audit M4b`), `data_kind`, `data` (symbol -> CSV path relative to this folder,
or for HISTORICAL_REAL `{"bhavcopy": [{"path", "sha256"}], "series", "manifest"}`), `as_of`
(`YYYY-MM-DD` = the 15:30 close, or an ISO datetime), `trade_type` (`MIT`, `WIT-75`,
`WIT-125`), `calendar`, `risk_per_trade` (number or null), `expected`, `explanation`.
Optional: `source_note` (required for HISTORICAL_REAL and OWNER_CHART).

`expected` (`symbol_status` required; `symbol` required only with more than one symbol):

| Key | Asserts |
|---|---|
| `symbol_status` | scanner symbol status (EVALUATED, NO_FRESH_EXECUTION_ZONE, DATA_INSUFFICIENT, BLOCKED, NOT_IN_UNIVERSE_AT_AS_OF) |
| `symbol_reason_contains` | each text occurs in a symbol reason |
| `candidate_count` | number of candidates |
| `candidates` | each `{match, status?, gates?, manual_review_contains?}` matches exactly one candidate (match on `zone_id`, `created_time`, `proximal`, `distal`, `pattern`); `gates` may be a subset of G0-G8 |
| `fresh_zone_count`, `fresh_zone_ids_absent`, `fresh_zones_absent`, `fresh_zones_present` | the fresh-zone report (`fresh_zones_present` may require a `zone_level_contains` text) |
| `blocked_zone_overlay_status` | `{match: {tf, zone_id}, overlay_status, disposition?}` on the scanner's blocked-zone audit |
| `overlay_zone_states` | `{match, overlay_status}` on the zone states of `mtf_freshness.replay` called as the scanner calls it (tells TESTED from INVALIDATED for zones the engine itself dropped) |
| `same_decisions_as` | another scenario id: every decision field of the symbol (status, reasons, price, candidates, blocked and fresh zones, top-down, series, limitations) is identical |

## Seed library (all SYNTHETIC)

| Scenario | Rule | Expected |
|---|---|---|
| `mit_fresh_7of7_actionable` | RB 661, 829; D3; R1-R3; spec 8 | ACTIONABLE (manual checks pending), every gate PASS |
| `mit_tested_after_pl_touch` | RB 683-697; D3 | overlay TESTED; no candidate, not in the fresh-zone report |
| `mit_invalidated_close_below_dl` | R4; D24 | overlay INVALIDATED; no candidate |
| `mit_wick_below_dl_without_close` | R4; D3 | overlay TESTED (not INVALIDATED); no candidate |
| `mit_missing_session_after_formation` | D27; D34 | blocked UNKNOWN_DATA_GAP; symbol DATA_INSUFFICIENT |
| `mit_no_calendar_never_actionable` | P-CAL-1; D28 | G0 MANUAL; MANUAL_REVIEW |
| `wit75_blocked`, `wit125_blocked` | audit M4b | BLOCKED; no output |
| `mit_legout_window_open` | RB 728; audit M1 | no candidate; fresh-zone row says LEGOUT_WINDOW_OPEN |
| `mit_legout_follow_through_completes` | RB 728 | one candidate, G1 and G2 PASS |
| `mit_mid_session_as_of_ignores_incomplete_candle` | D23 | no candidate at 12:00 |
| `mit_prefix_invariance_later_candles` | spec 9; D23 | identical decisions to the reference |
| `mit_data_quality_error_before_as_of` | spec 8 G0 | DATA_INSUFFICIENT (OHLC_INCONSISTENT) |
| `mit_data_quality_error_after_as_of_is_invisible` | spec 9 | identical decisions to the reference |
| `mit_aggressive_zone_above_monthly_demand` | R3; D15 | G6 MANUAL (Aggressive); MANUAL_REVIEW |
| `mit_weekly_supply_within_10pct` | spec 7.4 | G5 MANUAL; MANUAL_REVIEW |
| `mit_no_risk_per_trade_needs_review` | RB 2162 | G8 MANUAL (EC7); MANUAL_REVIEW |
| `mit_half_yearly_history_missing` | spec 7.4; RB 1748 | G5 DATA_INSUFFICIENT; DATA_INSUFFICIENT |
| `mit_hoc_strong_up_rejected` | R5; RB 1901 | G3 MANUAL, G4 FAIL; REJECTED |

Limits: every seed scenario is SYNTHETIC, so a fully passing library proves the software
reproduces these rule readings on invented candles and nothing more. No HISTORICAL_REAL or
OWNER_CHART scenario ships: an expectation on real data has to come from the rules and the
owner's reading of the chart, not from the scanner's output. WIT expectations are BLOCKED
only, because no intraday output exists (audit M4b).
