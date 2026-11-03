"""Load a script from a skill folder (the folder names have hyphens)."""

import importlib.util
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures")

# Set to 1 for a Phase 1 acceptance run: a missing local prerequisite then fails the
# test instead of skipping it, so an acceptance result can never rest on skipped checks.
ACCEPTANCE_ENV = "NSE_PHASE1_ACCEPTANCE"


def require_local(condition, what):
    """Skip (normal run) or fail (acceptance run) when git-ignored local evidence such as
    official PDFs or raw NSE files is absent. `what` names the missing prerequisite."""
    if condition:
        return
    message = "PREREQUISITE MISSING: " + what
    if os.environ.get(ACCEPTANCE_ENV) == "1":
        raise AssertionError(message + " (%s=1)" % ACCEPTANCE_ENV)
    raise unittest.SkipTest(message)


def load(folder, name):
    path = os.path.join(ROOT, folder, name + ".py")
    spec = importlib.util.spec_from_file_location("trader_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
