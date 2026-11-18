"""Process configuration. Paths and origins come from the environment, not from domain code."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1"})


@dataclass(frozen=True)
class Settings:
    bind_host: str
    bind_port: int
    advertised_port: int
    public_origins: tuple[str, ...]
    platform_db: Path
    research_db: Path | None
    cookie_secure: bool
    data_dir: Path
    testing: bool = False

    cookie_name: str = "gtf_session"
    session_ttl_seconds: int = 18 * 60 * 60
    csv_dir: Path | None = None
    bhavcopy_dir: Path | None = None
    eod_manifest: Path | None = None
    calendar_dir: Path | None = None
    universe_path: Path | None = None
    instruments_path: Path | None = None
    corporate_actions_path: Path | None = None
    equity_names_path: Path | None = None
    source_label: str = "USER_CSV"
    price_adjustment: str = "UNKNOWN"
    series: str = "EQ"
    scheduler_enabled: bool = False
    fixture_mode: bool = False
    repo_root: Path | None = None

    def origin(self) -> str:
        return "http://%s:%s" % (self.bind_host, self.advertised_port)

    def allowed_origins(self) -> frozenset[str]:
        return frozenset((self.origin(),) + self.public_origins)

    def expected_host(self) -> str:
        return "%s:%s" % (self.bind_host, self.advertised_port)


def default_data_dir() -> Path:
    """Local launcher default. Override with GTF_DATA_DIR for tests and later hosts."""
    configured = os.environ.get("GTF_DATA_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / "Library" / "Application Support" / "GTFTradingIntelligence"


def load_settings(*, advertised_port: int | None = None, testing: bool = False) -> Settings:
    host = os.environ.get("GTF_BIND_HOST", "127.0.0.1").strip()
    if host not in LOOPBACK_HOSTS:
        raise ValueError("GTF_BIND_HOST must be 127.0.0.1 or ::1")
    port = _port(os.environ.get("GTF_BIND_PORT", "0"))
    data_dir = default_data_dir()
    db_env = os.environ.get("GTF_PLATFORM_DB", "").strip()
    platform_db = Path(db_env).expanduser() if db_env else data_dir / "platform.sqlite"
    research_env = os.environ.get("GTF_RESEARCH_DB", "").strip()
    research_db = Path(research_env).expanduser() if research_env else None
    secure = os.environ.get("GTF_COOKIE_SECURE", "0").strip() == "1"
    root = Path(__file__).resolve().parents[2]
    fixture_mode = os.environ.get("GTF_FIXTURE", "0").strip() == "1"
    source_label = os.environ.get("GTF_SOURCE_LABEL", "USER_CSV").strip() or "USER_CSV"
    price_adjustment = os.environ.get("GTF_PRICE_ADJUSTMENT", "UNKNOWN").strip() or "UNKNOWN"
    if price_adjustment not in {"UNKNOWN", "NONE"}:
        raise ValueError("GTF_PRICE_ADJUSTMENT must be UNKNOWN or NONE")
    if fixture_mode and "FIXTURE" not in source_label and "SYNTHETIC" not in source_label:
        source_label = "FIXTURE"
    origins = tuple(
        item.strip().rstrip("/")
        for item in os.environ.get("GTF_PUBLIC_ORIGINS", "").split(",")
        if item.strip()
    )
    shown = port if advertised_port is None else advertised_port
    if shown == 0:
        shown = port
    paths = _data_paths(root, fixture_mode)
    return Settings(
        bind_host=host,
        bind_port=port,
        advertised_port=shown,
        public_origins=origins,
        platform_db=platform_db,
        research_db=research_db,
        cookie_secure=secure,
        data_dir=data_dir,
        testing=testing,
        csv_dir=paths["csv_dir"],
        bhavcopy_dir=paths["bhavcopy_dir"],
        eod_manifest=paths["eod_manifest"],
        calendar_dir=paths["calendar_dir"],
        universe_path=paths["universe_path"],
        instruments_path=paths["instruments_path"],
        corporate_actions_path=paths["corporate_actions_path"],
        equity_names_path=paths["equity_names_path"],
        source_label=source_label,
        price_adjustment=price_adjustment,
        scheduler_enabled=os.environ.get("GTF_SCHEDULER", "0").strip() == "1",
        fixture_mode=fixture_mode,
        repo_root=root,
    )


def _optional_path(env_name: str) -> Path | None:
    raw = os.environ.get(env_name, "").strip()
    if not raw:
        return None
    return Path(raw).expanduser()


def _data_paths(root: Path, fixture_mode: bool) -> dict[str, Path | None]:
    """Environment paths win. Otherwise use the repository data tree when it is present.

    Fixture mode is refused against the official EOD directory so labelled fixtures
    cannot read accepted NSE archives.
    """
    csv_dir = _optional_path("GTF_CSV_DIR")
    bhavcopy_dir = _optional_path("GTF_BHAVCOPY_DIR")
    manifest = _optional_path("GTF_EOD_MANIFEST")
    calendar_dir = _optional_path("GTF_CALENDAR_DIR")
    universe_path = _optional_path("GTF_UNIVERSE")
    instruments_path = _optional_path("GTF_INSTRUMENTS")
    corporate_actions_path = _optional_path("GTF_CORPORATE_ACTIONS")
    equity_names_path = _optional_path("GTF_EQUITY_NAMES")
    official = root / "nse" / "data" / "eod" / "raw"
    official_manifest = root / "nse" / "data" / "eod" / "manifest.csv"
    using_official = False
    if csv_dir is None and bhavcopy_dir is None and official.is_dir():
        bhavcopy_dir = official
        using_official = True
    if manifest is None and using_official and official_manifest.is_file():
        manifest = official_manifest
    if calendar_dir is None:
        candidate = root / "nse" / "data" / "calendar"
        if candidate.is_dir():
            calendar_dir = candidate
    if universe_path is None:
        candidate = root / "nse" / "data" / "universe" / "nifty100_universe.csv"
        if candidate.is_file():
            universe_path = candidate
    if instruments_path is None:
        candidate = root / "nse" / "data" / "universe" / "instrument_records.csv"
        if candidate.is_file():
            instruments_path = candidate
    if corporate_actions_path is None:
        candidate = root / "nse" / "data" / "corporate_actions" / "actions.csv"
        if candidate.is_file():
            corporate_actions_path = candidate
    if equity_names_path is None:
        candidate = root / "nse" / "data" / "universe" / "evidence" / "identity" / "EQUITY_L.csv"
        if candidate.is_file():
            equity_names_path = candidate
    if fixture_mode and bhavcopy_dir is not None and official.exists():
        if bhavcopy_dir.resolve() == official.resolve():
            raise ValueError("GTF_FIXTURE cannot read the official EOD archive")
    return {
        "csv_dir": csv_dir,
        "bhavcopy_dir": bhavcopy_dir,
        "eod_manifest": manifest,
        "calendar_dir": calendar_dir,
        "universe_path": universe_path,
        "instruments_path": instruments_path,
        "corporate_actions_path": corporate_actions_path,
        "equity_names_path": equity_names_path,
    }


def with_port(settings: Settings, port: int) -> Settings:
    return replace(settings, advertised_port=port)


def _port(raw: str) -> int:
    try:
        port = int(raw)
    except ValueError as exc:
        raise ValueError("GTF_BIND_PORT must be an integer") from exc
    if port < 0 or port > 65535:
        raise ValueError("GTF_BIND_PORT is out of range")
    return port
