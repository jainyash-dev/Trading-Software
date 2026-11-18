"""Architecture fitness (nse/validation/architecture.py) and documentation health
(nse/validation/docs_health.py). The real tree must pass, and every rule must catch a
planted violation, so a green run proves the rules were exercised (docs/ARCHITECTURE.md)."""

import os
import sys
import tempfile
import unittest

from _load import ROOT

sys.path.insert(0, ROOT)
from nse.validation import architecture as arch, docs_health as dh  # noqa: E402


def planted(**sources):
    """Module facts for planted sources: name -> source text (paths derived from names)."""
    return arch.describe({name: (name.replace(".", "/") + ".py", text) for name, text in sources.items()})


def rules(found):
    return sorted(set(r for r, _, _ in found))


class RealTree(unittest.TestCase):
    def test_the_repository_satisfies_every_architecture_rule(self):
        self.assertEqual(arch.violations(), [])

    def test_the_documentation_has_no_stale_link_or_command(self):
        self.assertEqual(dh.findings(), [])

    def test_every_layer_module_exists_and_the_map_is_complete(self):
        mm = arch.module_map()
        self.assertTrue(all(info["layer"] for info in mm.values()))
        # the one qualification pathway: the scanner reaches the overlay through qualification
        self.assertIn("nse.research.qualification", mm["nse.research.scanner"]["imports"])
        self.assertIn("nse.research.scanner", mm["nse.research.backtest"]["imports"])

    def test_the_cli_is_imported_by_nothing_inside_nse(self):
        self.assertEqual(arch.module_map()["nse.research.cli"]["imported_by"], [])

    def test_domain_layers_never_import_the_application_layer(self):
        mm = arch.module_map()
        app = set(arch.LAYERS["application"])
        for name, info in mm.items():
            if info["layer"] in ("contracts", "engines", "data", "methodology"):
                self.assertFalse(app & set(info["imports"]), name)


class PlantedViolations(unittest.TestCase):
    def test_A1_an_unassigned_module_fails(self):
        found = arch.violations(planted(**{"nse.research.newthing": "x = 1\n"}), complete=False)
        self.assertEqual(rules(found), ["A1"])

    def test_A2_methodology_importing_presentation_fails(self):
        found = arch.violations(planted(**{
            "nse.research.qualification": "from nse.research import dashboard\n",
            "nse.research.dashboard": "x = 1\n"}), complete=False)
        self.assertEqual(rules(found), ["A2"])

    def test_A2_applies_to_imports_inside_functions(self):
        found = arch.violations(planted(**{
            "nse.research.levels": "def f():\n    from nse.research import narrative\n",
            "nse.research.narrative": "x = 1\n"}), complete=False)
        self.assertEqual(rules(found), ["A2"])

    def test_A2_a_documented_exception_is_allowed(self):
        found = arch.violations(planted(**{
            "nse.research.decision_replay": "def cmd():\n    from nse.research import dashboard\n",
            "nse.research.dashboard": "x = 1\n"}), complete=False)
        self.assertEqual(found, [])

    def test_A3_a_module_level_cycle_fails(self):
        found = arch.violations(planted(**{
            "nse.research.structure": "from nse.research import trend\n",
            "nse.research.trend": "from nse.research import structure\n"}), complete=False)
        self.assertIn("A3", rules(found))

    def test_A4_importing_the_cli_fails_even_from_the_application_layer(self):
        found = arch.violations(planted(**{
            "nse.research.dashboard": "from nse.research import cli\n",
            "nse.research.cli": "x = 1\n"}), complete=False)
        self.assertEqual(rules(found), ["A4"])

    def test_A5_a_third_party_import_fails(self):
        for src in ("import pandas\n", "from requests import get\n"):
            found = arch.violations(planted(**{"nse.research.levels": src}), complete=False)
            self.assertEqual(rules(found), ["A5"], src)

    def test_A6_a_second_path_loaded_engine_copy_fails(self):
        found = arch.violations(planted(**{
            "nse.research.levels": "import importlib.util\nimportlib.util.spec_from_file_location('x', 'y')\n"}),
            complete=False)
        self.assertEqual(rules(found), ["A6"])

    def test_A7_a_second_status_derivation_or_status_literal_fails(self):
        found = arch.violations(planted(**{"nse.research.reports": "def derive_status(g):\n    return g\n"}),
                                complete=False)
        self.assertEqual(rules(found), ["A7"])
        found = arch.violations(planted(**{"nse.research.reports":
                                           "S = 'ACTIONABLE_CANDIDATE_' 'MANUAL_CHECKS_PENDING'\n"}), complete=False)
        self.assertEqual(rules(found), ["A7"])
        found = arch.violations(planted(**{"nse.research.reports":
                                           "def eligible_after_overlay(tf):\n    return []\n"}), complete=False)
        self.assertEqual(rules(found), ["A7"])

    def test_A7_a_docstring_mentioning_the_status_is_not_a_literal(self):
        found = arch.violations(planted(**{"nse.research.risk":
                                           '"""Only ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING gets sizing."""\n'}),
                                complete=False)
        self.assertEqual(found, [])

    def test_A8_unsafe_constructs_fail(self):
        for src in ("eval('1')\n", "import os\nos.system('ls')\n", "import pickle\n",
                    "import subprocess\nsubprocess.run('ls', shell=True)\n"):
            found = arch.violations(planted(**{"nse.research.levels": src}), complete=False)
            self.assertEqual(rules(found), ["A8"], src)


class EvasionRegressions20261108(unittest.TestCase):
    """Each way independent QA found to slip past the first version of the checker."""

    def test_the_status_literal_is_read_from_models(self):
        self.assertEqual(arch.status_literals(), ("ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING",))

    def test_relative_imports_are_edges(self):
        found = arch.violations(planted(**{"nse.research.levels": "from . import dashboard\n",
                                           "nse.research.dashboard": "x = 1\n"}), complete=False)
        self.assertEqual(rules(found), ["A2"])
        found = arch.violations(planted(**{"nse.research.levels": "from .cli import main\n",
                                           "nse.research.cli": "x = 1\n"}), complete=False)
        self.assertIn("A4", rules(found))

    def test_import_module_with_a_literal_is_an_edge(self):
        found = arch.violations(planted(**{
            "nse.research.levels": "import importlib\nimportlib.import_module('nse.research.cli')\n",
            "nse.research.cli": "x = 1\n"}), complete=False)
        self.assertIn("A4", rules(found))

    def test_every_path_loading_spelling_is_caught(self):
        for src in ("from importlib.util import spec_from_file_location\n",
                    "import runpy\nrunpy.run_path('x.py')\n",
                    "from importlib.machinery import SourceFileLoader\n"):
            found = arch.violations(planted(**{"nse.research.levels": src}), complete=False)
            self.assertEqual(rules(found), ["A6"], src)

    def test_unsafe_spellings_are_caught(self):
        for src in ("from os import system\n", "import os\ngetattr(os, 'system')('ls')\n",
                    "import subprocess\nflag = True\nsubprocess.run('ls', shell=flag)\n"):
            found = arch.violations(planted(**{"nse.research.levels": src}), complete=False)
            self.assertEqual(rules(found), ["A8"], src)
        ok = "import subprocess\nsubprocess.run(['git', 'status'], shell=False)\n"
        self.assertEqual(arch.violations(planted(**{"nse.research.levels": ok}), complete=False), [])

    def test_a_concatenated_status_literal_is_caught(self):
        for src in ("S = 'ACTIONABLE_CANDIDATE_' + 'MANUAL_CHECKS_PENDING'\n",
                    "S = f'ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING'\n"):
            found = arch.violations(planted(**{"nse.research.reports": src}), complete=False)
            self.assertEqual(rules(found), ["A7"], src)


class SinglePathway(unittest.TestCase):
    """A9 / A10 (contrarian review 2026-11-08): one qualification pathway, and the raw
    engine audit list is read only by the listed view modules."""

    def test_A9_only_the_scanner_imports_qualification(self):
        self.assertEqual(arch.module_map()["nse.research.qualification"]["imported_by"], ["nse.research.scanner"])
        for importer in ("nse.research.backtest", "nse.research.reports", "nse.research.dashboard"):
            found = arch.violations(planted(**{importer: "from nse.research import qualification\n",
                                               "nse.research.qualification": "x = 1\n"}), complete=False)
            self.assertIn("A9", rules(found), importer)

    def test_A10_a_new_reader_of_raw_assessments_fails(self):
        found = arch.violations(planted(**{"nse.research.reports":
                                           "def f(s):\n    return [a for a in s.engine.assessments]\n"}),
                                complete=False)
        self.assertEqual(rules(found), ["A10"])

    def test_A10_sees_the_real_readers(self):
        # canary: the rule would pass vacuously if it never matched anything
        readers = sorted(i["path"] for i in arch.analyse().values() if i["reads_assessments"])
        for p in ("nse/research/scanner.py", "nse/research/structure.py", "nse/research/refcheck.py",
                  "nse/research/decision_replay.py"):
            self.assertIn(p, readers)


class PlantedDocFindings(unittest.TestCase):
    def tree(self, text):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        os.makedirs(os.path.join(tmp.name, "nse", "research"))
        os.makedirs(os.path.join(tmp.name, "nse", "validation"))
        with open(os.path.join(tmp.name, "nse", "research", "cli.py"), "w") as fh:
            fh.write("def main(sub):\n    sub.add_parser('scan')\n")
        with open(os.path.join(tmp.name, "nse", "validation", "run_all.py"), "w") as fh:
            fh.write("GROUPS = ((\"lookahead\", []),)\n")
        with open(os.path.join(tmp.name, "README.md"), "w") as fh:
            fh.write(text)
        with open(os.path.join(tmp.name, "here.md"), "w") as fh:
            fh.write("ok\n")
        return tmp.name

    def test_good_links_and_commands_pass(self):
        root = self.tree("[a](here.md) [b](https://example.com) [c](#top)\n"
                         "python3 -m nse.research.cli scan\npython3 -m nse.validation.run_all --group lookahead\n"
                         "python3 -m pytest -q\n")
        self.assertEqual(dh.findings(root), [])

    def test_each_kind_of_stale_reference_is_found(self):
        root = self.tree("[a](missing.md)\npython3 -m nse.research.cli scna\n"
                         "python3 -m nse.validation.run_all --group lookahead --group nope\n"
                         "python3 -m nse.research.gone\n")
        self.assertEqual(sorted(r for r, _, _ in dh.findings(root)), ["H1", "H2", "H3", "H4"])

    def test_links_inside_code_fences_are_not_links(self):
        root = self.tree("```\n[a](missing.md)\n```\n")
        self.assertEqual(dh.findings(root), [])


if __name__ == "__main__":
    unittest.main()
