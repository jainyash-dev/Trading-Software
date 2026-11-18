# P4 Implementation Status - Trade Planning

**Date:** 2026-11-17 | **HEAD:** `69858d0` (unchanged) | **Verdict:** `P4_ACCEPTANCE_READY` (owner retains `ACCEPTED`)

Row-level detail: `P2_P4_ACCEPTANCE_MATRIX.md` section C (20 rows: 11 INDEPENDENT_REVIEWED, 1 VALIDATED,
5 TESTED, 1 DEFERRED_OWNER, 2 BLOCKED).

## P4-IR-04 plan/journal cancellation desynchronisation (owner Decision 4)

**Reproduced first.** `test_ir04_*` were written before the fix and failed: after a journal CANCELLED the
platform plan stayed APPROVED in preview, list, counts and history.

**Exact failing operation:** `POST /api/v1/journal/{entry_id}/events {kind: CANCELLED}` commits in the
research store (`research.sqlite`); the plan row lives in `platform.sqlite`; nothing wrote the plan. Platform
cancel of an APPROVED plan with an entry is (still, correctly) refused 409 under ED-3.

**Consistency model (recoverable, not atomic).** Two SQLite files cannot share a transaction.
1. The journal is written first and is authoritative. No journal row is rewritten or deleted.
2. In the same request the platform mirrors the terminal journal state onto linked APPROVED plans
   (`desk.sync_plans_from_journal` -> `planning.mirror_journal_terminal`), inside the platform write
   transaction. The response reports `plan_sync: APPLIED` or `PENDING_REPAIR_ON_READ`.
3. If step 2 did not run (crash, research CLI edit), every plan read (list, preview, history, cancel) and
   app startup (`app._repair_plan_journal_mirror`) re-runs the idempotent mirror before showing the plan.
4. The mirror is identity-bound: the journal entry must have the plan's symbol and zone_id and the journal
   idempotency record `approve:<plan_id>` must name that entry. Otherwise `JOURNAL_IDENTITY_MISMATCH` and no
   write (a recreated journal reuses entry numbers).
5. Writes are guarded (`WHERE state='APPROVED' AND entry_id=?`, rowcount checked) and append a
   `JOURNAL_SYNC_CANCELLED` / `JOURNAL_SYNC_EXPIRED` plan event and an audit row. Plan history stays
   append-only.
6. Every plan view carries `journal_state`, `journal_sync` (`IN_SYNC`, `CONFLICT`, `JOURNAL_UNAVAILABLE`,
   `JOURNAL_ENTRY_MISSING`, `JOURNAL_IDENTITY_MISMATCH`, `NO_JOURNAL_ENTRY`) and `journal_zone_invalidated`.
   The UI warns on anything but IN_SYNC; the chart withholds plan lines.

UI: approved plans with an entry show "Cancel it in the Journal" instead of a platform Cancel button; the
Journal page gained a "Record CANCELLED" control (explicit reason required) that posts to the existing
journal events route, so the journal's own ED-3 / allowed-event rules decide. A repeated platform cancel of a
CANCELLED plan is idempotent.

Tests (`platform/tests/test_trade_planning.py`): sync on write and read; repeated cancel and journal replay
idempotency; recovery after an interrupted mirror (restart); repair on read without restart; journal
unavailable and entry missing disclosed; mirror failure rolls back and is repaired on read; journal refusal
(CANCELLED on an OPEN trade) leaves the plan unchanged; 8 concurrent readers/cancellers mirror once; OPEN
and CLOSED keep APPROVED; journal EXPIRED mirrored; recreated journal with reused entry ids not trusted;
foreign zone mismatch; ZONE_INVALIDATED flagged. Browser: BR-12, BR-13, BR-14.

## FR-5.9 / TP-010 later-scan mismatch (gap found and closed)

No code showed the owner a later scan that changed a planned candidate. New
`desk.later_scan_comparison` (read-only) returns `later_scan` on plan preview: CHANGED (field differences:
status, entry range, stop ranges, overlay status, test count, proximal, distal), UNCHANGED,
ZONE_NOT_A_CANDIDATE, LATER_RESULT_NOT_EVALUATED, NO_LATER_SCAN, UNAVAILABLE. Only scans with the same
fixture flag, trade type and dataset_id are compared; zones match on id and timeframe. The plan's version
and frozen snapshot are never changed. Tests `test_tp010_*`; UI warning on the Plans page; BR-15.

## Expiry (owner Decision 5)

No automatic plan expiry was added. D42's 10 verified sessions are a journal pending-order rule
(`store._refuse_expired_fill`), not a plan validity rule. The only plan EXPIRED producer is the mirror of an
owner-recorded journal EXPIRED event (reviewer confirmed: no clock or session-count path). The Plans page
states "No automatic plan expiry runs." The Journal UI has no EXPIRED control (API/CLI only, unchanged).

## Verified, unchanged

Geometry, R:R, sizing (BR-08 shows combinations with entry, stop, target, qty, risk/share, loss at stop,
R:R); approval refused with an unanswered checklist (BR-09); approval writes the journal and says "No order
was sent" with `authorises_order false` (BR-10); rejection requires an explicit reason and is recorded
(BR-15). Charges (B12): `nse/research/charges.py` unchanged; no tariff value added or assumed.

## Order-authorisation boundary

No route was added (63 `add_api_route` registrations; the committed `openapi.json` equality test passes).
`authorises_order` stays false in every plan and journal response touched. Approval and journal cancel
messages state that no order was sent or touched.

## Owner-deferred / blocked

- Automatic EXPIRED: `DEFERRED_OWNER`.
- Certified planning (P4-R17/R18): `BLOCKED` by P0.
- Tariffs (P4-TARIFF / B12): `BLOCKED`; owner-supplied schedule or ABSENT.

## Limitations

- Recoverable rather than atomic consistency; between a failed mirror and the next read the plan row is
  stale on disk, but no read path returns it without re-running the mirror.
- Plan GET routes now write (idempotent mirror) and hold `db_lock` while reading the journal per linked plan.
- On a pre-idempotency journal only symbol + zone bind a plan to its entry.
- TP-006/007/008/012 and FR-5.10 rely on existing automated tests; no fills were recorded in the browser run.
