"""Files that must never change, with their pinned SHA-256 (D12; user instruction: the
Rulebook and the Pine Script are not modified). tests/test_repo.py pins the same hashes
independently; the validation runner and the Claude Code hook read this module."""

import hashlib
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROTECTED = {
    "nse/sources/Demand&Supply Indicator.pine":
        "14293fa5d3c8e5ba9309b45804a840bb5d8c43d47c193ebb6bca0480bc0a5519",
    "nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md":
        "039883be6b97ca39b00e5afe80f219a5d759dae99fa9c4179475f506a275d54b",
    # the owner's Rulebook PDF (a different revision of the Markdown: RB-VERSION-1 in
    # nse/docs/DECISION_REGISTER.md); an authoritative reference, never edited
    "340fe490-8783-4eea-8cbd-e834449e9a42_Trading_Rulebook.pdf":
        "e41cd0e7893513a492a39095c0f771ec67b320f1b51bc356da7c6a2c2946c2fc",
}


def check(root=ROOT):
    """[(path, expected, actual or None)] for every protected file that does not match."""
    bad = []
    for rel, want in sorted(PROTECTED.items()):
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            bad.append((rel, want, None))
            continue
        with open(path, "rb") as fh:
            got = hashlib.sha256(fh.read()).hexdigest()
        if got != want:
            bad.append((rel, want, got))
    return bad


def is_protected(path, root=ROOT):
    full = os.path.realpath(os.path.join(root, path) if not os.path.isabs(path) else path)
    return any(full == os.path.realpath(os.path.join(root, rel)) for rel in PROTECTED)
