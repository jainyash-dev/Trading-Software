# User journey assessment

A screen that renders is not a journey. Each journey below is what the owner can do on 2026-11-10 in the working tree. CLI-only steps are named as CLI. They are not counted as the application.

## Journey A - Discover a stock

**Status: partial. The scanner path exists. A certified universe scan does not.**

| Step | State |
|---|---|
| Open the shell and see health | Works in code. Frontend tests stub it. This audit did not open a browser |
| See `data_ready` false and the dataset id | Implemented. The flag is hardcoded false |
| See the Nifty 100 list and that it is unverified | The universe route can say so. Human review is empty (B11-R) |
| Submit a MIT scan and poll a job | Implemented. Verified by a platform test on a fixture CSV, not on the archive |
| Read why a symbol failed or needs review | Stored reasons can render. A real Nifty 100 result was not produced in this audit |
| WIT | Blocked, and the platform test confirmed `BLOCKED` |

**Missing or unverified:** a browser session; a scan of the supported universe; a visible explanation of the ED-44 history cut; job state on the overview.

**Dependencies:** local EOD, calendar, and, for a full-universe claim, B11-R.

**To make it reliable:** run one real MIT scan from the UI with `UNIVERSE_UNVERIFIED` on the header, and do not call that run certified.

## Journey B - Analyse a stock

**Status: not reliable. The chart is a fixture.**

| Step | State |
|---|---|
| Open Stock Analysis | The route renders and says the module is not in the current release |
| See Monthly, Weekly, and Daily candles from the scanner's series | The candle API exists (`GET /api/v1/candles` → `inputs.load` and `mtf.replay`). The page does not call it |
| See canonical zones and overlay freshness | Not on the chart. Five hardcoded rectangles and a fixture G1 `PASS` appear only after "Show fixture specimens" |
| Read G0-G8 beside the chart | The scanner table can show stored gates. The analysis page does not |
| Deterministic qualification | The engine does this. The chart does not recompute it, because the chart does not ask the engine |

**What works elsewhere:** the scanner's last-12-bars HTML table, labelled "Not a live price."

**Dependencies:** a stored `scan_key`, the candle route, and UX-005.

**To make it reliable:** mount `CandleChart` on the candle API and draw zones from the bundle. Remove the fixture `PASS` from any path that could be read as a result.

## Journey C - Plan a trade

**Status: not possible in the application. Possible only as a library call.**

| Step | State |
|---|---|
| Start from a stored candidate | `risk_plan_for_candidate` can, inside `pipeline.run`. No plan is stored |
| See entry, stop, and target ranges | `levels.py` and G7. The Plans page shows unavailable |
| Pick a buffer | The engine refuses to pick one. The UI has no control |
| See quantity and the risk stage | `risk.py`. No settings persistence for stage |
| See the 10/10 caps from the journal | `portfolio_at` if a research DB is opened. The client must not send the count as the source of truth |
| Approve the plan | No route |

**Dependencies:** TP-009, TP-010, the research journal, and a candidate id.

**To make it reliable:** one plan record that copies the candidate and writes nothing to a broker. Quantity stays empty until the owner selects a buffer.

## Journey D - Execute manually

**Status: CLI only. The application does not record an order.**

| Step | State |
|---|---|
| The app does not send an order | Verified. No order route. `authorises_order` is false |
| Record "I submitted this in Kite" | `journal_order_submitted` from the CLI |
| Record the fill | `TRIGGERED` from the CLI |
| See planned versus actual | Columns exist. No view |

**Missing:** the API and the screen. A fill must call the research journal so the monthly cap stays one counter (PR-011).

## Journey E - Monitor a position

**Status: blocked. There is no position screen and no market-hours price.**

| Step | State |
|---|---|
| See open positions | `portfolio_at` in the CLI. The Portfolio page is a placeholder |
| Update during market hours | No quote source. OQ-1 is open. EX-007 and EX-008 are blocked |
| Record an exit | CLI event kinds. No UI |
| Alert on stop or target during the session | Not implemented. Scan-diff alerts are a different feature |

**Dependencies:** an owner-approved quote that is not stored as the research price, plus the journal read model.

**To make it reliable:** do not start an intraday scanner. A monitor, if built, reads open journal rows and a labelled quote.

## Journey F - Review trading performance

**Status: not possible as a product journey.**

| Step | State |
|---|---|
| Compare plan and fill | No screen |
| Rule compliance | Notes exist. No review workflow |
| Win rate of the owner's journal | `journal_summary` computes one and says it is not a strategy result. The UI must not promote it |
| Strategy performance | Backtest metrics exist in the CLI and are labelled `NOT_PERFORMANCE_EVIDENCE`. The Analytics page shows the words and `Unavailable` |

**Dependencies:** journeys C and D, then a manifest if a backtest number is shown.

## Journey G - Improve the methodology

**Status: not reliable. The tools exist and the dataset is not certified.**

| Step | State |
|---|---|
| Point-in-time scan history | `scan_history` and lookahead tests passed |
| Backtest with explicit costs and slippage | Implemented. No Zerodha schedule is embedded. Zero cost is allowed |
| Walk-forward and sensitivity | Commands exist. They write no run manifest (TD-4) |
| A result the owner can trust as evidence the method works | Not available. R4 is open. B11-R, CAL-2, corporate-action gaps, and missing TradingView references all still apply |
| External zone check | Not started (B8, B10, B17) |

**To make it reliable:** finish the data blockers that change who is in the universe and which history is visible, attach manifests to every quantitative command, and keep the not-performance label on every number.

## Journey verdict

| Journey | Can the owner complete it in the app today? |
|---|---|
| A Discover | Only as an uncertified, and in this audit unverified-in-browser, scan |
| B Analyse | No |
| C Plan | No |
| D Execute manually | No. The app also does not execute for them, which is correct |
| E Monitor | No |
| F Review | No |
| G Improve the method | No |

The initial product workflow is not usable end to end.
