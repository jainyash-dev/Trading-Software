"""One shared copy of each existing NSE module (their folders have hyphens, so they are
loaded by path). Every research module imports them from here, so a dataclass from the
Zone Engine is the same class everywhere in one process."""

import importlib.util
import os

NSE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(NSE)


def _load(name, *parts):
    spec = importlib.util.spec_from_file_location(name, os.path.join(NSE, *parts))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


replay_mod = _load("nse_research_replay", "eod", "nse_replay.py")
mtf = replay_mod.mtf            # nse/mtf-freshness/mtf_freshness.py, as nse_replay uses it
ze = mtf.ze                     # nse/zone-engine/zone_engine.py, as the orchestrator uses it
bhavcopy = _load("nse_research_bhavcopy", "eod", "nse_bhavcopy.py")
reference = _load("nse_research_reference", "eod", "nse_reference.py")
calendar = _load("nse_research_calendar", "calendar", "nse_calendar.py")

CALENDAR_DIR = os.path.join(NSE, "data", "calendar")
EOD_RAW_DIR = os.path.join(NSE, "data", "eod", "raw")
EOD_MANIFEST = os.path.join(NSE, "data", "eod", "manifest.csv")
REFERENCE_DIR = os.path.join(NSE, "data", "reference")
