"""The Stock Market Council skill (.claude/skills/llm-council) and its entry skills.

Structure: references exist and are linked; every specialist brief has its output
contract; the verdict vocabulary is the same everywhere; every test the validation cases
name exists. Behaviour: the council's verdict cap is computed from the REAL scanner on the
SYNTHETIC trading cases T1-T7, and the engineering cases E1/E2 are applied as mutations to
show that the named safeguards catch them (E5 pins the primary evidence of a chair-verification
case). AuditFixes guards the 2026-11-02 installation-audit fixes. Nothing here is market data."""

import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import _research as R
from _load import ROOT
from nse.research import reports, scanner

SKILLS = os.path.join(ROOT, ".claude", "skills")
COUNCIL = os.path.join(SKILLS, "llm-council")
PACK = os.path.join(COUNCIL, "scripts", "evidence_pack.py")
ENTRY = ("engineering-council", "trading-council", "nse-code-review", "trade-analysis", "position-review",
         "strategy-review", "backtest-review")
COUNCIL_FILES = [os.path.join(SKILLS, n, "SKILL.md") for n in ENTRY + ("llm-council",)] + [
    os.path.join(COUNCIL, "references", f) for f in sorted(os.listdir(os.path.join(COUNCIL, "references")))]
WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
VERDICTS = ("BUY CANDIDATE", "WAIT", "AVOID", "EXIT / REDUCE", "INSUFFICIENT DATA")
CAL = R.WeekdayCalendar()


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


def load_pack():
    import importlib.util
    spec = importlib.util.spec_from_file_location("council_evidence_pack", PACK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Structure(unittest.TestCase):
    def test_coordinator_frontmatter_and_linked_files(self):
        text = read(COUNCIL, "SKILL.md")
        fm = re.match(r"^---\n(.*?)\n---\n", text, re.S).group(1)
        self.assertIn("name: llm-council\n", fm + "\n")
        self.assertIn("argument-hint:", fm)
        linked = set(re.findall(r"references/[a-z-]+\.md|scripts/[a-z_]+\.py", text))
        on_disk = set("references/" + f for f in os.listdir(os.path.join(COUNCIL, "references")))
        on_disk |= set("scripts/" + f for f in os.listdir(os.path.join(COUNCIL, "scripts")) if f.endswith(".py"))
        self.assertEqual(linked, on_disk)             # nothing linked is missing, nothing on disk is orphaned

    def test_every_entry_skill_routes_to_the_council_with_evidence(self):
        for name in ENTRY:
            text = read(SKILLS, name, "SKILL.md")
            self.assertIn("/llm-council", text, name)
            self.assertRegex(text, r"python3 (-m nse\.|\.claude/skills/llm-council/scripts/)", name)

    def test_m1_approved_decisions_are_not_labelled_proposed(self):
        policy = read(COUNCIL, "references", "authority-and-approval-policy.md")
        self.assertIn("R1-R6 are", policy)
        self.assertIn("`USER_APPROVED` and authoritative", policy)
        cases = read(COUNCIL, "references", "validation-cases.md")
        self.assertIn("approved R2 mapping", cases)
        self.assertNotIn("P-TREND-1 (PROPOSED)", cases)

    def test_specialist_briefs_are_complete(self):
        eng = read(COUNCIL, "references", "engineering-specialists.md")
        for h in ("## A. Architecture Reviewer", "## B. Code Quality Reviewer", "## C. Data Integrity Reviewer",
                  "## D. Security Reviewer", "## E. Adversarial Testing Reviewer"):
            self.assertIn(h, eng)
        for field in ("SPECIALIST:", "COMMANDS RUN:", "FINDINGS:", "REQUIRED TESTS:", "VERDICT FOR THIS AREA:"):
            self.assertIn(field, eng)
        trd = read(COUNCIL, "references", "trading-specialists.md")
        for h in ("## A. Market Structure Analyst", "## B. Multi-Timeframe Analyst", "## C. Risk Manager",
                  "## D. Scenario Analyst", "## E. Devil's Advocate", "## F. Trading Strategist"):
            self.assertIn(h, trd)
        for field in ("INPUTS USED:", "FACTS", "RULE CITATIONS:", "POSITION:", "WHAT WOULD CHANGE MY POSITION:"):
            self.assertIn(field, trd)
        agents = set(f[:-3] for f in os.listdir(os.path.join(ROOT, ".claude", "agents")))
        for named in set(re.findall(r"`([a-z-]+)`", eng + trd)) & {"independent-reviewer", "data-validator",
                                                                   "trading-rule-auditor", "test-engineer"}:
            self.assertIn(named, agents)              # only existing agents are reused

    def test_mandatory_principles_are_stated(self):
        policy = read(COUNCIL, "references", "authority-and-approval-policy.md")
        for must in ("eligible_after_overlay", "Tested, invalidated, or unknown-freshness zones are not eligible",
                     "cannot override deterministic eligibility", "No broker connection", "PROPOSED",
                     "never upgrades", "RB 2343", "RB 2139"):
            self.assertIn(must, policy)

    def test_verdict_vocabulary_is_one_set(self):
        for f in ("authority-and-approval-policy.md", "report-format.md"):
            text = read(COUNCIL, "references", f)
            for v in ("BUY CANDIDATE", "WAIT", "AVOID", "INSUFFICIENT DATA"):
                self.assertIn(v, text, f)
        pack = load_pack()
        self.assertEqual(set(pack.STATUS_CAP.values()) | {"EXIT / REDUCE"}, set(VERDICTS))

    def test_named_tests_in_the_validation_cases_exist(self):
        import unittest as u
        text = read(COUNCIL, "references", "validation-cases.md")
        names = set(re.findall(r"`(test_[a-z_0-9]+\.[A-Za-z]+\.test_[a-z_0-9]+)`", text))
        self.assertGreaterEqual(len(names), 9)
        for n in sorted(names):
            suite = u.defaultTestLoader.loadTestsFromName(n)
            self.assertEqual(suite.countTestCases(), 1, n)


def agent_tools(name):
    fm = re.match(r"^---\n(.*?)\n---\n", read(ROOT, ".claude", "agents", name + ".md"), re.S).group(1)
    return {t.strip() for t in re.search(r"^tools:(.*)$", fm, re.M).group(1).split(",")}


class AuditFixes(unittest.TestCase):
    """The 2026-11-02 installation audit: each approved fix has a check that fails if it regresses."""

    def test_project_skill_does_not_shadow_the_builtin_code_review(self):
        # an actual conflict was observed: with a project skill named code-review, Claude Code
        # listed only the project skill; after the rename the built-in reappeared
        self.assertFalse(os.path.exists(os.path.join(SKILLS, "code-review")))
        fm = re.match(r"^---\n(.*?)\n---\n", read(SKILLS, "nse-code-review", "SKILL.md"), re.S).group(1)
        self.assertIn("name: nse-code-review\n", fm + "\n")
        for f in COUNCIL_FILES:
            self.assertNotRegex(read(f), r"(?<![\w-])/code-review\b", f)   # no route to the built-in by mistake

    def test_modes_are_named_one_way_and_routes_name_real_workflows(self):
        wf = read(COUNCIL, "references", "workflows.md")
        workflows = set(re.findall(r"^\| `([a-z-]+)` \|", wf, re.M))
        self.assertEqual(workflows, {"general", "code-review", "architecture", "trade", "position", "scenario",
                                     "strategy", "backtest", "combined"})
        hint = re.search(r"argument-hint:.*workflows: ([a-z| -]+)\"", read(COUNCIL, "SKILL.md")).group(1)
        self.assertEqual({w.strip() for w in hint.split("|")}, workflows)
        stale = re.compile(r"`(engineering|trading)` mode|\b(trading|engineering|Trading Product) mode\b|five-perspective", re.I)
        for f in COUNCIL_FILES:
            text = read(f)
            self.assertIsNone(stale.search(text), f)
            for route in re.findall(r"/llm-council ([a-z|-]+)", text):
                for w in route.split("|"):
                    self.assertIn(w, workflows, "%s routes to unknown workflow %r" % (f, w))

    def test_specialists_are_told_to_read_skill_files_and_those_skills_exist(self):
        for f in ("engineering-specialists.md", "trading-specialists.md"):
            text = read(COUNCIL, "references", f)
            self.assertIn("Subagents cannot invoke skills", text, f)
            self.assertIn(".claude/skills/<skill>/SKILL.md", text, f)
            rows = [line.split("|") for line in text.splitlines() if re.match(r"\| [A-F]\. ", line)]
            self.assertGreaterEqual(len(rows), 5, f)
            for r in rows:
                for skill in re.findall(r"`([a-z-]+)`", r[3]):
                    self.assertTrue(os.path.isfile(os.path.join(SKILLS, skill, "SKILL.md")), (f, skill))
        self.assertIn("read `.claude/skills/<skill>/SKILL.md`", read(COUNCIL, "references", "workflows.md"))

    def test_every_council_specialist_runs_without_write_tools(self):
        agents = set()
        for f in ("engineering-specialists.md", "trading-specialists.md"):
            for line in read(COUNCIL, "references", f).splitlines():
                if re.match(r"\| [A-F]\. ", line):
                    named = re.findall(r"`([a-z-]+)`", line.split("|")[2])
                    self.assertTrue(named, line)
                    agents.update(n for n in named if n != "test-engineer")   # writes tests only when the user asks
        general = next(l for l in read(COUNCIL, "references", "workflows.md").splitlines() if l.startswith("| `general`"))
        self.assertIn("`independent-reviewer`", general)
        agents.add("independent-reviewer")
        self.assertNotIn("trading-rule-auditor", agents)                       # it has Edit (TRACEABILITY.md)
        for a in sorted(agents):
            self.assertFalse(agent_tools(a) & WRITE_TOOLS, a)

    def test_security_brief_checks_protected_sources_through_the_pins(self):
        sec = read(COUNCIL, "references", "engineering-specialists.md").split("## D. Security Reviewer")[1]
        sec = sec.split("## E.")[0]
        self.assertIn("python3 -m nse.validation.run_all --group repository", sec)
        self.assertNotIn("shasum", sec)
        self.assertIn("NSE_ALLOW_GIT_WRITE", read(ROOT, ".claude", "hooks", "guard.py"))   # guard untouched in kind

    def test_chair_verifies_material_claims_against_primary_evidence(self):
        proto = read(COUNCIL, "references", "peer-review-protocol.md")
        for must in ("## Chair Verification of Material Facts", "primary evidence", "VERIFIED", "REFUTED",
                     "UNVERIFIABLE", "Majority agreement is never proof", "even when every reviewer agreed",
                     "marked \"verified\" or \"confirmed\" by reviewers"):
            self.assertIn(must, proto)
        fmt = read(COUNCIL, "references", "report-format.md")
        self.assertIn("## Chair Verification", fmt)
        self.assertEqual(fmt.count("Chair Verification:"), 4)                  # Engineering, Trading, Strategy, Combined
        skill = read(COUNCIL, "SKILL.md")
        self.assertIn("majority agreement is never proof", skill)
        self.assertIn("Chair\n  Verification table", skill)
        self.assertIn("Majority agreement is never proof", read(COUNCIL, "references", "authority-and-approval-policy.md"))


def scan_json(candles, as_of=None):
    cfg = scanner.ScanConfig(as_of=as_of or candles[-1].end, calendar=CAL, calendar_label="TEST_WEEKDAYS",
                             risk_per_trade=1000.0)
    return json.loads(reports.to_json(scanner.scan([R.daily_input("SYN", candles)], cfg)))


class TradingCases(unittest.TestCase):
    """T1-T6 of validation-cases.md through the real scanner (SYNTHETIC fixtures)."""

    @classmethod
    def setUpClass(cls):
        cls.pack = load_pack()
        base = R.long_mit_candles()
        cls.base = base
        cls.cases = {
            "T1": scan_json(base),
            "T2": scan_json(R.extend(base, [(176.0, 176.5, 159.5, 170.0), (170.0, 171.0, 169.0, 170.5)])),
            "T3": scan_json(R.extend(base, [(176.0, 176.0, 150.0, 151.0)])),
            "T4": scan_json(R.long_mit_candles(start=datetime.date(2023, 2, 1))),
            "T5": scan_json(R.long_mit_candles(k=1.79, tail_step=1.0, tail_wick=.002)),
        }

    def cap(self, case, pl):
        return self.pack.pack(self.cases[case], "SYN", zone_pl=pl)

    def test_t1_fresh_zone_allows_a_buy_candidate_with_the_checklist(self):
        p = self.cap("T1", R.LONG_PL)
        self.assertEqual(p["verdict_cap"], "BUY CANDIDATE")
        self.assertIn("TRADER_STATE", p["candidate"]["manual_checks"])
        self.assertIn("NOT_EXTERNALLY_VALIDATED", p["candidate"]["limitations"])

    def test_t2_t3_t6_tested_or_invalidated_zone_is_avoid_whatever_the_rr(self):
        for case in ("T2", "T3"):
            p = self.cap(case, R.LONG_PL)
            self.assertEqual(p["verdict_cap"], "AVOID", case)
            self.assertNotIn("candidate", p)
        # T6: the same zone had R:R of about 3.8 while it was fresh
        rr = self.cap("T1", R.LONG_PL)["candidate"]["rr"]
        self.assertGreater(rr[0], 3.5)
        self.assertFalse(self.pack.check("BUY CANDIDATE", self.cap("T2", R.LONG_PL)["verdict_cap"]))

    def test_t4_missing_higher_timeframe_history_is_insufficient_data(self):
        p = self.cap("T4", R.LONG_PL)
        self.assertEqual((p["candidate"]["status"], p["verdict_cap"]), ("DATA_INSUFFICIENT", "INSUFFICIENT DATA"))
        self.assertEqual(p["candidate"]["gates"]["G5"], "DATA_INSUFFICIENT")

    def test_t5_conflicting_scenarios_cap_at_wait(self):
        p = self.cap("T5", round(95.2 * 1.79, 2))
        self.assertEqual((p["candidate"]["status"], p["verdict_cap"]), ("MANUAL_REVIEW", "WAIT"))
        self.assertIn("G5", p["candidate"]["not_passed"])
        self.assertFalse(self.pack.check("BUY CANDIDATE", "WAIT"))
        self.assertTrue(self.pack.check("AVOID", "WAIT"))

    def test_absent_symbol_or_blocked_wit_is_insufficient_data(self):
        self.assertEqual(self.pack.pack(self.cases["T1"], "NOPE")["verdict_cap"], "INSUFFICIENT DATA")
        cfg = scanner.ScanConfig(as_of=self.base[-1].end, trade_type="WIT-125", calendar=CAL)
        wit = json.loads(reports.to_json(scanner.scan([R.daily_input("SYN", self.base)], cfg)))
        self.assertEqual(self.pack.pack(wit, "SYN")["verdict_cap"], "INSUFFICIENT DATA")

    def test_t7_blocked_symbol_caps_at_insufficient_data_even_with_a_zone_query(self):
        # regression (2026-11-02 audit): naming a zone used to turn BLOCKED into AVOID
        cfg = scanner.ScanConfig(as_of=self.base[-1].end, trade_type="WIT-125", calendar=CAL)
        wit = json.loads(reports.to_json(scanner.scan([R.daily_input("SYN", self.base)], cfg)))
        self.assertEqual(wit["symbols"][0]["status"], "BLOCKED")
        zone_id = self.cap("T1", R.LONG_PL)["candidate"]["zone_id"]           # the zone that is a BUY cap under MIT
        for kw in (dict(zone_pl=R.LONG_PL), dict(zone_id=zone_id), dict(zone_id="no-such-zone")):
            p = self.pack.pack(wit, "SYN", **kw)
            self.assertEqual(p["verdict_cap"], "INSUFFICIENT DATA", kw)
            self.assertNotIn("candidate", p)
            self.assertIn("BLOCKED", p["reason"])
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "wit.json")
            with open(path, "w") as fh:
                json.dump(wit, fh)
            for flag, val in (("--zone-pl", str(R.LONG_PL)), ("--zone-id", zone_id)):
                run = lambda v: subprocess.run(  # noqa: E731
                    [sys.executable, PACK, "--scan", path, "--symbol", "SYN", flag, val, "--check-verdict", v],
                    capture_output=True, text=True, cwd=ROOT).returncode
                self.assertEqual(run("INSUFFICIENT DATA"), 0, flag)          # failed (exit 1) before the fix
                self.assertEqual(run("AVOID"), 0, flag)                      # weaker is still allowed
                self.assertEqual(run("WAIT"), 1, flag)
                self.assertEqual(run("BUY CANDIDATE"), 1, flag)
        finally:
            shutil.rmtree(tmp)
        # the hierarchy elsewhere is unchanged: a tested zone stays AVOID, not INSUFFICIENT DATA
        self.assertEqual(self.cap("T2", R.LONG_PL)["verdict_cap"], "AVOID")

    def test_check_verdict_exit_codes_through_the_command_line(self):
        tmp = tempfile.mkdtemp()
        try:
            for case in ("T1", "T2"):
                with open(os.path.join(tmp, case + ".json"), "w") as fh:
                    json.dump(self.cases[case], fh)
            run = lambda case, v: subprocess.run(  # noqa: E731
                [sys.executable, PACK, "--scan", os.path.join(tmp, case + ".json"), "--symbol", "SYN",
                 "--zone-pl", str(R.LONG_PL), "--check-verdict", v], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(run("T1", "BUY CANDIDATE").returncode, 0)
            self.assertEqual(run("T2", "BUY CANDIDATE").returncode, 1)
            self.assertEqual(run("T2", "AVOID").returncode, 0)
            self.assertEqual(json.loads(run("T2", "WAIT").stdout)["verdict_allowed"], False)
        finally:
            shutil.rmtree(tmp)


class EngineeringCases(unittest.TestCase):
    """E1/E2 applied as mutations: the safeguards the cases name must catch them."""

    def test_e1_overlay_bypass_is_caught_by_the_repository_guard(self):
        src = read(ROOT, "nse", "research", "qualification.py")
        mutated = src.replace("kept_e, blocked_e = snap.eligible_after_overlay(exec_tf)",
                              "kept_e, blocked_e = snap.series[exec_tf].engine.eligible, []")
        self.assertNotEqual(mutated, src)
        raw = re.compile(r"\.eligible\b(?!_after_overlay)")       # the pattern test_repo enforces
        self.assertIsNone(raw.search(src))
        self.assertIsNotNone(raw.search(mutated))

    def test_e2_signal_day_lookahead_is_caught(self):
        from nse.research import backtest as bt
        src = read(ROOT, "nse", "research", "backtest.py")
        mutated = src.replace("if c.start > signal_end and c.complete", "if c.end >= signal_end and c.complete")
        self.assertNotEqual(mutated, src)
        ns = dict(bt.__dict__)
        exec(compile(mutated, "mutated_backtest", "exec"), ns)
        T0 = datetime.datetime(2025, 1, 3, 15, 30)
        rows = [(103, 103, 99, 101), (101, 111, 100, 110)]
        cs = [R.candle(d, *r) for d, r in zip(R.weekdays(datetime.date(2025, 1, 2), 2), rows)]
        model = bt.ExecutionModel(entry="ENTRY_MAX", stop="NORMAL_WIDE", target="STRUCTURAL",
                                  statuses=("ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING",), entry_expiry_sessions=5,
                                  cancel_if_target_first=False, gap_fill="AT_LEVEL", same_bar="STOP_FIRST",
                                  cost_pct_per_side=0.0, slippage_pct_per_side=0.0)
        good = bt.simulate((100.0, 95.0, 110.0), cs, T0, model)
        bad = ns["simulate"]((100.0, 95.0, 110.0), cs, T0, model)
        self.assertEqual(good["exit_reason"], "OPEN_ORDER_AT_END_OF_DATA")
        self.assertNotEqual(bad["exit_reason"], good["exit_reason"])     # the mutation reads the signal candle

    def test_e5_majority_claim_is_settled_by_primary_evidence(self):
        """Validation case E5: the primary evidence the chair must consult, kept true by test.
        Claim (majority-"verified" in review): to_dict stores only kept-zone ids -> REFUTED.
        Claim: no loader rebuilds a snapshot from its dict -> VERIFIED."""
        from nse.research.deps import mtf
        candles = R.long_mit_candles()
        d = mtf.replay(candles, "D", htf=scanner.HTF, as_of=candles[-1].end, calendar=CAL).to_dict()
        engine = d["series"]["D"]["engine"]
        self.assertIsInstance(engine, dict)
        self.assertIn("assessments", engine)                               # full engine output, not ids
        zone = next(iter(d["zones"].values()))
        for field in ("status", "manual_review", "usable_as_fresh_context", "events", "proximal", "distal"):
            self.assertIn(field, zone)                                      # every zone field
        self.assertTrue(all(isinstance(z, str) for z in d["overlay"]["D"]["kept"]))   # ids are added on top
        self.assertFalse([n for n in dir(mtf.MtfSnapshot) if "from" in n or "load" in n])


if __name__ == "__main__":
    unittest.main()
