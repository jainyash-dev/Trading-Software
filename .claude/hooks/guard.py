#!/usr/bin/env python3
"""PreToolUse guard for this repository (Claude Code hook). Standard library only.

Reads the hook JSON on stdin. Exit 2 blocks the tool call and the message on stderr goes
back to Claude; exit 0 allows it. It enforces, deterministically, rules the user set:
  - the Rulebook and the Pine Script are never modified (any tool, any shell command);
  - nothing is staged, committed or pushed without explicit authorisation. The user can
    run such a command with the `!` prefix, or start Claude Code with NSE_ALLOW_GIT_WRITE=1
    after authorising it;
  - no destructive git command: reset --hard, clean, checkout/restore that discards
    changes, stash (other than list/show), branch -D, rebase, history rewrites;
  - no broker or order endpoint (D10, D17).
It never modifies anything itself.
"""

import json
import os
import re
import sys

PROTECTED_NAMES = ("Demand&Supply Indicator.pine", "Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md",
                   "340fe490-8783-4eea-8cbd-e834449e9a42_Trading_Rulebook.pdf")
WRITE_HINTS = re.compile(r"(\s-i\b|\s-i\.|>|\btee\b|\bmv\b|\bcp\b|\brm\b|\btruncate\b|\bdd\b|\binstall\b|\bchmod\b|"
                         r"\bperl\b.*\s-p?i|open\([^)]*['\"]w)")
GIT_WRITE = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?(add|commit|push|tag)\b")
GIT_DESTRUCTIVE = [
    (re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?reset\b.*--hard"), "git reset --hard discards work"),
    (re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?clean\b"), "git clean deletes untracked files"),
    (re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?checkout\b\s+(--\s|\.(\s|$)|-f\b)"), "git checkout would discard changes"),
    (re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?restore\b"), "git restore discards changes"),
    (re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?stash\b(?!\s+(list|show)\b)"), "git stash hides user work"),
    (re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?branch\b.*\s-D\b"), "git branch -D deletes a branch"),
    (re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?(rebase|filter-branch|filter-repo|update-ref|reflog\s+expire)\b"),
     "history rewrite"),
    (re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?commit\b.*--amend"), "git commit --amend rewrites history"),
]
BROKER = re.compile(r"kiteconnect|api\.kite\.trade|place_order|modify_order|cancel_order", re.I)


def block(msg):
    sys.stderr.write("BLOCKED by .claude/hooks/guard.py: %s\n" % msg)
    return 2


def check_bash(cmd):
    # Conservative: a command that names a protected file and contains any write-like
    # token is refused, even when the write targets another file (e.g. a heredoc that
    # merely mentions the name). Use the Write/Edit tools for such files instead.
    quiet = re.sub(r"\d?>&\d|\d?>\s*/dev/null", " ", cmd)      # stream redirections write nothing
    if any(n in cmd for n in PROTECTED_NAMES) and WRITE_HINTS.search(quiet):
        return block("the command may modify a protected source (Rulebook / Pine Script). They are never modified.")
    if re.search(r"\brm\b[^|;&]*\s-[a-zA-Z]*r", cmd) and re.search(r"(^|\s)(\.|\./|nse|nse/|nse/sources|nse/data|tests|\.git)(/|\s|$)", cmd):
        return block("recursive delete of repository content. Destructive cleanup needs explicit user authorisation.")
    for rx, why in GIT_DESTRUCTIVE:
        if rx.search(cmd):
            return block(why + ". Ask the user; never discard or hide existing work.")
    m = GIT_WRITE.search(cmd)
    if m and os.environ.get("NSE_ALLOW_GIT_WRITE") != "1":
        return block("`git %s` needs explicit user authorisation. Ask the user; they can run it with the `!` "
                     "prefix, or restart Claude Code with NSE_ALLOW_GIT_WRITE=1 after authorising it." % m.group(1))
    if BROKER.search(cmd):
        return block("broker or order endpoint (D10, D17): not approved.")
    return 0


def check_path(path, project):
    if not path:
        return 0
    full = os.path.realpath(path if os.path.isabs(path) else os.path.join(project, path))
    for name in PROTECTED_NAMES:
        if full == os.path.realpath(os.path.join(project, "nse", "sources", name)) or os.path.basename(full) == name:
            return block("%s is a protected source and is never modified." % name)
    if (os.sep + ".git" + os.sep) in full:
        return block("writing inside .git is not allowed.")
    return 0


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0                                   # not a hook payload: nothing to judge
    tool = data.get("tool_name", "")
    inp = data.get("tool_input") or {}
    project = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    if tool == "Bash":
        return check_bash(inp.get("command", ""))
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        return check_path(inp.get("file_path") or inp.get("notebook_path"), project)
    return 0


if __name__ == "__main__":
    sys.exit(main())
