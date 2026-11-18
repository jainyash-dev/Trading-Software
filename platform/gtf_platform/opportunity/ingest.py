"""Ingest opportunity rows from a stored scan_result envelope.

Copies canonical status and provenance. Does not re-run qualification.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from gtf_platform.errors import ApiError
from gtf_platform.opportunity.repository import insert_opportunity
from gtf_platform.store import get_scan, record_audit


def classify_source_quality(*, fixture: bool, limitations: list[str] | None) -> str:
    """Map scan provenance to a quality label. Never invents CERTIFIED."""
    if fixture:
        return "FIXTURE"
    text = " ".join(str(item) for item in (limitations or []))
    upper = text.upper()
    if "FIXTURE" in upper or "FIXTURE_NOT_MARKET_DATA" in upper:
        return "FIXTURE"
    # Local non-fixture data remains exploratory while P0 certified dates are zero.
    return "EXPLORATORY"


def initial_workflow(canonical_status: str, *, source_quality: str) -> str:
    if source_quality == "FIXTURE":
        # Fixtures are ingested for UI development only; start BLOCKED for workflow.
        return "BLOCKED"
    status = (canonical_status or "").upper()
    if status in {"BLOCKED", "DATA_INSUFFICIENT"}:
        return "BLOCKED"
    if status == "REJECTED":
        return "REJECTED"
    return "DISCOVERED"


def ingest_scan(
    connection: sqlite3.Connection,
    scan_key: str,
    *,
    actor: str = "owner",
    include_rejected: bool = True,
) -> dict:
    row = get_scan(connection, scan_key)
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Scan not found")
    try:
        envelope = json.loads(row["envelope_json"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise ApiError(422, "DATA_INSUFFICIENT", "Scan envelope is not readable JSON") from exc
    if not isinstance(envelope, dict):
        raise ApiError(422, "DATA_INSUFFICIENT", "Scan envelope is not an object")
    fixture = bool(row["fixture"]) or bool(envelope.get("fixture"))
    limitations = list(envelope.get("limitations") or [])
    if row["limitations_json"]:
        try:
            limitations = list(json.loads(row["limitations_json"]))
        except json.JSONDecodeError:
            pass
    source_quality = classify_source_quality(fixture=fixture, limitations=limitations)
    as_of = row["as_of"] or envelope.get("as_of")
    dataset_id = row["dataset_id"] or envelope.get("dataset_id")
    created: list[dict] = []
    existing: list[dict] = []
    skipped = 0
    symbols = envelope.get("symbols") or []
    if not isinstance(symbols, list):
        raise ApiError(422, "DATA_INSUFFICIENT", "Scan envelope symbols are missing")
    for symbol_row in symbols:
        if not isinstance(symbol_row, dict):
            skipped += 1
            continue
        symbol = str(symbol_row.get("symbol") or "").strip().upper()
        if not symbol:
            skipped += 1
            continue
        candidates = symbol_row.get("candidates") or []
        symbol_status = str(symbol_row.get("status") or "UNKNOWN")
        if not candidates:
            if not include_rejected and symbol_status in {"REJECTED", "BLOCKED"}:
                skipped += 1
                continue
            view, is_new = _upsert_one(
                connection,
                scan_key=scan_key,
                symbol=symbol,
                zone_id=None,
                timeframe=None,
                as_of=as_of,
                dataset_id=dataset_id,
                canonical_status=symbol_status,
                source_quality=source_quality,
                fixture=fixture,
                source_snapshot=_symbol_snapshot(symbol_row, None),
            )
            (created if is_new else existing).append(view)
            continue
        for candidate in candidates:
            if not isinstance(candidate, dict):
                skipped += 1
                continue
            status = str(candidate.get("status") or symbol_status or "UNKNOWN")
            if not include_rejected and status in {"REJECTED", "BLOCKED"}:
                skipped += 1
                continue
            zone = candidate.get("zone") if isinstance(candidate.get("zone"), dict) else {}
            zone_id = candidate.get("zone_id") or zone.get("zone_id") or zone.get("id")
            if zone_id is not None:
                zone_id = str(zone_id)
            # Canonical stored keys (nse/research reports): candidate execution_tf, zone tf.
            timeframe = (
                candidate.get("execution_tf") or zone.get("tf")
                or candidate.get("timeframe") or zone.get("timeframe")
            )
            if timeframe is not None:
                timeframe = str(timeframe)
            view, is_new = _upsert_one(
                connection,
                scan_key=scan_key,
                symbol=symbol,
                zone_id=zone_id,
                timeframe=timeframe,
                as_of=as_of,
                dataset_id=dataset_id,
                canonical_status=status,
                source_quality=source_quality,
                fixture=fixture,
                source_snapshot=_symbol_snapshot(symbol_row, candidate),
            )
            (created if is_new else existing).append(view)
    result = {
        "scan_key": scan_key,
        "source_quality": source_quality,
        "fixture": fixture,
        "created_count": len(created),
        "existing_count": len(existing),
        "skipped_count": skipped,
        "created": created,
        "existing": existing,
        "authorises_order": False,
        "p0_certified_discovery": False,
        "note": (
            "Ingested from stored scanner output only. "
            "Workflow state does not change GTF eligibility. "
            "Fixture rows are labelled and are not market opportunities."
            if fixture
            else "Ingested from stored scanner output. Source quality remains exploratory while P0 certification is incomplete."
        ),
    }
    record_audit(
        connection,
        actor=actor,
        action="opportunity.ingest",
        object_id=scan_key,
        after={
            "created_count": result["created_count"],
            "existing_count": result["existing_count"],
            "source_quality": source_quality,
            "fixture": fixture,
        },
    )
    return result


def _upsert_one(
    connection: sqlite3.Connection,
    **kwargs: Any,
) -> tuple[dict, bool]:
    workflow = initial_workflow(kwargs["canonical_status"], source_quality=kwargs["source_quality"])
    return insert_opportunity(connection, workflow_state=workflow, **kwargs)


def _symbol_snapshot(symbol_row: dict, candidate: dict | None) -> dict:
    """Immutable provenance slice. Not a second eligibility record."""
    gates = None
    if candidate is not None:
        gates = candidate.get("gates") or candidate.get("gate_results")
    return {
        "symbol_status": symbol_row.get("status"),
        "candidate_status": None if candidate is None else candidate.get("status"),
        "zone_id": None if candidate is None else (candidate.get("zone_id") or (candidate.get("zone") or {}).get("zone_id")),
        "timeframe": None if candidate is None else candidate.get("timeframe"),
        "manual_checks": None if candidate is None else candidate.get("manual_checks"),
        "deciding_gates": None if candidate is None else candidate.get("deciding_gates"),
        "gates_present": gates is not None,
        "snapshot_kind": "stored_scan_candidate",
        "authorises_order": False,
    }
