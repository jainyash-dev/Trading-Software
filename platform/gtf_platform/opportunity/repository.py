"""SQLite persistence for opportunity workflow metadata."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from gtf_platform.opportunity.priority import organizational_priority
from gtf_platform.store import new_id, utcnow

SOURCE_QUALITIES = frozenset({"FIXTURE", "EXPLORATORY", "UNKNOWN", "UNAVAILABLE", "CERTIFIED"})


def opportunity_view(row: sqlite3.Row | dict) -> dict:
    data = dict(row) if not isinstance(row, dict) else dict(row)
    snapshot = data.get("source_snapshot_json")
    if isinstance(snapshot, str):
        try:
            snapshot_obj = json.loads(snapshot)
        except json.JSONDecodeError:
            snapshot_obj = {}
    else:
        snapshot_obj = snapshot or {}
    view = {
        "opportunity_id": data["opportunity_id"],
        "scan_key": data["scan_key"],
        "symbol": data["symbol"],
        "zone_id": data.get("zone_id"),
        "timeframe": data.get("timeframe"),
        "as_of": data.get("as_of"),
        "dataset_id": data.get("dataset_id"),
        "exchange": data.get("exchange") or "NSE",
        "canonical_status": data["canonical_status"],
        "workflow_state": data["workflow_state"],
        "source_quality": data["source_quality"],
        "fixture": bool(data.get("fixture")),
        "authorises_order": False,
        "eligibility_authority": "stored research envelope snapshot only",
        "source_snapshot": snapshot_obj,
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "allowed_transitions": _lazy_transitions(data["workflow_state"], data["canonical_status"]),
    }
    view["organizational_priority"] = organizational_priority(view)
    return view


def _lazy_transitions(state: str, canonical_status: str | None = None) -> list[str]:
    from gtf_platform.opportunity.lifecycle import allowed_transitions

    return allowed_transitions(state, canonical_status=canonical_status)


def get_opportunity(connection: sqlite3.Connection, opportunity_id: str) -> dict | None:
    row = connection.execute(
        "SELECT * FROM opportunity WHERE opportunity_id = ?",
        (opportunity_id,),
    ).fetchone()
    if row is None:
        return None
    return opportunity_view(row)


def list_opportunities(
    connection: sqlite3.Connection,
    *,
    symbol: str | None = None,
    workflow_state: str | None = None,
    canonical_status: str | None = None,
    timeframe: str | None = None,
    source_quality: str | None = None,
    scan_key: str | None = None,
    watchlist_id: str | None = None,
    include_fixtures: bool = False,
    q: str | None = None,
    sort: str = "priority",
    limit: int = 100,
    offset: int = 0,
) -> dict:
    clauses: list[str] = []
    params: list[Any] = []
    if not include_fixtures:
        clauses.append("fixture = 0")
    if symbol:
        clauses.append("symbol = ?")
        params.append(symbol.upper())
    if workflow_state:
        clauses.append("workflow_state = ?")
        params.append(workflow_state)
    if canonical_status:
        clauses.append("canonical_status = ?")
        params.append(canonical_status)
    if timeframe:
        clauses.append("timeframe = ?")
        params.append(timeframe)
    if source_quality:
        clauses.append("source_quality = ?")
        params.append(source_quality)
    if scan_key:
        clauses.append("scan_key = ?")
        params.append(scan_key)
    if q:
        clauses.append("(symbol LIKE ? OR canonical_status LIKE ? OR workflow_state LIKE ?)")
        needle = "%%%s%%" % q.upper().replace("%", "").replace("_", "")
        params.extend([needle, needle, needle])
    if watchlist_id:
        clauses.append(
            """
            symbol IN (
                SELECT symbol FROM watchlist_symbol WHERE watchlist_id = ?
            )
            """
        )
        params.append(watchlist_id)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    total = connection.execute(
        "SELECT COUNT(*) AS n FROM opportunity" + where,
        params,
    ).fetchone()["n"]
    rows = connection.execute(
        "SELECT * FROM opportunity" + where + " ORDER BY updated_at DESC, opportunity_id",
        params,
    ).fetchall()
    items = [opportunity_view(row) for row in rows]
    if sort == "priority":
        items.sort(key=lambda item: (item["organizational_priority"]["score"], item["symbol"], item["opportunity_id"]))
    elif sort == "symbol":
        items.sort(key=lambda item: (item["symbol"], item["opportunity_id"]))
    elif sort == "discovered":
        items.sort(key=lambda item: (item.get("created_at") or "", item["opportunity_id"]), reverse=True)
    elif sort == "updated":
        items.sort(key=lambda item: (item.get("updated_at") or "", item["opportunity_id"]), reverse=True)
    capped = max(1, min(int(limit), 500))
    start = max(0, int(offset))
    page = items[start : start + capped]
    counts: dict[str, int] = {}
    for item in items:
        key = item["workflow_state"]
        counts[key] = counts.get(key, 0) + 1
    return {
        "opportunities": page,
        "total": total,
        "counts_by_workflow": counts,
        "filters_applied": {
            "symbol": symbol,
            "workflow_state": workflow_state,
            "canonical_status": canonical_status,
            "timeframe": timeframe,
            "source_quality": source_quality,
            "scan_key": scan_key,
            "watchlist_id": watchlist_id,
            "include_fixtures": include_fixtures,
            "q": q,
            "sort": sort,
        },
        "priority_disclosure": organizational_priority({"canonical_status": "", "workflow_state": "", "source_quality": "UNKNOWN", "fixture": False})[
            "disclosure"
        ],
        "authorises_order": False,
        "p0_certified_discovery": False,
        "limitation": "P0 certification is incomplete. Opportunities are research organization records, not certified production discoveries.",
    }


def insert_opportunity(
    connection: sqlite3.Connection,
    *,
    scan_key: str,
    symbol: str,
    zone_id: str | None,
    timeframe: str | None,
    as_of: str | None,
    dataset_id: str | None,
    canonical_status: str,
    source_quality: str,
    fixture: bool,
    source_snapshot: dict,
    workflow_state: str = "DISCOVERED",
    exchange: str = "NSE",
) -> tuple[dict, bool]:
    """Insert or return existing. Second value is True when newly created."""
    if source_quality not in SOURCE_QUALITIES:
        raise ValueError("invalid source_quality")
    # CERTIFIED is reserved until P0 produces certified dates. Refuse assignment.
    if source_quality == "CERTIFIED":
        source_quality = "EXPLORATORY"
    identity_zone = zone_id or ""
    existing = connection.execute(
        """
        SELECT opportunity_id FROM opportunity
        WHERE scan_key = ? AND symbol = ? AND IFNULL(zone_id, '') = ?
        """,
        (scan_key, symbol, identity_zone),
    ).fetchone()
    if existing is not None:
        view = get_opportunity(connection, existing["opportunity_id"])
        return view, False  # type: ignore[return-value]
    opportunity_id = new_id("opp")
    now = utcnow()
    connection.execute(
        """
        INSERT INTO opportunity (
            opportunity_id, scan_key, symbol, zone_id, timeframe, as_of, dataset_id,
            exchange, canonical_status, workflow_state, source_quality, fixture,
            source_snapshot_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            opportunity_id,
            scan_key,
            symbol,
            zone_id,
            timeframe,
            as_of,
            dataset_id,
            exchange,
            canonical_status,
            workflow_state,
            source_quality,
            1 if fixture else 0,
            json.dumps(source_snapshot, sort_keys=True, default=str),
            now,
            now,
        ),
    )
    connection.execute(
        """
        INSERT INTO opportunity_transition (
            history_id, opportunity_id, from_state, to_state, actor, reason, at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (new_id("oth"), opportunity_id, None, workflow_state, "system", "ingested from stored scan", now),
    )
    return get_opportunity(connection, opportunity_id), True  # type: ignore[return-value]


def list_history(connection: sqlite3.Connection, opportunity_id: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT history_id, opportunity_id, from_state, to_state, actor, reason, at
        FROM opportunity_transition
        WHERE opportunity_id = ?
        ORDER BY at, history_id
        """,
        (opportunity_id,),
    ).fetchall()
    return [
        {
            "history_id": row["history_id"],
            "opportunity_id": row["opportunity_id"],
            "from_state": row["from_state"],
            "to_state": row["to_state"],
            "actor": row["actor"],
            "reason": row["reason"],
            "at": row["at"],
        }
        for row in rows
    ]


def add_note(
    connection: sqlite3.Connection,
    opportunity_id: str,
    *,
    actor: str,
    body: str,
) -> dict:
    text = body.strip()
    if not text:
        raise ValueError("empty note")
    if len(text) > 2000:
        raise ValueError("note too long")
    note_id = new_id("onote")
    now = utcnow()
    connection.execute(
        """
        INSERT INTO opportunity_note (note_id, opportunity_id, actor, body, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (note_id, opportunity_id, actor, text, now),
    )
    connection.execute(
        "UPDATE opportunity SET updated_at = ? WHERE opportunity_id = ?",
        (now, opportunity_id),
    )
    return {"note_id": note_id, "opportunity_id": opportunity_id, "actor": actor, "body": text, "created_at": now}


def list_notes(connection: sqlite3.Connection, opportunity_id: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT note_id, opportunity_id, actor, body, created_at
        FROM opportunity_note
        WHERE opportunity_id = ?
        ORDER BY created_at, note_id
        """,
        (opportunity_id,),
    ).fetchall()
    return [dict(row) for row in rows]
