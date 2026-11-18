"""The validation runner itself (nse/validation/run_all.py): it must never report a skip,
a load error or missing evidence as a pass, acceptance mode must fail without evidence,
and a run must leave no generated files in the working tree."""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from _load import ROOT

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from nse.validation import protected, run_all   # noqa: E402

MODULE = '''
import unittest
from _load import require_local

class T(unittest.TestCase):
    def test_pass(self):
        self.assertTrue(True)
%s
'''
PREREQ = '''
    def test_prereq(self):
        require_local(False, "synthetic missing evidence")
'''
FAILING = '''
    def test_fail(self):
        self.assertEqual(1, 2)
'''
PLAIN_SKIP = '''
    @unittest.skip("not a prerequisite")
    def test_skip(self):
        pass
'''


class Groups(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        sys.path.insert(0, self.tmp)
        self.names = []

    def tearDown(self):
        sys.path.remove(self.tmp)
        for n in self.names:
            sys.modules.pop(n, None)
        shutil.rmtree(self.tmp)

    def module(self, name, body):
        with open(os.path.join(self.tmp, name + ".py"), "w") as fh:
            fh.write(MODULE % body)
        self.names.append(name)
        return name

    def test_clean_group_passes(self):
        r = run_all.run_group("g", [self.module("vr_clean", "")])
        self.assertEqual((r["status"], r["ran"], r["skipped"]), (run_all.PASS, 1, 0))

    def test_missing_prerequisite_is_skipped_not_passed_and_fails_in_acceptance(self):
        name = self.module("vr_prereq", PREREQ)
        with mock.patch.dict(os.environ, {run_all.ACCEPTANCE_ENV: ""}):
            r = run_all.run_group("g", [name])
        self.assertEqual(r["status"], run_all.SKIPPED)
        self.assertEqual(r["prerequisite_skips"][0]["reason"].split(":")[0], "PREREQUISITE MISSING")
        sys.modules.pop(name, None)
        with mock.patch.dict(os.environ, {run_all.ACCEPTANCE_ENV: "1"}):
            r = run_all.run_group("g", [name])
        self.assertEqual((r["status"], r["failures"]), (run_all.FAIL, 1))

    def test_failures_plain_skips_and_import_errors_fail(self):
        self.assertEqual(run_all.run_group("g", [self.module("vr_fail", FAILING)])["status"], run_all.FAIL)
        self.assertEqual(run_all.run_group("g", [self.module("vr_skip", PLAIN_SKIP)])["status"], run_all.FAIL)
        r = run_all.run_group("g", ["vr_does_not_exist"])
        self.assertEqual(r["status"], run_all.FAIL)
        self.assertGreaterEqual(r["errors"], 1)          # unittest reports it as a failed import

    def test_a_group_that_runs_no_test_fails(self):
        # audit 2026-11-06 (Agent 6 #7): zero tests used to be a PASS
        with open(os.path.join(self.tmp, "vr_empty.py"), "w") as fh:
            fh.write("import unittest\n")
        self.names.append("vr_empty")
        r = run_all.run_group("g", ["vr_empty"])
        self.assertEqual((r["status"], r["ran"]), (run_all.FAIL, 0))


class ReferenceEvidence(unittest.TestCase):
    """audit 2026-11-06 (Agent 5): cited evidence files are re-hashed, never trusted by format."""

    def test_evidence_files_are_rehashed(self):
        import hashlib
        from nse.research.deps import NSE

        class Row(object):
            def __init__(self, f, h):
                self.export_file, self.export_sha256 = f, h
        tmp = tempfile.mkdtemp(dir=os.path.join(NSE, "data"))
        try:
            with open(os.path.join(tmp, "vr-evidence-ok.png"), "wb") as fh:
                fh.write(b"SYNTHETIC")
            good = hashlib.sha256(b"SYNTHETIC").hexdigest()
            got = run_all._evidence_hashes([Row("vr-evidence-ok.png", good), Row("vr-evidence-gone.png", good)])
            self.assertEqual(got, {"matched": ["vr-evidence-ok.png"], "mismatch": [], "missing": ["vr-evidence-gone.png"]})
            got = run_all._evidence_hashes([Row("vr-evidence-ok.png", "a" * 64)])
            self.assertEqual(got["mismatch"], ["vr-evidence-ok.png"])
        finally:
            shutil.rmtree(tmp)


class Verdict(unittest.TestCase):
    def c(self, status, required=True):
        return {"name": "x%s" % status, "status": status, "required": required}

    def test_verdicts_and_exit_codes(self):
        V = run_all.verdict
        self.assertEqual(V([self.c("PASS")], False), ("PASS", 0))
        self.assertEqual(V([self.c("PASS"), self.c("FAIL")], False)[1], 1)
        self.assertEqual(V([self.c("FAIL", required=False)], False)[1], 1)
        text, code = V([self.c("PASS"), self.c(run_all.SKIPPED)], False)
        self.assertEqual(code, 0)
        self.assertNotEqual(text, "PASS")
        text, code = V([self.c("PASS"), self.c(run_all.UNAVAILABLE, required=False)], False)
        self.assertEqual(code, 0)
        self.assertIn("EVIDENCE_UNAVAILABLE", text)
        # acceptance: missing evidence is a failure
        self.assertEqual(V([self.c(run_all.UNAVAILABLE, required=False)], True)[1], 1)
        self.assertEqual(V([self.c(run_all.SKIPPED)], True)[1], 1)

    def test_acceptance_cannot_be_partial(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            run_all.main(["--acceptance", "--no-data"])

    def test_main_returns_1_when_a_group_fails_and_records_readiness(self):
        tmp = tempfile.mkdtemp()
        try:
            out = os.path.join(tmp, "r.json")
            fake = [("bad", ["vr_does_not_exist"]), ("good", ["test_research_reports"])]
            with mock.patch.object(run_all, "GROUPS", fake), \
                    mock.patch.object(run_all, "check_repository", return_value={"name": "repository_checks",
                                                                                 "status": run_all.PASS}), \
                    contextlib.redirect_stdout(io.StringIO()):
                code = run_all.main(["--no-data", "--out", out])
            self.assertEqual(code, 1)
            with open(out) as fh:
                rep = json.load(fh)
            self.assertTrue(rep["verdict"].startswith("FAIL"))
            # the skipped optional checks are named in the report, not silently absent
            self.assertEqual(rep["checks_not_run"], ["local_data, reference_comparison (--no-data)"])
            self.assertIn("static_lint", [c["name"] for c in rep["checks"]])      # lint still ran
            rows = {r["id"]: r for r in rep["readiness"]}
            self.assertTrue(rows["zone_engine"]["unit_tested_state"].startswith("UNCONFIRMED"))
        finally:
            shutil.rmtree(tmp)

    def test_missing_local_data_is_unavailable_not_pass(self):
        tmp = tempfile.mkdtemp()
        try:
            from nse.research import deps
            with mock.patch.object(deps, "EOD_RAW_DIR", tmp), mock.patch.object(deps, "CALENDAR_DIR", tmp), \
                    mock.patch.object(deps, "REFERENCE_DIR", tmp):
                self.assertEqual(run_all.check_local_data()["status"], run_all.UNAVAILABLE)
                self.assertEqual(run_all.check_reference()["status"], run_all.UNAVAILABLE)
        finally:
            shutil.rmtree(tmp)


class StaticLint(unittest.TestCase):
    def test_no_linter_is_unavailable_never_pass(self):
        with mock.patch.object(run_all, "_lint_command", return_value=(None, None)):
            c = run_all.check_static_lint()
        self.assertEqual(c["status"], run_all.UNAVAILABLE)
        self.assertFalse(c["required"])

    def test_findings_fail_and_are_reported(self):
        cmd = [sys.executable, "-c", "print('nse/x.py:1:1: bad'); raise SystemExit(1)"]
        with mock.patch.object(run_all, "_lint_command", return_value=("fake", cmd)):
            c = run_all.check_static_lint()
        self.assertEqual(c["status"], run_all.FAIL)
        self.assertEqual(c["details"]["findings"], ["nse/x.py:1:1: bad"])
        self.assertEqual(run_all.verdict([c], False)[1], 1)    # an optional FAIL still fails the run

    def test_a_clean_run_passes(self):
        with mock.patch.object(run_all, "_lint_command", return_value=("fake", [sys.executable, "-c", "pass"])):
            self.assertEqual(run_all.check_static_lint()["status"], run_all.PASS)

    def test_acceptance_cannot_skip_lint(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            run_all.main(["--acceptance", "--no-lint"])


class Hygiene(unittest.TestCase):
    def caches(self):
        found = set()
        for base, dirs, _ in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in (".git", ".venv")]     # .venv: local dev tools, git-ignored
            if os.path.basename(base) == "__pycache__":
                found.add(base)
        return found

    def test_a_run_leaves_no_bytecode_or_changes_protected_files(self):
        before = self.caches()
        tmp = tempfile.mkdtemp()
        try:
            env = dict(os.environ)
            env.pop("PYTHONDONTWRITEBYTECODE", None)
            p = subprocess.run([sys.executable, "-m", "nse.validation.run_all", "--group", "strategy_gates",
                                "--no-data", "--out", os.path.join(tmp, "r.json")],
                               cwd=ROOT, capture_output=True, text=True, env=env)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        finally:
            shutil.rmtree(tmp)
        p = subprocess.run([sys.executable, "-m", "nse.research.cli", "readiness"], cwd=ROOT, capture_output=True,
                           text=True, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.caches() - before, set())
        self.assertEqual(protected.check(), [])


if __name__ == "__main__":
    unittest.main()
