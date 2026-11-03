#!/usr/bin/env python3
"""PostToolUse check after Edit / Write (Claude Code hook). Fast, never runs the suite.

  - an edited .py file must still compile (syntax only, no import side effects);
  - the protected sources must still match their pinned SHA-256.
Exit 2 sends the problem back to Claude; exit 0 is silent. It modifies nothing.
Targeted tests and the full validation run stay manual steps:
  python3 -m nse.validation.run_all --group <group>      python3 -m nse.validation.run_all
"""

import json
import os
import sys


def main():
    sys.dont_write_bytecode = True             # the check must not leave __pycache__ behind
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    project = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    path = (data.get("tool_input") or {}).get("file_path") or ""
    problems = []
    if path.endswith(".py") and os.path.isfile(path):
        try:
            with open(path, "rb") as fh:
                compile(fh.read(), path, "exec")        # syntax only; writes no bytecode
        except (SyntaxError, ValueError) as e:
            problems.append("does not compile: %s (line %s)" % (getattr(e, "msg", e), getattr(e, "lineno", "?")))
    sys.path.insert(0, project)
    try:
        from nse.validation import protected
        bad = protected.check(project)
    except Exception as e:                     # the check itself must not hide a problem
        bad = [("nse/validation/protected.py", "", "unavailable: %s" % e)]
    for rel, want, got in bad:
        problems.append("protected file %s changed or missing (expected %s, got %s)" % (rel, want[:12], got))
    if problems:
        sys.stderr.write("post_edit check: %s: %s\n" % (os.path.relpath(path, project) if path else "-", "; ".join(problems)))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
