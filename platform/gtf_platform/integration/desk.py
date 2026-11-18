"""Trade plans, the research journal, portfolio reads, explanations, backup, and export.

Eligibility stays in nse.research. This module calls the existing journal and risk
functions. It does not place an order and it does not keep a second monthly counter.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import uuid
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from gtf_platform.config import Settings
from gtf_platform.errors import ApiError
from gtf_platform.integration import reference, sources

REFUSED = {"BLOCKED", "REJECTED", "DATA_INSUFFICIENT"}
DATA_READY_REASON = "DATA_READY is not claimed. Universe review (B11-R) and identity evidence are still open."
ACTIVE_JOB_STATES = frozenset({"PENDING_DATA", "VALIDATING", "RUNNING"})
FAILED_JOB_STATES = frozenset({"FAILED", "INTERRUPTED", "CANCELLED"})
SUCCESS_JOB_STATES = frozenset({"SUCCEEDED_COMPLETE", "SUCCEEDED_PARTIAL"})


def evaluate_data_ready(settings: Settings) -> dict:
    """Derive DATA_READY from authoritative limitation / certification signals.

    Fail closed: a missing or unavailable verdict never becomes ready. P0 certification
    incomplete always yields data_ready=false. This function never invents CERTIFIED_P0_DATA.
    """
    try:
        limitations = list(reference.limitation_list(settings))
    except Exception:
        return {
            "data_ready": False,
            "data_ready_reason": "DATA_READY verdict unavailable; fail closed.",
            "readiness_state": "UNAVAILABLE",
            "limitations": ["DATA_LIMITATIONS_UNAVAILABLE", "DATA_READY_NOT_CLAIMED"],
            "certified_p0_data": False,
        }
    blocked = any(
        code in limitations
        for code in (
            "DATA_READY_NOT_CLAIMED",
            "DATA_LIMITATIONS_UNAVAILABLE",
            "UNIVERSE_NOT_CONFIGURED",
            "UNIVERSE_UNVERIFIED",
        )
    )
    # Never invent READY / CERTIFIED_P0_DATA here. A future owner-approved wiring to a
    # real P0 certification verdict must replace this fail-closed return; do not flip
    # a local boolean.
    reason = DATA_READY_REASON
    if "DATA_LIMITATIONS_UNAVAILABLE" in limitations:
        reason = "DATA_READY verdict unavailable; fail closed."
    elif blocked:
        reason = DATA_READY_REASON
    else:
        reason = "DATA_READY requires an explicit certified P0 verdict; none is wired."
    return {
        "data_ready": False,
        "data_ready_reason": reason,
        "readiness_state": "NOT_READY" if limitations else "UNAVAILABLE",
        "limitations": limitations,
        "certified_p0_data": False,
    }


def overview_facts(connection, envelope: dict | None, scan_key: str | None, settings: Settings | None = None) -> dict:
    limitations = list((envelope or {}).get("limitations") or [])
    job = None
    if scan_key:
        row = connection.execute(
            "SELECT job_id, state, error_code, error_message FROM job WHERE result_ref = ? ORDER BY created_at DESC LIMIT 1",
            (scan_key,),
        ).fetchone()
        if row is not None:
            job = {"job_id": row["job_id"], "state": row["state"], "error_code": row["error_code"], "error_message": row["error_message"]}
    active_row = connection.execute(
        """
        SELECT job_id, state, error_code, error_message, result_ref
        FROM job
        WHERE state IN ('PENDING_DATA', 'VALIDATING', 'RUNNING')
        ORDER BY created_at DESC
        LIMIT 1
        """
    ).fetchone()
    active_job = None
    if active_row is not None:
        active_job = {
            "job_id": active_row["job_id"],
            "state": active_row["state"],
            "error_code": active_row["error_code"],
            "error_message": active_row["error_message"],
            "result_ref": active_row["result_ref"],
        }
    scan_due = _scan_due_state(connection, settings) if settings is not None else {
        "state": "UNAVAILABLE",
        "as_of": None,
        "reason": "Settings were not supplied",
    }
    readiness = (
        evaluate_data_ready(settings)
        if settings is not None
        else {
            "data_ready": False,
            "data_ready_reason": DATA_READY_REASON,
            "readiness_state": "NOT_READY",
            "limitations": ["DATA_READY_NOT_CLAIMED"],
            "certified_p0_data": False,
        }
    )
    job_phase = _job_phase(active_job, job, envelope)
    return {
        "job": job,
        "active_job": active_job,
        "scan_due": scan_due,
        "job_phase": job_phase,
        "limitations": limitations,
        "history_cut": _history_cut(envelope),
        "identity_findings": _identity_findings(envelope),
        "manifest_id": None if envelope is None else envelope.get("manifest_id"),
        "full_universe_scan": False if envelope is None else bool(envelope.get("full_universe_scan")),
        "data_ready": bool(readiness["data_ready"]),
        "data_ready_reason": readiness["data_ready_reason"],
        "readiness_state": readiness["readiness_state"],
        "certified_p0_data": bool(readiness.get("certified_p0_data")),
        "authorises_order": False,
    }


def _job_phase(active_job: dict | None, stored_job: dict | None, envelope: dict | None) -> str:
    """Map runner + scan completeness onto the P1 overview vocabulary."""
    if active_job is not None and active_job.get("state") in ACTIVE_JOB_STATES:
        return "RUNNING"
    state = None if stored_job is None else stored_job.get("state")
    if state in FAILED_JOB_STATES:
        return "FAILED"
    completeness = None if envelope is None else envelope.get("completeness")
    if completeness == "FAILED" or state in FAILED_JOB_STATES:
        return "FAILED"
    if completeness == "PARTIAL" or state == "SUCCEEDED_PARTIAL":
        # Partial is finished work that is not fully ready; never collapse into READY.
        return "NOT_READY"
    if completeness == "COMPLETE" or state == "SUCCEEDED_COMPLETE":
        return "READY"
    if stored_job is None and envelope is None:
        return "UNAVAILABLE"
    return "NOT_READY"


def _scan_due_state(connection, settings: Settings) -> dict:
    """Honest scan-due signal for overview. Never invents a due day when inputs are missing."""
    from gtf_platform.integration import schedule as schedule_mod

    if not schedule_mod._scheduler_enabled(settings, connection):
        return {"state": "NOT_READY", "as_of": None, "reason": "Scheduler is not enabled"}
    if settings.calendar_dir is None or settings.universe_path is None:
        return {"state": "UNAVAILABLE", "as_of": None, "reason": "Calendar or universe is not configured"}
    try:
        identity = sources.dataset_identity(settings)
    except Exception:
        return {"state": "UNAVAILABLE", "as_of": None, "reason": "Dataset identity is unavailable"}
    if identity is None:
        return {"state": "NOT_READY", "as_of": None, "reason": "No local dataset"}
    try:
        moment = datetime.now(timezone.utc)
        local = moment.astimezone(ZoneInfo("Asia/Kolkata"))
        day = local.date()
        if local.time() < time(15, 45):
            day = day - timedelta(days=1)
        due = schedule_mod._due_day(settings, day)
    except Exception:
        return {"state": "UNAVAILABLE", "as_of": None, "reason": "Due-day evaluation failed"}
    if due is None:
        return {"state": "NOT_READY", "as_of": None, "reason": "No scan is due"}
    return {"state": "READY", "as_of": due.isoformat(), "reason": None}


def coverage_facts(settings: Settings) -> dict:
    return reference.corporate_action_limitations(settings)


def explain_symbol(envelope: dict, symbol: str) -> dict:
    sources.ensure_repo_on_path()
    from nse.research.explain import why

    scan = envelope.get("scan") if isinstance(envelope.get("scan"), dict) else envelope
    if not isinstance(scan, dict) or "symbols" not in scan:
        raise ApiError(422, "DATA_INSUFFICIENT", "The stored scan has no explainable record")
    answer = why(scan, symbol.strip().upper())
    answer["changes_status"] = False
    answer["model"] = None
    return answer


def create_plan(
    connection,
    envelope: dict,
    scan_key: str,
    symbol: str,
    zone_id: str,
    *,
    opportunity_id: str | None = None,
    rationale: str | None = None,
    fixture: bool = False,
) -> dict:
    from gtf_platform.planning import service as planning

    return planning.create_plan(
        connection,
        envelope,
        scan_key,
        symbol,
        zone_id,
        opportunity_id=opportunity_id,
        rationale=rationale,
        fixture=fixture,
    )


def preview_plan(settings: Settings, connection, plan_id: str) -> dict:
    from gtf_platform.planning import service as planning

    plan = _plan_row(connection, plan_id)
    snapshot = json.loads(plan["snapshot_json"])
    candidate = snapshot.get("candidate") or {}
    config = _risk_config(settings, connection)
    combinations = [] if config is None else _combinations(candidate, config)
    quantity_state = "UNAVAILABLE" if config is None or not combinations else "AWAITING_BUFFER"
    note = None
    if config is None:
        note = "Capital and one risk percent are not saved in settings. Quantity stays empty."
    selected = json.loads(plan["selected_json"]) if plan["selected_json"] else None
    vs_actual = None
    if plan["entry_id"] is not None:
        vs_actual = planned_versus_actual(settings, int(plan["entry_id"]), selected)
    view = planning.enrich_preview(
        connection,
        plan_id,
        combinations=combinations,
        quantity_state=quantity_state,
        note=note,
        portfolio_checks=_portfolio_checks_for_candidate(settings, candidate),
        capacity=_capacity_snapshot(settings),
        risk_inputs=_risk_inputs(connection),
        planned_versus_actual=vs_actual,
    )
    view["later_scan"] = later_scan_comparison(connection, plan)
    return view


def approve_plan(settings: Settings, connection, plan_id: str, body: dict, scan: dict) -> dict:
    from gtf_platform.planning import service as planning
    from gtf_platform.planning.states import APPROVABLE

    plan = _plan_row(connection, plan_id)
    if plan["state"] == "APPROVED" and plan["entry_id"] is not None:
        view = planning.plan_view(connection, plan_id)
        view["authorises_order"] = False
        view["candidate_status_unchanged"] = plan["candidate_status"]
        return view
    if plan["state"] not in APPROVABLE:
        raise ApiError(409, "CONFLICT", "Plan state %s cannot be approved" % plan["state"])
    snapshot = json.loads(plan["snapshot_json"])
    candidate = snapshot["candidate"]
    if candidate.get("status") in REFUSED:
        raise ApiError(409, "CONFLICT", "A %s candidate cannot be approved" % candidate.get("status"))
    config = _risk_config(settings, connection)
    if config is None:
        raise ApiError(422, "DATA_INSUFFICIENT", "Save capital and a risk percent before approval")
    combos = _combinations(candidate, config)
    index = body.get("combination_index")
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(combos):
        raise ApiError(400, "REQUEST_INVALID", "combination_index must select one printed buffer")
    chosen = combos[index]
    if chosen.get("quantity") in (None, 0) or chosen.get("status") == "INVALID_LEVELS":
        raise ApiError(409, "CONFLICT", "The selected buffer has no valid quantity")
    checklist = _checklist(body.get("checklist"))
    note = body.get("alert_note")
    if not isinstance(note, str) or not note.strip():
        raise ApiError(400, "REQUEST_INVALID", "alert_note is required")
    resolution = body.get("manual_review_resolution")
    recorded_at = _match_journal_clock(body.get("recorded_at") or datetime.now(timezone.utc).isoformat(), scan.get("as_of"))
    sources.ensure_repo_on_path()
    from nse.research import store

    path = research_path(settings)
    research = store.open_store(str(path))
    try:
        store.import_scan(research, scan)
        entry_id = store.journal_add(research, {
            "scan_key": store.scan_key(scan),
            "symbol": candidate["symbol"],
            "zone_id": candidate["zone"]["zone_id"],
            "planned_entry": chosen["entry"],
            "planned_stop": chosen["stop"],
            "planned_target": chosen["target"],
            "quantity": int(chosen["quantity"]),
            "alert_note": note.strip(),
            "checklist": checklist,
            "recorded_at": recorded_at,
            "manual_review_resolution": resolution,
        }, request_key="approve:" + plan_id)
    except store.JournalRefused as exc:
        raise ApiError(409, "CONFLICT", str(exc)) from exc
    except store.StoreError as exc:
        raise ApiError(400, "REQUEST_INVALID", str(exc)) from exc
    finally:
        research.close()
    view = planning.mark_approved(connection, plan_id, entry_id=entry_id, selected=chosen, actor="owner")
    view["authorises_order"] = False
    view["candidate_status_unchanged"] = candidate.get("status")
    view["manual_execution"] = {
        "authorises_order": False,
        "instruction": (
            "Execution takes place manually outside the platform. "
            "Approving a plan does not submit an order."
        ),
    }
    return view


def journal_rows(settings: Settings, filters: dict | None = None) -> dict:
    path = research_path(settings)
    if not path.is_file():
        return {
            "entries": [],
            "total": 0,
            "limit": (filters or {}).get("limit", 100),
            "offset": (filters or {}).get("offset", 0),
            "note": "No research journal file exists yet.",
            "authorises_order": False,
            "evidence_class": "JOURNAL_DESCRIPTIVE",
        }
    sources.ensure_repo_on_path()
    from nse.research import store

    conn = store.open_readonly(str(path))
    try:
        return store.journal_query(conn, filters)
    except store.StoreError as exc:
        raise ApiError(400, "REQUEST_INVALID", str(exc)) from exc
    finally:
        conn.close()


def journal_detail(settings: Settings, entry_id: int) -> dict:
    path = research_path(settings)
    if not path.is_file():
        raise ApiError(404, "NOT_FOUND", "No research journal file exists yet.")
    sources.ensure_repo_on_path()
    from nse.research import store

    conn = store.open_readonly(str(path))
    try:
        detail = store.journal_entry_detail(conn, entry_id)
        detail["planned_versus_actual"] = store.journal_planned_versus_actual(conn, entry_id)
        return detail
    except store.StoreError as exc:
        raise ApiError(404, "NOT_FOUND", str(exc)) from exc
    finally:
        conn.close()


def journal_performance_view(settings: Settings, filters: dict | None = None) -> dict:
    path = research_path(settings)
    if not path.is_file():
        return {
            "evidence_class": "JOURNAL_DESCRIPTIVE",
            "totals": {"recorded_trades": 0},
            "note": "No research journal file exists yet.",
            "authorises_order": False,
        }
    sources.ensure_repo_on_path()
    from nse.research import store

    conn = store.open_readonly(str(path))
    try:
        return store.journal_performance(conn, filters)
    except store.StoreError as exc:
        raise ApiError(400, "REQUEST_INVALID", str(exc)) from exc
    finally:
        conn.close()


def journal_export_view(settings: Settings, filters: dict | None = None) -> dict:
    path = research_path(settings)
    if not path.is_file():
        return {
            "format": "gtf-journal-export-v1",
            "rows": [],
            "total": 0,
            "note": "No research journal file exists yet.",
            "authorises_order": False,
            "evidence_class": "JOURNAL_DESCRIPTIVE",
        }
    sources.ensure_repo_on_path()
    from nse.research import store

    conn = store.open_readonly(str(path))
    try:
        return store.journal_export(conn, filters)
    except store.StoreError as exc:
        raise ApiError(400, "REQUEST_INVALID", str(exc)) from exc
    finally:
        conn.close()


def add_journal_note(settings: Settings, entry_id: int, body: dict, request_key: str | None = None) -> dict:
    return _mutate(settings, lambda conn, store: store.journal_add_note(
        conn, entry_id,
        note_key=body.get("note_key"),
        at=_match_journal_clock(body.get("at"), _entry_scan_as_of(settings, entry_id)),
        kind=body.get("kind"),
        body=body.get("body"),
        actor=body.get("actor") or "owner",
        request_key=request_key,
    ))


def add_journal_review(settings: Settings, entry_id: int, body: dict, request_key: str | None = None) -> dict:
    return _mutate(settings, lambda conn, store: store.journal_add_review(
        conn, entry_id,
        review_key=body.get("review_key"),
        at=_match_journal_clock(body.get("at"), _entry_scan_as_of(settings, entry_id)),
        review_status=body.get("review_status"),
        outcome_class=body.get("outcome_class"),
        mistake_category=body.get("mistake_category"),
        note=body.get("note"),
        setup_label=body.get("setup_label"),
        rule_refs=body.get("rule_refs"),
        actor=body.get("actor") or "owner",
        request_key=request_key,
    ))


def add_journal_attachment(settings: Settings, entry_id: int, body: dict, request_key: str | None = None) -> dict:
    """Store image bytes under data_dir and register append-only metadata in the research journal."""
    import base64
    import hashlib
    import re

    sources.ensure_repo_on_path()
    from nse.research import store

    raw_b64 = body.get("content_base64")
    filename = body.get("filename")
    content_type = body.get("content_type")
    attachment_id = body.get("attachment_id")
    if not isinstance(raw_b64, str) or not raw_b64.strip():
        raise ApiError(400, "REQUEST_INVALID", "content_base64 is required")
    if not isinstance(filename, str) or not filename.strip():
        raise ApiError(400, "REQUEST_INVALID", "filename is required")
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise ApiError(400, "REQUEST_INVALID", "filename must be a safe basename")
    try:
        payload = base64.b64decode(raw_b64, validate=True)
    except Exception as exc:
        raise ApiError(400, "REQUEST_INVALID", "content_base64 is not valid base64") from exc
    if content_type not in store.ATTACHMENT_CONTENT_TYPES:
        raise ApiError(400, "REQUEST_INVALID", "unsupported content_type")
    if len(payload) > store.ATTACHMENT_MAX_BYTES:
        raise ApiError(400, "REQUEST_INVALID", "attachment exceeds size limit")
    # Require positive image magic that matches the declared content type.
    magic_ok = (
        (content_type == "image/png" and payload.startswith(b"\x89PNG\r\n\x1a\n"))
        or (content_type == "image/jpeg" and payload.startswith(b"\xff\xd8\xff"))
        or (content_type == "image/gif" and (payload.startswith(b"GIF87a") or payload.startswith(b"GIF89a")))
        or (content_type == "image/webp" and len(payload) >= 12 and payload.startswith(b"RIFF") and payload[8:12] == b"WEBP")
    )
    if not magic_ok:
        raise ApiError(400, "REQUEST_INVALID", "attachment bytes do not match the declared image content_type")
    digest = hashlib.sha256(payload).hexdigest()
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename)[:180]
    storage_name = "%s_%s" % ((attachment_id or "att").strip()[:40], safe_name)
    folder = settings.data_dir / "journal_attachments" / str(entry_id)
    folder.mkdir(parents=True, mode=0o700, exist_ok=True)
    target = folder / storage_name
    if target.exists():
        existing = target.read_bytes()
        if hashlib.sha256(existing).hexdigest() != digest:
            raise ApiError(409, "CONFLICT", "attachment storage name already used with different bytes")
    else:
        target.write_bytes(payload)
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass
    at = _match_journal_clock(body.get("at"), _entry_scan_as_of(settings, entry_id))
    registered = _mutate(settings, lambda conn, store_mod: store_mod.journal_register_attachment(
        conn, entry_id,
        attachment_id=attachment_id,
        at=at,
        filename=safe_name,
        content_type=content_type,
        size_bytes=len(payload),
        sha256=digest,
        storage_name=storage_name,
        note=body.get("note"),
        missing=False,
        request_key=request_key,
    ))
    registered["storage_relative"] = "journal_attachments/%s/%s" % (entry_id, storage_name)
    return registered


def read_journal_attachment(settings: Settings, entry_id: int, attachment_id: str) -> tuple[bytes, str, str]:
    path = research_path(settings)
    if not path.is_file():
        raise ApiError(404, "NOT_FOUND", "No research journal file exists yet.")
    sources.ensure_repo_on_path()
    from nse.research import store

    conn = store.open_readonly(str(path))
    try:
        rows = store._attachment_rows(conn, entry_id)
    finally:
        conn.close()
    match = next((row for row in rows if row["attachment_id"] == attachment_id), None)
    if match is None:
        raise ApiError(404, "NOT_FOUND", "Attachment was not found for this journal entry.")
    file_path = settings.data_dir / "journal_attachments" / str(entry_id) / match["storage_name"]
    # Path confinement: resolve and require the attachments root as parent.
    root = (settings.data_dir / "journal_attachments").resolve()
    try:
        resolved = file_path.resolve()
    except OSError as exc:
        raise ApiError(404, "NOT_FOUND", "Attachment file is missing.") from exc
    if root not in resolved.parents and resolved != root:
        raise ApiError(404, "NOT_FOUND", "Attachment path is invalid.")
    if not resolved.is_file():
        raise ApiError(404, "NOT_FOUND", "Attachment file is missing.")
    return resolved.read_bytes(), match["content_type"], match["filename"]


def submit_order(settings: Settings, entry_id: int, body: dict, request_key: str | None = None) -> dict:
    submitted = _match_journal_clock(body.get("submitted_at"), _entry_scan_as_of(settings, entry_id))
    return _mutate(settings, lambda conn, store: store.journal_order_submitted(
        conn, entry_id, submitted, body.get("order_ref"), body.get("note"), request_key=request_key,
    ))


def record_event(settings: Settings, entry_id: int, body: dict, request_key: str | None = None) -> dict:
    sources.ensure_repo_on_path()
    from nse.research import store

    calendar = _calendar(settings)
    path = research_path(settings)
    conn = store.open_store(str(path))
    try:
        at = _match_journal_clock(body.get("at"), _entry_scan_as_of(settings, entry_id))
        seq = store.journal_event(
            conn, entry_id, body.get("kind"), at,
            price=body.get("price"), note=body.get("note"), stop_level=body.get("stop_level"),
            calendar=calendar, revalidated=bool(body.get("revalidated")), request_key=request_key,
        )
        return {"entry_id": entry_id, "seq": seq, "authorises_order": False}
    except store.JournalRefused as exc:
        raise ApiError(409, "CONFLICT", str(exc)) from exc
    except store.StoreError as exc:
        raise ApiError(400, "REQUEST_INVALID", str(exc)) from exc
    finally:
        conn.close()


def record_execution(settings: Settings, entry_id: int, body: dict, request_key: str | None = None) -> dict:
    unknown = set(body) - {"side", "quantity", "price", "at", "print_key", "note", "revalidated"}
    if unknown:
        raise ApiError(400, "REQUEST_INVALID", "unknown field")
    sources.ensure_repo_on_path()
    from nse.research import store

    conn = store.open_store(str(research_path(settings)))
    try:
        at = _match_journal_clock(body.get("at"), _entry_scan_as_of(settings, entry_id))
        result = store.journal_execution(
            conn, entry_id, body.get("side"), body.get("quantity"), body.get("price"), at,
            body.get("print_key"), note=body.get("note"), calendar=_calendar(settings),
            revalidated=bool(body.get("revalidated")), request_key=request_key,
        )
        result["authorises_order"] = False
        return result
    except store.JournalRefused as exc:
        raise ApiError(409, "CONFLICT", str(exc)) from exc
    except store.StoreError as exc:
        raise ApiError(400, "REQUEST_INVALID", str(exc)) from exc
    finally:
        conn.close()


def record_charges(settings: Settings, entry_id: int, body: dict, request_key: str | None = None) -> dict:
    mode = body.get("mode")
    sources.ensure_repo_on_path()
    from nse.research import store

    conn = store.open_store(str(research_path(settings)))
    try:
        at = _match_journal_clock(body.get("at"), _entry_scan_as_of(settings, entry_id))
        if mode == "SCHEDULE":
            unknown = set(body) - {"mode", "schedule", "side", "quantity", "price", "at", "print_key"}
            if unknown:
                raise ApiError(400, "REQUEST_INVALID", "unknown field")
            result = store.journal_apply_schedule(
                conn, entry_id, body.get("schedule"), side=body.get("side"), quantity=body.get("quantity"),
                price=body.get("price"), at=at, print_key=body.get("print_key"),
            )
        elif mode == "ACTUAL":
            unknown = set(body) - {"mode", "lines", "at", "source"}
            if unknown:
                raise ApiError(400, "REQUEST_INVALID", "unknown field")
            result = store.journal_record_charges(
                conn, entry_id, body.get("lines"), at=at, source=body.get("source"), estimated=False,
                request_key=request_key,
            )
        else:
            raise ApiError(400, "REQUEST_INVALID", "mode must be SCHEDULE or ACTUAL")
        result["authorises_order"] = False
        result["note"] = "Charges are journal records. They are not a broker contract note."
        return result
    except store.JournalRefused as exc:
        raise ApiError(409, "CONFLICT", str(exc)) from exc
    except store.StoreError as exc:
        raise ApiError(400, "REQUEST_INVALID", str(exc)) from exc
    finally:
        conn.close()


def portfolio_view(settings: Settings, at: str) -> dict:
    sources.ensure_repo_on_path()
    from nse.research import inputs as inputs_mod
    from nse.research import store

    from gtf_platform.integration import valuation as valuation_mod

    path = research_path(settings)
    if not path.is_file():
        return {
            "state": "UNAVAILABLE",
            "reason": "No research journal file exists yet.",
            "sector": None,
            "sector_state": "UNAVAILABLE",
            "drawdown": None,
            "drawdown_state": "UNAVAILABLE",
            "valuation": None,
            "valuation_state": "UNAVAILABLE",
            "unrealised_pnl": "UNAVAILABLE",
            "authorises_order": False,
        }
    conn = store.open_readonly(str(path))
    try:
        from nse.research.models import IST

        raw = at or datetime.now(timezone.utc).isoformat()
        moment = inputs_mod.parse_as_of(raw)
        if moment.tzinfo is not None and moment.utcoffset() is not None:
            moment = moment.astimezone(IST).replace(tzinfo=None)
        try:
            book = store.portfolio_at(conn, moment)
        except store.StoreError as exc:
            raise ApiError(409, "CONFLICT", str(exc)) from exc
    finally:
        conn.close()
    positions = []
    for zone in book.get("zones_holding_allowance") or []:
        positions.append({
            "entry_id": zone.get("entry_id"),
            "symbol": zone.get("symbol"),
            "zone_id": zone.get("zone_id"),
            "reason": zone.get("reason"),
            "state": zone.get("state") or "UNKNOWN",
            "counts_as_open": bool(zone.get("counts_as_open")),
            "open_quantity": zone.get("open_quantity"),
            "requested_quantity": zone.get("requested_quantity"),
            "executed_entry_quantity": zone.get("executed_entry_quantity"),
            "executed_exit_quantity": zone.get("executed_exit_quantity"),
            "unfilled_quantity": zone.get("unfilled_quantity"),
            "average_entry_price": zone.get("average_entry_price"),
            "average_exit_price": zone.get("average_exit_price"),
            "realised_pnl": zone.get("realised_pnl"),
            "unrealised": zone.get("unrealised"),
            "fill_source": zone.get("fill_source"),
            "planned_entry": zone.get("planned_entry"),
            "planned_stop": zone.get("planned_stop"),
            "planned_target": zone.get("planned_target"),
            "locked_stop": zone.get("locked_stop"),
        })
    marked = valuation_mod.mark_positions(settings, positions, moment)
    return {
        "as_of": book.get("as_of") or (moment.isoformat() if hasattr(moment, "isoformat") else at),
        "ist_month": book.get("ist_month"),
        "trades_triggered_this_month": book.get("trades_triggered_this_month"),
        "monthly_cap": book.get("monthly_cap"),
        "open_positions": book.get("open_positions"),
        "open_position_cap": book.get("open_position_cap"),
        "zones": marked["positions"],
        "sector": None,
        "sector_state": "UNAVAILABLE",
        "drawdown": None,
        "drawdown_state": "UNAVAILABLE",
        "valuation": marked["valuation"],
        "valuation_state": marked["valuation_state"],
        "valuation_reason": marked.get("valuation_reason"),
        "unrealised_pnl": marked["unrealised_pnl"],
        "exposure": marked.get("exposure"),
        "exposure_state": marked.get("exposure_state"),
        "portfolio_risk": marked.get("portfolio_risk"),
        "portfolio_risk_state": marked.get("portfolio_risk_state"),
        "research_use": marked.get("research_use"),
        "source": book.get("source"),
        "authorises_order": False,
        "note": (
            "Counts come from the research journal only. Valuation uses the last accepted "
            "EOD close on or before the valuation date and prints that close's date. "
            "Position risk uses remaining open quantity and the locked or planned stop. "
            "Missing closes or stops stay UNAVAILABLE. Sector and live drawdown stay UNAVAILABLE. "
            "This is not an order."
        ),
    }


def export_report(settings: Settings, scan_key: str, name: str) -> tuple[bytes, str]:
    allowed = {"candidates.csv", "fresh_zones.csv", "blocked_zones.csv", "data_quality.csv", "summary.json", "scan.json", "readiness.json", "run_manifest.json"}
    if name not in allowed:
        raise ApiError(400, "REQUEST_INVALID", "Unknown report file")
    folder = settings.data_dir / "reports" / scan_key
    path = folder / name
    if not path.is_file():
        raise ApiError(404, "NOT_FOUND", "That report was not written for this scan")
    return path.read_bytes(), "text/csv" if name.endswith(".csv") else "application/json"


def backup_to(settings: Settings, directory: Path) -> dict:
    """Consistent SQLite backup into a new directory. Does not replace the live files.

    The copy is not a verified backup until restore_copy checks it. The historical
    bhavcopy archive under nse/data/eod/raw is not included.
    """
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(directory, 0o700)
    copied = []
    counts = {}
    required = _required_backup_sqlite(settings)

    def _scrub_incomplete_backup() -> None:
        for name in list(copied):
            path = directory / name
            if path.is_file():
                path.unlink()
        copied.clear()
        counts.clear()

    for source, name in _backup_sources(settings):
        if source is None:
            continue
        if not source.exists() or source.is_dir():
            if name in required:
                _scrub_incomplete_backup()
                raise ApiError(422, "DATA_INSUFFICIENT", "Backup refused: required %s is missing" % name)
            continue
        target = directory / name
        if target.exists():
            raise ApiError(409, "CONFLICT", "Backup refused to overwrite %s" % name)
        if target.resolve() == source.resolve():
            raise ApiError(409, "CONFLICT", "Backup refused to overwrite the live database")
        partial = target.with_name(target.name + ".partial")
        if partial.exists():
            partial.unlink()
        try:
            if source.suffix == ".sqlite" or source.name.endswith(".sqlite"):
                _sqlite_backup(source, partial)
                os.chmod(partial, 0o600)
                os.replace(partial, target)
                counts[name] = _table_counts(target)
            else:
                shutil.copy2(source, partial)
                os.chmod(partial, 0o600)
                os.replace(partial, target)
        except Exception:
            if partial.exists():
                partial.unlink()
            _scrub_incomplete_backup()
            raise
        os.chmod(target, 0o600)
        copied.append(name)
    missing_required = sorted(name for name in required if name not in copied)
    if missing_required:
        _scrub_incomplete_backup()
        raise ApiError(
            422,
            "DATA_INSUFFICIENT",
            "Backup refused: required %s missing from the copy" % ", ".join(missing_required),
        )
    manifest = {
        "backup_format": 1,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": copied,
        "counts": counts,
        "includes_bhavcopy_archive": False,
        "status": "BACKUP_NOT_VERIFIED",
        "note": "Run restore-check before treating this copy as recoverable. Raw bhavcopies are not in this backup.",
    }
    manifest_path = directory / "backup_manifest.json"
    if manifest_path.exists():
        raise ApiError(409, "CONFLICT", "Backup refused to overwrite backup_manifest.json")
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    os.chmod(manifest_path, 0o600)
    copied.append("backup_manifest.json")
    return {
        "directory": str(directory),
        "files": copied,
        "counts": counts,
        "live_files_unchanged": True,
        "status": "BACKUP_NOT_VERIFIED",
        "includes_bhavcopy_archive": False,
    }


def restore_copy(settings: Settings, backup_dir: Path) -> dict:
    """Copy a backup into a new restore-checks directory and verify it. The live files stay put."""
    if not backup_dir.is_dir():
        raise ApiError(404, "NOT_FOUND", "Backup directory was not found")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    dest = settings.data_dir / "restore-checks" / stamp
    partial = dest.with_name(dest.name + ".partial")
    partial.mkdir(parents=True, mode=0o700)
    os.chmod(partial, 0o700)
    live = {path.resolve() for path, _name in _backup_sources(settings) if path is not None}
    if partial.resolve() in live or dest.resolve() in live:
        raise ApiError(409, "CONFLICT", "Restore refused to use a live database path")
    for path in live:
        if path == partial.resolve() or str(path).startswith(str(partial.resolve())):
            raise ApiError(409, "CONFLICT", "Restore refused to use a live database path")
    copied = []
    restored_counts = {}
    backup_counts = {}
    try:
        expected = _expected_backup_files(backup_dir, settings)
        for name in ("platform.sqlite", "research.sqlite", "manifest.csv"):
            source = backup_dir / name
            if not source.is_file():
                if name in expected:
                    raise ApiError(422, "DATA_INSUFFICIENT", "Backup is incomplete: missing %s" % name)
                continue
            target = partial / name
            if target.resolve() in live:
                raise ApiError(409, "CONFLICT", "Restore refused to use a live database path")
            shutil.copy2(source, target)
            os.chmod(target, 0o600)
            if name.endswith(".sqlite"):
                _integrity(target)
                restored_counts[name] = _table_counts(target)
                backup_counts[name] = _table_counts(source)
                if restored_counts[name] != backup_counts[name]:
                    raise ApiError(422, "DATA_INSUFFICIENT", "Restored row counts do not match the backup")
            copied.append(name)
        if not copied:
            raise ApiError(422, "DATA_INSUFFICIENT", "Backup directory has no database to check")
        missing_expected = [name for name in expected if name not in copied]
        if missing_expected:
            raise ApiError(
                422,
                "DATA_INSUFFICIENT",
                "Backup is incomplete: missing %s" % ", ".join(missing_expected),
            )
        os.replace(partial, dest)
    except Exception:
        if partial.exists():
            shutil.rmtree(partial, ignore_errors=True)
        raise
    live_counts = {}
    for source, name in _backup_sources(settings):
        if source is not None and source.is_file() and name.endswith(".sqlite"):
            live_counts[name] = _table_counts(source)
    return {
        "restored_to": str(dest),
        "files": copied,
        "backup_counts": backup_counts,
        "restored_counts": restored_counts,
        "live_counts": live_counts,
        "counts_match_backup": True,
        "counts_match_live": live_counts == restored_counts,
        "live_files_unchanged": True,
        "status": "RESTORE_CHECK_PASSED",
        "includes_bhavcopy_archive": False,
    }


def run_backtest(settings: Settings, body: dict) -> dict:
    cost = body.get("cost_pct_per_side")
    slip = body.get("slippage_pct_per_side")
    if not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
        raise ApiError(422, "DATA_INSUFFICIENT", "An owner-supplied cost_pct_per_side is required. No brokerage tariff is built in.")
    if not isinstance(slip, (int, float)) or isinstance(slip, bool) or slip < 0:
        raise ApiError(422, "DATA_INSUFFICIENT", "slippage_pct_per_side is required")
    if settings.calendar_dir is None:
        raise ApiError(422, "DATA_INSUFFICIENT", "A backtest requires the trading calendar")
    symbols = body.get("symbols") or []
    if not isinstance(symbols, list) or not symbols:
        raise ApiError(400, "REQUEST_INVALID", "symbols is required")
    sources.ensure_repo_on_path()
    from nse.research import backtest, inputs as inputs_mod, scanner

    try:
        start = inputs_mod.parse_as_of(body.get("start") or "")
        end = inputs_mod.parse_as_of(body.get("end") or "")
    except ValueError as exc:
        raise ApiError(400, "REQUEST_INVALID", "start and end must be timestamps") from exc
    loaded = inputs_mod.load(
        [str(symbol).upper() for symbol in symbols],
        csv_dir=str(settings.csv_dir) if settings.csv_dir else None,
        bhavcopy_dir=str(settings.bhavcopy_dir) if settings.bhavcopy_dir else None,
        manifest=str(settings.eod_manifest) if settings.eod_manifest else None,
        series=settings.series,
        source_label=settings.source_label,
        price_adjustment=settings.price_adjustment,
        instrument_records=str(settings.instruments_path) if settings.instruments_path else None,
    )
    calendar = sources.load_calendar(settings)
    times = sorted({candle.end for item in loaded for candle in item.candles if start <= candle.end <= end})
    if not times:
        raise ApiError(422, "DATA_INSUFFICIENT", "No candles fall inside the requested window")
    config = scanner.ScanConfig(
        as_of=times[-1],
        calendar=calendar,
        calendar_label="NSE",
        trade_type="MIT",
        generated_at=None,
    )
    model = backtest.ExecutionModel(
        entry="ENTRY_MIN",
        stop="NORMAL_WIDE",
        target="STRUCTURAL",
        statuses=("ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING",),
        entry_expiry_sessions=10,
        cancel_if_target_first=True,
        gap_fill="AT_OPEN",
        same_bar="STOP_FIRST",
        cost_pct_per_side=float(cost),
        slippage_pct_per_side=float(slip),
    )
    result = backtest.run(loaded, times, config, model)
    limitations = list(result.get("limitations") or [])
    metrics = (result.get("metrics") or {}).get("ALL") or {}
    return {
        "metrics": metrics,
        "sample_size": metrics.get("closed"),
        "limitations": limitations,
        "not_performance_evidence": True,
        "release_gate_r4": "OPEN",
        "assumptions": {
            "entry": "ENTRY_MIN",
            "stop": "NORMAL_WIDE",
            "target": "STRUCTURAL",
            "cost_pct_per_side": float(cost),
            "slippage_pct_per_side": float(slip),
        },
        "cost_note": "The percentages were typed for this run. They are not a dated Zerodha schedule.",
        "authorises_order": False,
    }


def _checklist(raw) -> dict:
    """Require an explicit true/false for every CHECKLIST code. Do not invent answers."""
    from nse.research import models

    if not isinstance(raw, dict):
        raise ApiError(400, "REQUEST_INVALID", "checklist must map every CHECKLIST code to true or false")
    codes = [item[0] for item in models.CHECKLIST]
    missing = [code for code in codes if code not in raw]
    extra = sorted(set(raw) - set(codes))
    if missing or extra:
        raise ApiError(
            400,
            "REQUEST_INVALID",
            "checklist must confirm exactly the CHECKLIST codes; missing: %s; unknown: %s"
            % (", ".join(missing) or "-", ", ".join(extra) or "-"),
        )
    not_bool = [code for code in codes if not isinstance(raw[code], bool)]
    if not_bool:
        raise ApiError(
            400,
            "REQUEST_INVALID",
            "checklist codes not explicitly true or false: %s" % ", ".join(not_bool),
        )
    return {code: raw[code] for code in codes}


def _match_journal_clock(value, scan_as_of) -> str:
    """Journal comparisons refuse a mix of naive and aware times.

    Stored scan times are naive exchange-local IST. A browser timestamp with an offset is
    converted to that same clock before it reaches the research journal. A timestamp that
    already matches the scan is left unchanged.
    """
    if not isinstance(value, str) or not value.strip():
        raise ApiError(400, "REQUEST_INVALID", "A journal time is required")
    try:
        moment = datetime.fromisoformat(value)
        scan = datetime.fromisoformat(scan_as_of) if isinstance(scan_as_of, str) and scan_as_of else None
    except ValueError as exc:
        raise ApiError(400, "REQUEST_INVALID", "A journal time must be an ISO date-time") from exc
    if scan is None:
        return value
    scan_aware = scan.tzinfo is not None and scan.utcoffset() is not None
    moment_aware = moment.tzinfo is not None and moment.utcoffset() is not None
    if scan_aware == moment_aware:
        return value
    sources.ensure_repo_on_path()
    from nse.research.models import IST

    if moment_aware:
        return moment.astimezone(IST).replace(tzinfo=None).isoformat(timespec="seconds")
    return moment.replace(tzinfo=IST).isoformat()


def _entry_scan_as_of(settings: Settings, entry_id: int):
    path = research_path(settings)
    if not path.is_file():
        return None
    sources.ensure_repo_on_path()
    from nse.research import store

    conn = store.open_readonly(str(path))
    try:
        row = conn.execute(
            "SELECT s.as_of FROM journal_entries j JOIN scans s ON s.scan_key = j.scan_key WHERE j.entry_id = ?",
            (entry_id,),
        ).fetchone()
    finally:
        conn.close()
    return None if row is None else row["as_of"]


def research_path(settings: Settings) -> Path:
    if settings.research_db is not None:
        return settings.research_db
    return settings.data_dir / "research.sqlite"


def _history_cut(envelope: dict | None) -> dict:
    if not envelope:
        return {"applied": None, "state": "UNAVAILABLE"}
    code = "HISTORY_STARTS_AFTER_UNRESOLVED_DATE"
    symbols = []
    for item in envelope.get("symbols") or []:
        limits = item.get("limitations") or []
        reasons = item.get("reasons") or []
        if code in limits or any(code in str(reason) for reason in reasons):
            symbols.append(item.get("symbol"))
    return {"applied": bool(symbols), "symbols": symbols, "code": code if symbols else None}


def _identity_findings(envelope: dict | None) -> list[str]:
    found = []
    for item in (envelope or {}).get("symbols") or []:
        for finding in item.get("findings") or []:
            if finding.get("code") == "ISIN_CHANGED_WITHOUT_RECORD":
                found.append(item.get("symbol"))
    return sorted(set(found))


def _candidate(envelope: dict, symbol: str, zone_id: str) -> dict:
    wanted = symbol.strip().upper()
    for item in envelope.get("symbols") or []:
        if item.get("symbol") != wanted:
            continue
        for candidate in item.get("candidates") or []:
            zone = candidate.get("zone") or {}
            if zone.get("zone_id") == zone_id:
                return candidate
    scan = envelope.get("scan") if isinstance(envelope.get("scan"), dict) else None
    if scan:
        return _candidate(scan, symbol, zone_id)
    raise ApiError(404, "NOT_FOUND", "Candidate was not in the stored scan")


def _combinations(candidate: dict, config) -> list[dict]:
    sources.ensure_repo_on_path()
    from nse.research.risk import plan_trade

    levels = candidate.get("levels") or {}
    entries = [value for value in (levels.get("entry") or []) if value is not None]
    stops = [value for pair in (levels.get("sl") or {}).values() for value in pair if value is not None]
    gates = [gate for gate in candidate.get("gates") or [] if gate.get("gate") == "G7"]
    target = ((gates[0].get("evidence") or {}).get("target") or {}).get("proximal") if gates else None
    if target is None:
        return []
    rows = []
    for entry in sorted(set(entries)):
        for stop in sorted(set(stops)):
            planned = plan_trade(entry, stop, target, config, False)
            planned["target"] = target
            rows.append(planned)
    return rows


def _risk_config(settings: Settings, connection):
    sources.ensure_repo_on_path()
    from gtf_platform.store import read_settings
    from nse.research.risk import RiskConfig

    values = read_settings(connection)
    capital = values.get("capital")
    pct = values.get("rpt_pct")
    stage = values.get("risk_stage")
    if capital in (None, "") or pct in (None, ""):
        return None
    try:
        return RiskConfig(capital=float(capital), rpt_pct=float(pct), stage=stage or None)
    except (TypeError, ValueError):
        return None


# --- P4-IR-04 plan <-> journal consistency ------------------------------------------
#
# Consistency model (two SQLite files, so no cross-file atomic commit):
#   1. The research journal is written first and is authoritative.
#   2. The platform plan row mirrors a terminal journal state (CANCELLED/EXPIRED)
#      in the same request that wrote the journal event (best effort).
#   3. If step 2 did not run (crash, journal edited by the research CLI), every
#      plan read and app startup re-runs the idempotent mirror, so the plan is
#      repaired before it is shown. Until then a read reports journal_sync.
# This is recoverable (repair-on-read) consistency, not an atomic commit.

PLAN_CONSISTENT = {
    "APPROVED": frozenset({"PLANNED", "OPEN", "CLOSED"}),
    "CANCELLED": frozenset({"CANCELLED"}),
    "EXPIRED": frozenset({"EXPIRED"}),
}


def journal_entry_states(settings: Settings, links: list[tuple[str, int, str, str]],
                         invalidated: set[str] | None = None) -> dict[str, str] | None:
    """plan_id -> journal state for each (plan_id, entry_id, symbol, zone_id) link.

    Returns "MISSING" when the entry is absent and "IDENTITY_MISMATCH" when the entry is not
    the one this plan approved: a different symbol or zone, or the journal's idempotency record
    for request key ``approve:<plan_id>`` names another entry (a recreated or swapped journal
    reuses entry numbers). None when the journal is unreadable.
    """
    if invalidated is None:
        invalidated = set()
    if not links:
        return {}
    path = research_path(settings)
    if not path.is_file():
        return None
    sources.ensure_repo_on_path()
    from nse.research import store

    try:
        conn = store.open_readonly(str(path))
    except Exception:
        return None
    try:
        has_keys = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'journal_idempotency'"
        ).fetchone() is not None
        found: dict[str, str] = {}
        for plan_id, entry_id, symbol, zone_id in links:
            entry = conn.execute(
                "SELECT symbol, zone_id FROM journal_entries WHERE entry_id = ?", (entry_id,)
            ).fetchone()
            if entry is None:
                found[plan_id] = "MISSING"
                continue
            if entry["symbol"] != symbol or entry["zone_id"] != zone_id:
                found[plan_id] = "IDENTITY_MISMATCH"
                continue
            if has_keys:
                bound = conn.execute(
                    "SELECT entry_id FROM journal_idempotency WHERE request_key = ?", ("approve:" + plan_id,)
                ).fetchone()
                if bound is None or bound["entry_id"] != entry_id:
                    found[plan_id] = "IDENTITY_MISMATCH"
                    continue
            events = store.journal_events(conn, entry_id)
            found[plan_id] = store._state(events)[0]
            if any(event["kind"] == "ZONE_INVALIDATED" for event in events):
                invalidated.add(plan_id)
        return found
    except Exception:
        return None
    finally:
        conn.close()


def sync_plans_from_journal(settings: Settings, connection, *, plan_ids: list[str] | None = None,
                            entry_id: int | None = None) -> dict:
    """Mirror terminal journal states onto linked plans and report per-plan status.

    Returns {"plans": {plan_id: {"journal_state", "journal_sync"}}, "synced": [...]}.
    Caller holds the platform write transaction. Only APPROVED plans can be written; a plan
    whose entry fails the identity check is reported and never written.
    """
    from gtf_platform.planning import service as planning

    clauses, params = ["entry_id IS NOT NULL"], []
    if plan_ids is not None:
        if not plan_ids:
            return {"plans": {}, "synced": []}
        clauses.append("plan_id IN (%s)" % ",".join("?" * len(plan_ids)))
        params.extend(plan_ids)
    if entry_id is not None:
        clauses.append("entry_id = ?")
        params.append(int(entry_id))
    rows = connection.execute(
        "SELECT plan_id, entry_id, state, symbol, zone_id FROM trade_plan WHERE %s" % " AND ".join(clauses), params
    ).fetchall()
    invalidated: set[str] = set()
    states = journal_entry_states(
        settings, [(row["plan_id"], int(row["entry_id"]), row["symbol"], row["zone_id"]) for row in rows], invalidated
    )
    report: dict[str, dict] = {}
    synced: list[str] = []
    for row in rows:
        plan_id, linked, plan_state = row["plan_id"], int(row["entry_id"]), row["state"]
        if states is None:
            report[plan_id] = {"journal_state": None, "journal_sync": "JOURNAL_UNAVAILABLE"}
            continue
        journal_state = states.get(plan_id, "MISSING")
        if journal_state == "MISSING":
            report[plan_id] = {"journal_state": None, "journal_sync": "JOURNAL_ENTRY_MISSING"}
            continue
        if journal_state == "IDENTITY_MISMATCH":
            report[plan_id] = {"journal_state": None, "journal_sync": "JOURNAL_IDENTITY_MISMATCH"}
            continue
        if plan_state == "APPROVED" and journal_state in planning.JOURNAL_TERMINAL_TO_PLAN:
            if planning.mirror_journal_terminal(connection, plan_id, entry_id=linked, journal_state=journal_state):
                synced.append(plan_id)
            plan_state = connection.execute(
                "SELECT state FROM trade_plan WHERE plan_id = ?", (plan_id,)
            ).fetchone()["state"]
        consistent = journal_state in PLAN_CONSISTENT.get(plan_state, frozenset())
        report[plan_id] = {
            "journal_state": journal_state,
            "journal_sync": "IN_SYNC" if consistent else "CONFLICT",
            "journal_zone_invalidated": plan_id in invalidated,
        }
    return {"plans": report, "synced": synced}


def annotate_journal(view: dict, report: dict) -> dict:
    info = (report.get("plans") or {}).get(view.get("plan_id"))
    if info is None:
        info = {"journal_state": None, "journal_sync": "NO_JOURNAL_ENTRY" if view.get("entry_id") is None else "JOURNAL_UNAVAILABLE"}
    view["journal_state"] = info["journal_state"]
    view["journal_sync"] = info["journal_sync"]
    view["journal_zone_invalidated"] = bool(info.get("journal_zone_invalidated"))
    return view


# --- FR-5.9 / TP-010: later scan versus the plan's stored candidate ---------------------

_COMPARED_FIELDS = (
    ("status", lambda c: c.get("status")),
    ("entry_range", lambda c: (c.get("levels") or {}).get("entry")),
    ("stop_ranges", lambda c: (c.get("levels") or {}).get("sl")),
    ("overlay_status", lambda c: (c.get("zone") or {}).get("overlay_status")),
    ("test_count", lambda c: (c.get("zone") or {}).get("test_count")),
    ("proximal", lambda c: (c.get("zone") or {}).get("proximal")),
    ("distal", lambda c: (c.get("zone") or {}).get("distal")),
)


def _find_candidate(envelope: dict, symbol: str, zone_id: str, tf: str | None) -> tuple[dict | None, dict | None, dict | None]:
    """(symbol_row, candidate, blocked_zone) for one stored envelope. Never raises.

    A zone matches on zone_id and, when the plan knows it, the zone timeframe: zone ids are
    built from candle positions and are not unique across timeframes.
    """
    pools = [envelope]
    if isinstance(envelope.get("scan"), dict):
        pools.append(envelope["scan"])

    def same(zone: dict) -> bool:
        return zone.get("zone_id") == zone_id and (tf is None or zone.get("tf") in (None, tf))

    row_found = None
    for pool in pools:
        for item in pool.get("symbols") or []:
            if item.get("symbol") != symbol:
                continue
            row_found = row_found or item
            for candidate in item.get("candidates") or []:
                if same(candidate.get("zone") or {}):
                    return item, candidate, None
            for blocked in item.get("blocked_zones") or []:
                if isinstance(blocked, dict) and same(blocked):
                    return item, None, blocked
    return row_found, None, None


def later_scan_comparison(connection, plan) -> dict:
    """Compare the plan's frozen candidate with the latest later stored scan of the same symbol.

    Read-only. The plan version is never overwritten (FR-5.9). Only scans with the same fixture
    flag, trade type, and dataset_id are compared: zone ids are not stable across datasets.
    """
    base = connection.execute(
        "SELECT as_of, fixture, created_at, trade_type, dataset_id FROM scan_result WHERE scan_key = ?",
        (plan["scan_key"],),
    ).fetchone()
    if base is None:
        return {"state": "UNAVAILABLE", "reason": "The plan's stored scan is no longer present.", "differences": []}
    snapshot = json.loads(plan["snapshot_json"])
    frozen = snapshot.get("candidate") or {}
    tf = (frozen.get("zone") or {}).get("tf") or frozen.get("execution_tf")
    rows = connection.execute(
        """
        SELECT scan_key, as_of, created_at, envelope_json FROM scan_result
        WHERE fixture = ? AND trade_type = ? AND dataset_id IS ? AND scan_key != ?
          AND (as_of > ? OR (as_of = ? AND created_at > ?))
        ORDER BY as_of DESC, created_at DESC LIMIT 50
        """,
        (base["fixture"], base["trade_type"], base["dataset_id"], plan["scan_key"],
         base["as_of"], base["as_of"], base["created_at"]),
    ).fetchall()
    for row in rows:
        try:
            envelope = json.loads(row["envelope_json"])
        except (TypeError, ValueError):
            continue
        symbol_row, candidate, blocked = _find_candidate(envelope, plan["symbol"], plan["zone_id"], tf)
        if symbol_row is None:
            continue  # that scan did not cover the symbol; it says nothing about the plan
        later = {"scan_key": row["scan_key"], "as_of": row["as_of"], "completeness": envelope.get("completeness")}
        symbol_status = symbol_row.get("status")
        if candidate is None and blocked is None and symbol_status != "EVALUATED" and symbol_status != "NO_FRESH_EXECUTION_ZONE":
            return {
                **later,
                "state": "LATER_RESULT_NOT_EVALUATED",
                "later_symbol_status": symbol_status,
                "differences": [],
                "reason": "The later scan recorded %s for this symbol, so it says nothing about this zone. "
                "The approved version is unchanged." % (symbol_status or "no status"),
            }
        if candidate is None:
            return {
                **later,
                "state": "ZONE_NOT_A_CANDIDATE",
                "later_disposition": None if blocked is None else blocked.get("disposition"),
                "later_overlay_status": None if blocked is None else blocked.get("overlay_status"),
                "differences": [],
                "reason": "The later scan evaluated this symbol and holds no candidate for this zone"
                + ("" if blocked is None else " (it is in blocked_zones)") + ". The approved version is unchanged.",
            }
        differences = []
        for name, read in _COMPARED_FIELDS:
            before, after = read(frozen), read(candidate)
            if before != after:
                differences.append({"field": name, "plan": before, "later_scan": after})
        return {
            **later,
            "state": "CHANGED" if differences else "UNCHANGED",
            "differences": differences,
            "reason": None if not differences else "A later scan changed this candidate. The plan keeps its own version.",
        }
    return {"state": "NO_LATER_SCAN", "differences": [], "reason": None}


def _plan_row(connection, plan_id: str):
    row = connection.execute("SELECT * FROM trade_plan WHERE plan_id = ?", (plan_id,)).fetchone()
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Plan was not found")
    return row


def _plan_view(connection, plan_id: str) -> dict:
    from gtf_platform.planning import service as planning

    return planning.plan_view(connection, plan_id)


def planned_versus_actual(settings: Settings, entry_id: int, selected: dict | None) -> dict:
    """Compare approved plan levels with recorded journal prints. Never invents fills."""
    path = research_path(settings)
    if not path.is_file():
        return {
            "state": "UNAVAILABLE",
            "reason": "No research journal file exists yet.",
            "authorises_order": False,
        }
    sources.ensure_repo_on_path()
    from nse.research import store

    conn = store.open_readonly(str(path))
    try:
        entry = conn.execute(
            "SELECT * FROM journal_entries WHERE entry_id = ?", (entry_id,)
        ).fetchone()
        if entry is None:
            return {"state": "UNAVAILABLE", "reason": "Journal entry was not found.", "authorises_order": False}
        events = store.journal_events(conn, entry_id)
        executions = store._execution_rows(conn, entry_id)
        book = store.position_book(conn, entry_id, entry["quantity"], events, None)
    finally:
        conn.close()
    planned = {
        "entry": entry["planned_entry"] if selected is None else (selected or {}).get("entry", entry["planned_entry"]),
        "stop": entry["planned_stop"] if selected is None else (selected or {}).get("stop", entry["planned_stop"]),
        "target": entry["planned_target"] if selected is None else (selected or {}).get("target", entry["planned_target"]),
        "quantity": entry["quantity"],
    }
    entry_prints = [row for row in executions if row.get("side") == "ENTRY"]
    exit_prints = [row for row in executions if row.get("side") == "EXIT"]
    actual_qty = book.get("executed_entry_quantity")
    actual_avg = book.get("average_entry_price")
    entry_delta = None
    try:
        if actual_avg is not None:
            entry_delta = float(actual_avg) - float(planned["entry"])
    except (TypeError, ValueError):
        entry_delta = None
    qty_delta = None if actual_qty is None else actual_qty - int(planned["quantity"] or 0)
    return {
        "state": "COMPARED" if entry_prints or exit_prints else "PLANNED_ONLY",
        "planned": planned,
        "actual": {
            "entry_prints": len(entry_prints),
            "exit_prints": len(exit_prints),
            "executed_entry_quantity": actual_qty,
            "average_entry_price": actual_avg,
            "open_quantity": book.get("open_quantity"),
            "unfilled_quantity": book.get("unfilled_quantity"),
        },
        "deltas": {
            "entry_price": entry_delta,
            "quantity_filled_vs_planned": qty_delta,
        },
        "authorises_order": False,
        "note": "Fills are owner-recorded prints. This comparison does not retrieve broker data.",
    }


def _portfolio_checks_for_candidate(settings: Settings, candidate: dict) -> list[dict]:
    path = research_path(settings)
    symbol = candidate.get("symbol")
    zone_id = (candidate.get("zone") or {}).get("zone_id")
    trade_type = candidate.get("trade_type") or "MIT"
    sources.ensure_repo_on_path()
    from nse.research.pipeline import PortfolioState, portfolio_checks

    if not path.is_file():
        return portfolio_checks(PortfolioState(), symbol, zone_id, trade_type)
    from nse.research import store
    from nse.research.models import IST

    conn = store.open_readonly(str(path))
    try:
        moment = datetime.now(timezone.utc).astimezone(IST).replace(tzinfo=None)
        state = PortfolioState.from_journal(conn, moment)
    except Exception:
        state = PortfolioState()
    finally:
        conn.close()
    return portfolio_checks(state, symbol, zone_id, trade_type)


def _capacity_snapshot(settings: Settings) -> dict:
    sources.ensure_repo_on_path()
    from nse.research import models as research_models

    monthly = research_models.OWNER_MONTHLY_TRADE_CAP
    opens = research_models.OWNER_MAX_OPEN_POSITIONS
    try:
        book = portfolio_view(settings, "")
    except ApiError:
        return {
            "state": "UNAVAILABLE",
            "monthly_cap": monthly,
            "open_position_cap": opens,
            "authorises_order": False,
        }
    return {
        "state": book.get("state") or "AVAILABLE",
        "trades_triggered_this_month": book.get("trades_triggered_this_month"),
        "monthly_cap": book.get("monthly_cap") if book.get("monthly_cap") is not None else monthly,
        "open_positions": book.get("open_positions"),
        "open_position_cap": book.get("open_position_cap") if book.get("open_position_cap") is not None else opens,
        "authorises_order": False,
        "note": "Closing a position releases open capacity only; monthly allowance is not restored.",
    }


def _risk_inputs(connection) -> dict:
    from gtf_platform.store import read_settings

    values = read_settings(connection)
    capital = values.get("capital")
    pct = values.get("rpt_pct")
    stage = values.get("risk_stage")
    configured = capital not in (None, "") and pct not in (None, "")
    return {
        "capital": None if capital in (None, "") else capital,
        "rpt_pct": None if pct in (None, "") else pct,
        "risk_stage": stage or None,
        "configured": configured,
        "max_rpt_pct": 2,
        "note": (
            "Capital and RPT percent are owner settings. "
            "No default risk percentage is invented. Stage bands are Rulebook Learning/Intermediate/Professional."
        ),
    }


def _mutate(settings: Settings, fn):
    sources.ensure_repo_on_path()
    from nse.research import store

    conn = store.open_store(str(research_path(settings)))
    try:
        result = fn(conn, store)
        return {"result": result, "authorises_order": False}
    except store.JournalRefused as exc:
        raise ApiError(409, "CONFLICT", str(exc)) from exc
    except store.StoreError as exc:
        raise ApiError(400, "REQUEST_INVALID", str(exc)) from exc
    finally:
        conn.close()


def _calendar(settings: Settings):
    """Return the trading calendar, or None only when no calendar_dir is configured.

    A configured but unloadable calendar must refuse journal fills (D42 expiry), not
    silently skip the check. Research scan paths already raise on the same failure.
    """
    if settings.calendar_dir is None:
        return None
    try:
        return sources.load_calendar(settings)
    except Exception as exc:
        raise ApiError(422, "DATA_INSUFFICIENT", "The NSE calendar could not be loaded") from exc


def _backup_sources(settings: Settings) -> list[tuple[Path | None, str]]:
    sources_ = [(settings.platform_db, "platform.sqlite"), (research_path(settings), "research.sqlite")]
    if settings.eod_manifest is not None:
        sources_.append((settings.eod_manifest, "manifest.csv"))
    return sources_


def _required_backup_sqlite(settings: Settings) -> set[str]:
    """Sqlite files that must be present for an application backup/restore to pass.

    The desk journal always resolves through research_path(settings), including the
    data_dir/research.sqlite fallback when GTF_RESEARCH_DB is unset. Application
    backup/restore therefore always requires both databases.
    """
    del settings  # settings reserved for future path-specific requirements
    return {"platform.sqlite", "research.sqlite"}


def _expected_backup_files(backup_dir: Path, settings: Settings) -> set[str]:
    """Files that a restore-check must recover.

    Manifest listings are a floor, not a ceiling: a truncated manifest cannot drop a
    required application database. When either sqlite is present on disk, both
    application databases must be restored.
    """
    required = _required_backup_sqlite(settings)
    expected: set[str] = set(required)
    manifest_path = backup_dir / "backup_manifest.json"
    if manifest_path.is_file():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ApiError(422, "DATA_INSUFFICIENT", "Backup manifest is unreadable") from exc
        files = payload.get("files") if isinstance(payload, dict) else None
        if not isinstance(files, list):
            raise ApiError(422, "DATA_INSUFFICIENT", "Backup manifest is incomplete")
        expected.update(name for name in files if isinstance(name, str) and name.endswith(".sqlite"))
    present = {name for name in ("platform.sqlite", "research.sqlite") if (backup_dir / name).is_file()}
    if present:
        expected.update(required)
    return expected


def _table_counts(path: Path) -> dict:
    wanted = (
        "trade_plan", "job", "journal_entries", "journal_events",
        "journal_executions", "journal_orders", "journal_charges",
    )
    conn = sqlite3.connect(path)
    try:
        present = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        return {name: conn.execute("SELECT COUNT(*) FROM " + name).fetchone()[0] for name in wanted if name in present}
    finally:
        conn.close()


def _sqlite_backup(source: Path, target: Path) -> None:
    origin = sqlite3.connect(source)
    try:
        dest = sqlite3.connect(target)
        try:
            origin.backup(dest)
        finally:
            dest.close()
    finally:
        origin.close()


def _integrity(path: Path) -> None:
    try:
        conn = sqlite3.connect(path)
        try:
            row = conn.execute("PRAGMA integrity_check").fetchone()
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:
        raise ApiError(422, "DATA_INSUFFICIENT", "Restored database failed integrity_check") from exc
    if row is None or row[0] != "ok":
        raise ApiError(422, "DATA_INSUFFICIENT", "Restored database failed integrity_check")
