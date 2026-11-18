"""Readiness of each capability, kept apart from test results.

Each capability carries independent states (spec: never one green tick):
  implemented, unit_tested, integration_tested, reference_validated, externally_validated,
  deferred, blocked, requires_human_decision
plus the evidence for each claim. "unit_tested" and "integration_tested" name the test
modules; the validation runner (nse/validation/run_all.py) marks a claim UNCONFIRMED
when those modules did not pass in the same run. reference_validated and
externally_validated stay False unless a recorded comparison exists; synthetic tests
never set them.
"""

CAPABILITIES = (
    {"id": "zone_engine", "component": "nse/zone-engine/zone_engine.py",
     "implemented": True, "unit_tested": ["test_zone_engine"], "integration_tested": ["test_research_integration", "test_research_e2e"],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": ["audit M1, L5-L9, rows 13 and 31"],
     "limits": ["no TradingView zone references recorded (B10)", "Pine parity not claimed (spec 10)"]},
    {"id": "mtf_overlay", "component": "nse/mtf-freshness/mtf_freshness.py",
     "implemented": True, "unit_tested": ["test_mtf_freshness"],
     "integration_tested": ["test_nse_replay", "test_research_integration"],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": [],
     "limits": ["HTF candle boundaries not compared with TradingView (B8, D23)"]},
    {"id": "intraday_75_125", "component": "nse/mtf-freshness (75m/125m zones), WIT execution",
     "implemented": False, "unit_tested": [], "integration_tested": [],
     "reference_validated": False, "externally_validated": False, "deferred": True, "blocked": True,
     "requires_human_decision": ["approve the 75/125-minute session and gap design (audit M4b)"],
     "limits": ["no intraday data source approved (B6, D32); WIT results are always BLOCKED"]},
    {"id": "calendar", "component": "nse/calendar/nse_calendar.py, nse/data/calendar/",
     "implemented": True, "unit_tested": ["test_nse_calendar", "test_nse_calendar_data"], "integration_tested": [],
     "reference_validated": "PARTIAL: 2016-2025 reconciles with all 2,466 official trading-day EOD files (D47, "
                            "D55); the four 2016-2019 Dhanteras dates are confirmed regular equity sessions "
                            "(D58, CAL-2 option A); no UNRESOLVED row", "externally_validated": False,
     "deferred": False, "blocked": False,
     "requires_human_decision": ["the 20 Jan 2024 hours are inferred from NSE/CMTR/41180 (D40 trail otherwise closed, "
                                 "2026-11-09)"],
     "limits": ["normal-hours review 2019-2025 not done", "no TradingView spot checks (B17)"]},
    {"id": "eod_loader", "component": "nse/eod/nse_bhavcopy.py",
     "implemented": True, "unit_tested": ["test_nse_bhavcopy", "test_nse_eod_evidence"],
     "integration_tested": ["test_nse_replay"],
     "reference_validated": "PARTIAL: 2,466 official equity-session archives 2016-2025 accepted "
                            "(2,098 legacy, 368 UDiFF); 12 excluded-session archives held separately (D30, D52); "
                            "legacy and UDiFF agree exactly on 4 official overlap dates (ED-20); 210 non-EQ rows "
                            "isolated (ED-30)", "externally_validated": False,
     "deferred": False, "blocked": False,
     "requires_human_decision": ["a new approval before any download outside 2016-2025"],
     "limits": ["UDiFF verified on 5 official samples (2 schema versions); a new header is refused",
                "unadjusted prices (B7)"]},
    {"id": "ohlc_reference_comparison", "component": "nse/eod/nse_reference.py",
     "implemented": True, "unit_tested": ["test_nse_replay"], "integration_tested": [],
     "reference_validated": "PARTIAL: INFY Q1 2022 daily rows match a Yahoo Finance reference (not independent)",
     "externally_validated": False, "deferred": False, "blocked": False, "requires_human_decision": [],
     "limits": ["zone comparison not implemented: matching rules to be set against real references"]},
    {"id": "trend_sma_clock", "component": "nse/research/trend.py",
     "implemented": True, "unit_tested": ["test_research_gates"], "integration_tested": ["test_research_integration", "test_research_e2e"],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": [],
     "limits": ["SMA values not compared with TradingView (B8)"]},
    {"id": "location_curve", "component": "nse/research/structure.py",
     "implemented": True, "unit_tested": ["test_research_gates"], "integration_tested": ["test_research_integration", "test_research_e2e"],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": [],
     "limits": ["P-LOC-2 is USER_APPROVED (decision log section 1F, 2026-11-08): a tested Monthly demand redraws from the next fresh Monthly demand below; unknown boundaries stay MANUAL. Not reference-validated and not externally validated.",
                "ambiguities the approval does not cover stay MANUAL REVIEW"]},
    {"id": "htf_conflict", "component": "nse/research/structure.py",
     "implemented": True, "unit_tested": ["test_research_gates"], "integration_tested": ["test_research_integration", "test_research_e2e"],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": [], "limits": ["'coming from' analysis is a manual check"]},
    {"id": "coinciding", "component": "nse/research/structure.py",
     "implemented": True, "unit_tested": ["test_research_gates"], "integration_tested": ["test_research_integration", "test_research_e2e"],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": ["Aggressive entry criteria, including achievement (RB 1843-1847, 1854-1855)"],
     "limits": ["a non-overlapping execution zone wholly above HTF demand is Aggressive and stays MANUAL pending its Rulebook conditions"]},
    {"id": "trade_levels", "component": "nse/research/levels.py",
     "implemented": True, "unit_tested": ["test_research_gates"], "integration_tested": ["test_research_integration", "test_research_e2e"],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": ["B9 buffer selection (deterministic backtests only)"],
     "limits": ["volatility SL adjustment not applied numerically (RB 2108-2110)"]},
    {"id": "qualification_mit", "component": "nse/research/qualification.py",
     "implemented": True, "unit_tested": ["test_research_gates", "test_research_adversarial"],
     "integration_tested": ["test_research_integration", "test_research_e2e"],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": [], "limits": ["no status means validated or approved"]},
    {"id": "scanner_and_reports", "component": "nse/research/scanner.py, reports.py, cli.py",
     "implemented": True, "unit_tested": ["test_research_reports"],
     "integration_tested": ["test_research_integration", "test_research_lookahead"],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": [], "limits": []},
    {"id": "universe", "component": "nse/research/universe.py",
     "implemented": True, "unit_tested": ["test_research_reports"], "integration_tested": [],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": True,
     "requires_human_decision": ["B11-R: row-level human review of nse/data/universe/nifty100_review.csv (D49, D53)"],
     "limits": ["nifty100_universe.csv (2020-12-31..2025-12-31, 185 periods) is UNVERIFIED until each row is "
                "accepted by a human reviewer: every scan is UNIVERSE_UNVERIFIED",
                "D59 provisional membership research starts 2020-12-31; earlier as-of dates are labelled, not certified, and 2016-2020 has no baseline (B11-P)"]},
    {"id": "corporate_actions", "component": "nse/research/corporate_actions.py (interface; no adjustment)",
     "implemented": "PARTIAL: records file and G0 MANUAL for an action inside the history; no adjustment method (D50)",
     "unit_tested": ["test_research_data"], "integration_tested": ["test_research_data"],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": True,
     "requires_human_decision": ["optional: an independent source to test the NSE API's completeness (R-10)"],
     "limits": ["D50: raw prices canonical, never adjusted", "D56: official NSE records for 189 historical members, "
                "2016-2025; coverage only where the response was non-empty (145 symbols, ED-39)",
                "the API's completeness is not documented by NSE (R-10): the PREVCLOSE discontinuity check stays active"]},
    {"id": "data_inventory", "component": "nse/research/inventory.py; cli inventory",
     "implemented": True, "unit_tested": ["test_research_data"], "integration_tested": ["test_research_data"],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": ["approval to download the EOD range it reports as missing (D31)"],
     "limits": ["legacy up to 2024-07-05, UDiFF from 2024-07-08 (ED-20)"]},
    {"id": "trend_reference_comparison", "component": "nse/research/refcheck.py compare_trend; nse_reference Q/HY/Y",
     "implemented": True, "unit_tested": ["test_research_data"], "integration_tested": ["test_research_data"],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": True,
     "requires_human_decision": ["approve the validation set (REFERENCE_VALIDATION_PLAN.md)"],
     "limits": ["no TradingView SMA or HTF OHLC reference recorded"]},
    {"id": "eod_manifest_tool", "component": "nse/research/manifest_tool.py; cli manifest-rows",
     "implemented": True, "unit_tested": ["test_research_data"], "integration_tested": [],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": ["download approval (D31)"], "limits": ["official .csv.zip archives only"]},
    {"id": "zone_reference_comparison", "component": "nse/research/refcheck.py",
     "implemented": True, "unit_tested": ["test_research_data"], "integration_tested": [],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": True,
     "requires_human_decision": ["matching key P-REF-1 (D41)"],
     "limits": ["no TradingView zone reference recorded (B10): nothing has been compared"]},
    {"id": "backtesting", "component": "nse/research/backtest.py; cli backtest",
     "implemented": "PARTIAL: signals, fills, exits, costs, R metrics, splits; every execution assumption is a "
                    "required user input",
     "unit_tested": ["test_research_backtest"], "integration_tested": ["test_research_backtest"],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": True,
     "requires_human_decision": ["execution model: buffer choice (B9), fills, same bar, expiry, costs (B12)",
                                 "point-in-time universe (B11)"],
     "limits": ["EOD 2016-2025 held, but the universe is unverified (B11-R) and the execution model undecided",
                "no performance figure has been produced"]},
    {"id": 'acquisition', "component": 'nse/research/acquisition.py; cli acquire-plan, acquire-ingest, daily-update, acquire-coverage',
     "implemented": True, "unit_tested": ['test_research_acquisition'], "integration_tested": ['test_research_acquisition'],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": ['approval to download the missing sessions (D31)'],
     "limits": ['local inbox only, no network code (D31)',
                'a verified file in the format not selected for its date is quarantined (ED-20)']},
    {"id": 'instruments', "component": 'nse/research/instruments.py; cli instruments-check; --instruments on scan, '
                                      'scan-history, backtest, replay-decision (ED-21)',
     "implemented": True, "unit_tested": ['test_research_instruments'], "integration_tested": [],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": True,
     "requires_human_decision": ['confirm the record semantics in the module docstring'],
     "limits": ['nse/data/universe/instrument_records.csv: NSE EQUITY_L / symbolchange, bhavcopy first sessions and '
                '27 ISIN changes evidenced by official corporate actions (ED-37); BAJFINANCE 2016-09-09, GRASIM '
                '2016-10-07 and YESBANK 2020-03-16 unevidenced (ISIN_CHANGED_WITHOUT_RECORD)', 'renames joined only through verified ISIN continuity (D51, ED-29); '
                'ISIN changes never joined']},
    {"id": 'risk_position_sizing', "component": 'nse/research/risk.py; cli risk-plan',
     "implemented": True, "unit_tested": ['test_research_risk'], "integration_tested": [],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": ['buffer choice inside the printed ranges (B9)'],
     "limits": ['separate from G0-G8: never changes a status', 'quantities are ranges over the printed buffer tiers']},
    {"id": 'pre_entry_score_14', "component": 'nse/research/confluence.py (spec 5.3 display)',
     "implemented": 'PARTIAL: core evaluated; EMA20, crossover, gap provisional; sector and RSI/Stoch not evaluated', "unit_tested": ['test_research_confluence'], "integration_tested": ['test_research_confluence'],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": ['trending-timeframe and gap-meaningfulness judgements are manual'],
     "limits": ['information only: no gate reads it', 'EMA values not compared with TradingView (B8)']},
    {"id": 'scenario_library', "component": 'nse/research/scenarios.py, nse/scenarios/',
     "implemented": True, "unit_tested": ['test_research_scenarios'], "integration_tested": ['test_research_scenarios'],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": ['owner chart scenarios to record'],
     "limits": ['seed scenarios are SYNTHETIC: software evidence only']},
    {"id": 'decision_replay_and_dashboard', "component": 'nse/research/decision_replay.py, dashboard.py; cli replay-decision, dashboard',
     "implemented": True, "unit_tested": ['test_research_dashboard'], "integration_tested": ['test_research_dashboard'],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": [],
     "limits": ['display only; charts not compared with TradingView', 'static HTML, no server']},
    {"id": 'research_assistant_alerts_reports', "component": 'nse/research/explain.py, alerts.py, narrative.py; cli explain, alerts, report',
     "implemented": True, "unit_tested": ['test_research_explain', 'test_research_alerts'], "integration_tested": ['test_research_explain', 'test_research_alerts'],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": ['external alert delivery (email, webhook) needs owner configuration and approval'],
     "limits": ['explains recorded evidence only; no LLM call; cannot change a status', 'notifications: stdout and local JSONL only']},
    {"id": 'research_store_journal', "component": 'nse/research/store.py; cli store-*, journal-*',
     "implemented": True, "unit_tested": ['test_research_store'], "integration_tested": ['test_research_store'],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": [],
     "limits": ['optional local SQLite; JSON/CSV reports remain the record', 'journal records owner decisions; places no order']},
    {"id": 'health_check', "component": 'nse/research/health.py; cli health',
     "implemented": True, "unit_tested": ['test_research_health'], "integration_tested": [],
     "reference_validated": False, "externally_validated": False, "deferred": False, "blocked": False,
     "requires_human_decision": [],
     "limits": ['checks the checkout can run; is not validation']},
)

STATE_KEYS = ("implemented", "unit_tested", "integration_tested", "reference_validated",
              "externally_validated", "deferred", "blocked", "requires_human_decision")


def report(passed_modules=None):
    """Readiness rows. passed_modules: test modules that passed in this run (None: not run).
    A tested claim whose modules did not all pass is marked UNCONFIRMED."""
    rows = []
    for c in CAPABILITIES:
        row = dict(c)
        for key in ("unit_tested", "integration_tested"):
            mods = c[key]
            if not mods:
                row[key + "_state"] = "NO"
            elif passed_modules is None:
                row[key + "_state"] = "CLAIMED (not run in this report)"
            elif all(x in passed_modules for x in mods):
                row[key + "_state"] = "CONFIRMED"
            else:
                row[key + "_state"] = "UNCONFIRMED: " + ", ".join(x for x in mods if x not in passed_modules)
        rows.append(row)
    return rows
