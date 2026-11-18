"""Job recovery and the single in-process runner.

This module does not import the research engine. Scan execution is a callable
supplied by the application. Job state is not scan completeness.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import datetime, timedelta, timezone

RUNNING = "RUNNING"
INTERRUPTED = "INTERRUPTED"
VALIDATING = "VALIDATING"
PENDING_DATA = "PENDING_DATA"
CANCELLED = "CANCELLED"

ACTIVE = frozenset({PENDING_DATA, VALIDATING, RUNNING})
RELEASED = frozenset({INTERRUPTED, "FAILED", CANCELLED})
SUCCEEDED = frozenset({"SUCCEEDED_COMPLETE", "SUCCEEDED_PARTIAL"})

log = logging.getLogger("gtf_platform.jobs")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def interrupt_stale(connection: sqlite3.Connection, now: datetime, stale_after: timedelta) -> int:
    """Mark RUNNING jobs whose heartbeat did not advance as INTERRUPTED.

    SUCCEEDED_COMPLETE rows are left alone. A missing heartbeat is stale.
    An interrupted job releases its idempotency key and is not marked successful.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    changed = 0
    connection.execute("BEGIN IMMEDIATE")
    try:
        rows = connection.execute(
            "SELECT job_id, state, heartbeat FROM job WHERE state = ?",
            (RUNNING,),
        ).fetchall()
        cutoff = now - stale_after
        for row in rows:
            heartbeat = row["heartbeat"]
            stale = True
            if heartbeat:
                seen = datetime.fromisoformat(heartbeat)
                if seen.tzinfo is None:
                    seen = seen.replace(tzinfo=timezone.utc)
                stale = seen < cutoff
            if stale:
                connection.execute(
                    "UPDATE job SET state = ?, updated_at = ? WHERE job_id = ? AND state = ?",
                    (INTERRUPTED, now.isoformat(), row["job_id"], RUNNING),
                )
                _release_key(connection, row["job_id"])
                changed += 1
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return changed


def _release_key(connection: sqlite3.Connection, job_id: str) -> None:
    names = {row["name"] for row in connection.execute("PRAGMA table_info(idempotency)")}
    if not names:
        return
    connection.execute(
        "UPDATE idempotency SET held = 0 WHERE object_id = ? AND kind = 'JOB' AND held = 1",
        (job_id,),
    )


class JobRunner:
    """One worker. Long research work runs without the database lock held."""

    def __init__(self, connection: sqlite3.Connection, lock: threading.Lock, execute, ready) -> None:
        self.connection = connection
        self.lock = lock
        self.execute = execute
        self.ready = ready
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._scheduler = None
        self._next_schedule = datetime.now(timezone.utc)

    def start(self, scheduler=None) -> None:
        self._scheduler = scheduler
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, name="gtf-jobs", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.wait(1.0):
            try:
                self.step()
                if self._scheduler is not None and datetime.now(timezone.utc) >= self._next_schedule:
                    self._next_schedule = datetime.now(timezone.utc) + timedelta(seconds=60)
                    self._scheduler()
            except Exception as exc:
                log.error("job loop failed: %s", type(exc).__name__)

    def drain(self, limit: int = 20) -> None:
        for _ in range(limit):
            if not self.step():
                return

    def step(self) -> bool:
        claimed = self._claim()
        if claimed is None:
            return False
        job_id, request = claimed
        stop = threading.Event()
        beater = threading.Thread(target=self._beat, args=(job_id, stop), name="gtf-heartbeat", daemon=True)
        beater.start()
        try:
            outcome = self.execute(request)
        except Exception as exc:
            code = getattr(exc, "code", "INTERNAL")
            message = getattr(exc, "message", None) or "Research run failed"
            self._fail(job_id, str(code), str(message)[:400])
            return True
        finally:
            stop.set()
            beater.join(timeout=2)
        self._finish(job_id, outcome)
        return True

    def _claim(self) -> tuple[str, dict] | None:
        import json

        with self.lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                rows = self.connection.execute(
                    """
                    SELECT job_id, state, request_json FROM job
                    WHERE state IN (?, ?)
                    ORDER BY created_at, job_id
                    LIMIT 20
                    """,
                    (PENDING_DATA, VALIDATING),
                ).fetchall()
                row = None
                request = None
                for candidate in rows:
                    body = json.loads(candidate["request_json"] or "{}")
                    if candidate["state"] == PENDING_DATA and not self.ready(body):
                        continue
                    row = candidate
                    request = body
                    break
                if row is None:
                    self.connection.commit()
                    return None
                now = utcnow().isoformat()
                self.connection.execute(
                    """
                    UPDATE job
                    SET state = ?, heartbeat = ?, updated_at = ?
                    WHERE job_id = ? AND state IN (?, ?)
                    """,
                    (RUNNING, now, now, row["job_id"], PENDING_DATA, VALIDATING),
                )
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise
        return row["job_id"], request

    def _beat(self, job_id: str, stop: threading.Event) -> None:
        while not stop.wait(5):
            now = utcnow().isoformat()
            with self.lock:
                self.connection.execute(
                    "UPDATE job SET heartbeat = ?, updated_at = ? WHERE job_id = ? AND state = ?",
                    (now, now, job_id, RUNNING),
                )

    def _fail(self, job_id: str, code: str, message: str) -> None:
        now = utcnow().isoformat()
        with self.lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                current = self.connection.execute(
                    "SELECT cancel_requested, state FROM job WHERE job_id = ?",
                    (job_id,),
                ).fetchone()
                if current is None or current["state"] != RUNNING:
                    self.connection.commit()
                    return
                state = CANCELLED if current["cancel_requested"] else "FAILED"
                self.connection.execute(
                    """
                    UPDATE job
                    SET state = ?, error_code = ?, error_message = ?, updated_at = ?, completeness = NULL
                    WHERE job_id = ? AND state = ?
                    """,
                    (state, code, message, now, job_id, RUNNING),
                )
                _release_key(self.connection, job_id)
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise
        log.info("job %s state %s code %s", job_id, state, code)

    def _finish(self, job_id: str, outcome: dict) -> None:
        now = utcnow().isoformat()
        with self.lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                current = self.connection.execute(
                    "SELECT cancel_requested, state FROM job WHERE job_id = ?",
                    (job_id,),
                ).fetchone()
                if current is None or current["state"] != RUNNING:
                    self.connection.commit()
                    return
                if current["cancel_requested"]:
                    self.connection.execute(
                        """
                        UPDATE job
                        SET state = ?, updated_at = ?, error_code = ?, error_message = ?
                        WHERE job_id = ? AND state = ?
                        """,
                        (CANCELLED, now, "CANCELLED", "Cancelled before the result was stored", job_id, RUNNING),
                    )
                    _release_key(self.connection, job_id)
                    self.connection.commit()
                    log.info("job %s state CANCELLED", job_id)
                    return
                completeness = outcome["completeness"]
                if completeness == "COMPLETE":
                    state = "SUCCEEDED_COMPLETE"
                elif completeness == "PARTIAL":
                    state = "SUCCEEDED_PARTIAL"
                else:
                    state = "FAILED"
                scan_key = outcome["scan_key"]
                self._insert_scan(job_id, outcome, now)
                done = outcome.get("symbols_done")
                total = outcome.get("symbols_total")
                self.connection.execute(
                    """
                    UPDATE job
                    SET state = ?, completeness = ?, result_ref = ?, research_key = ?,
                        fixture = ?, progress_done = ?, progress_total = ?, progress_unit = ?,
                        updated_at = ?, heartbeat = ?,
                        error_code = ?, error_message = ?
                    WHERE job_id = ? AND state = ?
                    """,
                    (
                        state,
                        completeness,
                        scan_key,
                        scan_key,
                        1 if outcome.get("fixture") else 0,
                        done,
                        total,
                        "symbols",
                        now,
                        now,
                        None if state != "FAILED" else "SCAN_FAILED",
                        None if state != "FAILED" else "The research run did not complete",
                        job_id,
                        RUNNING,
                    ),
                )
                if state == "FAILED":
                    _release_key(self.connection, job_id)
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise
        log.info(
            "job %s state %s scan %s dataset %s",
            job_id,
            state,
            outcome.get("scan_key"),
            outcome.get("dataset_id"),
        )

    def _insert_scan(self, job_id: str, outcome: dict, now: str) -> None:
        import json

        envelope = outcome["envelope"]
        scan_key = outcome["scan_key"]
        existing = self.connection.execute(
            "SELECT scan_key FROM scan_result WHERE scan_key = ?",
            (scan_key,),
        ).fetchone()
        if existing is not None:
            return
        self.connection.execute(
            """
            INSERT INTO scan_result (
                scan_key, job_id, as_of, trade_type, invocation, dataset_id, universe_label,
                completeness, full_universe_scan, fixture, limitations_json,
                symbols_not_opened_json, envelope_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan_key,
                job_id,
                envelope.get("as_of"),
                envelope.get("trade_type"),
                envelope.get("invocation"),
                envelope.get("dataset_id"),
                (envelope.get("scan") or {}).get("universe"),
                envelope.get("completeness"),
                1 if envelope.get("full_universe_scan") else 0,
                1 if outcome.get("fixture") else 0,
                json.dumps(envelope.get("limitations") or []),
                json.dumps(envelope.get("symbols_not_opened") or []),
                outcome["envelope_json"],
                now,
            ),
        )
