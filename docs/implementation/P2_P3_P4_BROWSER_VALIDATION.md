# P2-P4 Browser Validation

**Date:** 2026-11-17. **Browser:** Google Chrome (headless) via `puppeteer-core` (existing dev dependency).
**Server:** the real platform launcher (`platform/gtf_platform/__main__.py`, started from `platform/`) on `127.0.0.1:8899` serving the built `platform/web/dist`, with
`GTF_FIXTURE=1`, a CSV dataset and SQLite files in a temporary directory. **Data:** FIXTURE only
(`setup_fixture_env.py`: the synthetic long-MIT series from `tests/_research.py` plus a random walk). Not
NSE market data; nothing here is external validation or a performance claim.

Evidence folder: `docs/implementation/evidence/p2-p4-browser/` (23 screenshots, `results.json`,
`results_supplement.json`, `results_fr42.json`, and the driver scripts). Assertions are on what the page
actually rendered (DOM text, `data-*` attributes, canvas pixel changes).

## Runs

| Run | Result |
|---|---|
| 1 | Chart did not render: the evidence panel showed **STALE Candles** ("dataset_id does not match the local files"). Cause: my fixture setup computed the dataset id with different settings from the server. The page behaved correctly (no chart drawn from mismatched data). Fixture rebound to the server's dataset id. |
| 2 | 22/22 steps passed, but two real defects were visible: Scanner showed "Unavailable" statuses on a canonical envelope (FR-3.3 key defect) and Opportunities showed TF "Unavailable" (ingest key defect). Both fixed (see P3 status). |
| 3 (final, after review remediation) | 22/22 steps pass from a clean fixture state. |
| Supplemental | Drawings and watchlist rename (pass); FR-4.2 zoom/pan/crosshair (pass). An earlier FR-4.2 attempt hovered outside the viewport and wrongly suggested a legend defect; an A/B rebuild proved the original code correct and the speculative change was reverted. |

Console errors in the final run (7) are the expected HTTP 401 (pre-bootstrap), 404, 409 and 422 responses of
the deliberate negative cases.

## Journeys and screenshots (final run)

| # | Workflow | Observed |
|---|---|---|
| 01 | Analysis with no stored scan | Empty state cites FR-4.5 and OD-P2-1; no standalone chart |
| 02/03/04 | Stored-bundle chart D / W / M | Canvas drawn; fixture banners; Volume PRESENT on D, W and M; evidence: Candles INCOMPLETE (series truncated, 2 missing sessions not filled), Stored bundle / Qualification / Explanation AVAILABLE, Data certification FIXTURE; 6 stored zones listed |
| 05 | Symbol not in the stored scan | Stored bundle MISSING, Qualification UNAVAILABLE |
| 06 | Unknown scan key | Stored bundle MISSING, error shown, Data certification UNCERTIFIED |
| 07 | Wrong dataset_id / wrong session as_of | Candles + bundle STALE; wrong session: bundle STALE, qualification UNAVAILABLE |
| 08 | Create draft from stored candidate | DRAFT; geometry VALID; combinations with entry, stop, target, qty, risk/share, loss at stop, R:R (MANUAL_REVIEW status per combination) |
| 09 | Approve with unanswered checklist | Refused: "Every checklist item must be answered" |
| 10 | Approve with answered checklist | "No order was sent"; journal entry 1; journal PLANNED; sync IN_SYNC; cancel redirected to the Journal; `authorises_order false` |
| 11 | Plan overlay | Three dashed lines `PLAN <id> entry/stop/target (journal PLANNED)` at 160.44 / 154.92 / 188.56 |
| 12 | Journal "Record CANCELLED" | Journal accepted the event; message reports linked plan sync |
| 13 | Plan after journal cancel | Plan CANCELLED, journal CANCELLED, sync IN_SYNC, "Cancelled from the journal"; counts Approved 0 / Cancelled 1 |
| 14 | Chart after cancel | 0 plan lines; note "CANCELLED. Inactive plans are not drawn." |
| 15 | Second draft: submit, reject | AWAITING_OWNER; reject without reason refused; REJECTED with reason; expiry note "No automatic plan expiry runs"; later-scan line "No later stored scan covers this symbol" |
| 16 | Scanner stored scan | Outcome panel QUALIFIED, "Manual checks are still pending. Not an order." |
| 17 | Real pipeline scan (WALK + missing NOPE) | as_of beyond data refused 422 DATA_INSUFFICIENT; valid scan job VALIDATING -> RUNNING -> SUCCEEDED_COMPLETE; outcome NOTHING_QUALIFIED with EVIDENCE_MISSING (NO_INPUT_FILE, EXECUTION_SERIES_TRUNCATED) and ZONES_BLOCKED 8 |
| 18 | Opportunities ingest | Row SYN, canonical status "Actionable, manual checks pending", quality FIXTURE, workflow BLOCKED (fixture rows start BLOCKED by design), no CERTIFIED text |
| 19 | Watchlist create | Persists after reload; Eligibility "Unavailable" |
| 20 | Scan history | Both scans listed (fixture table) |
| 21 | Zoom / pan / crosshair | Zoom-in, pan after zoom, and Fit each change chart pixels; legend `2019-11-21 O 258.68 H 261.78 L 255.58 C 258.68 V 130392` |
| 22 | Drawing persistence | Horizontal mark saved as `PLATFORM_DB`, present after reload, deleted, absent after reload |
| 23 | Watchlist rename | Rename persists after reload |

## Not covered in the browser

Empty or loading states were only observed transiently; disconnected/API-down state (covered by vitest);
plan update after approval with recorded fills; later-scan CHANGED display (API-tested); opportunity workflow
transitions; scan form submit (vitest); instrument search; scheduler. The scan in BR-17 was posted through
the API from the browser session.

## Fixture limitation

The weekday-only fixture lacks NSE Saturday special sessions (2020-02-01, 2024-01-20), so the daily chart
truncates at 2020-01-31 (`SERIES_TRUNCATED`, Candles INCOMPLETE). This is the required fail-closed
behaviour. It means the 2024 zone and plan levels lie below the visible candles in BR-11.
