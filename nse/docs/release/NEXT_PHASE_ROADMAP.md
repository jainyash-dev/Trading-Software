# Next phase roadmap

> Dated snapshot (2026-11-02). Current status: `docs/MILESTONE_STATUS.md`, `nse/docs/DECISION_LOG.md` (section 1F, 2026-11-08 approvals) and `docs/ARCHITECTURE.md`.

In dependency order. Each step names the smallest action and the command that verifies it.

1. **Owner decisions:** RB-VERSION-1 (which Rulebook revision), P-LOC-2, P-RISK-1. Record
   in `DECISION_REGISTER.md`; add a scenario per decision (`nse-scenario-library` skill).
2. **Real history for MIT:** download the missing legacy sessions for 2021-2025 (list:
   `cli acquire-plan --start 2021-01-01 --end 2025-12-31 --calendar nse/data/calendar`),
   ingest with `cli acquire-ingest`, then `run_all --acceptance --require-window 2021-01-01 2025-12-31`.
   One UDiFF sample to close B18 before 2024-07 data can be used.
3. **Universe and corporate actions:** Nifty 100 constituent history (B11) as a universe CSV;
   corporate-action records (B7) and an adjustment convention. Re-scan with `--universe`.
4. **External validation, targeted:** record TradingView W/M/Q OHLC, SMA-50 and zone
   references for 3-5 agreed symbols (`nse/data/reference/*.template.csv`), run `refcheck`,
   and add the matching HISTORICAL_REAL scenarios.
5. **Backtest:** owner execution model (B9 buffer, B12 fills, costs from official
   schedules, monthly cap choice); run `backtest-walk-forward` on point-in-time scans with
   folds fixed before looking at results.

Later: paper-trading loop using the journal; sector evaluation if the owner defines it
(D6); WIT after M4b and an intraday source (B6); external alert delivery after approval.
