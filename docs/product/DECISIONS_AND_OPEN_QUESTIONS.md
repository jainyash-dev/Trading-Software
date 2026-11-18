# Decisions and open questions

> Product Prompt 00. Owner decisions already in force are listed so later prompts do not
> re-open them. Architecture recommendations are engineering choices for the desktop
> product. They are not ED numbers: `nse/docs/ENGINEERING_DECISIONS.md` is in active use
> by the data and research workstreams, and this prompt does not take the next id.

## 1. Owner decisions already in force

These come from the product brief that opened Prompt 00 and from the decision register.
Later prompts implement them. They are not questions.

| Topic | Decision | Where it already lives |
|---|---|---|
| User, OS, shell | One owner, macOS, local desktop | This product brief |
| Market | NSE cash equities, positional and swing, Monthly / Weekly / Daily | This product brief and the MIT role map |
| Charts | Native interactive charts inside the app: zoom, pan, crosshair, drawings | This product brief. Library choice is AR-4 |
| Execution | Manual Kite / Zerodha. No broker integration. No automated orders | B12, D10, D17 |
| Storage | Local-first. Cloud not required for core use | This product brief |
| AI | Explanations only. Eligibility stays deterministic | P1, council invariant 4 |
| Eligibility | Fresh unbreached demand only, via `eligible_after_overlay`. Tested, invalidated, and unknown freshness do not qualify | Council invariants, A10 |
| Status | `MANUAL_REVIEW`, `BLOCKED`, and `DATA_INSUFFICIENT` never become actionable. The best status still has manual checks pending | `models.derive_status`, `models.CHECKLIST` |
| History | Point-in-time. Later evidence does not rewrite an earlier scan | D44 |
| Prices | Raw unadjusted OHLC is canonical. Unknown corporate-action evidence does not become PASS | D50 |
| Caps | 10 trades per IST month and 10 simultaneous positions, independent | D42, D45, D46 |
| One order per zone | A plan never submitted can release the zone. A submitted order does not | ED-3, owner brief |
| WIT | Blocked until intraday data and a session design exist | M4b |
| Buffers | Printed tiers. The software does not pick one | B9 |
| Risk stage | Above the stage maximum fails. Below the minimum, or no stage, is manual. No automatic promotion | P-RISK-1 |
| Pine-only supply | Relevant opposing Pine-only zones make G5 / G7 manual and are not targets | D43 |
| Calendar holes | Unresolved dates stay unresolved | D54, CAL-2 |
| Universe review | Humans accept membership rows. Agents do not write `ACCEPTED` | D53, B11-R |

The supported scan universe for the first release is the Nifty 100 membership model
already in the repository. The product brief says cash equities and a supported universe.
It does not require every listed equity before the first release. An ad-hoc list remains
available and stays `UNIVERSE_UNVERIFIED` when the file says so.

## 2. Architecture recommendations

These are level-C engineering choices. Prompt 03 and Prompt 04 proceed with them.
An owner override before Prompt 04 starts replaces the named choice. Silence means
the recommendation stands.

| Id | Recommendation | Why | Rejected alternative |
|---|---|---|---|
| AR-1 | Modular monolith. New code in `platform/`. `nse/` does not import it | A5 and the network ban stay true | Microservices, or FastAPI inside `nse/` |
| AR-2 | Local API on `127.0.0.1` with an HttpOnly session cookie, `SameSite=Strict`, origin and host checks, and `X-GTF-Request` (D57) | A page on another origin must not drive the engine | A bearer token in the page, and a port with no session |
| AR-3 | React and TypeScript in the browser, built with Vite (D57) | One local origin now, and the same UI can be hosted later | Tauri, Electron, and a native AppKit shell |
| AR-4 | Lightweight Charts 5 as the candle renderer. Zones, drawings, and plan lines are our primitives. Show the library attribution | Candles and scales are solved. Eligibility must not live in the chart. Advanced Charts is proprietary and the vendor does not offer it for personal use (checked 2026-11-09) | KLineChart, unless the spike fails. A from-scratch canvas. Advanced Charts |
| AR-5 | Two SQLite files: the existing research store, and a platform store for jobs, drawings, fills, and paper | Prompt 02 can keep editing `store.py` | New tables in `store.py` during that work |
| AR-6 | Official accepted bhavcopies remain the research price. A second provider is a comparison dataset. Scheduled fetch of public NSE files is off until the owner enables it, and it runs outside `nse/` | D50 and the surprise-network concern. The backfills already approved stay approved | Using a vendor close when the official file is missing |
| AR-7 | Paper and shadow fills use private cap counters and `book: SIMULATED` | D42 counts actual fills. A paper book that consumed the live cap would block the owner's real month | Sharing `journal_orders` |
| AR-8 | A parse cache, if built, is keyed by archive hash and loader version and is disposable | TD-17. Raw files stay canonical | A warehouse that becomes the price |
| AR-9 | No quality ranking in the scanner UI | The envelope already says row order is not a ranking | A composite score |
| AR-10 | Fixtures set `fixture: true` and use non-market labels | The UI must not look like an NSE result | Realistic fake INFY charts |
| AR-11 | Platform dependencies live in `platform/pyproject.toml`. Root `dependencies` stay empty | ED-17 and A5 | Adding FastAPI to the research project |
| AR-12 | One new root directory, `platform`, with the desktop app inside it | `tests/test_repo.py` pins the root list. One addition is one test edit | Separate `apps/` and `platform/` roots |
| AR-13 | Valuation is the latest accepted daily close, with the session date printed | The initial product has no tick feed | A live quote |
| AR-14 | Sector and unevaluated breadth render as `UNAVAILABLE` | D6. A descriptive advance/decline count is allowed only when the screen names the universe and the session | A sector gate |
| AR-15 | The desktop stable zone reference is symbol, timeframe, side, `start_time`, and `created_time`. Defining prices and pattern are compared after that match. Dataset id, bar count, and the series start are provenance only. The engine id is unchanged | A new session changes `dataset_id`. A prepend changes the index id and keeps the creation times. A new distal can keep the same index id | The Prompt 00 fingerprint (first candle and bar count) and a dataset id inside the zone key |
| AR-16 | One desktop instance. A second launch exits and does not read the API token. An optional focus socket returns no secret | A second shell with the token is a second journal writer | Attaching a second shell by reading the token file |
| AR-17 | A live trade consumes the monthly cap and an open slot only when `journal_event` commits `TRIGGERED`. A platform pending or refused row does not. The API serializes those calls on one connection. Two connections can still both commit, as a 2026-11-09 probe showed (11 triggers) | D42 is implemented as that event. A second `TRIGGERED` on one entry is refused. The count and the insert are not one transaction | Counting the first platform `ENTRY` row, or counting `PENDING` toward the cap |

AR-4 licence note: Lightweight Charts is Apache-2.0. The project README also requires
TradingView attribution and a user-visible link. KLineChart is Apache-2.0. Confirm the
SPDX text from the pinned version before Prompt 14.

D57 (2026-11-09, owner): the product is a local-first web application. AR-2 and AR-3
above replace the same-day recommendations that named a per-launch bearer token and a
Tauri shell. Those earlier rows are withdrawn. The review log in section 8 stays as
history.

## 3. Decisions that still need the owner

Only items that block a specific later prompt. Established decisions are not repeated
as questions.

| Id | Question | Blocks | What proceeds meanwhile |
|---|---|---|---|
| OQ-1 | Which third-party market-data provider, if any, is approved, and under what rights and budget? | Any non-NSE adapter that is used as more than a sketched interface | Official files, the inbox, and comparison-only design |
| OQ-2 | Which assistant provider may be called, and which fields may leave the machine? | Turning the assistant on | The disabled assistant, the rest of the app |
| OQ-3 | Should a scheduled job download the public bhavcopy by itself, or only ingest an inbox? | The default of the fetch switch | AR-6 default is off. The owner can enable it later without a methodology change. This is recorded so the default is visible, not because the architecture is stuck |

OQ-3 is a default, not a blocker. It is listed because unattended download is a
privacy behaviour the owner may want to flip deliberately.

## 4. Owner actions already decided, not new questions

| Id | Action still required | Effect until it happens |
|---|---|---|
| B11-R | Fill `nse/data/universe/nifty100_review.csv` as the human reviewer | Scans stay `UNIVERSE_UNVERIFIED`. R1 stays open for a verified-universe claim |
| CAL-2 | Done 2026-11-10 (D58): the owner confirmed the four Dhanteras dates as regular equity sessions | None: no date is `UNRESOLVED`, and 2016-2025 is `eod_ready` |
| B8, B10, B17 | Record TradingView references when ready | No external zone or SMA parity claim |
| B12 cost file | Supply a dated Zerodha schedule if a backtest should use those fees | The engine refuses to invent the figures. Slippage grid can still be studied |
| M4b | Decide WIT only when intraday data exists | WIT remains blocked |

## 5. Deferred scope

Intraday and WIT, futures and options, broker APIs, automated orders, multi-user
accounts, hosted service, mobile, other exchanges, sector rules, tick valuation,
notarised distribution beyond this Mac, and any paid data vendor.

## 6. Assumptions

| Id | Assumption | If it is wrong |
|---|---|---|
| AS-1 | The first supported universe is Nifty 100, not every EQ symbol | A broader universe needs membership evidence and a new prompt |
| AS-2 | English UI, IST labels, INR prices | A localisation prompt |
| AS-3 | One main window is enough | A multi-window prompt |
| AS-4 | `readiness.py` still contains an older sentence that P-LOC-2 is open. The decision register shows P-LOC-2 approved on 2026-11-08 | Do not re-open P-LOC-2 from that sentence. The data workstream can refresh the string when it next edits the file |
| AS-5 | Performance numbers in the requirements are proposals | Prompt 03 and Prompt 06 replace them with measurements |

## 7. Where recommendations are written down

They are not copied into `nse/docs/ENGINEERING_DECISIONS.md` by Prompt 00. If the
integration lead later wants an ED id, the next free number is taken in that
workstream's session, with a pointer back to this file, so two sessions cannot both
claim the same id.

## 8. Independent review (2026-11-09)

Read-only reviews, incorporated into the contracts above. No reviewer edited a file.

| Review | Result used |
|---|---|
| Contrarian review `55019981-3dd3-4249-970e-902f42ba7797` | Zone links carry a fingerprint and an unresolved state. Charts from a `scan_key` do not recompute. Fixture runs stay out of the last scan. The plan action follows stored status. A missing corporate-action file stays a visible limitation. G0 is not redefined |
| Security review `f166351d-97d1-4003-af88-f4fde6b07149` | Token delivery, idempotency, wake interrupts a stalled job, and fill recovery before the next fill |
| Quant review `5c3dec1d-6402-408b-840f-7f5e0f7f5476` | The research journal is the only live cap. Paper code cannot write it. Analytics require a manifest. Off-grid backtests are experimental. Walk-forward quotes use the pooled result |
| Data review `25677d46-1df2-475c-b975-c6d3158e4e9b` | Research validation is none. Quarantine no longer cites a whole-file rule the loader has passed. Empty corporate-action responses are not coverage |
| Trading-rule review `28ca41a3-b50b-449a-b9ce-29399856e0a9` | No methodology change required |
| Backend review `d3bd9f8c-72de-4fef-abd7-7decc7a1d645` | One scan call, `pipeline.run`. Database ownership split by migration files. Screens render engine fields |
| Frontend review `5f7dbcbe-7bf9-4cf2-836e-331b2004dbf8` | Status colours, fixture symbols, non-draggable zones, and primitive autoscaling |

The quant reviewer also ran `python3 -m nse.validation.run_all --group backtest --group lookahead --group risk_instruments` and reported 220 tests, 0 failures. That run is theirs. It is not a Prompt 00 engine change.

## 9. Prompt 00.1 contract correction

The fingerprint in the first AR-15 is withdrawn. The replacement is the AR-15 row above.
The audit, the probe outputs, and the readiness verdict are in
[PROMPT_00_1_CONTRACT_AUDIT.md](PROMPT_00_1_CONTRACT_AUDIT.md). No new owner decision
was opened. The non-atomic monthly cap is an engine defect for Prompt 02, not a new
cap rule.
