# Operations runbook

> Development setup, everyday commands, troubleshooting, backup and recovery. Every
> command here is checked by `python3 -m nse.validation.docs_health` (it fails if a
> command or `run_all` group no longer exists). Run everything from the repository root.

## 1. Requirements

| Item | Requirement | Evidence |
|---|---|---|
| Python | 3.10 or newer (`pyproject.toml` `requires-python`) | full `run_all` passes on 3.10.20 and 3.12.7 (`docs/VALIDATION_SCORECARD.md`) |
| Runtime packages | none: `nse/` uses the standard library only (architecture rule A5) | `python3 -m nse.validation.architecture` |
| Dev tools (optional) | ruff 0.17.4 (`[dependency-groups] dev`); pytest for an alternative runner | without them `run_all` reports `static_lint UNAVAILABLE`, never PASS |
| Credentials | none, ever (`.env.example`) | `tests/test_repo.py` forbids network and broker code under `nse/` |
| Legacy `trader-*` pack | Python 3.8+ (its own promise, tested by `test_repo`) | - |

## 2. Bootstrap (owner's Mac or a fresh machine)

```
git clone <repository> day-trader-skill && cd day-trader-skill
python3 --version                                   # 3.10 or newer
python3 -m venv .venv                                # optional, git-ignored; holds dev tools only
.venv/bin/python -m pip install "ruff==0.17.4"       # optional; or, with uv: uv sync --group dev
python3 -m nse.validation.run_all                    # must end with "verdict: PASS..."
```

`run_all` finds ruff in `.venv/bin/ruff` or on `PATH`, otherwise pyflakes in the running
interpreter. Agents use exactly these commands (`CLAUDE.md`).

Local evidence is git-ignored (`.gitignore`, D31): `nse/data/eod/raw/` (bhavcopy
archives) and `nse/data/calendar/circulars/` (official PDFs). Without them the data
checks report `UNAVAILABLE` or tests skip with `PREREQUISITE MISSING`; nothing pretends
to pass. Do not download data as part of setup: acquisition is an owner action
(`nse-data-engineering` skill).

EOD formats (ED-20): legacy `cm*bhav.csv.zip` for trade dates up to 2024-07-05, UDiFF
`BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip` from 2024-07-08. `acquire-plan` prints the
file name and official URL for each session. A file in the other format is quarantined.
Format evidence is in `nse/data/eod/evidence/`, and it is never research data. Scans,
scan-history, backtest and replay-decision accept `--instruments <records.csv>`; without
it, results carry `IDENTITY_UNVERIFIED` (ED-21).

## 3. Everyday commands

| Purpose | Command |
|---|---|
| Full validation (tests, repository checks, local data, reference, lint, readiness) | `python3 -m nse.validation.run_all` |
| Acceptance (any missing evidence fails) | `python3 -m nse.validation.run_all --acceptance` |
| List groups / targeted run | `python3 -m nse.validation.run_all --list`, then `python3 -m nse.validation.run_all --group strategy_gates --group lookahead` |
| Fast loop while editing (skips data and lint) | `python3 -m nse.validation.run_all --group <group> --no-data` |
| Architecture rules / module map | `python3 -m nse.validation.architecture`, `python3 -m nse.validation.architecture --map` |
| Documentation health | `python3 -m nse.validation.docs_health` |
| Lint only | `.venv/bin/ruff check --no-cache nse tests .claude/hooks` |
| Same tests under pytest | `python3 -m pytest -q` |
| Scan | `python3 -m nse.research.cli scan --as-of 2022-03-31 --symbols INFY --bhavcopy-dir nse/data/eod/raw --manifest nse/data/eod/manifest.csv --calendar nse/data/calendar --out nse/output/scan-2022-03-31` |
| Readiness table | `python3 -m nse.research.cli readiness` |
| Environment health | `python3 -m nse.research.cli health` |
| What data is missing for a window | `python3 -m nse.research.cli acquire-plan --start 2021-01-01 --end 2025-12-31 --calendar nse/data/calendar` |
| Coverage report (downloaded / parsed / validated / accepted, dataset id, eod_ready (EOD files only; data_ready never claimed)) | `python3 -m nse.research.cli eod-coverage --start 2021-01-01 --end 2025-12-31 --symbols INFY --out nse/output/data_readiness/eod_coverage.json` |

Outputs go to `nse/output/` (git-ignored). Every scan writes `run_manifest.json` next to
its reports: run id, input file hashes, dataset hash, methodology versions, protected
source hashes, git revision and dirty flag, output hashes (ED-18).

Exit codes: `run_all` 0 = no required or optional check failed (skips and UNAVAILABLE are
named in the verdict), 1 = a check failed (or, with `--acceptance`, evidence is missing).
CLI commands: 0 = ran, 2 = usage or input error.

## 4. Validation layers

| When | Run |
|---|---|
| After each edit (automatic) | `.claude/hooks/post_edit.py`: the file still compiles; protected hashes unchanged |
| Before any tool call (automatic) | `.claude/hooks/guard.py`: blocks protected-file writes, git writes, destructive and broker commands |
| After a component change | `python3 -m nse.validation.run_all --group <groups touched> --no-data` |
| Before reporting completion | `python3 -m nse.validation.run_all`, then `git diff --check` |

## 5. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `repository_checks FAIL: test modules not in any validation group` | a new `tests/test_*.py` must be added to `GROUPS` in `nse/validation/run_all.py` |
| `architecture: FAIL ... A1 ... has no layer` | a new `nse/` module: add it to `LAYERS` in `nse/validation/architecture.py` and `docs/ARCHITECTURE.md` section 3 |
| `A2 ... imports ...` | an upward dependency; move the shared code down (see `nse/research/inputs.py`) rather than adding an exception |
| `static_lint UNAVAILABLE` | no ruff or pyflakes; install the dev tools (section 2) or accept the stated gap |
| `static_lint FAIL` | run the lint command in section 3 and fix the named lines |
| `protected file ... changed or missing` | stop. Do not "fix" the hash. Inspect `git diff` of `nse/sources/` and tell the owner |
| `SKIPPED_PREREQUISITE` / `UNAVAILABLE` for local data | git-ignored evidence absent on this machine; expected on a fresh clone |
| a vendored skill test fails | a vendored file was edited; restore it from upstream (`docs/SKILLS_REGISTRY.md` section 5) |
| `docs health ... H2 unknown CLI command` | a doc names a removed or renamed subcommand; fix the doc |

## 6. Backup and recovery

- **Source and docs:** git. The owner decides commits; agents never commit or push.
- **Before a risky local change:** copy the affected files to the session scratchpad (or
  `cp -p file file.bak-<date>` outside tracked paths). Never use `git stash`, `reset` or
  `clean` to recover: they discard the owner's uncommitted work.
- **Uncommitted-work snapshot (read-only):** `git diff > <scratch>/working-tree.patch` and
  `git status --porcelain > <scratch>/status.txt` record the state without changing it.
- **Research store:** `python3 -m nse.research.cli store-backup --db <store.sqlite> --dest <backup.sqlite>`
  (SQLite online backup; migrations are additive and checksummed, `database-engineering` skill).
  The command refuses to overwrite the destination. A copy that has not been opened and checked is not a verified backup.
- **Platform application:** `POST /api/v1/backup` copies `platform.sqlite` and `research.sqlite` with the SQLite
  backup API into a new directory and refuses to overwrite those files or the live database.
  `POST /api/v1/restore-check` copies that backup into `restore-checks/<timestamp>/`, runs `PRAGMA integrity_check`,
  and compares row counts with the backup. It does not replace the live files. Neither copy includes
  `nse/data/eod/raw/`. No backup schedule is installed (`NO_BACKUP_SCHEDULE`). Pointing the running application
  at a restored directory is an owner action.
- **Local evidence:** back up `nse/data/eod/raw/` and `nse/data/calendar/circulars/` with
  the owner's normal file backup; they are not in git (D31). `nse/data/eod/manifest.csv`
  (in git) holds their SHA-256 so a restored file can be verified (`run_all` local_data).
- **Rollback of a structural change:** each foundation change is listed in
  `docs/MILESTONE_STATUS.md` (MP0 change record) and is a small file-local edit; revert by
  hand-editing, then rerun `run_all`. Compatibility aliases (`cli._as_of`, `cli._inputs`,
  `scenarios.parse_as_of`) keep old call sites working.

## 7. Security notes

- No secrets in the repository or in logs; `.env` is git-ignored and not needed.
- No outbound network from `nse/` (`test_repo`); acquisition is an offline inbox.
- Hooks never modify files, never commit and never call the network.
- Third-party skills are read before vendoring and pinned by hash.
