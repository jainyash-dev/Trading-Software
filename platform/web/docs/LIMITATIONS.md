# Known limitations

P10 (2026-11-17) changed presentation only: no route, contract or rule changed. Strategy Analytics and Shadow / Paper are capability pages (no backend). The AI Research Assistant is the deterministic explainer; no language model is connected. Jobs and Monitoring shows only the latest and active job because the API has no job list. Risk Overview reads `/portfolio` and `/settings` and computes nothing. Trade-plan actions are shown from the backend's `allowed_transitions`.

Updated 2026-11-15 for GTF P2. Scan, candle, plan, journal, portfolio, backtest, report export, backup, and deterministic explain routes exist. They do not place orders. `DATA_READY` stays false. WIT stays blocked. Paper trading and the language-model assistant are not built.

- No Tauri shell, by D57. Cloud hosting is not built.
- Drawings persist in the platform SQLite database (FR-4.3) via GET/POST/PATCH/DELETE `/api/v1/drawings`. They are not eligibility inputs. Older docs that said `MEMORY_ONLY` are obsolete.
- Weekly and monthly candle volume is the sum of the constituent daily sessions that built the HTF candle (`volume_sessions` gives the count; 2026-11-17, P2-VOL-WM). It is null with `HTF_VOLUME_INCOMPLETE` when any constituent session has no stated volume, and null with `HTF_VOLUME_SESSION_MISMATCH` if the session count disagrees with the HTF candle. Daily volume uses CSV `volume` or bhavcopy `TOTTRDQTY` / `traded_qty`. Missing volume stays null; it is never coerced to zero.
- Plan lines (FR-4.9) are drawn only for an APPROVED plan whose journal entry is confirmed PLANNED or OPEN, from the recorded selected levels. Cancelled, rejected, expired, closed, draft, and journal-unconfirmed plans are listed but not drawn.
- Plan GET routes (`/api/v1/plans`, `/plans/{id}`, `/plans/{id}/history`) run the journal mirror inside a platform write transaction and hold the process `db_lock` while reading the journal once per linked plan. Writes are idempotent mirrors of journal state only; cost grows with the number of linked plans. A plan is bound to its journal entry by symbol, zone_id, and the journal idempotency record `approve:<plan_id>`; on an old journal without that table only symbol and zone are checked.
- No automatic plan expiry runs. A plan shows EXPIRED only when the owner records EXPIRED on its journal entry; the plan mirrors journal CANCELLED/EXPIRED (P4-IR-04, recoverable repair-on-read, not an atomic cross-file commit).
- Chart `data_quality.certified` is always false on the candle route. The route does not run the P0 certification matrix. Fixtures are `FIXTURE_NOT_MARKET_DATA`; other local sources are labelled `EXPLORATORY_ONLY_NOT_CERTIFIED`.
- Stock Analysis opens from a stored scan (FR-4.5). Standalone chart inspection without a scan is reserved as owner decision OD-P2-1 and is not implemented.
- Zone overlays render stored candidates, `fresh_zones`, and `blocked_zones`. The chart does not recompute zones or qualification.
- Health may stay `WARNING` until a later route reads a non-fixture scan. `WARNING` is not a claim that research is ready.
- `Secure` is off on `http://127.0.0.1` so the cookie is stored by Safari. Turn `GTF_COOKIE_SECURE=1` only for an HTTPS origin.
