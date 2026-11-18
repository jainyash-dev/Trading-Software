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
# a name, a glob or a folder that can reach a protected source: a literal file name is not
# the only way to address it (audit 2026-11-06: `nse/sources/*.pine`, `Demand*` slipped through)
PROTECTED_REFS = re.compile(r"nse/sources|\.pine\b|Trading[\s_*?]*Rulebook|Demand[&*?]", re.I)
# in-place editors only (sed/perl/ruby -i); a bare -i is also grep's ignore-case, which reads
WRITE_HINTS = re.compile(r"(\b(sed|perl|ruby)\b[^|;&]*\s-[a-zA-Z]*i|>|\btee\b|\bmv\b|\bcp\b|\brm\b|\btruncate\b|"
                         r"\bdd\b|\binstall\b|\bchmod\b|\bln\b|\bunlink\b|\btouch\b|open\(.*?,\s*['\"][wax+]|\.write(_text|_bytes)?\(|"
                         r"\bgit\b[^|;&]*\b(checkout|restore|apply|mv|rm)\b)")
# git's global options (-C dir, -c key=value, --git-dir=..., --work-tree=...) before the subcommand
_G = r"\bgit(?:\s+(?:-[Cc]\s+\S+|--[a-z-]+(?:=\S+)?))*\s+"
GIT_WRITE = re.compile(_G + r"(add|commit|push|tag)\b")
GIT_DESTRUCTIVE = [
    (re.compile(_G + r"reset\b.*--(hard|merge|keep)\b"), "git reset --hard/--merge/--keep discards work"),
    (re.compile(_G + r"clean\b"), "git clean deletes untracked files"),
    (re.compile(_G + r"checkout\b(?:.*\s--(\s|$)|\s+\.(\s|$)|.*\s-f\b)"), "git checkout would discard changes"),
    # `git checkout <ref> <path>` overwrites the path without `--` (a lone branch name only switches)
    (re.compile(_G + r"checkout\s+(?!-)\S+\s+[^-|;&\s]"), "git checkout <ref> <path> overwrites files"),
    (re.compile(_G + r"switch\b.*(\s-f\b|--force\b|--discard-changes\b)"), "git switch --force discards changes"),
    (re.compile(_G + r"restore\b"), "git restore discards changes"),
    (re.compile(_G + r"stash\b(?!\s+(list|show)\b)"), "git stash hides user work"),
    (re.compile(_G + r"branch\b.*\s-D\b"), "git branch -D deletes a branch"),
    (re.compile(_G + r"(rebase|filter-branch|filter-repo|update-ref|reflog\s+expire)\b"), "history rewrite"),
    (re.compile(_G + r"commit\b.*--amend"), "git commit --amend rewrites history"),
]
BROKER = re.compile(r"kiteconnect|api\.kite\.trade|place_order|modify_order|cancel_order", re.I)


def block(msg):
    sys.stderr.write("BLOCKED by .claude/hooks/guard.py: %s\n" % msg)
    return 2


def check_bash(cmd):
    # Conservative: a command that names a protected file and contains any write-like
    # token is refused, even when the write targets another file (e.g. a heredoc that
    # merely mentions the name). Use the Write/Edit tools for such files instead.
    # stream redirections, and output written only to a temp folder outside the repository,
    # cannot change a protected source (keeps `ls nse/sources > /tmp/x` and `| tee /tmp/h` readable)
    quiet = re.sub(r"\d?>&\d|\d?>>?\s*/dev/null|\d?>>?\s*/(private/)?tmp/\S+|\|\s*tee\s+(-a\s+)?/(private/)?tmp/\S+",
                   " ", cmd)
    if (any(n in cmd for n in PROTECTED_NAMES) or PROTECTED_REFS.search(cmd)) and WRITE_HINTS.search(quiet):
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
