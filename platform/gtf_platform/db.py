"""Platform SQLite. This is not the research journal database."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MIGRATIONS: tuple[tuple[str, str], ...] = (
    (
        "001_jobs",
        """
        CREATE TABLE job (
            job_id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            state TEXT NOT NULL,
            idempotency_key TEXT,
            heartbeat TEXT,
            created_at TEXT NOT NULL
        );
        """,
    ),
)


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if not path.exists():
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
    else:
        os.chmod(path, 0o600)
    # Autocommit. Callers open explicit transactions. One process lock serialises threads.
    connection = sqlite3.connect(path, isolation_level=None, check_same_thread=False, timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA journal_mode = WAL")
    migrate(connection)
    return connection


def migrate(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migration (
            id TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )
    applied = {row["id"] for row in connection.execute("SELECT id FROM schema_migration")}
    now = datetime.now(timezone.utc).isoformat()
    for migration_id, script in MIGRATIONS:
        if migration_id in applied:
            continue
        connection.executescript(script)
        connection.execute(
            "INSERT INTO schema_migration (id, applied_at) VALUES (?, ?)",
            (migration_id, now),
        )
        applied.add(migration_id)
    if "002_platform_state" not in applied:
        _migration_002(connection)
        connection.execute(
            "INSERT INTO schema_migration (id, applied_at) VALUES (?, ?)",
            ("002_platform_state", now),
        )
    applied = {row["id"] for row in connection.execute("SELECT id FROM schema_migration")}
    if "003_trade_plan" not in applied:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS trade_plan (
                plan_id TEXT PRIMARY KEY,
                scan_key TEXT NOT NULL,
                symbol TEXT NOT NULL,
                zone_id TEXT NOT NULL,
                candidate_status TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                state TEXT NOT NULL,
                entry_id INTEGER,
                approved_at TEXT,
                approved_by TEXT,
                selected_json TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO schema_migration (id, applied_at) VALUES (?, ?)",
            ("003_trade_plan", now),
        )
    applied = {row["id"] for row in connection.execute("SELECT id FROM schema_migration")}
    if "004_opportunity_intelligence" not in applied:
        _migration_004(connection)
        connection.execute(
            "INSERT INTO schema_migration (id, applied_at) VALUES (?, ?)",
            ("004_opportunity_intelligence", now),
        )
    applied = {row["id"] for row in connection.execute("SELECT id FROM schema_migration")}
    if "005_trade_plan_lifecycle" not in applied:
        _migration_005(connection)
        connection.execute(
            "INSERT INTO schema_migration (id, applied_at) VALUES (?, ?)",
            ("005_trade_plan_lifecycle", now),
        )


def _migration_002(connection: sqlite3.Connection) -> None:
    existing = {row["name"] for row in connection.execute("PRAGMA table_info(job)")}
    columns = (
        ("request_json", "TEXT"),
        ("body_hash", "TEXT"),
        ("result_ref", "TEXT"),
        ("research_key", "TEXT"),
        ("completeness", "TEXT"),
        ("error_code", "TEXT"),
        ("error_message", "TEXT"),
        ("progress_done", "INTEGER"),
        ("progress_total", "INTEGER"),
        ("progress_unit", "TEXT"),
        ("fixture", "INTEGER NOT NULL DEFAULT 0"),
        ("cancel_requested", "INTEGER NOT NULL DEFAULT 0"),
        ("updated_at", "TEXT"),
    )
    for name, declaration in columns:
        if name not in existing:
            connection.execute("ALTER TABLE job ADD COLUMN %s %s" % (name, declaration))
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS idempotency (
            idempotency_key TEXT PRIMARY KEY,
            body_hash TEXT NOT NULL,
            kind TEXT NOT NULL,
            object_id TEXT NOT NULL,
            held INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS scan_result (
            scan_key TEXT PRIMARY KEY,
            job_id TEXT,
            as_of TEXT NOT NULL,
            trade_type TEXT NOT NULL,
            invocation TEXT NOT NULL,
            dataset_id TEXT,
            universe_label TEXT,
            completeness TEXT NOT NULL,
            full_universe_scan INTEGER NOT NULL,
            fixture INTEGER NOT NULL,
            limitations_json TEXT NOT NULL,
            symbols_not_opened_json TEXT NOT NULL,
            envelope_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS scan_result_created ON scan_result (created_at, scan_key);
        CREATE INDEX IF NOT EXISTS job_state ON job (state);
        CREATE INDEX IF NOT EXISTS job_research_key ON job (research_key);
        CREATE TABLE IF NOT EXISTS watchlist (
            watchlist_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS watchlist_symbol (
            watchlist_id TEXT NOT NULL REFERENCES watchlist (watchlist_id),
            position INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            PRIMARY KEY (watchlist_id, symbol),
            UNIQUE (watchlist_id, position)
        );
        CREATE TABLE IF NOT EXISTS scan_config (
            config_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            parameters_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS drawing (
            drawing_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            as_of TEXT,
            geometry_json TEXT NOT NULL,
            version INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS drawing_symbol_tf ON drawing (symbol, timeframe);
        CREATE TABLE IF NOT EXISTS app_setting (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_event (
            audit_id TEXT PRIMARY KEY,
            at TEXT NOT NULL,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            object_id TEXT NOT NULL,
            before_digest TEXT,
            after_digest TEXT
        );
        CREATE INDEX IF NOT EXISTS audit_object ON audit_event (object_id);
        """
    )


def _migration_004(connection: sqlite3.Connection) -> None:
    """Opportunity workflow metadata and watchlist research fields.

    Does not store a second eligibility engine. Opportunities reference stored
    scan candidates. Watchlist membership remains non-authoritative.
    """
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS opportunity (
            opportunity_id TEXT PRIMARY KEY,
            scan_key TEXT NOT NULL,
            symbol TEXT NOT NULL,
            zone_id TEXT,
            timeframe TEXT,
            as_of TEXT,
            dataset_id TEXT,
            exchange TEXT NOT NULL DEFAULT 'NSE',
            canonical_status TEXT NOT NULL,
            workflow_state TEXT NOT NULL,
            source_quality TEXT NOT NULL,
            fixture INTEGER NOT NULL DEFAULT 0,
            source_snapshot_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS opportunity_identity
            ON opportunity (scan_key, symbol, IFNULL(zone_id, ''));
        CREATE INDEX IF NOT EXISTS opportunity_workflow
            ON opportunity (workflow_state, updated_at);
        CREATE INDEX IF NOT EXISTS opportunity_symbol
            ON opportunity (symbol, updated_at);
        CREATE TABLE IF NOT EXISTS opportunity_transition (
            history_id TEXT PRIMARY KEY,
            opportunity_id TEXT NOT NULL REFERENCES opportunity (opportunity_id),
            from_state TEXT,
            to_state TEXT NOT NULL,
            actor TEXT NOT NULL,
            reason TEXT,
            at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS opportunity_transition_opp
            ON opportunity_transition (opportunity_id, at);
        CREATE TABLE IF NOT EXISTS opportunity_note (
            note_id TEXT PRIMARY KEY,
            opportunity_id TEXT NOT NULL REFERENCES opportunity (opportunity_id),
            actor TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS opportunity_note_opp
            ON opportunity_note (opportunity_id, created_at);
        """
    )
    symbol_cols = {row["name"] for row in connection.execute("PRAGMA table_info(watchlist_symbol)")}
    for name, declaration in (
        ("added_at", "TEXT"),
        ("reason", "TEXT"),
        ("note", "TEXT"),
    ):
        if name not in symbol_cols:
            connection.execute(
                "ALTER TABLE watchlist_symbol ADD COLUMN %s %s" % (name, declaration)
            )


def _migration_005(connection: sqlite3.Connection) -> None:
    """P4 trade-plan lifecycle columns, audit events and notes.

    candidate_status remains the immutable stored scanner status. Lifecycle
    states organise the desk only. Caps and ED-3 stay in the research journal.
    """
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
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS trade_plan_event (
            event_id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL REFERENCES trade_plan (plan_id),
            from_state TEXT,
            to_state TEXT NOT NULL,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            detail_json TEXT,
            at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS trade_plan_event_plan
            ON trade_plan_event (plan_id, at);
        CREATE TABLE IF NOT EXISTS trade_plan_note (
            note_id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL REFERENCES trade_plan (plan_id),
            actor TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS trade_plan_note_plan
            ON trade_plan_note (plan_id, created_at);
        CREATE INDEX IF NOT EXISTS trade_plan_state
            ON trade_plan (state, created_at);
        """
    )


def probe(path: Path | None) -> dict:
    if path is None:
        return {"configured": False, "reachable": False}
    if not path.is_file():
        return {"configured": True, "reachable": False}
    try:
        connection = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
        try:
            connection.execute("SELECT 1")
        finally:
            connection.close()
    except sqlite3.Error:
        return {"configured": True, "reachable": False}
    return {"configured": True, "reachable": True}
