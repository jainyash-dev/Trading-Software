# Browser test report

## Tooling

Cursor's built-in browser. User agent: `Cursor/3.22.12 Chrome/148.0.7778.280 Electron/42.10.0`.

There is no Playwright suite in the repository. These journeys were driven in that browser against the Vite dev server. They are not a substitute for the pytest suite, and the pytest suite is not a substitute for them.

## Lab

| Item | Value |
|---|---|
| UI | `http://127.0.0.1:5173` |
| API | `http://127.0.0.1:8765` |
| Allowed browser origin | `GTF_PUBLIC_ORIGINS=http://127.0.0.1:5173` |
| Platform database | `/tmp/gtf-p02/platform.sqlite` |
| Research journal | `/tmp/gtf-p02/research.sqlite` |
| Candles | `/tmp/gtf-p02/csv/FIX.csv`, fixture label `FIXTURE` |
| Owner journal | Not used |

The first page load showed "API unavailable" because the API rejected origin `http://127.0.0.1:5173`. After the API was restarted with that origin allowed, Overview connected. A later API restart dropped the in-memory session; a reload bootstrapped a new cookie. No OTP, password, or broker token was entered.

Screenshot of the daily fixture chart: `/var/folders/6r/tqmc5gfn7yx3m00p_t69dm7h0000gn/T/cursor/screenshots/tmp/gtf-p02/browser-analysis-daily.png`.

## Journey A  -  Discovery

| Step | Result |
|---|---|
| Overview connected | API connected. Session Authenticated. |
| `data_ready` | False. Text: "data_ready is false. DATA_READY is not claimed." Warnings included `DATA_READY_NOT_CLAIMED`, `UNIVERSE_UNVERIFIED`, `CORPORATE_ACTION_COVERAGE_INCOMPLETE`, `IDENTITY_JOINS_ARE_NOT_PERFORMED_HERE`. |
| Research database before any journal write | Health said "not reachable" because the lab research file did not exist yet. |
| Fixture MIT scan | Dataset `75a41bfc0511558bfb091b47ab2ad25556393ba4426fc37e5109d1200ecf569f`, as of `2024-06-18`. |
| Job | `job-4c4e8a612f51f95a`. HTTP 202, then `SUCCEEDED_COMPLETE`, completeness `COMPLETE`, progress 1 of 1. |
| Stored scan | `scan-8bec0a5c5d7566eb`. Hidden until "Show fixture scans", then labelled `FIXTURE_NOT_MARKET_DATA`. |
| Manifest | `/tmp/gtf-p02/reports/scan-8bec0a5c5d7566eb/run_manifest.json` (10,536 bytes). `git_head` `9e302df1a81c2b13696d8fab61f05d377481be2e`, `dirty: true`. |
| Symbol row | FIX, symbol status `NO_FRESH_EXECUTION_ZONE`. The badge text is "Unknown status: NO_FRESH_EXECUTION_ZONE" because that code is not in the candidate-status list. The reason text under it is the engine reason. |

## Journey B  -  Stock Analysis

Opened from the scanner. URL carried `scan=scan-8bec0a5c5d7566eb`, `symbol=FIX`, `as_of=2024-06-18T15:30:00`, the dataset id, and `fixtures=1`.

| Check | Result |
|---|---|
| Daily candles | HTTP 200, 11 bars, `2024-06-03` open 100 close 101 through `2024-06-18` open 111 close 112. `meta.fixture` true, label `FIXTURE_NOT_MARKET_DATA`. |
| Chart | Seven canvases. Screenshot shows rising green candles, last close label 112.00, and the fixture warning above the plot. |
| Weekly | Button `W` reported pressed. The candle route returned 2 bars (`2024-06-07`, `2024-06-14`). A separate weekly screenshot was not taken. |
| Monthly | HTTP 200, 0 bars. The page shows "No candles at this as-of" and does not fill the gap. |
| Empty page | `#/analysis` with no symbol: "No stored symbol. Open a symbol from a stored scan." |
| Mismatch | `dataset_id=deadbeef` and `scan-missing`: "dataset_id does not match the local files", completeness unavailable, explanation "Scan was not found". The previous FIX qualification was not left on screen. |
| Explanation | "FIX symbol status NO_FRESH_EXECUTION_ZONE: no fresh demand zone on D passed the MTF overlay" and "no candidate was evaluated for FIX." |

## Journey C  -  Trade planning

A real `scanner.scan` of the repository's synthetic long-MIT fixture was stored as fixture scan `scan-synthetic` (symbol SYN, zone `demand-1250-1251`, status `ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING`). It is not NSE market data. Settings saved capital 100000, risk percent 1, stage LEARNING. Scheduler checkbox stayed off.

| Step | Result |
|---|---|
| Rejected candidate | `scan-rejected`, same zone, status rewritten to `REJECTED` in that stored envelope only. Create draft showed "A REJECTED candidate cannot be planned". |
| Valid draft | Eight buffers. First: entry 160.44, stop 154.92, target 188.56, quantity 181, buffer status `MANUAL_REVIEW`. Draft quantity fact stayed Unavailable. `authorises_order` false. Candidate status unchanged. |
| Approve | "Approved in the research journal. No order was sent." Plan state `APPROVED`, quantity 181. Research journal entry 1, event `PLANNED` only. `recorded_at` stored as naive `2026-11-10T12:20:42`. |
| Second approve of the same plan | Still one `journal_entries` row and one `PLANNED` event. |

A second order on the same zone was not clicked in the browser. `test_plan_approval_journal_portfolio_export_and_backup` asserts HTTP 409 `ONE_ORDER_PER_ZONE` for that case.

## Journey D  -  Manual execution

| Step | Result |
|---|---|
| Journal before submission | Entry 1 SYN, planned 160.44 / 154.92 / 188.56 / 181. Order "not submitted". |
| Record submission | "Submission recorded. No order was sent." Order ref `KITE-LAB-1`, note "Owner submitted in Kite". |
| Record fill | `TRIGGERED` at `2026-11-10T12:22:12`, price 160.44. Message: "This app did not place the order." |
| Record close | `CLOSED_MANUAL` at price 170. Message: "The monthly allowance was not restored." |

No Zerodha page was opened and no credential was stored.

## Journey E  -  Portfolio

Before the close, the page read: trades this month 1 of 10, open positions 1 of 10, valuation `UNAVAILABLE`, sector `UNAVAILABLE`, drawdown `UNAVAILABLE`, zone SYN `demand-1250-1251`.

After the close: trades this month 1 of 10, open positions 0 of 10. The zone line says the order is now `CLOSED` and keeps the allowance. Valuation remains `UNAVAILABLE`.

The first portfolio request after the journal clock fix was required. Before that fix the route returned HTTP 500 (`portfolio_at` mixed naive and aware times). The successful reading above is from after the fix and a session reload.

## Journey F  -  Export and backup

| Step | Result |
|---|---|
| Export `scan-8bec0a5c5d7566eb` `candidates.csv` | HTTP 200. Body length 282. The on-screen `<pre>` equalled the API body. The stored file is 282 bytes. |
| Missing scan export | HTTP 404, "That report was not written for this scan". |
| Backup | "Backup copied to `/tmp/gtf-p02/backups`. Files: platform.sqlite, research.sqlite. Live databases were not replaced." |
| Integrity of both backup files | `PRAGMA integrity_check` = `ok`. |
| Restore-check | `/tmp/gtf-p02/restore-checks/20261110T065806Z-6ad56037`. Both restored files `ok`. Restored journal entries: 1. |
| Live hashes | Unchanged across the backup. Platform `d405fbc2df562fce249630e4ce77beebfb8bfd930b23db6660d919028115b515`. Research `e7a7f9dcdea13342a90e402d514aaeab1e8f9ee27f693e5c82ba02cc6c891793`. Live events: `PLANNED`, `TRIGGERED`, `CLOSED_MANUAL`. |

## Not claimed as browser evidence

- The five scheduler cases (saved true, saved false, missing, invalid, restart) were not each clicked. The settings control was saved as false and the API returned `scheduler_enabled: false`. The case matrix is in `platform/tests/test_platform_api.py`, which passed inside the 37-test run.
- A partial scan was not created in the browser. The product test covers completeness `PARTIAL`.
- Fees were not entered. The journal schema has nowhere to put them.
- No Playwright trace file was produced.
