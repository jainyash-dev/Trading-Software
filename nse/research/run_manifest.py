"""Research-run manifest: what a run used, so it can be reproduced and audited.

A manifest is a sidecar (run_manifest.json) next to a run's outputs. The outputs
themselves stay deterministic (no clock, no git state inside scan.json); everything that
varies by machine or moment lives here. Fields:

  run_id           "run-" + 16 hex of SHA-256 over kind, as_of, parameters, input
                   fingerprints, methodology and code identity (git HEAD plus the SHA-256
                   of the uncommitted diff and of untracked files, both limited to the
                   Python code under nse/). The same inputs, settings and code give the
                   same run_id; the wall-clock time and documentation edits are not part
                   of it.
  recorded_at      UTC wall-clock time the manifest was written (informational only)
  as_of            the historical point in time the run evaluated
  inputs           every local input file with its SHA-256 and size (the dataset identity);
                   missing_inputs lists named paths that did not exist
  dataset_sha256   SHA-256 over the sorted input fingerprints
  methodology      pipeline / engine versions and the protected sources' pinned hashes
  code             git HEAD, whether the nse/ code differs from it, the SHA-256 of the
                   tracked diff and of the untracked files
  parameters       the run's configuration as given
  assumptions      execution or other assumptions the caller declares (backtests)
  limitations      the run's own limitations, copied from its result
  outputs          each output file with its SHA-256 (the manifest itself excluded)

Standard library only. Reads files and `git rev-parse` / `git status`; never the network.
ENGINEERING_DECISIONS ED-18.
"""

import datetime
import glob
import hashlib
import json
import os
import subprocess

from nse.research import models as m
from nse.research.deps import ROOT, mtf, ze
from nse.validation import protected

MANIFEST_VERSION = "1.0.0"
MANIFEST_NAME = "run_manifest.json"
PATH_PARAMS = ("model", "universe", "calendar", "csv_dir", "bhavcopy_dir", "manifest", "instruments",
               "corporate_actions")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel(path):
    full = os.path.abspath(path)
    return os.path.relpath(full, ROOT).replace(os.sep, "/") if full.startswith(ROOT + os.sep) else full


def fingerprints(paths):
    """[{path, sha256, bytes}] for each existing file, sorted by path; folders are walked
    (hidden files such as .DS_Store skipped). Use missing() for paths that do not exist."""
    files = set()
    for p in paths:
        if not p:
            continue
        if os.path.isdir(p):
            for folder, dirs, names in os.walk(p):
                dirs[:] = sorted(d for d in dirs if d != "__pycache__" and not d.startswith("."))
                files.update(os.path.join(folder, n) for n in names if not n.startswith("."))
        elif os.path.isfile(p):
            files.add(p)
    return [{"path": _rel(f), "sha256": _sha256(f), "bytes": os.path.getsize(f)} for f in sorted(files, key=_rel)]


def missing(paths):
    return sorted(set(_rel(p) for p in paths if p and not os.path.exists(p)))


def relative_paths(params, keys):
    """params with the path-valued keys made repository-relative, so the same files named
    by a relative or an absolute path give the same run_id."""
    return {k: (_rel(v) if k in keys and isinstance(v, str) and v and os.path.exists(v) else v)
            for k, v in params.items()}


CODE_PATHSPEC = ":(glob)nse/**/*.py"     # the code a research run executes (docs and tests excluded)


def code_revision(root=ROOT):
    """{git_head, dirty, diff_sha256, untracked_files, untracked_sha256} for the Python code
    under nse/; None values when git is unavailable (never guessed)."""
    def git(*args):
        try:
            p = subprocess.run(["git"] + list(args), cwd=root, capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            return None
        return p.stdout if p.returncode == 0 else None
    none = {"git_head": None, "dirty": None, "diff_sha256": None, "untracked_files": None, "untracked_sha256": None}
    head = git("rev-parse", "HEAD")
    diff = git("diff", "HEAD", "--binary", "--", CODE_PATHSPEC) if head is not None else None
    listed = git("ls-files", "--others", "--exclude-standard", "-z", "--", CODE_PATHSPEC) if head is not None else None
    if head is None or diff is None or listed is None:
        return none
    untracked = sorted(x for x in listed.decode().split("\0") if x)
    h = hashlib.sha256()
    for rel in untracked:
        h.update(rel.encode() + b"\0" + _sha256(os.path.join(root, rel)).encode() + b"\0")
    return {"git_head": head.decode().strip(), "dirty": bool(diff) or bool(untracked),
            "diff_sha256": hashlib.sha256(diff).hexdigest() if diff else None,
            "untracked_files": len(untracked), "untracked_sha256": h.hexdigest() if untracked else None}


def methodology():
    return {"pipeline_version": m.PIPELINE_VERSION,
            "engine_versions": {"zone_engine": ze.ENGINE_VERSION, "mtf_freshness": mtf.ENGINE_VERSION},
            "protected_sources": dict(sorted(protected.PROTECTED.items()))}


def dataset_sha256(fingerprints_):
    """SHA-256 of the sorted path/hash pairs. `build` uses this as dataset_sha256."""
    return hashlib.sha256(json.dumps([[i["path"], i["sha256"]] for i in fingerprints_]).encode()).hexdigest()


def build(kind, as_of, parameters, input_paths, limitations=(), assumptions=None, code=None, recorded_at=None):
    """The manifest without outputs (see write). kind: e.g. "scan", "backtest"."""
    inputs = fingerprints(input_paths)
    absent = missing(input_paths)
    dataset = dataset_sha256(inputs)
    body = {"manifest_version": MANIFEST_VERSION, "kind": kind,
            "as_of": as_of.isoformat() if hasattr(as_of, "isoformat") else as_of,
            "parameters": parameters, "assumptions": assumptions or {}, "inputs": inputs, "missing_inputs": absent,
            "dataset_sha256": dataset, "methodology": methodology(),
            "code": code if code is not None else code_revision()}
    canonical = json.dumps(body, sort_keys=True, default=str, separators=(",", ":"))
    body["run_id"] = "run-" + hashlib.sha256(canonical.encode()).hexdigest()[:16]
    body["recorded_at"] = recorded_at or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    body["limitations"] = sorted(set(limitations))
    if body["code"].get("dirty"):
        body["limitations"].append("CODE_REVISION_HAS_UNCOMMITTED_CHANGES: git_head alone does not reproduce this run; "
                                   "code.diff_sha256 and code.untracked_sha256 identify the uncommitted nse/ code")
    if body["code"].get("git_head") is None:
        body["limitations"].append("CODE_REVISION_UNKNOWN: git unavailable; the code identity is not recorded")
    if absent:
        body["limitations"].append("INPUT_PATHS_MISSING: %s" % ", ".join(absent))
    return body


def write(manifest, folder, outputs=None, name=MANIFEST_NAME):
    """Hash the outputs (default: every other file in folder) and write the manifest as
    folder/name (run_manifest.json; a single-file output uses "<file>.manifest.json")."""
    names = outputs if outputs is not None else sorted(
        n for n in os.listdir(folder) if n != name and os.path.isfile(os.path.join(folder, n)))
    manifest = dict(manifest, outputs=[{"path": n, "sha256": _sha256(os.path.join(folder, n))} for n in names])
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(manifest, sort_keys=True, indent=1, default=str) + "\n")
    return path


def scan_input_paths(args, symbols=None, loads_data=True):
    """Local files a scan-like command reads, from its options and the symbols it loaded
    (the same selection as inputs.load). loads_data=False (a BLOCKED WIT scan loads no
    candles) leaves out the market-data files."""
    paths = []
    if loads_data and getattr(args, "csv_dir", None):
        wanted = set(symbols) if symbols else None     # inputs.load matches the symbol as given
        paths += sorted(p for p in glob.glob(os.path.join(args.csv_dir, "*.csv"))
                        if wanted is None or os.path.splitext(os.path.basename(p))[0].upper() in wanted)
    elif loads_data and getattr(args, "bhavcopy_dir", None):
        from nse.research.deps import bhavcopy
        paths += bhavcopy.archive_paths(args.bhavcopy_dir)
        if getattr(args, "manifest", None):
            paths.append(args.manifest)
    for opt in ("universe", "calendar", "corporate_actions", "instruments"):
        if getattr(args, opt, None):
            paths.append(getattr(args, opt))
    actions = getattr(args, "corporate_actions", None)
    if actions:
        coverage = os.path.join(os.path.dirname(os.path.abspath(actions)), "coverage.csv")
        if os.path.isfile(coverage):
            paths.append(coverage)
    return paths
