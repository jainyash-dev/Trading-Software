"""Launcher. Puts the platform directory on sys.path without shadowing stdlib platform."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gtf_platform.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
