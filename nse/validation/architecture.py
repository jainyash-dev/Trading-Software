"""Architecture fitness checks for nse/ (docs/ARCHITECTURE.md is the prose version).

  python3 -m nse.validation.architecture           # check; exit 1 on any violation
  python3 -m nse.validation.architecture --map     # module map: layer, imports, imported-by (JSON)

Standard library only (ast). It reads source files; it imports nothing it checks.
Rules, each enforced by tests/test_architecture.py:

  A1 every Python module under nse/ is assigned to exactly one layer below;
  A2 a module imports only its own or a lower layer, module-level or inside a function,
     except the pairs in EXCEPTIONS (each with its reason);
  A3 module-level imports have no cycles;
  A4 nothing imports the CLI entry point nse.research.cli;
  A5 nse/ uses the standard library and its own modules only (no third-party import);
  A6 the path-loaded engines (folders with hyphens) are loaded only by the modules in
     PATH_LOADERS, so each engine has one shared copy (nse/research/deps.py);
  A7 the core business rules are defined once (SINGLE_DEFINITIONS); the actionable status
     is a string constant (literal or constant concatenation) only in models.py and the
     frozen store migration;
  A8 no eval / exec / pickle / marshal / shelve / os.system / os.popen (called, imported by
     name or fetched with getattr) and no shell= other than a literal False under nse/.

  A9 nse.research.qualification (G0-G8) is imported by nse.research.scanner only: one
     qualification pathway; the backtest, replay and reports reach it through the scanner;
  A10 the raw engine audit list (`.assessments` on an engine result) is read only by the
     modules in ASSESSMENT_READERS, each of which joins it with the overlay state for a
     report or context view; candidates come from the overlay methods (test_repo and the
     adversarial q4 test forbid the engine's raw eligible list and run_engine calls in
     nse/research).

Known limit: A7 matches definitions by name, so a renamed copy of a rule is not caught;
review and the single-pathway rules (A9, A10) are the guard against that.

Imports are read statically: absolute, relative and importlib.import_module("literal").
An import whose module name is computed at run time (cli.COMMAND_MODULES) is not an edge.

The layers are the logical architecture (docs/ARCHITECTURE.md section 3). The map is a
navigation aid for people and agents; the source code stays the authority.
"""

import argparse
import ast
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NSE = os.path.join(ROOT, "nse")

# lowest first; a module may import its own layer or any layer before it
LAYER_ORDER = ("contracts", "engines", "data", "methodology", "research", "portfolio", "application", "tooling")

LAYERS = {
    "contracts": ("nse.research", "nse.research.models", "nse.research.readiness",
                  "nse.validation.protected"),
    # the original engines, loaded by file path (their folders have hyphens) through deps.py
    "engines": ("nse.research.deps", "nse.zone-engine.zone_engine", "nse.mtf-freshness.mtf_freshness",
                "nse.eod.nse_replay", "nse.eod.nse_reference", "nse.eod.nse_bhavcopy",
                "nse.calendar.nse_calendar"),
    "data": ("nse.research.marketdata", "nse.research.inputs", "nse.research.universe", "nse.research.membership",
             "nse.research.instruments", "nse.research.corporate_actions", "nse.research.manifest_tool",
             "nse.research.acquisition", "nse.research.dataset_eligibility",
             "nse.research.index_incl_excl"),
    "methodology": ("nse.research.structure", "nse.research.trend", "nse.research.topdown",
                    "nse.research.confluence", "nse.research.levels", "nse.research.qualification"),
    "research": ("nse.research.scanner", "nse.research.reports", "nse.research.decision_replay",
                 "nse.research.scenarios", "nse.research.refcheck", "nse.research.inventory",
                 "nse.research.eod_coverage", "nse.research.p0_certification"),
    "portfolio": ("nse.research.backtest", "nse.research.execution_policy", "nse.research.risk",
                  "nse.research.store", "nse.research.charges", "nse.research.journal_taxonomy",
                  "nse.research.run_manifest"),
    "application": ("nse.research.explain", "nse.research.narrative", "nse.research.alerts",
                    "nse.research.dashboard", "nse.research.health",
                    "nse.research.pipeline", "nse.research.cli"),
    "tooling": ("nse.validation", "nse.validation.run_all", "nse.validation.architecture",
                "nse.validation.docs_health", "nse.scenarios", "nse.scenarios.generate"),
}

# (importer, imported): reason. Keep this short; each entry is reviewed technical debt.
EXCEPTIONS = {
    ("nse.research.decision_replay", "nse.research.dashboard"):
        "X1: the replay-decision command handler writes decision.html with dashboard.render_decision; "
        "the import is inside cmd_replay_decision, so the bundle logic stays presentation-free (TD-2)",
}

PATH_LOADERS = ("nse/research/deps.py", "nse/eod/nse_replay.py", "nse/eod/nse_reference.py",
                "nse/mtf-freshness/mtf_freshness.py")

# function or method name -> the one file that may define it
SINGLE_DEFINITIONS = {
    "run_engine": "nse/zone-engine/zone_engine.py",
    "core_score": "nse/zone-engine/zone_engine.py",
    "eligible_after_overlay": "nse/mtf-freshness/mtf_freshness.py",
    "manual_review_after_overlay": "nse/mtf-freshness/mtf_freshness.py",
    "derive_status": "nse/research/models.py",
    "parse_as_of": "nse/research/inputs.py",
}
QUALIFICATION = "nse.research.qualification"
QUALIFICATION_CALLERS = ("nse.research.scanner",)
# modules allowed to walk an engine result's full .assessments list (audit / context views)
ASSESSMENT_READERS = ("nse/research/scanner.py", "nse/research/structure.py", "nse/research/refcheck.py",
                      "nse/research/decision_replay.py", "nse/mtf-freshness/mtf_freshness.py",
                      "nse/zone-engine/zone_engine.py")
STATUS_CONSTANTS = ("ACTIONABLE",)       # models.py names whose string value must not be re-spelled
STATUS_LITERAL_OWNERS = ("nse/research/models.py", "nse/research/store.py")   # store: frozen v1 migration SQL

FORBIDDEN_CALLS = {("os", "system"), ("os", "popen"), (None, "eval"), (None, "exec")}
FORBIDDEN_MODULES = ("pickle", "marshal", "shelve")
FORBIDDEN_FROM = {"os": ("system", "popen"), "builtins": ("eval", "exec")}
# every way to load a module from a file path, as a call or an imported name (A6)
PATH_LOAD_NAMES = ("spec_from_file_location", "run_path", "SourceFileLoader", "load_source", "SourcelessFileLoader")


def status_literals():
    """The string values of STATUS_CONSTANTS, read from models.py's source (not imported)."""
    with open(os.path.join(NSE, "research", "models.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    out = []
    for n in tree.body:
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) \
                and any(getattr(t, "id", None) in STATUS_CONSTANTS for t in n.targets):
            out.append(n.value.value)
    return tuple(out)


def _fold(node):
    """The string a constant expression builds ("a" "b", "a" + "b"), else None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _fold(node.left), _fold(node.right)
        return left + right if left is not None and right is not None else None
    if isinstance(node, ast.JoinedStr) and all(isinstance(v, ast.Constant) for v in node.values):
        return "".join(v.value for v in node.values)
    return None


def layer_of(module):
    for name, mods in LAYERS.items():
        if module in mods:
            return name
    return None


def module_name(path):
    rel = os.path.relpath(path, ROOT)[:-3].replace(os.sep, ".")
    return rel[:-len(".__init__")] if rel.endswith(".__init__") else rel


def source_files():
    out = []
    for folder, dirs, files in os.walk(NSE):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        out.extend(os.path.join(folder, f) for f in sorted(files) if f.endswith(".py"))
    return out


def _imports(tree, known, name="", is_package=False):
    """(module imported, line, module_level) for every nse import in the tree: absolute,
    relative (resolved against the module's package) and importlib.import_module("literal")."""
    found = []
    top = set(id(n) for n in tree.body)
    package = name.split(".") if is_package else name.split(".")[:-1]

    def add(target, node):
        found.append((target, node.lineno, id(node) in top))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "nse" or a.name.startswith("nse."):
                    add(a.name, node)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = package[:len(package) - node.level + 1] if node.level <= len(package) else []
                base = ".".join(parts + ([node.module] if node.module else []))
            if base == "nse" or base.startswith("nse."):
                for a in node.names:
                    sub = base + "." + a.name
                    add(sub if sub in known else base, node)
        elif isinstance(node, ast.Call) and node.args and \
                ((isinstance(node.func, ast.Attribute) and node.func.attr == "import_module") or
                 (isinstance(node.func, ast.Name) and node.func.id in ("import_module", "__import__"))):
            target = _fold(node.args[0])
            if target and (target == "nse" or target.startswith("nse.")):
                add(target, node)
    return found


def _third_party(tree):
    std = set(sys.stdlib_module_names)
    bad = []
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names = [node.module]
        for n in names:
            head = n.split(".")[0]
            if head != "nse" and head not in std and head != "__future__":
                bad.append((n, node.lineno))
    return bad


def _unsafe(tree):
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            key = (f.value.id, f.attr) if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else \
                (None, f.id) if isinstance(f, ast.Name) else None
            if key in FORBIDDEN_CALLS:
                bad.append(("%s()" % ".".join(x for x in key if x), node.lineno))
            for kw in node.keywords:                 # anything but a literal False may enable a shell
                if kw.arg == "shell" and not (isinstance(kw.value, ast.Constant) and kw.value.value is False):
                    bad.append(("shell=%s" % ast.unparse(kw.value), node.lineno))
            if isinstance(f, ast.Name) and f.id == "getattr" and len(node.args) >= 2 \
                    and isinstance(node.args[0], ast.Name) and _fold(node.args[1]) in FORBIDDEN_FROM.get(node.args[0].id, ()):
                bad.append(("getattr(%s, %r)" % (node.args[0].id, _fold(node.args[1])), node.lineno))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for n in names:
                if n.split(".")[0] in FORBIDDEN_MODULES:
                    bad.append(("import %s" % n, node.lineno))
            if isinstance(node, ast.ImportFrom) and node.module in FORBIDDEN_FROM:
                for a in node.names:
                    if a.name in FORBIDDEN_FROM[node.module]:
                        bad.append(("from %s import %s" % (node.module, a.name), node.lineno))
    return bad


def describe(sources):
    """{module name: (repo-relative path, source text)} -> the per-module facts the rules
    read. analyse() feeds it the real tree; tests feed it planted violations."""
    known = set(sources)
    modules = {}
    for name, (rel, text) in sorted(sources.items()):
        tree = ast.parse(text, rel)
        defs = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        strings = set(x for x in (_fold(n) for n in ast.walk(tree)) if x is not None)
        reads_assessments = sorted(set(n.lineno for n in ast.walk(tree)
                                       if isinstance(n, ast.Attribute) and n.attr == "assessments"))
        path_load = any((isinstance(n, ast.Attribute) and n.attr in PATH_LOAD_NAMES) or
                        (isinstance(n, ast.Name) and n.id in PATH_LOAD_NAMES) or
                        (isinstance(n, ast.alias) and n.name in PATH_LOAD_NAMES) for n in ast.walk(tree))
        modules[name] = {
            "path": rel, "layer": layer_of(name),
            "imports": _imports(tree, known, name, rel.endswith("__init__.py")),
            "third_party": _third_party(tree), "unsafe": _unsafe(tree), "defs": defs,
            "path_load": path_load, "strings": strings, "reads_assessments": reads_assessments,
        }
    return modules


def analyse():
    sources = {}
    for path in source_files():
        with open(path, encoding="utf-8") as fh:
            sources[module_name(path)] = (os.path.relpath(path, ROOT).replace(os.sep, "/"), fh.read())
    return describe(sources)


def _cycles(modules):
    graph = {m: sorted(set(d for d, _, top in info["imports"] if top and d in modules and d != m))
             for m, info in modules.items()}
    index, low, stack, on, out, counter = {}, {}, [], set(), [], [0]

    def strong(v):                                  # Tarjan's algorithm
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on.add(v)
        for w in graph[v]:
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                out.append(sorted(comp))

    for v in sorted(graph):
        if v not in index:
            strong(v)
    return out


def violations(modules=None, complete=True):
    """List of (rule, location, message). Empty means the architecture holds. complete=False
    skips the checks that need the whole tree (unused LAYERS entries, missing definitions)."""
    modules = modules if modules is not None else analyse()
    out = []
    literals = status_literals()
    rank = {name: i for i, name in enumerate(LAYER_ORDER)}
    assigned = [m for mods in LAYERS.values() for m in mods]
    for m in sorted(set(x for x in assigned if assigned.count(x) > 1)):
        out.append(("A1", m, "assigned to more than one layer"))
    for m, info in sorted(modules.items()):
        loc = info["path"]
        if info["layer"] is None:
            out.append(("A1", loc, "module %s has no layer in nse/validation/architecture.py LAYERS" % m))
            continue
        for dep, line, _ in info["imports"]:
            if dep == m or dep not in modules:
                continue
            if dep == "nse.research.cli":
                out.append(("A4", "%s:%d" % (loc, line), "imports the CLI entry point nse.research.cli"))
            dl = modules[dep]["layer"]
            if dl is not None and rank[dl] > rank[info["layer"]] and (m, dep) not in EXCEPTIONS:
                out.append(("A2", "%s:%d" % (loc, line), "%s layer imports %s (%s layer)" % (info["layer"], dep, dl)))
        for name, line in info["third_party"]:
            out.append(("A5", "%s:%d" % (loc, line), "third-party import %s" % name))
        if info["path_load"] and loc not in PATH_LOADERS:
            out.append(("A6", loc, "loads a module by file path; use nse/research/deps.py"))
        for fn, owner in SINGLE_DEFINITIONS.items():
            if fn in info["defs"] and loc != owner:
                out.append(("A7", loc, "defines %s(), which belongs to %s only" % (fn, owner)))
        if loc not in STATUS_LITERAL_OWNERS:
            for lit in literals:
                if lit in info["strings"]:
                    out.append(("A7", loc, "spells the status %s; use models.ACTIONABLE" % lit))
        for dep, line, _ in info["imports"]:
            if dep == QUALIFICATION and m not in QUALIFICATION_CALLERS:
                out.append(("A9", "%s:%d" % (loc, line), "imports qualification; only the scanner may (one pathway)"))
        if info["reads_assessments"] and loc not in ASSESSMENT_READERS:
            out.append(("A10", "%s:%d" % (loc, info["reads_assessments"][0]),
                        "reads engine .assessments; candidates come only from the overlay methods"))
        for what, line in info["unsafe"]:
            out.append(("A8", "%s:%d" % (loc, line), "unsafe construct %s" % what))
    for fn, owner in SINGLE_DEFINITIONS.items() if complete else ():
        if not any(fn in i["defs"] and i["path"] == owner for i in modules.values()):
            out.append(("A7", owner, "%s() is no longer defined here; update SINGLE_DEFINITIONS" % fn))
    for (src, dst), _ in sorted(EXCEPTIONS.items()) if complete else ():
        if not any(d == dst for d, _, _ in modules.get(src, {}).get("imports", ())):
            out.append(("A2", src, "exception %s -> %s is no longer used; remove it" % (src, dst)))
    for comp in _cycles(modules):
        out.append(("A3", " <-> ".join(comp), "module-level import cycle"))
    for m in sorted(set(assigned) - set(modules)) if complete else ():
        out.append(("A1", m, "listed in LAYERS but no such module"))
    return out


def module_map(modules=None):
    modules = modules if modules is not None else analyse()
    by = {m: sorted(set(x for x, i in modules.items() if any(d == m for d, _, _ in i["imports"]) and x != m))
          for m in modules}
    return {m: {"path": i["path"], "layer": i["layer"],
                "imports": sorted(set(d for d, _, _ in i["imports"] if d in modules and d != m)),
                "imported_by": by[m]} for m, i in sorted(modules.items())}


def main(argv=None):
    p = argparse.ArgumentParser(prog="python3 -m nse.validation.architecture", description=__doc__.splitlines()[0])
    p.add_argument("--map", action="store_true", help="print the module map as JSON")
    args = p.parse_args(argv)
    modules = analyse()
    if args.map:
        print(json.dumps({"layers": list(LAYER_ORDER), "modules": module_map(modules)}, indent=1, sort_keys=True))
        return 0
    bad = violations(modules)
    for rule, loc, msg in bad:
        print("%s %s: %s" % (rule, loc, msg))
    print("architecture: %s (%d modules, %d violations)" % ("FAIL" if bad else "PASS", len(modules), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    sys.exit(main())
