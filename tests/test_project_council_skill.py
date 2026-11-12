"""The autonomous-gtf-project-council skill (.claude/skills/autonomous-gtf-project-council):
its references must exist and its owner-decision list must match DECISION_LOG.md, so the
skill cannot drift from the records it tells future sessions to follow."""

import os
import re
import unittest

from _load import ROOT

SKILLS = os.path.join(ROOT, ".claude", "skills")
AGENTS = os.path.join(ROOT, ".claude", "agents")
SKILL = os.path.join(SKILLS, "autonomous-gtf-project-council", "SKILL.md")
OWNER_IDS = ("D40", "D41", "D42", "D43", "D44", "D45", "D46", "P-LOC-2", "P-LOC-3", "P-RISK-1", "B9", "B12",
             "RB-VERSION-1")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


class CouncilSkill(unittest.TestCase):
    def setUp(self):
        with open(SKILL, encoding="utf-8") as fh:
            self.text = fh.read()

    def test_frontmatter(self):
        fm = re.match(r"^---\n(.*?)\n---\n", self.text, re.S).group(1)
        self.assertRegex(fm, r"(?m)^name: autonomous-gtf-project-council$")
        self.assertRegex(fm, r"(?m)^description: \S.{80,}")

    def test_every_named_skill_and_agent_exists(self):
        table = self.text.split("## 6.")[1].split("## 7.")[0]
        rows = [r for r in table.splitlines() if r.startswith("| ") and not r.startswith("| Role") and "---" not in r]
        # the seven council roles plus Frontend & Design (foundation milestone, owner prompt 5.2)
        self.assertEqual(len(rows), 8)
        names = set(re.findall(r"`([a-z][a-z0-9-]+)`", table))
        agents = {n for n in names if os.path.isfile(os.path.join(AGENTS, n + ".md"))}
        skills = {n for n in names if os.path.isfile(os.path.join(SKILLS, n, "SKILL.md"))}
        self.assertEqual(names - agents - skills, set())
        self.assertTrue({"trading-rule-auditor", "independent-reviewer", "data-validator", "test-engineer"} <= agents)
        for s in ("llm-council", "engineering-council", "trading-council", "project-orchestrator", "repository-guardian"):
            self.assertTrue(os.path.isfile(os.path.join(SKILLS, s, "SKILL.md")), s)

    def test_named_documents_and_protected_sources_exist(self):
        for path in re.findall(r"`(nse/docs/[A-Z_]+\.md)`", self.text):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, path)), path)
        for path in ("nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md",
                     "nse/sources/Demand&Supply Indicator.pine",
                     "340fe490-8783-4eea-8cbd-e834449e9a42_Trading_Rulebook.pdf"):
            self.assertIn(path, self.text)
            self.assertTrue(os.path.isfile(os.path.join(ROOT, path)), path)

    def test_owner_decisions_listed_are_recorded_as_approved(self):
        log = read("nse", "docs", "DECISION_LOG.md")
        section = log.split("## 1F.")[1].split("\n## 2.")[0]
        for d in OWNER_IDS:
            self.assertIn("**%s**" % d if not d.startswith("D4") else d, self.text, d)
            self.assertIn(d, section, d)
        for d in ("D43", "D44", "D45", "D46"):
            self.assertRegex(section, r"### %s\..*\n- \*\*Status:\*\* `USER_APPROVED`" % d, d)
        self.assertRegex(section, r"### D42 \(status update\).*\n- \*\*Status:\*\* `USER_STATED`")
        # an escalated discrepancy stays visible, never reconciled away
        self.assertIn("D40-Q1", section)
        self.assertIn("D40-Q1", read("nse", "docs", "DECISION_REGISTER.md"))

    def test_hard_boundaries_and_invariants_are_stated(self):
        for phrase in ("git commit", "broker", "eligible_after_overlay", "never become ACTIONABLE",
                       "Synthetic tests are\nnever external validation", "AUTO_APPROVED", "three targeted repair cycles"):
            self.assertIn(phrase, self.text, phrase)

    def test_engineering_decisions_are_not_owner_decisions(self):
        eng = read("nse", "docs", "ENGINEERING_DECISIONS.md")
        self.assertIn("None of these is\nan owner decision", eng)
        self.assertNotIn("USER_APPROVED", eng)
        for n in re.findall(r"### (ED-\d+)\.", eng):
            block = eng.split("### %s." % n)[1].split("\n### ")[0]
            self.assertRegex(block, r"Category [CD]", n)
            self.assertRegex(block, r"Status `(AUTO_APPROVED|PROPOSED|BLOCKED)`", n)
            self.assertRegex(block, r"(?m)^- Reversible: (yes|no)", n)


if __name__ == "__main__":
    unittest.main()
