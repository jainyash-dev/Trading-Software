# P2-P4 Acceptance Matrix

**Updated:** 2026-11-17 (programme execution; supersedes the Batch 0 baseline version of this file)
**HEAD:** `69858d07ccb016b74bc1d518b66b9948656ad6cf` (unchanged; no git mutation)
**Final phase stamps:** none. `ACCEPTED` is reserved for the owner.

Requirement IDs, wording, and acceptance criteria are the canonical ones from
`docs/product/PRODUCT_REQUIREMENTS.md` (FR-*) and `docs/product-discovery/02_MASTER_CAPABILITY_MAP.md`
(OI-*, TP-*, UX-*). Residual rows (`P2-VOL-WM`, `P4-IR-04`, ...) are the Batch 0 engineering residuals,
kept so no November 16 gap is lost. No new requirement ID was created.

Status values follow the programme definitions: `IMPLEMENTED` (code exists), `TESTED` (automated tests
pass), `VALIDATED` (browser/API evidence), `INDEPENDENT_REVIEWED` (independent review done, no unresolved
Critical/Important), `DEFERRED_OWNER`, `BLOCKED`. Every in-scope row below was in scope of the
independent review (initial FAIL, remediated, re-review PASS), so rows that reached `VALIDATED` are
reported as `INDEPENDENT_REVIEWED`.

Evidence keys:
- **API** = `platform/tests/test_platform_api.py` (18 PASS), **PLAN** = `platform/tests/test_trade_planning.py` (20 PASS),
  **OPP** = `platform/tests/test_opportunity.py` (9 PASS), **PLAT** = all `platform/tests` (100 PASS),
  **VT** = web vitest (16 files, 89 PASS).
- **BR-nn** = screenshot `docs/implementation/evidence/p2-p4-browser/nn-*.png`, real headless Chrome against the
  running platform on FIXTURE data. See `P2_P3_P4_BROWSER_VALIDATION.md`.
- **IR-n** = independent review finding n (`P2_P3_P4_INDEPENDENT_REVIEW.md`).

---

## A. P2 - Stock analysis and charting (18 rows)

| ID | Original requirement | Acceptance criteria | Implementation | Tests | Validation | Limitations | Dependency | Independent review | Final status |
|---|---|---|---|---|---|---|---|---|---|
| FR-4.1 | Interactive M/W/D candlesticks from the same validated series the scanner used | M/W/D candles; as_of truncation; dataset bind | `integration/candles.py` via `mtf.replay`; Analysis page | API candle tests | BR-02/03/04 (D/W/M render, fixture banner) | Fixture daily series truncates at NSE special sessions it lacks (fail-closed, disclosed) | Local EOD or fixture | Reviewed: aggregation sound | INDEPENDENT_REVIEWED |
| FR-4.2 | Zoom, pan, crosshair | Interactive chart gestures | Lightweight Charts in `CandleChart.tsx` (unchanged) | none new | BR-21: zoom-in, pan-after-zoom, Fit change pixels; crosshair legend shows OHLC+V | None found | None | Reviewed scope | INDEPENDENT_REVIEWED |
| FR-4.3 | Drawing tools persist per symbol and timeframe | H-line, trend, rect, text; round trip | Drawings API + UI (unchanged) | API drawings tests | BR-22: save mark, persists after reload (`PLATFORM_DB`), delete persists | Browser check covered horizontal mark only | None | Reviewed scope | INDEPENDENT_REVIEWED |
| FR-4.4 | Engine zones, MTF state, opposing supply are overlays from a bundle or scan; chart does not recompute | Overlays from stored payload only | `zonesFromStored` (unchanged); no frontend zone engine | VT `zones.test.ts` | BR-02 engine zones incl. W/M supply listed from stored bundle | None | Stored scan | No hidden recompute found | INDEPENDENT_REVIEWED |
| FR-4.5 | Chart from a stored scan renders that run's bundle; new replay is a new run | Scan-linked open; empty without scan | Unchanged; bundle by `scan_key` | API, VT | BR-01 (empty state cites OD-P2-1), BR-02 | Standalone mode is OD-P2-1 (deferred) | None | Sound | INDEPENDENT_REVIEWED |
| FR-4.6 | Fresh/tested/invalidated/unknown; unknown never drawn fresh | Overlay status mapping | `zones.ts` (unchanged) | VT `zones.test.ts` | BR-02 FRESH labels from stored overlay status | None | None | Sound | INDEPENDENT_REVIEWED |
| FR-4.7 | G0-G8, data warnings, evidence references beside the chart | Qualification panel + explanation + limitations | New `chart/evidence.ts` evidence-status panel (AVAILABLE/MISSING/INCOMPLETE/STALE/UNAVAILABLE/FAILED/FIXTURE/UNCERTIFIED) | VT `evidence.test.ts` (10) | BR-02, 05, 06, 07 | Evidence states are display classifications, not a canonical status vocabulary | Stored envelope | IR-2 fixed (re-review PASS) | INDEPENDENT_REVIEWED |
| FR-4.8 | User drawings excluded from every eligibility input | Drawings never enter gates | Unchanged | Architecture boundary tests | Arch PASS | None | None | Sound | INDEPENDENT_REVIEWED |
| FR-4.9 | Trade-plan entry, stop, and target lines are a third overlay, labelled as a plan | Plan lines when a plan is present | New `chart/plans.ts`; `CandleChart` price lines labelled `PLAN <id> <kind>`; Analysis fetches `/plans?symbol&scan_key` | VT `plans.test.ts` (7); PLAN `test_ir04_*` | BR-11 (3 labelled lines), BR-14 (cancelled plan not drawn) | Drawn only for APPROVED plans with journal PLANNED/OPEN confirmed IN_SYNC; drafts have no selected levels so no lines | Plan + journal | IR-1, IR-4 fixed | INDEPENDENT_REVIEWED |
| UX-005 | Stock analysis chart M/W/D; same series; no gate recompute | Symbol -> chart -> zones journey | Analysis page | API, VT | BR-02..07, 11, 14 | See FR-4.1 | Fixtures OK | Sound | INDEPENDENT_REVIEWED |
| UX-006 | Drawings persist; excluded from eligibility | See FR-4.3 / FR-4.8 | Unchanged | API | BR-22 | See FR-4.3 | None | Sound | INDEPENDENT_REVIEWED |
| UX-013 | Empty/loading/error; unavailable is not zero | Distinct states on analysis | Evidence panel + existing empty states | VT `evidence.test.ts` | BR-01, 05 (wrong symbol -> MISSING), 06 (unknown scan), 07 (wrong dataset/session -> STALE) | Loading state observed transiently only | None | IR-2 fixed | INDEPENDENT_REVIEWED |
| UX-014 | Fixture labelling | Fixture banner / research_use | Unchanged + evidence row `FIXTURE`/`UNCERTIFIED` | API quality tests, VT | BR-02 banners | None | None | Sound | INDEPENDENT_REVIEWED |
| OD-P2-1 | Owner: allow analysis without a stored scan? | Only if owner authorises | Not implemented (owner Decision 1) | n/a | BR-01 empty state cites OD-P2-1 | Owner-deferred | Owner | Confirmed not implemented | DEFERRED_OWNER |
| P2-VOL-WM | W/M volume aggregation | Honest aggregated traded quantity or unavailable | `candles._aggregate_volume`: sum of constituent sessions (count checked against `HtfCandle.sessions_present`); null + `HTF_VOLUME_INCOMPLETE` / `HTF_VOLUME_SESSION_MISMATCH`; `volume_sessions`; duplicate CSV date -> null | API: sum/holiday/partial-month/month boundary, zero/invalid/gap, duplicate (3 new) | BR-03/04 `volume_state PRESENT` on W/M | Confirmed-excluded sessions are left out of HTF volume, matching OHLC | Calendar + daily volume | Reviewed sound | INDEPENDENT_REVIEWED |
| P2-SMA-CHART | SMA-50 display on chart (roadmap; no FR ID) | n/a | Not implemented (owner Decision 2: out of scope). Research SMA-50 in `trend.py` unchanged | n/a | n/a | Out of scope | Owner | Confirmed absent | DEFERRED_OWNER |
| P2-TV | TradingView comparison | External reference protocol | Unchanged; worksheet 34/34 rows blank; INFY file is Yahoo screenshot transcription | n/a | Not possible without exports | No parity claim | TV-1 external | n/a | BLOCKED |
| P2-BROWSER | Browser validation of analysis | Programme P2-H | Real Chrome run | n/a | BR-01..07, 11, 14, 21, 22 | Fixture data only | Local app | n/a | VALIDATED |

## B. P3 - Opportunity intelligence (27 rows)

| ID | Original requirement | Acceptance criteria | Implementation | Tests | Validation | Limitations | Dependency | Independent review | Final status |
|---|---|---|---|---|---|---|---|---|---|
| OI-001 | Read stored candidate status later | Status from envelope, not recompute | Ingest copies `status`; Scanner now reads canonical `status` | OPP (incl. real-scanner-shape test), VT | BR-16, 18 | None | Stored scan | Sound | INDEPENDENT_REVIEWED |
| OI-002 | Pass/fail/manual reasons; do not invent a reason | Render stored outcomes | New `scanOutcome` panel from stored statuses and deciding gates | VT `model.test.ts` (scan outcome, 6 + 3 canonical-key) | BR-16 (QUALIFIED), BR-17 (real pipeline scan: NOTHING_QUALIFIED with stored reasons) | Stored reason text may include local file paths | None | Sound | INDEPENDENT_REVIEWED |
| OI-003 | Decision bundle | Bundle from `scan_key` | Unchanged | API, VT | BR-02 | None | Scan | Sound | INDEPENDENT_REVIEWED |
| OI-004 | HTF obstacles / opposing supply | Show G5 evidence | Unchanged; stored supply zones listed | VT | BR-02 (W/M supply zones, G5 line) | None | None | Sound | INDEPENDENT_REVIEWED |
| OI-005 | Curve and confluence context; confluence not a rank | Stored; priority non-authoritative | Unchanged | Priority tests | BR-18 (priority captioned non-authoritative) | None | None | Sound | INDEPENDENT_REVIEWED |
| OI-006 | Candidate comparison (capability map: "Yes, degraded") | Compare stored results; no composite rank | Unchanged: research `explain` compare; no product screen | Research assistant tests (run_all) | CLI only | Degraded as specified | None | n/a | TESTED |
| OI-007 | Similar historical setups | Only with validated PIT matcher; otherwise omit | Omitted (owner Decision 3) | n/a | n/a | No approved algorithm | Owner / P7 | Confirmed absent | DEFERRED_OWNER |
| OI-008 | Human review; do not rename best status | Checklist pending; no buy language | Unchanged; outcome panel says "Manual checks are still pending. Not an order." | VT | BR-16 | None | None | Sound | INDEPENDENT_REVIEWED |
| FR-3.1 | MIT via pipeline; WIT blocked | Scan path uses pipeline | Unchanged | API, VT | BR-17 real pipeline job VALIDATING->RUNNING->SUCCEEDED_COMPLETE | None | None | Sound | INDEPENDENT_REVIEWED |
| FR-3.2 | Scheduled/manual/historical modes | Modes at research+jobs layer | Unchanged | Scheduler API tests | Manual only in browser | Scheduler not exercised in browser | Calendar | n/a | TESTED |
| FR-3.3 | Show symbol/candidate/overlay/G0-G8 | Scanner renders stored fields | **Defect fixed:** Scanner read non-existent `symbol_status`/`candidate_status`; now `symbolStatusOf`/`candidateStatusOf` read canonical `status` | VT canonical-key regression (3) | BR-16 before fix showed "Unavailable" statuses; after fix QUALIFIED | Legacy keys kept as fallback | None | Re-review confirms helpers | INDEPENDENT_REVIEWED |
| FR-3.4 | Explain rejections from stored reasons; no invented rank | Zero-result / partial distinction | `scanOutcome`: UNAVAILABLE, FAILED, EMPTY, QUALIFIED, NOTHING_QUALIFIED with PARTIAL_SCAN, STALE_DATASET, EVIDENCE_MISSING, EVIDENCE_INCOMPLETE, CANDIDATES_REJECTED, NO_FRESH_ZONE, ZONES_BLOCKED, COUNTS_DISAGREE | VT | BR-16, 17; scan with as_of beyond data refused 422 DATA_INSUFFICIENT (not an empty success) | Staleness only from dataset mismatch (no other stale signal exists in the envelope) | None | Sound | INDEPENDENT_REVIEWED |
| FR-3.5 | Filters hide rows; do not change status | Filters | Status filter now matches canonical rows | VT | BR-16 | None | None | Sound | INDEPENDENT_REVIEWED |
| FR-3.6 | Search symbol/name/ISIN | Instrument search | Unchanged | Instrument tests | Not exercised in browser | No browser check | Identity file | n/a | TESTED |
| FR-3.7 | Watchlists are not universe/eligibility | CRUD | Unchanged | VT, API | BR-19 create + persist, BR-23 rename persists; eligibility shown "Unavailable" | Reorder not browser-checked | None | n/a | VALIDATED |
| FR-3.8 | Saved scan configs; no gate override | scan-configs API | Unchanged | API | Not in browser | No browser check | None | n/a | TESTED |
| FR-3.9 | Scan history; old run shows its own bytes | History + reopen | Unchanged | VT | BR-20 both scans listed; BR-16/17 reopen stored envelopes | None | None | n/a | VALIDATED |
| UX-003 | Scanner screen run/read | Submit/poll/cancel/history | Unchanged + outcome panel | VT | BR-16, 17, 20 (scan submitted via API from the browser session, not the form) | Form submit path covered by vitest only | None | Sound | INDEPENDENT_REVIEWED |
| UX-004 | Watchlist screen | Create/rename/add/reorder | Unchanged | VT | BR-19, 23 | Reorder/add not browser-checked | None | n/a | VALIDATED |
| P3-R08 | Ingest from stored scan only | No qualification import | Unchanged; timeframe now read from canonical `execution_tf`/`zone.tf` (defect fix) | OPP real-shape regression | BR-18 | None | Scan envelope | Re-review confirms | INDEPENDENT_REVIEWED |
| P3-R09 | Source quality; never promote to CERTIFIED | CERTIFIED refused while P0 = 0 | Unchanged | OPP | BR-18 (FIXTURE label, no certified claim) | None | P0 count | Sound | INDEPENDENT_REVIEWED |
| P3-R12/R13 | Certified discovery / counts | Refuse CERTIFIED mode | Unchanged | OPP | BR-18 | P0 certified symbol-dates 0 | P0/D66 | n/a | BLOCKED |
| P3-R15 | OI-007 matcher | See OI-007 | Omitted | n/a | n/a | See OI-007 | Owner | n/a | DEFERRED_OWNER |
| P3-R16 / D6 | Sector filter | UNAVAILABLE until sector source; no proxy | Unchanged (`USER_APPROVED` D6: not evaluated, no proxy) | product_flow sector_state | n/a | No approved sector source | Sector source + owner | n/a | BLOCKED |
| P3-ALERTS | Alerts | EX-007/008 blocked; scan-diff local only | Unchanged | Research alert tests (run_all) | n/a | No external delivery, no paid provider | Quote provider / owner | n/a | BLOCKED |
| P3-BROWSER | Browser opportunity journey | Programme P3-K | Real Chrome run | n/a | BR-16..20, 23 | Fixture data only | Local app | n/a | VALIDATED |
| P3-NULL-ZONE | Null zone_id desk collapse | Accepted IR-06 (P3) | Unchanged | Documented | n/a | Accepted earlier limitation | None | n/a | TESTED |

## C. P4 - Trade planning (20 rows)

| ID | Original requirement | Acceptance criteria | Implementation | Tests | Validation | Limitations | Dependency | Independent review | Final status |
|---|---|---|---|---|---|---|---|---|---|
| TP-001 / FR-5.1 | Plan from stored candidate; copy status/gates/levels/checks | Refuse BLOCKED/REJECTED/DATA_INSUFFICIENT | Unchanged | PLAN | BR-08 draft from stored candidate | None | Stored candidate | Sound | INDEPENDENT_REVIEWED |
| TP-002 / FR-5.2 | Entry/stop inside printed ranges; software does not pick buffer | Combinations from engine ranges | Unchanged | PLAN | BR-08 combinations listed | None | B9 | Sound | INDEPENDENT_REVIEWED |
| TP-003 / FR-5.3-5.4 | Structural target with G7 provenance; invalid geometry manual | No invented target | Unchanged | PLAN `test_geometry_blocks_tested_overlay` | BR-08 geometry VALID | None | None | Sound | INDEPENDENT_REVIEWED |
| TP-004 | R:R / 2:1 across buffers | Show combination R:R | Unchanged | PLAN | BR-08 (R:R per combination) | None | None | Sound | INDEPENDENT_REVIEWED |
| TP-005 / FR-5.5 | Quantity from `risk.py`; invalid -> no invented number | Transparent sizing | Unchanged | PLAN, research risk | BR-08 (qty, risk/share, loss at stop) | None | Capital/RPT | Sound | INDEPENDENT_REVIEWED |
| TP-006 | Risk stage bands | Stage bands | Unchanged | Research risk tests | Settings LEARNING used | None | Settings | n/a | TESTED |
| TP-007 / FR-5.6 / FR-6.1 | Capital owner-entered; no assumed capital | Quantity empty until chosen | Unchanged | product_flow | Settings set explicitly before BR-08 | None | Owner capital | n/a | TESTED |
| TP-008 / FR-5.7 | Cap checks; NOT_SUPPLIED is not pass | Preview checks; hard refuse in journal | Unchanged | PLAN, P5/P6 suites | BR-08 capacity facts | None | Journal | n/a | TESTED |
| TP-009 / FR-5.8 | Owner approval records person; no order | Approve -> journal row; `authorises_order` false | Unchanged | PLAN, product_flow | BR-09 (refused with unanswered checklist), BR-10 (approved, "No order was sent", `authorises_order false`) | None | None | Sound | INDEPENDENT_REVIEWED |
| TP-010 / FR-5.9 | Plans versioned; later scan does not overwrite; UI shows mismatch | Mismatch shown | **New** `desk.later_scan_comparison` -> `later_scan` on preview (CHANGED / UNCHANGED / ZONE_NOT_A_CANDIDATE / LATER_RESULT_NOT_EVALUATED / NO_LATER_SCAN); same fixture flag, trade type, dataset; zone matched on id + tf; Plans UI warning | PLAN `test_tp010_*` (2) | BR-15 (NO_LATER_SCAN shown) | Changed-scan UI not captured in browser (API-tested) | Later scans | IR-3, IR-5 fixed | INDEPENDENT_REVIEWED |
| TP-011 | One order per zone (ED-3) | Journal holds zone; cancel rules | Platform cancel of approved+entry still 409; journal decides | PLAN | BR-10 cancel redirected to journal | None | Journal | Sound | INDEPENDENT_REVIEWED |
| TP-012 | Planned vs actual after fills | Compare planned vs recorded fills | Unchanged | PLAN, P6 | Not browser-checked with fills | No fills recorded in browser run | Fills | n/a | TESTED |
| FR-5.10 | BLOCKED/REJECTED/DATA_INSUFFICIENT cannot journal | Store refuse | Unchanged | PLAN, store | n/a | None | None | n/a | TESTED |
| UX-007 | Trade-plan screen builds TP-001..012 | Desk UI | Plans UI + journal state/sync, later-scan, expiry note | PLAN, VT | BR-08..15 | None | None | Sound | INDEPENDENT_REVIEWED |
| P4-R17/R18 | Certified planning claims | Refuse while P0 = 0 | Unchanged | PLAN `test_certified_source_downgraded_to_exploratory` | n/a | P0 uncertified | P0 | n/a | BLOCKED |
| P4-R21 / safety | `authorises_order` always false; no broker | Adversarial coverage | Unchanged; no route added (63 routes, OpenAPI test unchanged) | security, PLAN, product_flow | BR-10, journal cancel message "No order was touched" | None | None | Reviewer confirmed | INDEPENDENT_REVIEWED |
| P4-IR-04 | Plan/journal cancel desynchronisation | No contradictory state | Journal-first, mirror-on-write, repair-on-read and at startup; identity-bound (symbol, zone, `approve:<plan_id>`); `JOURNAL_SYNC_*` events; Journal "Record CANCELLED" control | PLAN `test_ir04_*` (9) + zone-invalidated test | BR-12 journal cancel, BR-13 plan CANCELLED / journal CANCELLED / IN_SYNC / counts, BR-14 | Recoverable, not atomic, consistency (two SQLite files) | Journal | IR-1 fixed; re-review PASS | INDEPENDENT_REVIEWED |
| P4-EXPIRED | Automatic EXPIRED | Original rule must exist | No automatic producer (owner Decision 5); plan mirrors only an owner-recorded journal EXPIRED | PLAN `test_ir04_journal_expired_event_is_mirrored_not_auto_produced` | BR-15 UI note "No automatic plan expiry runs" | Automatic expiry deferred; no Journal UI control for EXPIRED (API/CLI only) | Owner specification | Reviewer confirmed no clock path | DEFERRED_OWNER |
| P4-TARIFF | Charge tariffs vs official PDFs | No invented rates | Unchanged; owner schedule or ABSENT | P1/P6 charge tests | n/a | No tariff verified in repo | Owner schedule / B12 | n/a | BLOCKED |
| P4-BROWSER | Browser planning journey | Programme P4-H | Real Chrome run | n/a | BR-08..15 | Fixture data only | Local app | n/a | VALIDATED |

## D. Count summary

| Phase | Rows | INDEPENDENT_REVIEWED | VALIDATED | TESTED | DEFERRED_OWNER | BLOCKED |
|---|---:|---:|---:|---:|---:|---:|
| P2 | 18 | 14 | 1 | 0 | 2 | 1 |
| P3 | 27 | 13 | 4 | 5 | 2 | 3 |
| P4 | 20 | 11 | 1 | 5 | 1 | 2 |
| **Total** | **65** | **38** | **6** | **10** | **5** | **6** |

The Batch 0 matrix stated 64 rows (P3 = 26), but its P3 table lists 27 rows; the same 27 rows are kept here, so the
correct total is 65. No row was added or removed.

`TESTED` rows were not changed in this programme and have passing automated tests but no browser evidence
in this run. `BLOCKED` rows are external or P0-dependent; `DEFERRED_OWNER` rows follow owner Decisions 1, 2,
3 and 5. No row is `ACCEPTED`.
