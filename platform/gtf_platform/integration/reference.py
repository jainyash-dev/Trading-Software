"""Read-only market reference. Universe certification is never upgraded here."""

from __future__ import annotations

import csv
import datetime

from gtf_platform.config import Settings
from gtf_platform.errors import ApiError
from gtf_platform.integration import sources

_CACHE: dict[tuple, object] = {}


def datasets(settings: Settings) -> dict:
    from gtf_platform.integration.desk import evaluate_data_ready

    identity = sources.dataset_identity(settings)
    readiness = evaluate_data_ready(settings)
    limitations = list(dict.fromkeys(list(limitation_list(settings)) + list(readiness.get("limitations") or [])))
    rows = []
    if identity is not None:
        rows.append(
            {
                "dataset_id": identity["dataset_id"],
                "manifest_sha256": identity["manifest_sha256"],
                "file_count": identity["file_count"],
                "research_validation": False,
                "data_ready": bool(readiness["data_ready"]),
                "readiness_state": readiness["readiness_state"],
                "fixture": identity["fixture"],
            }
        )
    return {"datasets": rows, "limitations": limitations, "fixture": bool(identity and identity["fixture"])}


def limitation_list(settings: Settings) -> list[str]:
    found = ["DATA_READY_NOT_CLAIMED"]
    universe = _universe(settings)
    if universe is None:
        found.append("UNIVERSE_NOT_CONFIGURED")
    else:
        found.extend(universe_limitations(settings))
    coverage = corporate_action_limitations(settings)
    found.extend(coverage["limitations"])
    found.append("IDENTITY_JOINS_ARE_NOT_PERFORMED_HERE")
    return list(dict.fromkeys(found))


def universe_payload(settings: Settings, as_of_text: str) -> dict:
    if not as_of_text:
        raise ApiError(400, "REQUEST_INVALID", "as_of is required")
    try:
        day = datetime.date.fromisoformat(as_of_text[:10])
    except ValueError as exc:
        raise ApiError(400, "REQUEST_INVALID", "as_of is not a date") from exc
    universe = _universe(settings)
    if universe is None:
        raise ApiError(422, "DATA_INSUFFICIENT", "No universe file is configured")
    members = []
    for row in universe.members(day):
        members.append(
            {
                "symbol": row.symbol,
                "series": row.series,
                "isin": row.isin or None,
                "verified": bool(row.verified),
                "effective_from": row.effective_from.isoformat(),
                "effective_to": None if row.effective_to is None else row.effective_to.isoformat(),
            }
        )
    limitations = universe.limitations(day)
    return {
        "as_of": day.isoformat(),
        "name": universe.name,
        "members": members,
        "limitations": limitations,
        "certified": False,
        "full_universe_scan": False,
    }


def universe_limitations(settings: Settings) -> list[str]:
    universe = _universe(settings)
    if universe is None:
        return ["UNIVERSE_NOT_CONFIGURED"]
    # A date inside the file still reports UNIVERSE_UNVERIFIED until a human certifies it.
    sample = universe.rows[0].effective_from if universe.rows else datetime.date(2024, 1, 1)
    return list(universe.limitations(sample))


def calendar_payload(settings: Settings, date_text: str) -> dict:
    if not date_text:
        raise ApiError(400, "REQUEST_INVALID", "date is required")
    try:
        day = datetime.date.fromisoformat(date_text)
    except ValueError as exc:
        raise ApiError(400, "REQUEST_INVALID", "date is not YYYY-MM-DD") from exc
    if settings.calendar_dir is None:
        return {"date": day.isoformat(), "status": "UNRESOLVED", "classification": None,
                "reason": "NO_CALENDAR"}
    sources.ensure_repo_on_path()
    from nse.research.deps import calendar as calendar_mod

    try:
        calendar = sources.load_calendar(settings)
        classification = calendar.session_type(day)
    except calendar_mod.CalendarAmbiguityError:
        return {"date": day.isoformat(), "status": "UNRESOLVED", "classification": None,
                "reason": "CALENDAR_UNRESOLVED"}
    except calendar_mod.CalendarCoverageError:
        return {"date": day.isoformat(), "status": "UNRESOLVED", "classification": None,
                "reason": "CALENDAR_UNCOVERED"}
    except Exception as exc:
        raise ApiError(422, "DATA_INSUFFICIENT", "The NSE calendar could not be loaded") from exc
    return {"date": day.isoformat(), "status": "CONFIRMED", "classification": classification, "reason": None}


def search_instruments(settings: Settings, query: str) -> list[dict]:
    """Search by symbol, company name or ISIN. One result per (symbol, ISIN): a symbol that
    traded under several ISINs is listed once per ISIN and never merged. An identity is
    verified only when a verified universe period has that symbol and that ISIN."""
    text = (query or "").strip()
    if len(text) < 1:
        return []
    needle = text.upper()
    rows = []
    seen = set()
    for item in _names(settings) + _identity_rows(settings):
        key = (item["symbol"], item["isin"])
        if key in seen:
            continue
        haystack = " ".join(part for part in (item["symbol"], item["name"], item["isin"]) if part).upper()
        if needle in haystack:
            rows.append(dict(item))
            seen.add(key)
        if len(rows) >= 50:
            break
    verified = _verified_identities(settings)
    for item in rows:
        item["verified"] = bool(item["isin"]) and (item["symbol"], item["isin"]) in verified
        if not item["verified"]:
            item["verification"] = "UNVERIFIED"
    return rows


def _identity_rows(settings: Settings) -> list[dict]:
    path = settings.instruments_path
    if path is None or not path.is_file():
        return []
    key = ("identity", str(path), path.stat().st_mtime)
    if key in _CACHE:
        return [dict(item) for item in _CACHE[key]]
    import csv

    rows = []
    seen = set()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            symbol = (raw.get("symbol") or raw.get("new_symbol") or "").strip().upper()
            isin = (raw.get("isin") or "").strip().upper() or None
            # one row per (symbol, ISIN): an ISIN change is a different security (ED-29)
            if not symbol or (symbol, isin) in seen:
                continue
            seen.add((symbol, isin))
            rows.append({"symbol": symbol, "name": None, "isin": isin, "verified": False, "source": "instrument_records"})
    _CACHE[key] = rows
    return [dict(item) for item in rows]


def corporate_action_limitations(settings: Settings) -> dict:
    """Missing coverage is not evidence that no corporate action occurred."""
    covered = _covered_symbols(settings)
    universe = _universe(settings)
    if settings.corporate_actions_path is None or covered is None:
        return {
            "limitations": ["CORPORATE_ACTION_COVERAGE_UNKNOWN"],
            "incomplete_symbols": [],
            "note": "No verified coverage file is configured. An empty response is not proof of no corporate action.",
        }
    members = sorted({row.symbol for row in universe.rows}) if universe is not None else []
    incomplete = [symbol for symbol in members if symbol not in covered] if members else sorted(set())
    limitations = []
    if incomplete:
        limitations.append("CORPORATE_ACTION_COVERAGE_INCOMPLETE")
    return {
        "limitations": limitations,
        "incomplete_symbols": incomplete,
        "covered_symbols": len(covered),
        "note": "A symbol without a verified coverage window is uncovered. Absence is not proof of no corporate action.",
    }


def _universe(settings: Settings):
    if settings.universe_path is None or not settings.universe_path.is_file():
        return None
    key = ("universe", str(settings.universe_path), settings.universe_path.stat().st_mtime)
    if key in _CACHE:
        return _CACHE[key]
    sources.ensure_repo_on_path()
    from nse.research import universe as universe_mod

    loaded = universe_mod.load(str(settings.universe_path), name="SUPPORTED")
    _CACHE[key] = loaded
    return loaded


def _covered_symbols(settings: Settings):
    if settings.corporate_actions_path is None:
        return None
    coverage = settings.corporate_actions_path.parent / "coverage.csv"
    if not coverage.is_file():
        return None
    key = ("coverage", str(coverage), coverage.stat().st_mtime)
    if key in _CACHE:
        return _CACHE[key]
    sources.ensure_repo_on_path()
    from nse.research import corporate_actions

    try:
        loaded = corporate_actions.load_coverage(str(coverage))
    except Exception:
        return None
    symbols = set(loaded)
    _CACHE[key] = symbols
    return symbols


def _names(settings: Settings) -> list[dict]:
    path = settings.equity_names_path
    key = ("names", str(path) if path else "", path.stat().st_mtime if path and path.is_file() else 0)
    if key in _CACHE:
        return [dict(item) for item in _CACHE[key]]
    rows = []
    if path is not None and path.is_file():
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for raw in reader:
                # NSE's EQUITY_L.csv header has a space after each comma (" ISIN NUMBER")
                raw = {(key or "").strip(): value for key, value in raw.items()}
                symbol = (raw.get("SYMBOL") or "").strip().upper()
                if not symbol:
                    continue
                rows.append(
                    {
                        "symbol": symbol,
                        "name": (raw.get("NAME OF COMPANY") or "").strip() or None,
                        "isin": (raw.get("ISIN NUMBER") or "").strip().upper() or None,
                        "verified": False,
                    }
                )
    _CACHE[key] = rows
    return [dict(item) for item in rows]


def _verified_identities(settings: Settings) -> set[tuple[str, str]]:
    universe = _universe(settings)
    if universe is None:
        return set()
    return {(row.symbol, row.isin) for row in universe.rows if row.verified and row.isin}
