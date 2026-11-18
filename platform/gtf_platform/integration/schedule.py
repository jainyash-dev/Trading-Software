"""After-close scan scheduling. It never downloads and never scans an unresolved date."""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from gtf_platform.config import Settings
from gtf_platform.errors import ApiError
from gtf_platform.integration import research, sources
from gtf_platform.store import accept_job, body_hash

log = logging.getLogger("gtf_platform.schedule")
IST = ZoneInfo("Asia/Kolkata")
AFTER_CLOSE = time(15, 45)


def consider(settings: Settings, connection, lock, now: datetime | None = None) -> dict | None:
    if not _scheduler_enabled(settings, connection):
        return None
    if settings.calendar_dir is None or settings.universe_path is None:
        log.info("scheduler skipped: calendar or universe is not configured")
        return None
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    local = moment.astimezone(IST)
    day = local.date()
    if local.time() < AFTER_CLOSE:
        day = day - timedelta(days=1)
    identity = sources.dataset_identity(settings)
    if identity is None:
        log.info("scheduler waiting: no local dataset")
        return None
    due = _due_day(settings, day)
    if due is None:
        return None
    body = {
        "mode": "SCHEDULED",
        "as_of": due.isoformat(),
        "trade_type": "MIT",
        "universe": "SUPPORTED",
        "dataset_id": identity["dataset_id"],
    }
    try:
        plan = research.prepare(settings, body)
    except ApiError as exc:
        log.info("scheduler did not start a scan: %s", exc.code)
        return None
    key = "schedule:%s:%s:%s" % (due.isoformat(), identity["dataset_id"], "SUPPORTED")
    payload = body_hash(research.canonical_plan_body(body))
    state = {
        "RUN": "VALIDATING",
        "PENDING_DATA": "PENDING_DATA",
        "SKIPPED_HOLIDAY": "SKIPPED_HOLIDAY",
        "SKIPPED_UNRESOLVED_CALENDAR": "SKIPPED_UNRESOLVED_CALENDAR",
    }[plan.disposition]
    with lock:
        connection.execute("BEGIN IMMEDIATE")
        try:
            kind, job = accept_job(
                connection,
                idempotency_key=key,
                payload_hash=payload,
                kind="SCAN",
                state=state,
                request=plan.stored,
                fixture=plan.fixture,
                research_key=plan.research_key,
                progress_total=plan.progress_total,
                error_code=plan.error_code,
                error_message=plan.error_message,
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    log.info("scheduler %s job %s state %s", kind, job.get("job_id"), job.get("state"))
    return job


def _scheduler_enabled(settings: Settings, connection) -> bool:
    """A saved owner setting is the flag the scheduler reads. An unsaved key keeps the process default."""
    from gtf_platform.store import read_settings

    row = connection.execute("SELECT 1 FROM app_setting WHERE key = 'scheduler_enabled'").fetchone()
    if row is None:
        return settings.scheduler_enabled
    value = read_settings(connection).get("scheduler_enabled")
    if not isinstance(value, bool):
        return False
    return value


def _due_day(settings: Settings, day):
    sources.ensure_repo_on_path()
    from nse.research.deps import calendar as calendar_mod

    try:
        calendar = sources.load_calendar(settings)
    except Exception:
        log.info("scheduler skipped: calendar failed to load")
        return None
    for _ in range(12):
        try:
            kind = calendar.session_type(day)
        except calendar_mod.CalendarAmbiguityError:
            log.info("scheduler unresolved calendar %s", day.isoformat())
            return day
        except calendar_mod.CalendarCoverageError:
            return None
        if kind in {"NORMAL", "NORMAL_SPECIAL"}:
            return day
        if kind in {"HOLIDAY", "WEEKEND", "EXCLUDED_MUHURAT", "EXCLUDED_SHORTENED"}:
            day = day - timedelta(days=1)
            continue
        return None
    return None
