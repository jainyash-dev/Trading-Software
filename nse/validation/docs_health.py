"""Documentation health: the commands and links the docs give still exist.

  python3 -m nse.validation.docs_health        # exit 1 on any finding

Standard library only. It reads files; it runs nothing it finds. Checks, over every
Markdown file except the immutable or third-party ones in SKIP:

  H1 a relative Markdown link [text](path) points at an existing file or folder;
  H2 `python3 -m nse.research.cli <command>` names a registered subcommand (an
     add_parser("<command>") call somewhere under nse/research/);
  H3 `run_all --group <name>` names a group in nse/validation/run_all.py GROUPS;
  H4 `python3 -m <module>` names a module that exists in this repository (or the
     standard-library / test runners listed in RUNNERS).

Historical reports (nse/docs/release/, nse/docs/archive/) are checked too: a stale
command there is still a trap for the next reader.
"""

import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SKIP = ("nse/sources/", "tests/fixtures/", "docs/owner/", ".git/")
RUNNERS = ("pytest", "unittest", "venv", "pip", "json.tool", "pyflakes", "ruff", "http.server")

LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CLI = re.compile(r"python3 -m nse\.research\.cli\s+([a-z][a-z0-9-]*)")
GROUP = re.compile(r"--group\s+([a-z_]+)")          # on lines that mention run_all
MODULE = re.compile(r"python3 (?:-I )?-m ([A-Za-z_][\w.]*)")


def _vendored(root):
    import json
    path = os.path.join(root, ".claude", "vendored-skills.json")
    if not os.path.isfile(path):
        return ()
    with open(path, encoding="utf-8") as fh:
        return tuple(".claude/skills/%s/" % s for s in json.load(fh)["skills"])


def markdown_files(root=ROOT):
    skip = SKIP + _vendored(root)
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in (
            ".git", ".venv", "__pycache__", "output", "raw", "node_modules", "dist"))
        for f in sorted(files):
            if f.endswith(".md"):
                rel = os.path.relpath(os.path.join(folder, f), root).replace(os.sep, "/")
                if not rel.startswith(skip):
                    yield rel


def subcommands(root=ROOT):
    names = set()
    folder = os.path.join(root, "nse", "research")
    if not os.path.isdir(folder):
        return names
    for f in sorted(os.listdir(folder)):
        if not f.endswith(".py"):
            continue
        with open(os.path.join(folder, f), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "add_parser" \
                    and n.args and isinstance(n.args[0], ast.Constant):
                names.add(n.args[0].value)
    return names


def groups(root=ROOT):
    path = os.path.join(root, "nse", "validation", "run_all.py")
    if not os.path.isfile(path):
        return set()
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "GROUPS" for t in n.targets):
            return set(e.elts[0].value for e in n.value.elts)
    return set()


def module_exists(name, root=ROOT):
    if name.split(".")[0] in RUNNERS or name in RUNNERS:
        return True
    base = os.path.join(root, *name.split("."))
    return os.path.isfile(base + ".py") or os.path.isfile(os.path.join(base, "__init__.py")) \
        or os.path.isfile(os.path.join(base, "__main__.py"))


def findings(root=ROOT):
    subs, grps, out = subcommands(root), groups(root), []
    for rel in markdown_files(root):
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        here = os.path.dirname(os.path.join(root, rel))
        fence = False
        for i, line in enumerate(lines, 1):
            if line.lstrip().startswith("```"):
                fence = not fence
            if not fence:
                for target in LINK.findall(line):
                    if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith(("#", "<")):
                        continue
                    path = target.split("#")[0]
                    if path and not os.path.exists(os.path.normpath(os.path.join(here, path))):
                        out.append(("H1", "%s:%d" % (rel, i), "broken link %s" % target))
            for cmd in CLI.findall(line):
                if cmd not in subs:
                    out.append(("H2", "%s:%d" % (rel, i), "unknown CLI command %s" % cmd))
            for g in (GROUP.findall(line) if "run_all" in line else ()):
                if g not in grps:
                    out.append(("H3", "%s:%d" % (rel, i), "unknown validation group %s" % g))
            for mod in MODULE.findall(line):
                mod = mod.rstrip(".")
                if not module_exists(mod, root):
                    out.append(("H4", "%s:%d" % (rel, i), "no module %s" % mod))
    return out


def main():
    bad = findings()
    for rule, loc, msg in bad:
        print("%s %s: %s" % (rule, loc, msg))
    print("docs health: %s (%d findings)" % ("FAIL" if bad else "PASS", len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    sys.exit(main())
