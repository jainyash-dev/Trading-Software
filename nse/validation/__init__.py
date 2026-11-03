"""Repository validation for the NSE research system: python3 -m nse.validation.run_all

Validation must leave the working tree as it found it. Python writes this package's own
bytecode before this file runs, so the cache it just wrote is removed here, and nothing
imported afterwards writes bytecode."""

import os
import sys
import time

sys.dont_write_bytecode = True


def _drop_own_cache():
    cached = globals().get("__cached__")
    if not cached or not os.path.isfile(cached):
        return
    folder = os.path.dirname(cached)
    if time.time() - os.path.getmtime(cached) > 10:
        return                              # an older cache, not written by this run: leave it
    os.remove(cached)
    if not os.listdir(folder):
        os.rmdir(folder)


try:
    _drop_own_cache()
except OSError:
    pass
