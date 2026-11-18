# Architecture and integration report

The production eligibility path is unchanged: `pipeline.run` calls `scanner.scan`, which calls `scan_symbol`, which calls `qualification.evaluate_symbol`. Platform routes do not import `qualification`.

New application behaviour sits in `platform/gtf_platform/integration/desk.py`. It calls `store.journal_add`, `store.journal_order_submitted`, `store.journal_event`, `store.portfolio_at`, `risk.plan_trade`, `explain.why`, and `backtest.run`. Those calls do not create a second monthly counter. `authorises_order` stays false.

A scan job now also writes the existing report files and a run manifest under the platform data directory. Export reads those files. It does not format a second CSV.

Drawings posted by Stock Analysis use the existing drawings table. They are not passed to `inputs.load`.

The scheduler reads a saved `scheduler_enabled` setting when that row exists. Otherwise it keeps the process flag. It still does not download.

`DATA_READY` on the overview is still false, with an explicit reason.

Known integration limits:

- Plan approval imports the stored scan dict into the research SQLite file before `journal_add`. If that dict is not a full scan record, approval fails closed.
- A fill expiry count runs only when a calendar is available. The API passes it. A missing calendar does not invent a session count.
- Valuation on the portfolio screen is `UNAVAILABLE`. No quote was added.
- The backtest screen uses owner-typed cost and slippage for that request. It is not a dated broker schedule.
