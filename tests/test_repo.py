import json
import os
import re
import unittest

from _load import ROOT

# v2, the day-trading pack: the eleven folders the reel's repo card shows
SKILLS = ["trader-scanner", "trader-news", "trader-entry", "trader-exit", "trader-timemachine",
          "trader-risk", "trader-budget", "trader-broker", "trader-alerts", "trader-analyst",
          "trader-pelosi"]
ABOUT = ("11 Claude skills for day trading: scan thousands of charts, track breaking news, time every "
         "entry and exit, and replay every outcome before you risk a dollar.")
# skills on the way to an order carry the safety block
ORDER_PATH = ["trader-scanner", "trader-entry", "trader-exit", "trader-timemachine", "trader-budget",
              "trader-pelosi", "trader-risk", "trader-broker", "trader-alerts"]
V1_ONLY = ["trader-copycat", "trader-screener", "trader-tax", "trader-rebalance"]
RULEBOOK_PDF = "340fe490-8783-4eea-8cbd-e834449e9a42_Trading_Rulebook.pdf"
RULEBOOK_PDF_SHA256 = "e41cd0e7893513a492a39095c0f771ec67b320f1b51bc356da7c6a2c2946c2fc"


with open(os.path.join(ROOT, ".claude", "vendored-skills.json"), encoding="utf-8") as _fh:
    VENDORED = tuple(os.path.join(".claude", "skills", s) + os.sep for s in json.load(_fh)["skills"])
# the owner's original 65 KB master prompt, moved verbatim out of CLAUDE.md (ED-16)
OWNER_PROMPT = os.path.join("docs", "owner", "MASTER_IMPLEMENTATION_PROMPT.md")
OWNER_PROMPT_SHA256 = "c6c8cd9176e83ed40452149a3e784fd6c45c66de98ff4c8144f0f58b5f86ba8f"
# git-ignored local tool state at the repository root only (.gitignore anchors these to
# the root); never committed. A nested folder with one of these names is still checked.
LOCAL_ONLY = (".venv", ".ruff_cache", ".pytest_cache", ".env")


def frontmatter(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return (m.group(1) if m else ""), text


def every_text_file():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "node_modules", "dist")
                   and not (base == ROOT and d in LOCAL_ONLY)]
        for f in files:
            if f.endswith((".md", ".py", ".json", ".csv", ".txt", ".xml")) or f == "LICENSE":
                yield os.path.join(base, f)


class Repo(unittest.TestCase):
    def test_eleven_skill_folders_at_the_root(self):
        found = sorted(d for d in os.listdir(ROOT)
                       if os.path.isfile(os.path.join(ROOT, d, "SKILL.md")))
        self.assertEqual(found, sorted(SKILLS))

    def test_root_matches_the_reel(self):
        # CLAUDE.md (the user's project instructions), .claude/ (project skills, agents and
        # hooks, which Claude Code reads only from the root), and the owner's two root
        # documents (the product status register and the Trading Rulebook PDF, an
        # authoritative reference kept exactly as supplied) are the only additions
        # Foundation milestone (ED-16): docs/ (engineering and project-management documents,
        # the owner's archived master prompt), pyproject.toml (tool settings, no runtime
        # dependencies) and .env.example (documents that no credential is needed)
        # GTF_ENGINEERING_FIRST_ROADMAP.md is the permanent engineering-priority assessment
        # that records P0-parked / P5-next sequencing without changing P0 acceptance criteria.
        root = sorted(d for d in os.listdir(ROOT) if not d.startswith(".git") and d not in LOCAL_ONLY)
        self.assertEqual(root, sorted([".claude", ".claude-plugin", "CLAUDE.md", "LICENSE", "README.md", "nse",
                                       "tests", "PRODUCT_MASTER_STATUS.md", RULEBOOK_PDF, "docs", "pyproject.toml",
                                       ".env.example", "platform", "GTF_ENGINEERING_FIRST_ROADMAP.md"] + SKILLS))

    def test_owner_master_prompt_is_kept_verbatim(self):
        # the owner's original CLAUDE.md, moved out of the root instruction file unchanged
        import hashlib
        with open(os.path.join(ROOT, OWNER_PROMPT), "rb") as fh:
            self.assertEqual(hashlib.sha256(fh.read()).hexdigest(), OWNER_PROMPT_SHA256)

    def test_owner_rulebook_pdf_is_kept_verbatim(self):
        # the PDF is an authoritative owner reference (never edited); pin it like nse/sources
        import hashlib
        with open(os.path.join(ROOT, RULEBOOK_PDF), "rb") as fh:
            self.assertEqual(hashlib.sha256(fh.read()).hexdigest(), RULEBOOK_PDF_SHA256)

    def test_frontmatter_name_and_description(self):
        for s in SKILLS:
            fm, text = frontmatter(os.path.join(ROOT, s, "SKILL.md"))
            self.assertIn("name: %s\n" % s, fm + "\n", s)
            self.assertRegex(fm, r"description: ", s)
            self.assertGreater(len(fm), 200, "%s description is too thin" % s)
            self.assertGreater(len(text.splitlines()), 60, s)

    def test_order_path_skills_carry_the_safety_rule(self):
        for s in ORDER_PATH:
            _, text = frontmatter(os.path.join(ROOT, s, "SKILL.md"))
            low = " ".join(text.lower().split())
            self.assertIn("not financial advice", low, s)
            self.assertIn("yes", low, s)

    def test_plugin_manifest_points_at_the_root_skills(self):
        with open(os.path.join(ROOT, ".claude-plugin", "plugin.json")) as fh:
            plugin = json.load(fh)
        self.assertEqual(plugin["name"], "day-trader-skill")
        self.assertEqual(plugin["skills"], "./")
        self.assertEqual(plugin["description"], ABOUT)
        with open(os.path.join(ROOT, ".claude-plugin", "marketplace.json")) as fh:
            market = json.load(fh)
        self.assertEqual(market["name"], "day-trader-skill")
        self.assertEqual(market["plugins"][0]["name"], "day-trader-skill")

    def test_readme_carries_the_reel_copy(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
            readme = " ".join(fh.read().split())
        self.assertTrue(readme.startswith("# The Day Trader skill"))
        for line in (ABOUT,
                     "https://github.com/Jakeschincariol/day-trader-skill install skill",
                     "/plugin marketplace add Jakeschincariol/day-trader-skill",
                     "/plugin install day-trader-skill@day-trader-skill",
                     "## Fine print"):
            self.assertIn(line, readme)
        for s in SKILLS:
            self.assertIn("/" + s, readme, s)

    def test_no_em_dashes_and_no_personal_email(self):
        for path in every_text_file():
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            rel = os.path.relpath(path, ROOT)
            # fixtures are real data, nse/sources holds the user's reference documents, CLAUDE.md
            # and its archived master prompt are the user's own instruction text, and vendored
            # skills are third-party files pinned by hash (test_claude_hooks); all kept as written
            if not rel.startswith((os.path.join("tests", "fixtures"), os.path.join("nse", "sources")) + VENDORED) \
                    and rel not in ("CLAUDE.md", OWNER_PROMPT):
                self.assertNotIn("\u2014", text, rel)
            self.assertNotIn("jakeschincariol" + "@" + "gmail.com", text, rel)  # built, so this file passes too

    def test_nse_reference_sources_are_kept_verbatim(self):
        # the em-dash exemption above covers exactly these two files, byte for byte
        import hashlib
        folder = os.path.join(ROOT, "nse", "sources")
        pinned = {
            "Demand&Supply Indicator.pine":
                "14293fa5d3c8e5ba9309b45804a840bb5d8c43d47c193ebb6bca0480bc0a5519",
            "Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md":
                "039883be6b97ca39b00e5afe80f219a5d759dae99fa9c4179475f506a275d54b",
        }
        self.assertEqual(sorted(os.listdir(folder)), sorted(pinned))
        for name, digest in pinned.items():
            with open(os.path.join(folder, name), "rb") as fh:
                self.assertEqual(hashlib.sha256(fh.read()).hexdigest(), digest, name)

    def test_nse_code_keeps_the_phase1_safety_boundaries(self):
        # Candidates may come only from MtfSnapshot.eligible_after_overlay (audit M4), never
        # from the engine's own eligible list; and nothing under nse/ may reach a network,
        # a broker or an order endpoint (D10, D17, D31, D32).
        raw_eligible = re.compile(r"\.eligible\b(?!_after_overlay)")
        forbidden = re.compile(r"^\s*(import|from)\s+(urllib|requests|http|socket|ssl|kiteconnect|websocket)\b"
                               r"|place_order|modify_order|cancel_order", re.M)
        owners = (os.path.join("nse", "zone-engine"), os.path.join("nse", "mtf-freshness"))
        for folder, _, files in os.walk(os.path.join(ROOT, "nse")):
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(folder, name)
                rel = os.path.relpath(path, ROOT)
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                self.assertIsNone(forbidden.search(text), rel)
                if not rel.startswith(owners):
                    self.assertIsNone(raw_eligible.search(text), rel)

    def test_no_v1_only_skill_is_left_behind(self):
        for path in every_text_file():
            rel = os.path.relpath(path, ROOT)
            if rel.startswith("tests" + os.sep) or rel == "README.md":
                continue  # the README points v1 users to the v1 commit
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            for old in V1_ONLY:
                self.assertNotIn(old, text, rel)

    def test_every_tool_runs_on_python_3_8(self):
        # no 3.9+ only modules or syntax in the tools (the README promises 3.8)
        for s in SKILLS:
            folder = os.path.join(ROOT, s)
            for f in os.listdir(folder):
                if not f.endswith(".py"):
                    continue
                with open(os.path.join(folder, f), encoding="utf-8") as fh:
                    src = fh.read()
                for bad in ("import zoneinfo", "from zoneinfo", ".removeprefix(", ".removesuffix(",
                            "match ", "list[", "dict[", "tuple["):
                    if bad == "match ":
                        self.assertNotRegex(src, r"(?m)^\s+match \w+.*:$", "%s/%s" % (s, f))
                    elif bad.endswith("["):
                        self.assertNotRegex(src, r"(?<![\w.])%s" % re.escape(bad), "%s/%s" % (s, f))
                    else:
                        self.assertNotIn(bad, src, "%s/%s" % (s, f))

    def test_day_trading_limits_ship_in_the_example_config(self):
        with open(os.path.join(ROOT, "trader-budget", "config.example.json")) as fh:
            cfg = json.load(fh)
        for k in ("max_loss_per_trade_usd", "max_daily_loss_usd", "max_trades_per_day",
                  "min_reward_risk", "require_stop", "no_entries_after", "flat_by"):
            self.assertIn(k, cfg, k)
        self.assertIs(cfg["require_stop"], True)
        self.assertIs(cfg.get("allow_short", False), False)
        self.assertIs(cfg.get("allow_margin", False), False)

    def test_paper_trading_is_the_default(self):
        with open(os.path.join(ROOT, "trader-budget", "config.example.json")) as fh:
            cfg = json.load(fh)
        self.assertIs(cfg["paper"], True)
        self.assertIs(cfg.get("allow_options", False), False)


if __name__ == "__main__":
    unittest.main()
