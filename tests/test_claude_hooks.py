"""The Claude Code hooks in .claude/ (guard.py, post_edit.py, settings.json) and the
frontmatter of the project skills and agents.

Each hook runs as Claude Code runs it: a subprocess reading the hook JSON on stdin.
Exit 2 blocks the tool call; 0 allows it."""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

from _load import ROOT

HOOKS = os.path.join(ROOT, ".claude", "hooks")
RULEBOOK = "nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md"
PINE = "nse/sources/Demand&Supply Indicator.pine"


def run(script, payload, **env):
    e = dict(os.environ, CLAUDE_PROJECT_DIR=ROOT)
    e.pop("NSE_ALLOW_GIT_WRITE", None)
    e.update(env)
    p = subprocess.run([sys.executable, os.path.join(HOOKS, script)], input=json.dumps(payload),
                       capture_output=True, text=True, env=e, cwd=ROOT)
    return p.returncode, p.stderr


def bash(cmd, **env):
    return run("guard.py", {"tool_name": "Bash", "tool_input": {"command": cmd}}, **env)[0]


class Guard(unittest.TestCase):
    def test_blocks_staging_committing_and_pushing_without_authorisation(self):
        for cmd in ("git commit -m x", "git add -A", "git add nse/research/models.py", "git push origin main",
                    "cd /x && git -C . commit -m y", "git tag v1"):
            self.assertEqual(bash(cmd), 2, cmd)
        self.assertEqual(bash("git commit -m x", NSE_ALLOW_GIT_WRITE="1"), 0)

    def test_blocks_destructive_git_even_when_git_writes_are_authorised(self):
        for cmd in ("git reset --hard", "git reset --hard HEAD~1", "git clean -fd", "git checkout -- nse",
                    "git checkout .", "git restore tests/test_repo.py", "git stash", "git stash drop",
                    "git branch -D nse-phase1", "git rebase main", "git commit --amend --no-edit"):
            self.assertEqual(bash(cmd, NSE_ALLOW_GIT_WRITE="1"), 2, cmd)

    def test_allows_read_only_work(self):
        for cmd in ("git status --short --branch", "git diff", "git diff --check", "git log --oneline -5",
                    "git stash list", "python3 -m nse.validation.run_all", 'shasum -a 256 "%s"' % RULEBOOK,
                    'sed -n 1,20p "%s" 2>&1' % PINE, "cd tests && python3 -m unittest", "git checkout -b feature"):
            self.assertEqual(bash(cmd), 0, cmd)

    def test_blocks_any_write_to_protected_sources(self):
        for cmd in ('sed -i "" s/a/b/ "%s"' % PINE, 'echo x > "%s"' % RULEBOOK, 'rm "%s"' % PINE,
                    'cp other.md "%s"' % RULEBOOK, 'mv "%s" /tmp/x' % PINE):
            self.assertEqual(bash(cmd), 2, cmd)
        for tool in ("Edit", "Write", "MultiEdit"):
            for path in (os.path.join(ROOT, PINE), RULEBOOK):
                code, err = run("guard.py", {"tool_name": tool, "tool_input": {"file_path": path}})
                self.assertEqual(code, 2, (tool, path))
                self.assertIn("protected", err)
        self.assertEqual(run("guard.py", {"tool_name": "Write",
                                          "tool_input": {"file_path": os.path.join(ROOT, ".git", "config")}})[0], 2)
        self.assertEqual(run("guard.py", {"tool_name": "Edit",
                                          "tool_input": {"file_path": os.path.join(ROOT, "nse", "research", "x.py")}})[0], 0)

    def test_blocks_recursive_deletes_and_broker_calls(self):
        for cmd in ("rm -rf nse/data", "rm -r tests", "rm -rf .git", "pip install kiteconnect",
                    "curl https://api.kite.trade/orders"):
            self.assertEqual(bash(cmd), 2, cmd)
        self.assertEqual(bash("rm -rf /private/tmp/scratch/out"), 0)

    def test_non_hook_input_is_ignored(self):
        p = subprocess.run([sys.executable, os.path.join(HOOKS, "guard.py")], input="not json",
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)


class PostEdit(unittest.TestCase):
    def test_compile_error_is_reported_and_clean_file_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "bad.py")
            with open(bad, "w") as fh:
                fh.write("def f(:\n")
            code, err = run("post_edit.py", {"tool_name": "Edit", "tool_input": {"file_path": bad}})
            self.assertEqual(code, 2)
            self.assertIn("does not compile", err)
            good = os.path.join(tmp, "good.py")
            with open(good, "w") as fh:
                fh.write("x = 1\n")
            self.assertEqual(run("post_edit.py", {"tool_name": "Write", "tool_input": {"file_path": good}})[0], 0)


class Settings(unittest.TestCase):
    def test_settings_reference_existing_hooks(self):
        with open(os.path.join(ROOT, ".claude", "settings.json")) as fh:
            cfg = json.load(fh)
        cmds = [h["command"] for ev in cfg["hooks"].values() for m in ev for h in m["hooks"]]
        self.assertEqual(len(cmds), 2)
        for c in cmds:
            script = c.split("/.claude/hooks/")[1].rstrip('"')
            self.assertTrue(os.path.isfile(os.path.join(HOOKS, script)), c)
        pre = cfg["hooks"]["PreToolUse"][0]["matcher"].split("|")
        for tool in ("Bash", "Edit", "Write"):
            self.assertIn(tool, pre)

    def test_skills_and_agents_have_frontmatter_and_a_runnable_check(self):
        base = os.path.join(ROOT, ".claude")
        skills = sorted(os.listdir(os.path.join(base, "skills")))
        self.assertTrue(skills)
        for s in skills:
            with open(os.path.join(base, "skills", s, "SKILL.md"), encoding="utf-8") as fh:
                text = fh.read()
            fm = re.match(r"^---\n(.*?)\n---\n", text, re.S)
            self.assertIsNotNone(fm, s)
            self.assertIn("name: %s\n" % s, fm.group(1) + "\n", s)
            self.assertRegex(fm.group(1), r"description: \S", s)
            # every skill names an executable check, so none is a placeholder
            self.assertRegex(text, r"python3 -m (nse\.validation\.run_all|unittest|nse\.research\.cli)", s)
        agents = sorted(os.listdir(os.path.join(base, "agents")))
        self.assertTrue(agents)
        for a in agents:
            with open(os.path.join(base, "agents", a), encoding="utf-8") as fh:
                text = fh.read()
            fm = re.match(r"^---\n(.*?)\n---\n", text, re.S)
            self.assertIsNotNone(fm, a)
            self.assertIn("name: %s\n" % a[:-3], fm.group(1) + "\n", a)
            self.assertRegex(fm.group(1), r"description: \S", a)


if __name__ == "__main__":
    unittest.main()
