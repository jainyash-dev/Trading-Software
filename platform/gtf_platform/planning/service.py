"""Trade-plan lifecycle, preview enrichment, and planned-versus-actual.

Does not calculate GTF eligibility. Does not place orders. Does not keep a
second monthly or open-position counter; those stay in the research journal.
Research-store reads for caps and fills happen only via the desk adapter.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from gtf_platform.errors import ApiError
from gtf_platform.planning.states import (
    APPROVABLE,
    CANCELABLE,
    PLAN_STATES,
    REJECTABLE,
    allowed_transitions,
    can_transition,
)
from gtf_platform.store import new_id, record_audit, utcnow

REFUSED = frozenset({"BLOCKED", "REJECTED", "DATA_INSUFFICIENT"})
ACTIVE_PLAN_STATES = frozenset({"DRAFT", "AWAITING_OWNER", "APPROVED"})


def ensure_schema_columns(connection: sqlite3.Connection) -> None:
    """Idempotent column probe for tests that may open an older fixture DB."""
    cols = {row["name"] for row in connection.execute("PRAGMA table_info(trade_plan)")}
    for name, declaration in (
        ("opportunity_id", "TEXT"),
        ("rationale", "TEXT"),
        ("source_quality", "TEXT"),
        ("plan_version", "INTEGER NOT NULL DEFAULT 1"),
        ("submitted_at", "TEXT"),
        ("rejected_at", "TEXT"),
        ("rejected_by", "TEXT"),
        ("rejection_reason", "TEXT"),
        ("cancelled_at", "TEXT"),
        ("cancelled_by", "TEXT"),
        ("cancel_reason", "TEXT"),
        ("updated_at", "TEXT"),
    ):
        if name not in cols:
            connection.execute("ALTER TABLE trade_plan ADD COLUMN %s %s" % (name, declaration))


def list_plans(
    connection: sqlite3.Connection,
    *,
    state: str | None = None,
    symbol: str | None = None,
    scan_key: str | None = None,
    limit: int = 100,
) -> dict:
    ensure_schema_columns(connection)
    clauses: list[str] = []
    params: list[Any] = []
    if state:
        if state not in PLAN_STATES:
            raise ApiError(400, "REQUEST_INVALID", "Unknown plan state filter")
        clauses.append("state = ?")
        params.append(state)
    if symbol:
        clauses.append("symbol = ?")
        params.append(symbol.strip().upper())
    if scan_key:
        clauses.append("scan_key = ?")
        params.append(scan_key)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    limit = max(1, min(int(limit or 100), 500))
    rows = connection.execute(
        "SELECT * FROM trade_plan%s ORDER BY created_at DESC LIMIT ?" % where,
        (*params, limit),
    ).fetchall()
    items = [_row_view(row) for row in rows]
    counts = {
        name: connection.execute(
            "SELECT COUNT(*) FROM trade_plan WHERE state = ?", (name,)
        ).fetchone()[0]
        for name in sorted(PLAN_STATES)
    }
    return {
        "plans": items,
        "counts_by_state": counts,
        "authorises_order": False,
        "note": "A plan is not an order. Caps are enforced in the research journal on TRIGGERED.",
    }


def create_plan(
    connection: sqlite3.Connection,
    envelope: dict,
    scan_key: str,
    symbol: str,
    zone_id: str,
    *,
    opportunity_id: str | None = None,
    rationale: str | None = None,
    fixture: bool = False,
) -> dict:
    ensure_schema_columns(connection)
    from gtf_platform.integration.desk import _candidate

    candidate = _candidate(envelope, symbol, zone_id)
    status = candidate.get("status")
    if status in REFUSED:
        raise ApiError(409, "CONFLICT", "A %s candidate cannot be planned" % status)
    symbol_u = symbol.strip().upper()
    existing = connection.execute(
        """
        SELECT plan_id FROM trade_plan
        WHERE scan_key = ? AND symbol = ? AND zone_id = ? AND state IN ('DRAFT', 'AWAITING_OWNER')
        ORDER BY created_at DESC LIMIT 1
        """,
        (scan_key, symbol_u, zone_id),
    ).fetchone()
    if existing is not None:
        return plan_view(connection, existing["plan_id"])
    if opportunity_id:
        opp = connection.execute(
            "SELECT opportunity_id, canonical_status FROM opportunity WHERE opportunity_id = ?",
            (opportunity_id,),
        ).fetchone()
        if opp is None:
            raise ApiError(404, "NOT_FOUND", "Opportunity was not found")
        if opp["canonical_status"] != status:
            raise ApiError(
                409,
                "CONFLICT",
                "Opportunity canonical_status %s does not match candidate status %s"
                % (opp["canonical_status"], status),
            )
    plan_id = "plan-" + uuid.uuid4().hex[:16]
    now = utcnow()
    source_quality = _source_quality(envelope, fixture=fixture)
    snapshot = {
        "candidate": candidate,
        "limitations": envelope.get("limitations") or [],
        "as_of": envelope.get("as_of"),
        "dataset_id": envelope.get("dataset_id"),
        "source_quality": source_quality,
    }
    connection.execute(
        """
        INSERT INTO trade_plan (
            plan_id, scan_key, symbol, zone_id, candidate_status, snapshot_json, state,
            created_at, opportunity_id, rationale, source_quality, plan_version, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'DRAFT', ?, ?, ?, ?, 1, ?)
        """,
        (
            plan_id,
            scan_key,
            symbol_u,
            zone_id,
            status,
            json.dumps(snapshot),
            now,
            opportunity_id,
            (rationale or "").strip() or None,
            source_quality,
            now,
        ),
    )
    _record_event(
        connection,
        plan_id,
        from_state=None,
        to_state="DRAFT",
        actor="owner",
        action="CREATED",
        detail={"candidate_status": status, "source_quality": source_quality},
    )
    record_audit(connection, actor="owner", action="plan.created", object_id=plan_id, before=None, after=plan_id)
    return plan_view(connection, plan_id)


def submit_for_review(connection: sqlite3.Connection, plan_id: str, *, note: str | None = None) -> dict:
    ensure_schema_columns(connection)
    row = _require(connection, plan_id)
    if row["state"] == "AWAITING_OWNER":
        return plan_view(connection, plan_id)
    if row["state"] not in ("DRAFT",):
        raise ApiError(409, "CONFLICT", "Only a DRAFT plan can be submitted for review")
    if row["candidate_status"] in REFUSED:
        raise ApiError(409, "CONFLICT", "A %s candidate cannot be submitted" % row["candidate_status"])
    now = utcnow()
    connection.execute(
        "UPDATE trade_plan SET state = 'AWAITING_OWNER', submitted_at = ?, updated_at = ? WHERE plan_id = ?",
        (now, now, plan_id),
    )
    _record_event(
        connection,
        plan_id,
        from_state="DRAFT",
        to_state="AWAITING_OWNER",
        actor="owner",
        action="SUBMITTED",
        detail={"note": (note or "").strip() or None},
    )
    record_audit(
        connection, actor="owner", action="plan.submitted", object_id=plan_id,
        before="DRAFT", after="AWAITING_OWNER",
    )
    return plan_view(connection, plan_id)


def reject_plan(
    connection: sqlite3.Connection,
    plan_id: str,
    *,
    reason: str,
    actor: str = "owner",
) -> dict:
    ensure_schema_columns(connection)
    if not isinstance(reason, str) or not reason.strip():
        raise ApiError(400, "REQUEST_INVALID", "rejection reason is required")
    row = _require(connection, plan_id)
    if row["state"] not in REJECTABLE:
        raise ApiError(409, "CONFLICT", "Plan state %s cannot be rejected" % row["state"])
    if not can_transition(row["state"], "REJECTED"):
        raise ApiError(409, "CONFLICT", "Transition to REJECTED is not allowed")
    now = utcnow()
    connection.execute(
        """
        UPDATE trade_plan
        SET state = 'REJECTED', rejected_at = ?, rejected_by = ?, rejection_reason = ?, updated_at = ?
        WHERE plan_id = ?
        """,
        (now, actor, reason.strip(), now, plan_id),
    )
    _record_event(
        connection,
        plan_id,
        from_state=row["state"],
        to_state="REJECTED",
        actor=actor,
        action="REJECTED",
        detail={"reason": reason.strip()},
    )
    record_audit(
        connection, actor=actor, action="plan.rejected", object_id=plan_id,
        before=row["state"], after="REJECTED",
    )
    return plan_view(connection, plan_id)


def cancel_plan(
    connection: sqlite3.Connection,
    plan_id: str,
    *,
    reason: str,
    actor: str = "owner",
) -> dict:
    ensure_schema_columns(connection)
    if not isinstance(reason, str) or not reason.strip():
        raise ApiError(400, "REQUEST_INVALID", "cancel reason is required")
    row = _require(connection, plan_id)
    if row["state"] == "CANCELLED":
        # Repeated cancellation (or cancel after a journal-side cancel was mirrored):
        # idempotent, no second event.
        return plan_view(connection, plan_id)
    if row["state"] not in CANCELABLE:
        raise ApiError(409, "CONFLICT", "Plan state %s cannot be cancelled" % row["state"])
    if row["state"] == "APPROVED" and row["entry_id"] is not None:
        raise ApiError(
            409,
            "CONFLICT",
            "An approved plan with a journal entry must be cancelled in the journal "
            "(ED-3). Platform cancel is refused so zone allowance is not silently released.",
        )
    if not can_transition(row["state"], "CANCELLED"):
        raise ApiError(409, "CONFLICT", "Transition to CANCELLED is not allowed")
    now = utcnow()
    connection.execute(
        """
        UPDATE trade_plan
        SET state = 'CANCELLED', cancelled_at = ?, cancelled_by = ?, cancel_reason = ?, updated_at = ?
        WHERE plan_id = ?
        """,
        (now, actor, reason.strip(), now, plan_id),
    )
    _record_event(
        connection,
        plan_id,
        from_state=row["state"],
        to_state="CANCELLED",
        actor=actor,
        action="CANCELLED",
        detail={"reason": reason.strip()},
    )
    record_audit(
        connection, actor=actor, action="plan.cancelled", object_id=plan_id,
        before=row["state"], after="CANCELLED",
    )
    return plan_view(connection, plan_id)


# P4-IR-04. The research journal is the canonical execution record. When the
# journal entry linked to an APPROVED plan reaches a terminal non-fill state that
# the owner recorded there (CANCELLED or EXPIRED), the platform plan mirrors it.
# No clock or session count produces EXPIRED here: the journal event is explicit.
JOURNAL_TERMINAL_TO_PLAN = {"CANCELLED": "CANCELLED", "EXPIRED": "EXPIRED"}
JOURNAL_SYNC_ACTOR = "journal-sync"


def mirror_journal_terminal(
    connection: sqlite3.Connection,
    plan_id: str,
    *,
    entry_id: int,
    journal_state: str,
) -> bool:
    """Move an APPROVED plan to the journal's terminal state. Idempotent.

    Returns True when this call changed the row. The UPDATE is guarded on the
    current state and entry_id so a concurrent or repeated sync is a no-op.
    """
    target = JOURNAL_TERMINAL_TO_PLAN.get(journal_state)
    if target is None:
        return False
    ensure_schema_columns(connection)
    row = _require(connection, plan_id)
    if row["state"] != "APPROVED" or row["entry_id"] != entry_id or not can_transition("APPROVED", target):
        return False
    now = utcnow()
    reason = "Journal entry %d recorded %s" % (entry_id, journal_state)
    if target == "CANCELLED":
        cursor = connection.execute(
            """
            UPDATE trade_plan
            SET state = 'CANCELLED', cancelled_at = ?, cancelled_by = ?, cancel_reason = ?, updated_at = ?
            WHERE plan_id = ? AND state = 'APPROVED' AND entry_id = ?
            """,
            (now, JOURNAL_SYNC_ACTOR, reason, now, plan_id, entry_id),
        )
    else:
        cursor = connection.execute(
            "UPDATE trade_plan SET state = ?, updated_at = ? WHERE plan_id = ? AND state = 'APPROVED' AND entry_id = ?",
            (target, now, plan_id, entry_id),
        )
    if cursor.rowcount != 1:
        return False
    _record_event(
        connection,
        plan_id,
        from_state="APPROVED",
        to_state=target,
        actor=JOURNAL_SYNC_ACTOR,
        action="JOURNAL_SYNC_%s" % target,
        detail={"entry_id": entry_id, "journal_state": journal_state, "reason": reason},
    )
    record_audit(
        connection, actor=JOURNAL_SYNC_ACTOR, action="plan.journal_sync", object_id=plan_id,
        before="APPROVED", after=target,
    )
    return True


def reopen_draft(connection: sqlite3.Connection, plan_id: str, *, actor: str = "owner") -> dict:
    ensure_schema_columns(connection)
    row = _require(connection, plan_id)
    if row["state"] == "DRAFT":
        return plan_view(connection, plan_id)
    if row["state"] not in ("AWAITING_OWNER", "REJECTED"):
        raise ApiError(409, "CONFLICT", "Only AWAITING_OWNER or REJECTED plans can return to DRAFT")
    if row["candidate_status"] in REFUSED:
        raise ApiError(409, "CONFLICT", "A %s candidate cannot be reopened" % row["candidate_status"])
    now = utcnow()
    connection.execute(
        """
        UPDATE trade_plan
        SET state = 'DRAFT', submitted_at = NULL, rejected_at = NULL, rejected_by = NULL,
            rejection_reason = NULL, updated_at = ?, plan_version = COALESCE(plan_version, 1) + 1
        WHERE plan_id = ?
        """,
        (now, plan_id),
    )
    _record_event(
        connection,
        plan_id,
        from_state=row["state"],
        to_state="DRAFT",
        actor=actor,
        action="REOPENED",
        detail=None,
    )
    record_audit(
        connection, actor=actor, action="plan.reopened", object_id=plan_id,
        before=row["state"], after="DRAFT",
    )
    return plan_view(connection, plan_id)


def set_rationale(connection: sqlite3.Connection, plan_id: str, rationale: str) -> dict:
    ensure_schema_columns(connection)
    row = _require(connection, plan_id)
    if row["state"] not in ("DRAFT", "AWAITING_OWNER"):
        raise ApiError(409, "CONFLICT", "Rationale can only be edited on DRAFT or AWAITING_OWNER plans")
    if not isinstance(rationale, str):
        raise ApiError(400, "REQUEST_INVALID", "rationale must be a string")
    now = utcnow()
    connection.execute(
        "UPDATE trade_plan SET rationale = ?, updated_at = ? WHERE plan_id = ?",
        (rationale.strip() or None, now, plan_id),
    )
    _record_event(
        connection,
        plan_id,
        from_state=row["state"],
        to_state=row["state"],
        actor="owner",
        action="RATIONALE_UPDATED",
        detail={"length": len(rationale.strip())},
    )
    return plan_view(connection, plan_id)


def add_note(connection: sqlite3.Connection, plan_id: str, body: str, *, actor: str = "owner") -> dict:
    ensure_schema_columns(connection)
    _require(connection, plan_id)
    if not isinstance(body, str) or not body.strip():
        raise ApiError(400, "REQUEST_INVALID", "note body is required")
    note_id = new_id("pnote")
    now = utcnow()
    connection.execute(
        """
        INSERT INTO trade_plan_note (note_id, plan_id, actor, body, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (note_id, plan_id, actor, body.strip(), now),
    )
    return {"note_id": note_id, "plan_id": plan_id, "actor": actor, "body": body.strip(), "created_at": now}


def list_notes(connection: sqlite3.Connection, plan_id: str) -> dict:
    ensure_schema_columns(connection)
    _require(connection, plan_id)
    rows = connection.execute(
        "SELECT * FROM trade_plan_note WHERE plan_id = ? ORDER BY created_at",
        (plan_id,),
    ).fetchall()
    return {
        "notes": [
            {
                "note_id": row["note_id"],
                "plan_id": row["plan_id"],
                "actor": row["actor"],
                "body": row["body"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    }


def history(connection: sqlite3.Connection, plan_id: str) -> dict:
    ensure_schema_columns(connection)
    _require(connection, plan_id)
    rows = connection.execute(
        "SELECT * FROM trade_plan_event WHERE plan_id = ? ORDER BY at, event_id",
        (plan_id,),
    ).fetchall()
    return {
        "events": [
            {
                "event_id": row["event_id"],
                "plan_id": row["plan_id"],
                "from_state": row["from_state"],
                "to_state": row["to_state"],
                "actor": row["actor"],
                "action": row["action"],
                "detail": json.loads(row["detail_json"]) if row["detail_json"] else None,
                "at": row["at"],
            }
            for row in rows
        ],
        "allowed_transitions": allowed_transitions(_require(connection, plan_id)["state"]),
    }


def plan_view(connection: sqlite3.Connection, plan_id: str) -> dict:
    ensure_schema_columns(connection)
    row = _require(connection, plan_id)
    return _row_view(row)


def enrich_preview(
    connection: sqlite3.Connection,
    plan_id: str,
    *,
    combinations: list[dict],
    quantity_state: str,
    note: str | None,
    portfolio_checks: list[dict],
    capacity: dict,
    risk_inputs: dict,
    planned_versus_actual: dict | None,
) -> dict:
    """Attach portfolio checks, geometry summary, capacity and manual-exec prep.

    Cap and fill facts are supplied by the desk adapter. This module does not
    import the research journal.
    """
    view = plan_view(connection, plan_id)
    snapshot = json.loads(_require(connection, plan_id)["snapshot_json"])
    candidate = snapshot.get("candidate") or {}
    zone = candidate.get("zone") or {}
    geometry = _geometry_summary(candidate, combinations)
    view.update(
        {
            "combinations": combinations,
            "quantity": None,
            "quantity_state": quantity_state,
            "note": note,
            "authorises_order": False,
            "approved": view.get("state") == "APPROVED",
            "geometry": geometry,
            "portfolio_checks": portfolio_checks,
            "capacity": capacity,
            "manual_execution": {
                "authorises_order": False,
                "broker": "Zerodha Kite (manual, outside this platform)",
                "instruction": (
                    "Execution takes place manually outside the platform. "
                    "Approving a plan does not submit an order. "
                    "A triggered plan is not proof of an actual fill."
                ),
                "prep_fields": {
                    "symbol": view["symbol"],
                    "quantity": None if view.get("selected") is None else (view["selected"] or {}).get("quantity"),
                    "proposed_entry": None if view.get("selected") is None else (view["selected"] or {}).get("entry"),
                    "stop_loss": None if view.get("selected") is None else (view["selected"] or {}).get("stop"),
                    "target": None if view.get("selected") is None else (view["selected"] or {}).get("target"),
                    "canonical_qualification": view["candidate_status"],
                    "zone_id": view["zone_id"],
                    "plan_status": view["state"],
                    "overlay_status": zone.get("overlay_status"),
                    "test_count": zone.get("test_count"),
                },
            },
            "risk_inputs": risk_inputs,
            "allowed_transitions": allowed_transitions(view["state"]),
            "source_quality": view.get("source_quality") or snapshot.get("source_quality") or "UNKNOWN",
            "planned_versus_actual": planned_versus_actual,
        }
    )
    return view


def mark_approved(
    connection: sqlite3.Connection,
    plan_id: str,
    *,
    entry_id: int,
    selected: dict,
    actor: str = "owner",
) -> dict:
    ensure_schema_columns(connection)
    row = _require(connection, plan_id)
    if row["state"] == "APPROVED" and row["entry_id"] is not None:
        return plan_view(connection, plan_id)
    if row["state"] not in APPROVABLE:
        raise ApiError(409, "CONFLICT", "Plan state %s cannot be approved" % row["state"])
    now = utcnow()
    connection.execute(
        """
        UPDATE trade_plan
        SET state = 'APPROVED', entry_id = ?, approved_at = ?, approved_by = ?,
            selected_json = ?, updated_at = ?
        WHERE plan_id = ?
        """,
        (entry_id, now, actor, json.dumps(selected), now, plan_id),
    )
    _record_event(
        connection,
        plan_id,
        from_state=row["state"],
        to_state="APPROVED",
        actor=actor,
        action="APPROVED",
        detail={"entry_id": entry_id, "quantity": selected.get("quantity")},
    )
    record_audit(
        connection, actor=actor, action="plan.approved", object_id=plan_id,
        before=row["state"], after="APPROVED",
    )
    return plan_view(connection, plan_id)


def _geometry_summary(candidate: dict, combinations: list[dict]) -> dict:
    levels = candidate.get("levels") or {}
    gates = [gate for gate in candidate.get("gates") or [] if gate.get("gate") == "G7"]
    target = ((gates[0].get("evidence") or {}).get("target") or {}).get("proximal") if gates else None
    zone = candidate.get("zone") or {}
    overlay = zone.get("overlay_status")
    test_count = zone.get("test_count")
    valid = [row for row in combinations if row.get("quantity") not in (None, 0) and row.get("status") != "INVALID_LEVELS"]
    invalid = [row for row in combinations if row.get("status") == "INVALID_LEVELS"]
    manual = [row for row in combinations if row.get("status") == "MANUAL_REVIEW"]
    reasons = []
    freshness_blocked = False
    if overlay and overlay != "FRESH":
        reasons.append("Zone overlay_status is %s; only fresh unbreached demand qualifies for long consideration" % overlay)
        freshness_blocked = True
    if isinstance(test_count, int) and test_count > 0:
        reasons.append("Zone test_count=%d; a tested zone must not become eligible through plan edits" % test_count)
        freshness_blocked = True
    if target is None:
        reasons.append("No structural G7 target proximal was present; targets are not invented")
    if not combinations and target is not None:
        reasons.append("Capital and risk percent are missing or no printed entry/stop range produced a combination")
    if freshness_blocked:
        status = "BLOCKED"
    elif valid:
        status = "VALID"
    elif manual or target is None:
        status = "MANUAL_REVIEW"
    elif invalid or reasons:
        status = "BLOCKED"
    else:
        status = "UNAVAILABLE"
    return {
        "status": status,
        "entry_range": levels.get("entry"),
        "stop_ranges": levels.get("sl"),
        "structural_target": target,
        "combination_count": len(combinations),
        "valid_combination_count": len(valid),
        "invalid_combination_count": len(invalid),
        "manual_combination_count": len(manual),
        "overlay_status": overlay,
        "test_count": test_count,
        "reasons": reasons,
        "note": "Geometry comes from the stored candidate. No chart screenshot inference.",
    }


def _source_quality(envelope: dict, *, fixture: bool) -> str:
    if fixture or envelope.get("fixture"):
        return "FIXTURE"
    label = str(envelope.get("source_label") or envelope.get("dataset_quality") or "").upper()
    if label in {"FIXTURE", "EXPLORATORY", "UNKNOWN", "UNAVAILABLE", "INVALID"}:
        return label
    if label == "CERTIFIED":
        # P0 incomplete: refuse certified planning inputs.
        return "EXPLORATORY"
    limitations = envelope.get("limitations") or []
    if any("FIXTURE" in str(item).upper() for item in limitations):
        return "FIXTURE"
    if envelope.get("dataset_id"):
        return "EXPLORATORY"
    return "UNKNOWN"


def _require(connection: sqlite3.Connection, plan_id: str):
    row = connection.execute("SELECT * FROM trade_plan WHERE plan_id = ?", (plan_id,)).fetchone()
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Plan was not found")
    return row


def _row_view(row) -> dict:
    selected = json.loads(row["selected_json"]) if row["selected_json"] else None
    keys = set(row.keys())
    return {
        "plan_id": row["plan_id"],
        "scan_key": row["scan_key"],
        "symbol": row["symbol"],
        "zone_id": row["zone_id"],
        "candidate_status": row["candidate_status"],
        "state": row["state"],
        "entry_id": row["entry_id"],
        "approved_at": row["approved_at"],
        "approved_by": row["approved_by"],
        "selected": selected,
        "quantity": None if selected is None else selected.get("quantity"),
        "opportunity_id": row["opportunity_id"] if "opportunity_id" in keys else None,
        "rationale": row["rationale"] if "rationale" in keys else None,
        "source_quality": row["source_quality"] if "source_quality" in keys else None,
        "plan_version": row["plan_version"] if "plan_version" in keys else 1,
        "submitted_at": row["submitted_at"] if "submitted_at" in keys else None,
        "rejected_at": row["rejected_at"] if "rejected_at" in keys else None,
        "rejected_by": row["rejected_by"] if "rejected_by" in keys else None,
        "rejection_reason": row["rejection_reason"] if "rejection_reason" in keys else None,
        "cancelled_at": row["cancelled_at"] if "cancelled_at" in keys else None,
        "cancelled_by": row["cancelled_by"] if "cancelled_by" in keys else None,
        "cancel_reason": row["cancel_reason"] if "cancel_reason" in keys else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"] if "updated_at" in keys else None,
        "authorises_order": False,
    }


def _record_event(
    connection: sqlite3.Connection,
    plan_id: str,
    *,
    from_state: str | None,
    to_state: str,
    actor: str,
    action: str,
    detail: dict | None,
) -> None:
    connection.execute(
        """
        INSERT INTO trade_plan_event (
            event_id, plan_id, from_state, to_state, actor, action, detail_json, at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id("pevt"),
            plan_id,
            from_state,
            to_state,
            actor,
            action,
            None if detail is None else json.dumps(detail),
            utcnow(),
        ),
    )
