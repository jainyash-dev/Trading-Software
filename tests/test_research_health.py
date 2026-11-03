"""nse/research/health.py: the checkout health report. It must never call a tampered
protected file, a failed import or a false validation claim healthy, and it must keep the
calendar and EOD data at WARNING while B17 / B7 / B18 are open."""

import argparse
import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from _load import ROOT

sys.path.insert(0, ROOT)
from nse.research import health, readiness  # noqa: E402
from nse.validation import protected  # noqa: E402


class Health(unittest.TestCase):
    def test_this_checkout_is_healthy_and_says_it_is_not_validation(self):
        rep = health.report()
        self.assertTrue(rep["healthy"], [c for c in rep["checks"] if c["status"] == health.FAIL])
        self.assertIn("not validation", rep["note"])

    def test_a_changed_protected_file_fails(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        for rel in protected.PROTECTED:                       # copy, then tamper with the copy only
            os.makedirs(os.path.dirname(os.path.join(tmp, rel)) or tmp, exist_ok=True)
            shutil.copyfile(os.path.join(ROOT, rel), os.path.join(tmp, rel))
        first = sorted(protected.PROTECTED)[0]
        with open(os.path.join(tmp, first), "ab") as fh:
            fh.write(b" ")
        self.assertEqual(health.check_protected(tmp)["status"], health.FAIL)
        self.assertEqual(health.check_protected(ROOT)["status"], health.OK)

    def test_calendar_is_never_ok_while_b17_is_open(self):
        self.assertEqual(health.check_calendar()["status"], health.WARNING)
        self.assertEqual(health.check_calendar(tempfile.gettempdir())["status"], health.UNAVAILABLE)

    def test_missing_eod_data_is_unavailable_not_ok(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        self.assertEqual(health.check_eod(tmp, os.path.join(tmp, "manifest.csv"))["status"], health.UNAVAILABLE)

    def test_an_external_validation_claim_without_evidence_fails(self):
        rows = readiness.report()
        rows[0] = dict(rows[0], externally_validated=True)
        with mock.patch.object(readiness, "report", return_value=rows):
            self.assertEqual(health.check_readiness()["status"], health.FAIL)

    def test_an_import_error_fails_and_is_named(self):
        real = health.importlib.import_module

        def boom(name):
            if name == "nse.research.trend":
                raise ImportError("simulated")
            return real(name)
        with mock.patch.object(health.importlib, "import_module", side_effect=boom):
            out = health.check_modules()
        self.assertEqual(out["status"], health.FAIL)
        self.assertIn("trend", out["detail"])

    def test_cli_exit_code_follows_the_verdict(self):
        p = argparse.ArgumentParser()
        sub = p.add_subparsers(dest="cmd")
        health.add_commands(sub)
        args = p.parse_args(["health"])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(args.func(args), 0)
            with mock.patch.object(health, "check_protected", return_value=health._check("protected_files", health.FAIL, "x")):
                self.assertEqual(args.func(args), 1)


if __name__ == "__main__":
    unittest.main()
