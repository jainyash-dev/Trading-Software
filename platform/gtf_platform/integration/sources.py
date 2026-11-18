"""Resolve local research inputs. Nothing here downloads or adjusts prices."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from gtf_platform.config import Settings

_DATASET_CACHE: dict[tuple, dict] = {}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def ensure_repo_on_path() -> None:
    root = str(repo_root())
    if root not in sys.path:
        sys.path.append(root)


def fixture_source(settings: Settings) -> bool:
    label = (settings.source_label or "").upper()
    return bool(settings.fixture_mode or "FIXTURE" in label or "SYNTHETIC" in label)


def official_eod(settings: Settings) -> bool:
    if settings.bhavcopy_dir is None:
        return False
    official = repo_root() / "nse" / "data" / "eod" / "raw"
    try:
        return settings.bhavcopy_dir.resolve() == official.resolve()
    except OSError:
        return False


def assert_fixture_isolation(settings: Settings) -> None:
    if fixture_source(settings) and official_eod(settings):
        raise RuntimeError("fixture mode cannot read the official EOD archive")


def input_files(settings: Settings) -> list[str]:
    """Files that identify the configured dataset. Symbol subsets do not change the id."""
    ensure_repo_on_path()
    from nse.research.deps import bhavcopy

    paths: list[str] = []
    if settings.csv_dir is not None and settings.csv_dir.is_dir():
        paths.extend(sorted(str(path) for path in settings.csv_dir.glob("*.csv")))
    elif settings.bhavcopy_dir is not None and settings.bhavcopy_dir.is_dir():
        paths.extend(bhavcopy.archive_paths(str(settings.bhavcopy_dir)))
        if settings.eod_manifest is not None and settings.eod_manifest.is_file():
            paths.append(str(settings.eod_manifest))
    for path in (
        settings.universe_path,
        settings.instruments_path,
        settings.corporate_actions_path,
    ):
        if path is not None and path.is_file():
            paths.append(str(path))
    if settings.corporate_actions_path is not None:
        coverage = settings.corporate_actions_path.parent / "coverage.csv"
        if coverage.is_file():
            paths.append(str(coverage))
    if settings.calendar_dir is not None and settings.calendar_dir.is_dir():
        paths.extend(sorted(str(path) for path in settings.calendar_dir.glob("*.csv")))
    return paths


def dataset_identity(settings: Settings) -> dict | None:
    assert_fixture_isolation(settings)
    files = [path for path in input_files(settings) if os.path.isfile(path)]
    if not files:
        return None
    signature = tuple((path, os.path.getsize(path), os.path.getmtime(path)) for path in files)
    cached = _DATASET_CACHE.get(signature)
    if cached is not None:
        return dict(cached)
    ensure_repo_on_path()
    import hashlib

    from nse.research import run_manifest

    fingerprints = run_manifest.fingerprints(files)
    manifest_sha = None
    if settings.eod_manifest is not None and settings.eod_manifest.is_file():
        digest = hashlib.sha256()
        with open(settings.eod_manifest, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        manifest_sha = digest.hexdigest()
    identity = {
        "dataset_id": run_manifest.dataset_sha256(fingerprints),
        "file_count": len(fingerprints),
        "manifest_sha256": manifest_sha,
        "research_validation": False,
        "data_ready": False,
        "fixture": fixture_source(settings),
    }
    _DATASET_CACHE[signature] = dict(identity)
    return identity


def load_calendar(settings: Settings):
    if settings.calendar_dir is None:
        return None
    ensure_repo_on_path()
    from nse.research.deps import calendar as calendar_mod

    return calendar_mod.NseCalendar.load(str(settings.calendar_dir))


def newest_session(settings: Settings):
    """Latest accepted session date, or None when the source is empty."""
    import datetime

    ensure_repo_on_path()
    if settings.eod_manifest is not None and settings.eod_manifest.is_file() and not settings.csv_dir:
        from nse.research.deps import bhavcopy

        rows = bhavcopy.read_manifest(str(settings.eod_manifest))
        dates = [
            datetime.date.fromisoformat(row["trade_date"])
            for row in rows
            if row.get("kind") == "ARCHIVE" and row.get("trade_date")
        ]
        return max(dates) if dates else None
    if settings.csv_dir is not None and settings.csv_dir.is_dir():
        latest = None
        for path in settings.csv_dir.glob("*.csv"):
            day = _csv_max_date(path)
            if day is not None and (latest is None or day > latest):
                latest = day
        return latest
    return None


def session_file_ready(settings: Settings, day) -> bool:
    """True when the accepted file for that session is already on disk. Never downloads."""
    ensure_repo_on_path()
    if settings.csv_dir is not None:
        for path in settings.csv_dir.glob("*.csv"):
            if _csv_has_date(path, day):
                return True
        return False
    if settings.bhavcopy_dir is None:
        return False
    from nse.research.deps import bhavcopy

    name = bhavcopy.official_name(day)
    if not (settings.bhavcopy_dir / name).is_file():
        return False
    if settings.eod_manifest is None or not settings.eod_manifest.is_file():
        return True
    rows = bhavcopy.read_manifest(str(settings.eod_manifest))
    return any(row.get("kind") == "ARCHIVE" and row.get("file_name") == name for row in rows)


def _csv_max_date(path: Path):
    latest = None
    for day in _csv_dates(path):
        if latest is None or day > latest:
            latest = day
    return latest


def _csv_has_date(path: Path, day) -> bool:
    return day in _csv_dates(path)


def _csv_dates(path: Path):
    import csv
    import datetime

    dates = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "date" not in reader.fieldnames:
            return dates
        for row in reader:
            try:
                dates.append(datetime.date.fromisoformat((row.get("date") or "").strip()))
            except ValueError:
                continue
    return dates
