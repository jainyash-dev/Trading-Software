# Executive summary

Audit date: 2026-11-10. Repository: `/Users/yash/day-trader-skill`. Branch `main`, HEAD `9e302df1a81c2b13696d8fab61f05d377481be2e` (`latest code`, 2026-11-03), tracking `origin/main`. The working tree was already dirty before this audit: 79 tracked paths differ from HEAD (about 10,093 insertions and 2,437 deletions) and the desktop application under `platform/`, the `docs/` tree, and the 2016-2025 data work are untracked. Nothing was staged. This audit did not commit, reset, or discard that work.

This is an assessment. It does not implement the roadmap.

## What the product is intended to become

The GTF Trading Intelligence Platform is a local, single-user research and decision-support application for NSE cash equities. It is supposed to apply the owner's GTF demand-and-supply methodology, show why a symbol qualifies, fails, or needs review, support a manual Zerodha Kite order that the owner types, watch open positions, and keep a journal and a reproducible research record. It is not an order router, and it is not allowed to claim profitability. The product definition is [PRODUCT_REQUIREMENTS.md](../product/PRODUCT_REQUIREMENTS.md). Release gates R1-R5 in [MASTER_PROMPT_ROADMAP.md](../product/MASTER_PROMPT_ROADMAP.md) are all still open.

## What currently exists

Two different systems share this repository.

1. **The research engine under `nse/`** is a real MIT pipeline: bhavcopy loading, a trading calendar, instrument identity, a Nifty 100 membership file, corporate-action records, zone detection, an MTF freshness overlay, gates G0-G8, a scanner, reports, a SQLite journal with the 10/10 caps, and a backtest that labels its arithmetic as not performance evidence. WIT is blocked before qualification. `authorises_order` stays false.
2. **The desktop shell under `platform/`** is untracked work that the milestone file still describes as not started. It is a loopback FastAPI process plus a React 19 / Vite application. Overview, Market Scanner, and Watchlists call that API. Eleven other screens are labelled unavailable and do not complete a workflow. There is no trade-plan API, no journal API, no fills API, no backtest API, no assistant API, and no broker client.

The legacy `trader-*` folders are the US day-trading skill pack this repository was forked from. They are not the GTF product. This audit did not treat them as implementation of the platform.

## What is genuinely operational

A developer on this Mac can run the research CLI against local files, and can run the local API and the three Work screens. On 2026-11-10 this audit re-ran 782 research tests in 19 groups with 0 failures, 24 platform API tests with 0 failures, and 40 frontend tests with 0 failures. The frontend production build succeeded. Architecture checks reported 50 modules and 0 violations. Docs health reported 0 findings before these audit files were added.

Those passes are software tests. The archive hash check (`local_data`) also passed: 2,478 archives, calendar years 2016-2025, and no reconciliation month flagged as an issue. That check still leaves the four unresolved Dhanteras dates as information, and it is not a certified Nifty 100 scan. The frontend tests stub `fetch`. The platform scan test uses a synthetic CSV labelled as a fixture. No browser session was run.

The API health field `data_ready` is fixed at false (`platform/gtf_platform/app.py`). The coverage report also forces `data_ready.ready` false (`nse/research/eod_coverage.py`). That matches the written verdict in [REAL_DATA_READINESS.md](../../nse/docs/REAL_DATA_READINESS.md): **PARTIALLY_READY. DATA_READY is not claimed.**

## What remains incomplete

The trader cannot, in the application, open a real chart of canonical zones, approve a plan, record a Kite fill, monitor an open position during the session, or read a performance report that is tied to a manifest. Those steps exist only as CLI or library behaviour (journal, backtest, explain) or as placeholder screens.

The research results that do exist cannot be treated as a verified historical study:

- Every Nifty 100 period in the converted file is unverified. Human review of `nse/data/universe/nifty100_review.csv` has not been done (B11-R). Scans carry `UNIVERSE_UNVERIFIED`.
- Four Dhanteras dates stay `UNRESOLVED` (CAL-2). A scan drops history through the last unresolved date before `as_of` (`nse/research/scanner.py`, ED-44). Ten-year `eod_ready` stays false.
- Corporate-action coverage is missing for symbols whose official response was empty. Prices are never adjusted.
- Three ISIN changes are not joined (BAJFINANCE, GRASIM, YESBANK).
- No TradingView zone or SMA reference has been recorded (B8, B10, B17).

## The most important blockers

| Blocker | Why it matters |
|---|---|
| B11-R | No certified point-in-time universe. A full-universe label is refused. |
| CAL-2 | Monthly-to-yearly context before 2019-10-28 is not used. `eod_ready` is false for the full window. |
| B7 / R-10 | Empty corporate-action responses are not coverage. Affected symbols stay G0 `MANUAL`. |
| B11-I | Three histories split on an unevidenced ISIN change. |
| B8, B10, B17 | Zone, freshness, and calendar behaviour have no external reference check. |
| No product journal or plan API | The desktop app cannot complete the trading workflow the engine already knows how to store. |
| No live price source | Market-hours position monitoring is in the product definition and has no feed. |

## The biggest risks

- **False completeness.** [MILESTONE_STATUS.md](../MILESTONE_STATUS.md) says product implementation has not started. [platform/web/docs/LIMITATIONS.md](../../platform/web/docs/LIMITATIONS.md) says scan and candle routes are not implemented. [VALIDATION_SCORECARD.md](../VALIDATION_SCORECARD.md) still says 62 of 1,233 sessions are held. [nse/data/calendar/README.md](../../nse/data/calendar/README.md) says both that 2016-2025 reconciles and that reconciliation covers Q1 2022 only. A reader who trusts the older sentence will misjudge the product.
- **False confidence in a scan.** The engine can emit `ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING` on synthetic data. On the stored real-data runs described in the milestone notes, candidates were manual or rejected. The UI will display a stored `PASS` if one is in the envelope. Nothing in the UI turns that into a buy, and nothing should.
- **Two databases, one cap.** The research journal is the live 10/10 counter. The platform database does not yet store plans or fills. A later screen that counts trades in the platform database would violate D42. The current code does not do that. The risk is the next prompt, not the current schema.
- **Concurrency of the monthly cap.** `journal_event` now counts and inserts a `TRIGGERED` row inside `BEGIN IMMEDIATE` (`nse/research/store.py`). [DECISIONS_AND_OPEN_QUESTIONS.md](../product/DECISIONS_AND_OPEN_QUESTIONS.md) still describes an earlier probe in which two connections both committed an 11th trade. This audit found no two-connection test and did not repeat the probe.
- **Scan cost.** Every full load re-parses the archive (TD-17). A Nifty 100 scan is a long local job. The UI can poll it. That does not make a full-universe, certified scan available.
- **Session bootstrap has no password.** Any local page that passes the host, origin, and `X-GTF-Request` checks can obtain a cookie. That matches the single-user loopback design. It is not multi-user authentication.

## Recommended direction

Do not add an assistant, a paper-trading book, or a broker client next. Do not describe the three Work screens as a finished product.

The useful sequence is:

1. Keep `DATA_READY` unclaimed until the owner finishes B11-R and either classifies CAL-2 or excludes those dates from the claimed window.
2. Make the scanner's limitations visible on every real run (universe, calendar cut, corporate-action coverage, identity splits). The API already has most of those fields. The chart and the plan do not.
3. Connect Stock Analysis to the existing candle route and to a stored decision bundle, still without recomputing eligibility in the browser.
4. Add plan and journal screens that call the existing research journal, with one cap counter.
5. Only after a manifest-backed real run exists, put backtest numbers on a screen. Until gate R4, those numbers stay labelled as not performance evidence.

## Distance to the intended release

The research engine for MIT is far ahead of the desktop product. The desktop product covers the front of the workflow (health, a scan job, watchlists) and stops. None of journeys B through G are reliable in the application. Release gates R1 through R5 are open. The initial product workflow is not usable end to end.

Counts and the counting method are in [10_FINAL_READINESS_SCORECARD.md](10_FINAL_READINESS_SCORECARD.md).
