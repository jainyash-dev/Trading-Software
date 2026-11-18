"""Platform SQLite repositories. This is not the research journal and not a trade-cap counter."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timezone

from gtf_platform.jobs import RELEASED, SUCCEEDED


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def body_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def digest(payload: object) -> str:
    return body_hash(payload)


def new_id(prefix: str) -> str:
    return "%s-%s" % (prefix, secrets.token_hex(8))


def job_view(row: sqlite3.Row) -> dict:
    progress = None
    if row["progress_total"] is not None or row["progress_done"] is not None:
        progress = {"unit": row["progress_unit"] or "symbols"}
        if row["progress_done"] is not None:
            progress["done"] = row["progress_done"]
        if row["progress_total"] is not None:
            progress["total"] = row["progress_total"]
    error = None
    if row["error_code"]:
        error = {"code": row["error_code"], "message": row["error_message"] or ""}
    return {
        "job_id": row["job_id"],
        "kind": row["kind"],
        "state": row["state"],
        "idempotency_key": row["idempotency_key"],
        "completeness": row["completeness"],
        "progress": progress,
        "result_ref": row["result_ref"],
        "error": error,
    }


def get_job(connection: sqlite3.Connection, job_id: str) -> sqlite3.Row | None:
    return connection.execute("SELECT * FROM job WHERE job_id = ?", (job_id,)).fetchone()


def get_job_by_result(connection: sqlite3.Connection, scan_key: str) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT * FROM job
        WHERE result_ref = ? OR research_key = ? OR job_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (scan_key, scan_key, scan_key),
    ).fetchone()


def _idempotency(connection: sqlite3.Connection, key: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM idempotency WHERE idempotency_key = ?",
        (key,),
    ).fetchone()


def accept_job(
    connection: sqlite3.Connection,
    *,
    idempotency_key: str,
    payload_hash: str,
    kind: str,
    state: str,
    request: dict,
    fixture: bool,
    research_key: str | None,
    progress_total: int | None,
    error_code: str | None = None,
    error_message: str | None = None,
    existing_scan: sqlite3.Row | None = None,
) -> tuple[str, dict]:
    """Return ('created'|'existing'|'conflict', job view).

    The caller owns the transaction.
    """
    current = _idempotency(connection, idempotency_key)
    if current is not None:
        if current["body_hash"] != payload_hash:
            return "conflict", {}
        job = get_job(connection, current["object_id"])
        if job is None:
            return "conflict", {}
        if current["held"] and job["state"] in SUCCEEDED | frozenset(
            {"PENDING_DATA", "VALIDATING", "RUNNING", "SKIPPED_HOLIDAY", "SKIPPED_UNRESOLVED_CALENDAR"}
        ):
            return "existing", job_view(job)
        if current["held"] and job["state"] not in RELEASED:
            return "existing", job_view(job)
        if not current["held"] and job["state"] in RELEASED:
            pass
        elif current["held"]:
            return "existing", job_view(job)
    active = None
    if research_key:
        active = connection.execute(
            """
            SELECT * FROM job
            WHERE research_key = ? AND state IN ('PENDING_DATA', 'VALIDATING', 'RUNNING',
                'SUCCEEDED_COMPLETE', 'SUCCEEDED_PARTIAL')
            ORDER BY created_at
            LIMIT 1
            """,
            (research_key,),
        ).fetchone()
    if active is not None and (current is None or not current["held"]):
        _bind(connection, idempotency_key, payload_hash, active["job_id"], held=1)
        return "existing", job_view(active)
    if existing_scan is not None and (current is None or not current["held"]):
        job_id = new_id("job")
        now = utcnow()
        state = _state_for_completeness(existing_scan["completeness"])
        connection.execute(
            """
            INSERT INTO job (
                job_id, kind, state, idempotency_key, heartbeat, created_at, request_json,
                body_hash, result_ref, research_key, completeness, fixture, progress_done,
                progress_total, progress_unit, updated_at, error_code, error_message
            ) VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'symbols', ?, NULL, NULL)
            """,
            (
                job_id,
                kind,
                state,
                idempotency_key,
                now,
                json.dumps(request, sort_keys=True),
                payload_hash,
                existing_scan["scan_key"],
                existing_scan["scan_key"],
                existing_scan["completeness"],
                existing_scan["fixture"],
                len(json.loads(existing_scan["envelope_json"]).get("symbols") or []),
                progress_total,
                now,
            ),
        )
        _bind(connection, idempotency_key, payload_hash, job_id, held=1 if state in SUCCEEDED else 0)
        row = get_job(connection, job_id)
        return "created", job_view(row)
    job_id = new_id("job")
    now = utcnow()
    held = 0 if state in RELEASED else 1
    connection.execute(
        """
        INSERT INTO job (
            job_id, kind, state, idempotency_key, heartbeat, created_at, request_json,
            body_hash, result_ref, research_key, completeness, error_code, error_message,
            progress_total, progress_unit, fixture, updated_at
        ) VALUES (?, ?, ?, ?, NULL, ?, ?, ?, NULL, ?, NULL, ?, ?, ?, 'symbols', ?, ?)
        """,
        (
            job_id,
            kind,
            state,
            idempotency_key,
            now,
            json.dumps(request, sort_keys=True),
            payload_hash,
            research_key,
            error_code,
            error_message,
            progress_total,
            1 if fixture else 0,
            now,
        ),
    )
    _bind(connection, idempotency_key, payload_hash, job_id, held=held)
    row = get_job(connection, job_id)
    return "created", job_view(row)


def _state_for_completeness(completeness: str) -> str:
    if completeness == "COMPLETE":
        return "SUCCEEDED_COMPLETE"
    if completeness == "PARTIAL":
        return "SUCCEEDED_PARTIAL"
    return "FAILED"


def _bind(connection: sqlite3.Connection, key: str, payload_hash: str, object_id: str, held: int) -> None:
    now = utcnow()
    connection.execute(
        """
        INSERT INTO idempotency (idempotency_key, body_hash, kind, object_id, held, created_at)
        VALUES (?, ?, 'JOB', ?, ?, ?)
        ON CONFLICT(idempotency_key) DO UPDATE SET
            body_hash = excluded.body_hash,
            object_id = excluded.object_id,
            held = excluded.held
        """,
        (key, payload_hash, object_id, held, now),
    )


def request_cancel(connection: sqlite3.Connection, scan_key: str) -> tuple[str, dict | None]:
    row = get_job_by_result(connection, scan_key)
    if row is None:
        stored = connection.execute(
            "SELECT scan_key FROM scan_result WHERE scan_key = ?",
            (scan_key,),
        ).fetchone()
        if stored is None:
            return "missing", None
        return "finished", None
    if row["state"] in SUCCEEDED:
        return "finished", job_view(row)
    if row["state"] not in {"PENDING_DATA", "VALIDATING", "RUNNING"}:
        return "existing", job_view(row)
    if row["state"] == "RUNNING":
        connection.execute(
            "UPDATE job SET cancel_requested = 1, updated_at = ? WHERE job_id = ? AND state = ?",
            (utcnow(), row["job_id"], "RUNNING"),
        )
        fresh = get_job(connection, row["job_id"])
        return "accepted", job_view(fresh)
    now = utcnow()
    connection.execute(
        """
        UPDATE job
        SET state = 'CANCELLED', error_code = 'CANCELLED', error_message = 'Cancelled',
            updated_at = ?
        WHERE job_id = ? AND state IN ('PENDING_DATA', 'VALIDATING')
        """,
        (now, row["job_id"]),
    )
    connection.execute(
        "UPDATE idempotency SET held = 0 WHERE object_id = ? AND kind = 'JOB'",
        (row["job_id"],),
    )
    fresh = get_job(connection, row["job_id"])
    return "accepted", job_view(fresh)


def latest_scan(connection: sqlite3.Connection, *, fixture: bool = False) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT * FROM scan_result
        WHERE fixture = ?
        ORDER BY created_at DESC, scan_key DESC
        LIMIT 1
        """,
        (1 if fixture else 0,),
    ).fetchone()


def get_scan(connection: sqlite3.Connection, scan_key: str) -> sqlite3.Row | None:
    return connection.execute("SELECT * FROM scan_result WHERE scan_key = ?", (scan_key,)).fetchone()


def find_scan_by_research_key(connection: sqlite3.Connection, research_key: str) -> sqlite3.Row | None:
    return get_scan(connection, research_key)


def list_scans(
    connection: sqlite3.Connection,
    *,
    limit: int,
    cursor: str | None,
    include_fixtures: bool,
) -> tuple[list[sqlite3.Row], str | None]:
    params: list[object] = []
    where = []
    if not include_fixtures:
        where.append("fixture = 0")
    if cursor:
        current = get_scan(connection, cursor)
        if current is None:
            return [], None
        where.append("(created_at < ? OR (created_at = ? AND scan_key < ?))")
        params.extend([current["created_at"], current["created_at"], current["scan_key"]])
    sql = "SELECT * FROM scan_result"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC, scan_key DESC LIMIT ?"
    params.append(limit + 1)
    rows = list(connection.execute(sql, params).fetchall())
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = rows[-1]["scan_key"]
    return rows, next_cursor


def scan_summary(row: sqlite3.Row) -> dict:
    return {
        "scan_key": row["scan_key"],
        "as_of": row["as_of"],
        "trade_type": row["trade_type"],
        "invocation": row["invocation"],
        "dataset_id": row["dataset_id"],
        "universe": row["universe_label"],
        "completeness": row["completeness"],
        "full_universe_scan": bool(row["full_universe_scan"]),
        "limitations": json.loads(row["limitations_json"]),
        "symbols_not_opened": json.loads(row["symbols_not_opened_json"]),
        "fixture": bool(row["fixture"]),
    }


def accept_object(
    connection: sqlite3.Connection,
    *,
    idempotency_key: str,
    payload_hash: str,
    kind: str,
) -> tuple[str, str | None]:
    current = _idempotency(connection, idempotency_key)
    if current is None:
        return "free", None
    if current["body_hash"] != payload_hash or current["kind"] != kind:
        return "conflict", None
    return "existing", current["object_id"]


def bind_object(
    connection: sqlite3.Connection,
    *,
    idempotency_key: str,
    payload_hash: str,
    kind: str,
    object_id: str,
) -> None:
    connection.execute(
        """
        INSERT INTO idempotency (idempotency_key, body_hash, kind, object_id, held, created_at)
        VALUES (?, ?, ?, ?, 1, ?)
        """,
        (idempotency_key, payload_hash, kind, object_id, utcnow()),
    )


def insert_watchlist(
    connection: sqlite3.Connection,
    name: str,
    symbols: list[str],
    *,
    items: list[dict] | None = None,
) -> dict:
    watchlist_id = new_id("wl")
    now = utcnow()
    connection.execute(
        "INSERT INTO watchlist (watchlist_id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (watchlist_id, name, now, now),
    )
    _replace_symbols(connection, watchlist_id, symbols, items=items, added_at=now)
    return watchlist_view(connection, watchlist_id)


def update_watchlist(
    connection: sqlite3.Connection,
    watchlist_id: str,
    *,
    name: str | None,
    symbols: list[str] | None,
    items: list[dict] | None = None,
) -> dict | None:
    row = connection.execute(
        "SELECT * FROM watchlist WHERE watchlist_id = ?",
        (watchlist_id,),
    ).fetchone()
    if row is None:
        return None
    now = utcnow()
    if name is not None:
        connection.execute(
            "UPDATE watchlist SET name = ?, updated_at = ? WHERE watchlist_id = ?",
            (name, now, watchlist_id),
        )
    else:
        connection.execute(
            "UPDATE watchlist SET updated_at = ? WHERE watchlist_id = ?",
            (now, watchlist_id),
        )
    if symbols is not None or items is not None:
        connection.execute("DELETE FROM watchlist_symbol WHERE watchlist_id = ?", (watchlist_id,))
        symbol_list = symbols if symbols is not None else [str(item.get("symbol") or "") for item in (items or [])]
        _replace_symbols(connection, watchlist_id, symbol_list, items=items, added_at=now)
    return watchlist_view(connection, watchlist_id)


def delete_watchlist(connection: sqlite3.Connection, watchlist_id: str) -> bool:
    row = connection.execute(
        "SELECT watchlist_id FROM watchlist WHERE watchlist_id = ?",
        (watchlist_id,),
    ).fetchone()
    if row is None:
        return False
    connection.execute("DELETE FROM watchlist_symbol WHERE watchlist_id = ?", (watchlist_id,))
    connection.execute("DELETE FROM watchlist WHERE watchlist_id = ?", (watchlist_id,))
    return True


def _replace_symbols(
    connection: sqlite3.Connection,
    watchlist_id: str,
    symbols: list[str],
    *,
    items: list[dict] | None = None,
    added_at: str | None = None,
) -> None:
    meta_by_symbol: dict[str, dict] = {}
    if items:
        for item in items:
            symbol = str(item.get("symbol") or "").strip().upper()
            if not symbol:
                continue
            meta_by_symbol[symbol] = item
    seen: set[str] = set()
    ordered: list[str] = []
    for symbol in symbols:
        text = str(symbol).strip().upper()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    stamp = added_at or utcnow()
    for position, symbol in enumerate(ordered):
        meta = meta_by_symbol.get(symbol) or {}
        reason = meta.get("reason")
        note = meta.get("note")
        if reason is not None:
            reason = str(reason).strip()[:500] or None
        if note is not None:
            note = str(note).strip()[:2000] or None
        connection.execute(
            """
            INSERT INTO watchlist_symbol (
                watchlist_id, position, symbol, added_at, reason, note
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (watchlist_id, position, symbol, stamp, reason, note),
        )


def watchlist_view(connection: sqlite3.Connection, watchlist_id: str) -> dict:
    row = connection.execute(
        "SELECT * FROM watchlist WHERE watchlist_id = ?",
        (watchlist_id,),
    ).fetchone()
    items = []
    for item in connection.execute(
        """
        SELECT symbol, added_at, reason, note
        FROM watchlist_symbol
        WHERE watchlist_id = ?
        ORDER BY position, symbol
        """,
        (watchlist_id,),
    ).fetchall():
        items.append(
            {
                "symbol": item["symbol"],
                "added_at": item["added_at"],
                "reason": item["reason"],
                "note": item["note"],
            }
        )
    symbols = [item["symbol"] for item in items]
    return {
        "watchlist_id": row["watchlist_id"],
        "name": row["name"],
        "symbols": symbols,
        "items": items,
        "eligibility": None,
        "authorises_order": False,
        "note": "Watchlist membership is not a trading signal and does not imply GTF eligibility.",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_watchlists(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute(
        "SELECT watchlist_id FROM watchlist ORDER BY created_at, watchlist_id"
    ).fetchall()
    return [watchlist_view(connection, row["watchlist_id"]) for row in rows]


def insert_scan_config(connection: sqlite3.Connection, name: str, parameters: dict) -> dict:
    config_id = new_id("cfg")
    now = utcnow()
    connection.execute(
        "INSERT INTO scan_config (config_id, name, parameters_json, created_at) VALUES (?, ?, ?, ?)",
        (config_id, name, json.dumps(parameters, sort_keys=True), now),
    )
    return {"config_id": config_id, "name": name, "parameters": parameters, "created_at": now}


def list_scan_configs(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute(
        "SELECT * FROM scan_config ORDER BY created_at, config_id"
    ).fetchall()
    return [
        {
            "config_id": row["config_id"],
            "name": row["name"],
            "parameters": json.loads(row["parameters_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def insert_drawing(connection: sqlite3.Connection, symbol: str, timeframe: str, as_of: str | None, geometry: dict) -> dict:
    drawing_id = new_id("draw")
    now = utcnow()
    connection.execute(
        """
        INSERT INTO drawing (
            drawing_id, symbol, timeframe, as_of, geometry_json, version, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """,
        (drawing_id, symbol, timeframe, as_of, json.dumps(geometry, sort_keys=True), now, now),
    )
    return drawing_view(connection, drawing_id)


def drawing_view(connection: sqlite3.Connection, drawing_id: str) -> dict | None:
    row = connection.execute("SELECT * FROM drawing WHERE drawing_id = ?", (drawing_id,)).fetchone()
    if row is None:
        return None
    return {
        "drawing_id": row["drawing_id"],
        "symbol": row["symbol"],
        "timeframe": row["timeframe"],
        "as_of": row["as_of"],
        "geometry": json.loads(row["geometry_json"]),
        "version": row["version"],
        "updated_at": row["updated_at"],
    }


def list_drawings(connection: sqlite3.Connection, symbol: str, timeframe: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT drawing_id FROM drawing
        WHERE symbol = ? AND timeframe = ?
        ORDER BY created_at, drawing_id
        """,
        (symbol, timeframe),
    ).fetchall()
    return [drawing_view(connection, row["drawing_id"]) for row in rows]


def delete_drawing(connection: sqlite3.Connection, drawing_id: str) -> bool:
    cursor = connection.execute("DELETE FROM drawing WHERE drawing_id = ?", (drawing_id,))
    return cursor.rowcount > 0


def update_drawing(connection: sqlite3.Connection, drawing_id: str, geometry: dict) -> dict | None:
    now = utcnow()
    cursor = connection.execute(
        """
        UPDATE drawing
        SET geometry_json = ?, version = version + 1, updated_at = ?
        WHERE drawing_id = ?
        """,
        (json.dumps(geometry, sort_keys=True), now, drawing_id),
    )
    if cursor.rowcount == 0:
        return None
    return drawing_view(connection, drawing_id)


SETTINGS_DEFAULTS = {
    "capital": None,
    "risk_stage": None,
    "scheduler_enabled": False,
    "assistant_enabled": False,
    "assistant_payload_policy": "citations-only",
    "backup_directory": None,
    "log_retention_days": 90,
}


def read_settings(connection: sqlite3.Connection) -> dict:
    found = {
        row["key"]: json.loads(row["value_json"])
        for row in connection.execute("SELECT key, value_json FROM app_setting")
    }
    values = dict(SETTINGS_DEFAULTS)
    values.update(found)
    return values


def patch_settings(connection: sqlite3.Connection, changes: dict) -> tuple[dict, dict]:
    before = read_settings(connection)
    now = utcnow()
    for key, value in changes.items():
        connection.execute(
            """
            INSERT INTO app_setting (key, value_json, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at
            """,
            (key, json.dumps(value), now),
        )
    after = read_settings(connection)
    record_audit(
        connection,
        actor="owner",
        action="settings.patch",
        object_id="settings",
        before=before,
        after=after,
    )
    return before, after


def record_audit(
    connection: sqlite3.Connection,
    *,
    actor: str,
    action: str,
    object_id: str,
    before: object = None,
    after: object = None,
) -> None:
    connection.execute(
        """
        INSERT INTO audit_event (audit_id, at, actor, action, object_id, before_digest, after_digest)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id("audit"),
            utcnow(),
            actor,
            action,
            object_id,
            None if before is None else digest(before),
            None if after is None else digest(after),
        ),
    )


def list_audit(connection: sqlite3.Connection, object_id: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT * FROM audit_event
        WHERE object_id = ?
        ORDER BY at, audit_id
        """,
        (object_id,),
    ).fetchall()
    return [
        {
            "audit_id": row["audit_id"],
            "at": row["at"],
            "actor": row["actor"],
            "action": row["action"],
            "object_id": row["object_id"],
            "before_digest": row["before_digest"],
            "after_digest": row["after_digest"],
        }
        for row in rows
    ]
