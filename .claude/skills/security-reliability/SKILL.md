---
name: security-reliability
description: Check the repository's security and reliability boundaries: no network, broker or order code under nse/, no secrets, protected sources unchanged, guard hooks active, deterministic outputs, idempotent ingestion and store imports, no destructive operations. Use before a release-readiness statement, after adding a dependency, command, hook, file writer or data path, and when asked whether the system is safe to run.
---

# Security and reliability review

## Run

```
python3 -m nse.research.cli health                                   # protected hashes, imports, local data
python3 -m nse.validation.run_all --group repository --group hooks    # boundaries, guard hook tests
python3 -m nse.validation.run_all                                     # everything
git status --short && git diff --cached --name-only                   # nothing staged
```

## Checklist

| Boundary | Enforced by |
|---|---|
| No network, broker or order code in nse/ (D10, D17, D31, D32) | `tests/test_repo.py` safety boundaries; `.claude/hooks/guard.py` |
| Candidates only through the MTF overlay (audit M4) | `tests/test_repo.py` (`.eligible` regex); adversarial q4 |
| Protected sources (Rulebook Markdown and PDF, Pine Script) unchanged | `nse/validation/protected.py`; guard and post-edit hooks; `health` |
| No commit, push, reset, clean, stash without authorisation | guard hook; `tests/test_claude_hooks.py` |
| No secrets in the repository; no credentials requested (D17) | review: grep for key, token, password, secret in new files |
| Standard library only; no new dependency without a reason | review imports; `health` imports every module |
| Deterministic outputs (no clock in reports) | determinism tests in reports, dashboard, scenarios, store |
| Idempotent ingestion and import; no overwrite of raw files | acquisition and store tests |
| No destructive migration or cleanup | store migration scan test; guard hook |

## Hard restrictions

- Report findings with file and line; do not "fix" by weakening a test or a hook.
- External notification delivery (email, webhooks) is not implemented and needs owner
  configuration and approval before it is added.

## Output

A findings list (severity, file:line, boundary, evidence) and the exact commands run with
their results. Write it to `nse/docs/release/SECURITY_REPORT.md` when asked for a report.
