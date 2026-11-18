"""Research-run manifests (nse/research/run_manifest.py, ED-18). SYNTHETIC inputs only.

A manifest must identify a run reproducibly (same inputs, settings and code -> same
run_id; any input byte or setting changed -> a different run_id), record the outputs it
describes, and never put machine- or moment-specific data into the deterministic reports.
"""

import contextlib
import datetime
import io
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import _research as R
from nse.research import cli, run_manifest as rm

AS_OF = datetime.datetime(2024, 1, 31, 15, 30)
CODE = {"git_head": "0" * 40, "dirty": False, "diff_sha256": None, "untracked_files": 0, "untracked_sha256": None}


class Manifest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.a = os.path.join(self.tmp, "A.csv")
        with open(self.a, "w") as fh:
            fh.write("date,open,high,low,close\n2024-01-01,1,2,0.5,1.5\n")

    def build(self, **kw):
        args = dict(kind="scan", as_of=AS_OF, parameters={"trade_type": "MIT"}, input_paths=[self.a], code=CODE)
        args.update(kw)
        return rm.build(**args)

    def test_same_inputs_settings_and_code_give_the_same_run_id_whatever_the_clock(self):
        one = self.build(recorded_at="2026-01-01T00:00:00+00:00")
        two = self.build(recorded_at="2027-06-30T12:00:00+00:00")
        self.assertEqual(one["run_id"], two["run_id"])
        self.assertRegex(one["run_id"], r"^run-[0-9a-f]{16}$")
        self.assertNotEqual(one["recorded_at"], two["recorded_at"])

    def test_any_change_to_data_settings_as_of_or_code_changes_the_run_id(self):
        base = self.build()["run_id"]
        self.assertNotEqual(self.build(parameters={"trade_type": "WIT-75"})["run_id"], base)
        self.assertNotEqual(self.build(as_of=AS_OF + datetime.timedelta(days=1))["run_id"], base)
        self.assertNotEqual(self.build(code=dict(CODE, git_head="1" * 40))["run_id"], base)
        # uncommitted edits on the same HEAD are a different code identity (QA 2026-11-08)
        dirty_a = self.build(code=dict(CODE, dirty=True, diff_sha256="a" * 64))["run_id"]
        dirty_b = self.build(code=dict(CODE, dirty=True, diff_sha256="b" * 64))["run_id"]
        self.assertNotEqual(dirty_a, dirty_b)
        self.assertNotEqual(dirty_a, base)
        before = self.build()["dataset_sha256"]
        with open(self.a, "a") as fh:
            fh.write("2024-01-02,1,2,0.5,1.6\n")                 # one input byte changes
        changed = self.build()
        self.assertNotEqual(changed["run_id"], base)
        self.assertNotEqual(changed["dataset_sha256"], before)

    def test_inputs_are_fingerprinted_and_folders_walked(self):
        sub = os.path.join(self.tmp, "cal")
        os.makedirs(sub)
        with open(os.path.join(sub, "events.csv"), "w") as fh:
            fh.write("x\n")
        m = self.build(input_paths=[self.a, sub, None])
        self.assertEqual([os.path.basename(i["path"]) for i in m["inputs"]], ["A.csv", "events.csv"])
        self.assertTrue(all(len(i["sha256"]) == 64 and i["bytes"] > 0 for i in m["inputs"]))

    def test_methodology_pins_the_protected_sources(self):
        meth = self.build()["methodology"]
        from nse.validation import protected
        self.assertEqual(meth["protected_sources"], dict(protected.PROTECTED))
        self.assertIn("zone_engine", meth["engine_versions"])

    def test_uncommitted_code_is_a_stated_limitation_and_unknown_git_is_not_guessed(self):
        dirty = self.build(code=dict(CODE, dirty=True, diff_sha256="a" * 64))
        self.assertTrue(any(x.startswith("CODE_REVISION_HAS_UNCOMMITTED_CHANGES") for x in dirty["limitations"]))
        with mock.patch.object(rm.subprocess, "run", side_effect=OSError("no git")):
            self.assertEqual(rm.code_revision(), {"git_head": None, "dirty": None, "diff_sha256": None,
                                                  "untracked_files": None, "untracked_sha256": None})
        unknown = self.build(code={"git_head": None, "dirty": None})
        self.assertIn("CODE_REVISION_UNKNOWN: git unavailable; the code identity is not recorded", unknown["limitations"])

    def fake_git(self, root, diff=b"", untracked=()):
        """subprocess.run stand-in answering the three git calls code_revision makes."""
        class P:
            def __init__(self, out):
                self.stdout, self.returncode = out, 0

        def run(cmd, **kw):
            if cmd[1] == "rev-parse":
                return P(b"%s\n" % (b"0" * 40))
            if cmd[1] == "diff":
                self.assertEqual(cmd[-1], rm.CODE_PATHSPEC)            # code only, never docs
                return P(diff)
            return P(b"\0".join(u.encode() for u in untracked))
        return mock.patch.object(rm.subprocess, "run", side_effect=run)

    def test_untracked_code_is_part_of_the_code_identity(self):
        # QA 2026-11-08: a new or edited untracked module under nse/ must change run_id
        root = self.tmp
        os.makedirs(os.path.join(root, "nse"))
        mod = os.path.join(root, "nse", "new_module.py")
        with open(mod, "w") as fh:
            fh.write("X = 1\n")
        with self.fake_git(root):
            clean = rm.code_revision(root)
        with self.fake_git(root, untracked=["nse/new_module.py"]):
            one = rm.code_revision(root)
        with open(mod, "w") as fh:
            fh.write("X = 2\n")
        with self.fake_git(root, untracked=["nse/new_module.py"]):
            two = rm.code_revision(root)
        self.assertFalse(clean["dirty"])
        self.assertTrue(one["dirty"])
        self.assertEqual(one["untracked_files"], 1)
        self.assertNotEqual(one["untracked_sha256"], two["untracked_sha256"])
        ids = [self.build(code=c)["run_id"] for c in (clean, one, two)]
        self.assertEqual(len(set(ids)), 3)
        self.assertTrue(any("CODE_REVISION_HAS_UNCOMMITTED_CHANGES" in x for x in self.build(code=one)["limitations"]))

    def test_missing_inputs_are_recorded_not_dropped(self):
        gone = os.path.join(self.tmp, "absent.csv")
        m = self.build(input_paths=[self.a, gone])
        self.assertEqual(len(m["missing_inputs"]), 1)
        self.assertTrue(any(x.startswith("INPUT_PATHS_MISSING") for x in m["limitations"]))
        self.assertNotEqual(m["run_id"], self.build()["run_id"])

    def test_relative_and_absolute_paths_give_the_same_run_id(self):
        rel = os.path.relpath(self.a)
        one = self.build(parameters=rm.relative_paths({"csv_dir": rel}, rm.PATH_PARAMS))
        two = self.build(parameters=rm.relative_paths({"csv_dir": os.path.abspath(self.a)}, rm.PATH_PARAMS))
        self.assertEqual(one["run_id"], two["run_id"])

    def test_hidden_files_in_input_folders_are_ignored(self):
        sub = os.path.join(self.tmp, "cal")
        os.makedirs(sub)
        for n in ("events.csv", ".DS_Store"):
            with open(os.path.join(sub, n), "w") as fh:
                fh.write("x\n")
        self.assertEqual([os.path.basename(i["path"]) for i in rm.fingerprints([sub])], ["events.csv"])

    def test_the_real_code_identity_has_a_hash_exactly_when_dirty(self):
        code = rm.code_revision()
        if code["git_head"] is None:
            self.skipTest("PREREQUISITE MISSING: git")
        self.assertEqual(code["dirty"], code["diff_sha256"] is not None or code["untracked_sha256"] is not None)

    def test_only_files_the_command_reads_are_inputs(self):
        import argparse
        for n in ("A", "B"):
            with open(os.path.join(self.tmp, n + ".csv"), "w") as fh:
                fh.write("x\n")
        os.makedirs(os.path.join(self.tmp, "eod"))
        man = os.path.join(self.tmp, "eod", "manifest.csv")              # outside the CSV folder
        with open(man, "w") as fh:
            fh.write("x\n")
        args = argparse.Namespace(csv_dir=self.tmp, bhavcopy_dir=None, manifest=man, universe=None, calendar=None)
        names = lambda ps: sorted(os.path.basename(p) for p in ps)
        self.assertEqual(names(rm.scan_input_paths(args, ["A"])), ["A.csv"])      # the scanned symbol only
        self.assertEqual(rm.scan_input_paths(args, ["a"]), [])     # inputs.load reports "a" as NO_INPUT_FILE
        self.assertEqual(names(rm.scan_input_paths(args)), ["A.csv", "B.csv"])   # no symbols: every CSV is read
        self.assertEqual(rm.scan_input_paths(args, ["A"], loads_data=False), [])  # WIT loads no candles
        # --manifest is read only with --bhavcopy-dir, so it is not an input of a CSV scan
        self.assertNotIn("manifest.csv", names(rm.scan_input_paths(args, ["A", "B"])))

    def test_identity_and_coverage_files_change_the_dataset_fingerprint(self):
        import argparse
        ident = os.path.join(self.tmp, "instruments.csv")
        actions = os.path.join(self.tmp, "actions.csv")
        coverage = os.path.join(self.tmp, "coverage.csv")
        with open(ident, "w") as fh:
            fh.write("symbol,isin\nSYN,INEONE\n")
        with open(actions, "w") as fh:
            fh.write("symbol,ex_date\n")
        with open(coverage, "w") as fh:
            fh.write("symbol,from_date\nSYN,2016-01-01\n")
        args = argparse.Namespace(csv_dir=None, bhavcopy_dir=None, manifest=None, universe=None, calendar=None,
                                  corporate_actions=actions, instruments=ident)
        names = sorted(os.path.basename(p) for p in rm.scan_input_paths(args, loads_data=False))
        self.assertEqual(names, ["actions.csv", "coverage.csv", "instruments.csv"])
        first = rm.build("scan", AS_OF, {"instruments": ident, "corporate_actions": actions},
                         rm.scan_input_paths(args, loads_data=False), code=CODE)
        with open(ident, "a") as fh:
            fh.write("TCS,INETWO\n")
        second = rm.build("scan", AS_OF, {"instruments": ident, "corporate_actions": actions},
                          rm.scan_input_paths(args, loads_data=False), code=CODE)
        self.assertNotEqual(first["dataset_sha256"], second["dataset_sha256"])
        with open(coverage, "a") as fh:
            fh.write("TCS,2016-01-01\n")
        third = rm.build("scan", AS_OF, {"instruments": ident, "corporate_actions": actions},
                         rm.scan_input_paths(args, loads_data=False), code=CODE)
        self.assertNotEqual(second["dataset_sha256"], third["dataset_sha256"])
        self.assertIn("instruments.csv", [os.path.basename(i["path"]) for i in third["inputs"]])
        self.assertIn("coverage.csv", [os.path.basename(i["path"]) for i in third["inputs"]])

    def test_write_hashes_outputs_and_excludes_itself(self):
        out = os.path.join(self.tmp, "out")
        os.makedirs(out)
        with open(os.path.join(out, "scan.json"), "w") as fh:
            fh.write("{}\n")
        path = rm.write(self.build(), out)
        rm.write(self.build(), out)                                  # rewriting never lists the manifest
        with open(path) as fh:
            data = json.load(fh)
        self.assertEqual([o["path"] for o in data["outputs"]], ["scan.json"])


class ScanCommand(unittest.TestCase):
    def test_scan_writes_a_manifest_and_keeps_the_reports_deterministic(self):
        cs = R.long_mit_candles()
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        data = os.path.join(tmp, "in")
        os.makedirs(data)
        with open(os.path.join(data, "SYN.csv"), "w", encoding="utf-8") as fh:
            fh.write("date,open,high,low,close\n")
            for c in cs:
                fh.write("%s,%s,%s,%s,%s\n" % (c.start.date(), c.open, c.high, c.low, c.close))
        outs = []
        for name in ("one", "two"):
            out = os.path.join(tmp, name)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["scan", "--as-of", str(cs[-1].start.date()), "--csv-dir", data,
                                           "--out", out]), 0)
            outs.append(out)
        with open(os.path.join(outs[0], rm.MANIFEST_NAME)) as fh:
            first = json.load(fh)
        with open(os.path.join(outs[1], rm.MANIFEST_NAME)) as fh:
            second = json.load(fh)
        self.assertEqual(first["run_id"], second["run_id"])
        self.assertEqual(first["outputs"], second["outputs"])        # identical report bytes, run to run
        self.assertEqual([i["path"].rsplit("/", 1)[-1] for i in first["inputs"]], ["SYN.csv"])
        self.assertIn("scan.json", [o["path"] for o in first["outputs"]])
        with open(os.path.join(outs[0], "scan.json")) as fh:
            scan_text = fh.read()
        for volatile in ("run_id", "recorded_at", "git_head"):        # nothing moment-specific in the report
            self.assertNotIn(volatile, scan_text)


if __name__ == "__main__":
    unittest.main()
