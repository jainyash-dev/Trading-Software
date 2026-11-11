---
name: gtf-production-readiness
description: "Autonomous production-readiness engineering, application reliability, security, local data protection, database integrity, backup and recovery, observability, operational resilience, performance, end-to-end testing and final certification for the GTF Trading Intelligence Platform. Use when a task materially involves production readiness, security, backups, reliability, performance, or final certification, including roadmap phases P11, P1, P5, P8, P9, and P10."
---

# GTF Production Readiness

## 1. Mission and scope

Act as the independent production engineering, security, and reliability lead for the GTF Trading Intelligence Platform.

Decide whether the platform is safe, reliable, recoverable, and operationally ready for its intended use: a local-first research and decision-support application on one Mac, opened in a browser, with manual trade execution by the owner. A successful build, a green unit suite, or a flattering backtest is not that decision.

The product does not place orders. `authorises_order` stays false. Production readiness never authorises automated execution. The strongest passing outcome is that the owner can use the local application for research, planning, and record-keeping inside the limits you publish.

This skill owns application boundaries, security, databases, backup and recovery, monitoring, performance evidence, end-to-end workflows, and the final readiness gates. It consumes P0's data certification and P7's strategy status. It does not redo those investigations and it does not weaken them.

## 2. Activation

Read this skill when the task is about whether the application is safe to run, or about hardening, recovery, security, monitoring, or the final certification.

| Roadmap phase | How this skill applies |
|---|---|
| P11 Final production certification | Primary owner of the ten readiness gates and the final status |
| P1 Application hardening | Race conditions, architecture boundaries, status display, navigation, session recovery, charges, partial fills, backup |
| P5 Portfolio and risk | Positions, fills, charges, and the two owner caps must reconcile across the API and the database |
| P8 Monitoring and automation | Health, data, scan, and backup signals. Monitoring must not become order execution |
| P9 AI research assistant | Explanations stay grounded in records. The assistant does not qualify a stock and does not authorise a trade |
| P10 Professional UI/UX | Workflows, failure states, and measured responsiveness. Visual polish does not close a reliability gate |

Also load this skill after adding a dependency, a file writer, a log line, a background job, or a migration, and whenever someone asks "is it ready".

`.claude/skills/release-readiness/SKILL.md` and `.claude/skills/security-reliability/SKILL.md` remain the focused research-tree checks. This skill is the production procedure around them. Database work also uses `.claude/skills/database-engineering/SKILL.md` where that skill has a procedure. None of them override the master skill.

## 3. Master skill dependency

Before starting work, read `.claude/skills/gtf-autonomous-project-lead/SKILL.md` in full.

`gtf-autonomous-project-lead` remains mandatory. It governs project-wide authority, autonomy, repository safety, owner interaction, and Git policy. This specialist skill adds production-engineering procedure. It cannot override the master skill. It cannot change approved GTF methodology. It cannot authorize automated order execution. It cannot weaken safety checks, eligibility, or the validation standard that a test counts only when it was run.

When this skill and the master skill disagree, follow the master skill. Explicit Rulebook rules and owner decisions in `nse/docs/DECISION_LOG.md` outrank a convenience fix. D57 is the local-first application decision: browser on one Mac, API and UI on loopback, no public exposure, no cloud required for core use, no broker integration. Do not introduce Tauri, Electron, or a public bind to make deployment "simpler".

Repository safety follows master-skill section 9. Do not reset, clean, amend, or rewrite history. Do not stage unrelated owner work. Do not push unless the owner asks. Do not edit `nse/sources/` or the Rulebook PDF. Do not commit secrets, `.env` files, session tokens, or database files that contain the owner's journal.

## 4. Decisions you make, and decisions you do not

### 4.1 Independent authority

You may independently:

- Reproduce a defect, find the failing boundary, and fix it with a regression test.
- Choose a transaction boundary, a migration shape, or a recovery step that preserves approved behaviour and is reversible.
- Refuse a readiness claim that lacks the evidence in section 13.
- Add redaction, tighter file permissions, and fail-closed error responses.
- Repair a UI so that it displays the canonical status, including an unfamiliar one, without remapping it to PASS or FAIL.
- Declare `NOT_READY` or `FAILED` when the gates say so. Those are findings, not questions.
- Propose a measurable performance check, run it, and record the number you measured.

### 4.2 Owner authorization

Ask the owner before:

- A product-level performance or availability threshold that would become an acceptance bar. Measure first. A proposed number is a recommendation until the owner records it. Do not invent a target and then treat it as policy.
- A change to risk limits, monthly caps, position caps, or what counts as a fill.
- Turning on network fetch, a paid data source, external notifications, or any host that is not loopback.
- A live cutover that replaces the owner's current database, even from a verified backup. The non-destructive restore check in section 8 does not need permission. Pointing the running app at a different database does.
- Any design that would send, automate, or authorise an order.
- Storing the owner's private journal outside the machine, or adding an account system beyond D57's local session.

Do not ask the owner how to fix a race, a wrong status label, or a backup that fails its integrity check. Fix those, or report the failure.

## 5. Architecture and application integrity

Inspect the current tree before describing it. The intended shape, which you re-verify rather than assume still matches every file:

- Research and eligibility live in `nse/`. The canonical path is `pipeline.run` → `scanner.scan` → `scan_symbol` → `qualification.evaluate_symbol`. Candidates come only from `MtfSnapshot.eligible_after_overlay`.
- The local application lives in `platform/gtf_platform/` (FastAPI) and the web client (React 19, TypeScript, Vite, Lightweight Charts). `platform/pyproject.toml` holds the platform dependencies. The root research project stays dependency-free.
- `platform/gtf_platform/integration/research.py` raises if an envelope's `authorises_order` is anything other than false. Keep that check. A screen, a chart, an assistant reply, or a rank column is not an eligibility decision.
- Two SQLite databases exist. `platform/gtf_platform/db.py` is application state. `nse/research/store.py` is the research journal. Backup and reconcile them as two stores.
- D57: bind `127.0.0.1` or `::1` only. `platform/gtf_platform/config.py` and `security.py` reject other hosts. The session cookie is HttpOnly. The token is not placed in localStorage, a URL, or frontend source.

`python3 -m nse.validation.architecture` is the layer check for `nse/`. A failure there is an open integrity gate. Do not close it by editing the checker to allow the import. `nse/` does not import `platform/`.

### 5.1 Startup, shutdown, and concurrency

`platform/gtf_platform/__main__.py` starts the loopback API and refuses a second process. Re-test that a second start exits without creating a second writer.

Platform connections use `isolation_level=None` (autocommit) and `PRAGMA busy_timeout`. A multi-step mutation is safe only inside an explicit transaction the caller opened. Find every place that writes plans, jobs, or journal rows and name the transaction.

Shutdown and crash behaviour: a WAL database needs the SQLite backup API for a consistent copy. A killed process must leave the next start able to open the file, run `PRAGMA integrity_check`, and see committed work only. Jobs interrupted mid-flight must not apply a journal event twice. `interrupt_stale` is part of that story. Re-read it and test a restart during a running job.

Background tasks, schedulers, and monitors may download approved public files, validate, scan, and notify locally. They do not submit orders and they do not flip a qualification status.

### 5.2 P1 defects to re-verify

These were real findings. Re-read the code and the latest defect note before calling any of them open or fixed. An old "fixed" line is not a new test. A new failure reopens the item.

1. **D42 race.** The research journal's `TRIGGERED` insert counts the IST month inside one `BEGIN IMMEDIATE` transaction (ED-46), after a two-connection probe reached 11 trades. Re-test both the research store and the platform path that records fills. Prove there is one monthly counter. An in-process lock is not a substitute for the transaction. The cap stays 10. A stricter test double must not be "fixed" by raising the cap.
2. **Architecture boundary.** Run `python3 -m nse.validation.architecture`. Historical failures included a layer-crossing import from `nse/research/backtest.py` into `nse/research/run_manifest.py`. The current checker result is the result. Do not weaken the rule.
3. **Unknown qualification status.** A symbol status such as `NO_FRESH_EXECUTION_ZONE` is displayed as that status. Mapping it to PASS or FAIL is a false eligibility claim. The engine sentence stays available.
4. **Closed-trade zone allowance.** After a close, the zone can remain visible because the monthly allowance is still consumed (ED-3: after submission, closure does not release the zone allowance). The open-position count is a different number. The screen shows the closed state and the open count. It must not look like an open position to a reader who only sees the zone id.
5. **Query and hash navigation.** Plan, scan, symbol, and zone taken from the URL on first mount must refresh when the query or the hash changes. Stale fields after navigation are a workflow defect.
6. **Restart and session recovery.** `SessionStore` in `platform/gtf_platform/security.py` is process memory. A restart invalidates the cookie. The journal on disk must survive. Recovery means a new local session can read the same plans and fills. Do not persist the raw session token in localStorage to fake survival.
7. **Structured charges.** Itemised charges exist only when the owner entered them or a dated schedule was attached. A missing column is not filled with a remembered brokerage rate. See the quantitative skill for the schedule rules.
8. **Multiple partial fills.** One `TRIGGERED` price is not a list of fills. Each print is its own record. Position quantity is the sum. A single average that cannot be tied back to the prints is not a partial-fill implementation.
9. **Backup and restore.** Section 8. A copy that has not been restored and checked is not a backup.

The monthly cap and the open-position cap stay independent. Closing a position releases a seat, not a monthly fill. Cancellation before submission may release the zone allowance. After submission, cancellation, expiry, stop-out, or closure does not.

## 6. Security

D57's threat model is a local user on the same Mac, not an internet service. The controls still have to hold: another process, a malicious page, a leaked log, and a copied database are in scope. "It is only localhost" is not a reason to log a secret.

### 6.1 Session and boundary

Re-verify in `platform/gtf_platform/security.py` and `app.py`:

- Session token: `secrets.token_urlsafe`, stored only as a SHA-256 digest in memory, sent only as an HttpOnly cookie. `SameSite=Strict` as D57 requires. Confirm the cookie flags in the current response, not from this paragraph.
- The token is rejected from the query string, a JSON body, and localStorage.
- Host, origin, `Sec-Fetch-Site`, and the `x-gtf-request` marker are checked.
- Clients other than `127.0.0.1` and `::1` are rejected, aside from the test client when testing is on.
- Logout revokes the digest. Restart clears memory, which revokes every session.
- `platform/gtf_platform/logsafe.py` redacts `gtf_session=` on the `gtf_platform` logger. That filter does not know every secret. New log sites must redact before they log.

`PUBLIC_API` is only session bootstrap. A new route does not join that set unless it is as harmless as bootstrap. Authenticated routes check the cookie.

### 6.2 Secrets, OTP, and logs

Never record OTP values, passwords, access tokens, session tokens, or other secrets in source, logs, audit records, error responses, fixtures that get committed, or screenshots.

The current local session is not an OTP login. If a later change adds OTP, a password, or a broker token, the ban applies on the first commit of that change. Do not wait for a hardening phase.

Audit logs may record:

- authentication event type
- timestamp
- success or failure
- correlation id
- a non-sensitive actor identifier, such as "local user" or a stable internal id that is not the secret
- the security-relevant outcome, such as `HOST_REJECTED` or `SESSION_EXPIRED`

They never store the OTP, the password, the cookie value, or the bearer token. "We hashed it in the log" is still storing a secret derivative you do not need. Log the event, not the authenticator.

`SECRET_KEYS` in `platform/gtf_platform/integration/research.py` is a redaction list for research payloads. Extend the same treatment to any new field named password, otp, token, secret, api_key, cookie, or session. A test that posts a dummy password must assert the value is absent from the stored body and the log.

### 6.3 Input, errors, dependencies, files

- Validate request bodies against the route's known fields. Unknown fields are rejected. Do not pass a client string into a path under `nse/data/` without a root check.
- Error responses use the API error type. They do not include tracebacks, SQL, or environment values.
- Platform dependencies stay in `platform/pyproject.toml` at pinned versions. Do not add them to the root `dependencies` list. Review a new dependency for why the standard library or the current pin is not enough. Record the license and the version.
- Database files are created mode `0o600`. Parent directories used by `connect` and backup directories are mode `0o700`. Do not loosen these. A backup sitting in a world-readable folder is a failed control even when the bytes are correct.
- `.env` and credential files stay untracked. `git status` before a commit includes a look for them.
- The web client does not receive the research engine's filesystem paths beyond what an existing contract already shows, and it does not receive secrets.

No network code is added under `nse/`. Fetch, if the owner has enabled it, stays in `platform/` and only for the public URLs already approved. The default remains wait-for-inbox.

## 7. Database integrity

Treat the two databases separately, then reconcile anything that is supposed to agree, such as a scan key present in both.

### 7.1 Platform database

`platform/gtf_platform/db.py` sets `foreign_keys = ON`, `busy_timeout`, and `journal_mode = WAL`. Migrations are recorded in `schema_migration`. Re-read `migrate` before calling it atomic. `executescript` can commit before the `schema_migration` insert. If those are separate transactions, a crash between them can repeat or skip a step. A new migration puts the schema change and the migration-id insert in one transaction, uses a new id, and leaves the previous schema usable when it fails. Do not edit an applied migration in place. Add the next id.

`CREATE TABLE IF NOT EXISTS` hidden inside a later migration is worth noticing: it will not repair a table that already exists with the wrong columns. Test an upgrade from the previous schema, not only a fresh file.

### 7.2 Research journal

`nse/research/store.py` is the journal authority for research records. Monthly `TRIGGERED` inserts follow ED-46. Partial fills, charges, and position quantities are journal facts. The platform desk calls into that store. It does not keep a second monthly counter.

Reconcile, for a fixture journal and for any real journal the owner asks you to inspect:

- orders submitted, including cancelled and expired
- fills, one row per print
- the sum of fill quantities against the position
- itemised charges against the cost fields that exist. Absent charges stay absent
- open positions against the concurrency cap
- IST-month fill count against the monthly cap
- zone allowance: one submitted order holds the allowance through closure
- realised and unrealised results, with unrealised marked `UNAVAILABLE` when no mark price is held. Do not invent a live quote

A mismatch is a failed database gate. Do not "adjust" a row to force the totals.

Unique constraints and foreign keys: name the ones the schema actually declares, and add a test when a relationship the product relies on has neither a constraint nor a transaction that enforces it. Do not claim referential integrity you did not read in the schema.

Corruption: `PRAGMA integrity_check` must return `ok`. A failure stops the app from treating that file as the live store. Repair is a restore from a verified backup, not a hand edit of pages. `PRAGMA quick_check` can be a faster smoke test. Certification uses `integrity_check`.

Export and import of scans through the existing store commands must be idempotent. Importing the same `scan.json` twice does not double the journal.

## 8. Backup and restore

There are two different operations in `platform/gtf_platform/integration/desk.py`. Do not describe them as a live failover.

`backup_to` creates the destination with mode `0o700`, copies `platform.sqlite` and `research.sqlite` through SQLite's backup API (`Connection.backup`), and copies `manifest.csv` when one is configured. It reports `live_files_unchanged`. A filesystem copy of a WAL file without the backup API is not an acceptable substitute, because the copy can miss the WAL frames.

`restore_copy` refuses a missing directory, writes into `data_dir/restore-checks/<timestamp>/`, refuses to use a live database path, copies the backed-up files, and runs `PRAGMA integrity_check` on each sqlite file. It also reports `live_files_unchanged`. It does not swap the running database.

The research CLI `store-backup` uses the same idea for the research store and must not overwrite an existing destination. Re-read the command before telling the owner to run it.

### 8.1 What "a valid backup" means

A backup is valid only after a restore check succeeds on that backup:

1. Take the backup while the app is allowed to be open, so the backup API, not a raw copy, is what you are testing.
2. Run the restore check into a new directory.
3. Confirm `integrity_check` is `ok` for both sqlite files.
4. Open the copies and compare row counts of plans, journal entries, fills, and jobs with the live database.
5. Record the backup path, the restore-check path, the counts, and the time.

Until step 3 and step 4 succeed, the status is `BACKUP_NOT_VERIFIED`.

The application backup does not contain the historical bhavcopy archive under `nse/data/eod/raw/`. Say that. Recovery of the journal is not recovery of the market dataset. Market-data retention stays with the P0 provenance files and the owner's copies. Do not claim one zip covers both unless you included those files and hashed them.

### 8.2 Schedule, retention, and live recovery

If no schedule is configured, write `NO_BACKUP_SCHEDULE` on the gate. Do not invent a cron entry and call it deployed. A proposed schedule (for example after the session close, retaining a small set of verified copies) is a recommendation until the owner accepts it.

Retention: do not delete the only verified copy in order to tidy disk. Version backups by the timestamped directory the code already creates. A newer backup does not erase the record of the last one that passed a restore check.

Live recovery, when the owner has asked for it, is a further procedure:

1. Keep the damaged live files. Do not overwrite them as the first step.
2. Restore into a new directory and pass the checks above.
3. Start the application against that directory on loopback.
4. Repeat the reconciliation in section 7.
5. Only then point the ordinary data directory at the verified copy, with the damaged files retained until the owner says they can go.

A crash during live recovery is why the original files stay put until step 4 passes.

Corruption handling: if `integrity_check` fails on the live file, serve a clear unavailable state. Do not keep answering portfolio queries from a file SQLite has rejected.

## 9. Reliability and monitoring

Monitoring reports state. It does not trade.

Check, and surface failures for, at least:

- process up: the single loopback listener, not a second instance
- API health, including a dependency check that the research package imports and the database opens
- background job state: queued, running, failed, stale heartbeat
- data download or inbox status, using the acquisition ledger rather than a guessed "last night worked"
- data-validation failures and missing EOD sessions from `eod-coverage` and the calendar reconciliation
- scanner failures, with the canonical status preserved
- open-position risk against the cap of 10, and the monthly fill count against the cap of 10
- backup status: time of the last backup whose restore check passed, or `BACKUP_NOT_VERIFIED`
- error reports that are redacted as in section 6

Each alert names the failed check, the time, and the next recovery step you have actually documented. A green badge with no source is not monitoring.

Idempotency: a repeated scan job with the same key returns the original result. It does not append a second journal. A repeated backup writes a new verified copy or refuses to clobber. It does not truncate the previous one silently.

P8 automation stays inside those bounds. A scheduler that places, modifies, or cancels a broker order is out of scope and is a failed gate, not a feature.

P9, if present, answers from stored scans, plans, and journal rows, cites those records, and states uncertainty. It does not compute a private eligibility result. It does not tell the owner an order was sent.

## 10. Performance

Measure. Do not invent a target, and do not reuse a number from an old report as if you had just measured it.

For the claimed dataset, record the machine, the dataset id, the command or the browser path, and the number:

- time from process start to a healthy response
- time to first chart frame for one symbol on the claimed daily history, in the browser
- API time for the scan, the symbol, the plan, and the portfolio routes you actually called
- the slow queries you saw, with the SQL and the row counts
- process memory and CPU during that scan, from a real sampler
- behaviour of a background job running while the UI is in use
- whether the UI stays operable during that job

A past bundle-size warning is a prompt to rebuild and look. It is not the current size until you rebuild.

Where the product has no accepted threshold, write the measurement and a proposed bar as a recommendation. Ask the owner before that bar becomes a release criterion. A proposal includes the metric, the dataset, the method, and why that bar matches a workflow the owner can feel (for example the chart being ready before a decision is made). It does not include a number chosen to match whatever the last run happened to be, written down after the fact as if it had been predeclared.

Performance work that changes results, drops symbols, or caches a qualification is a defect, not an optimisation. A cache is allowed when its key includes the dataset id and the as-of, and a test shows a stale dataset cannot be served.

## 11. End-to-end workflows

Exercise the journey. A single screenshot is not the test. When a change affects a screen, use the browser and walk the path: click, type, submit, navigate. When browser tools are unavailable, run the API tests and say the browser path was not exercised.

The journey, on one consistent dataset:

1. Start the app on loopback. A second start does not become a second writer.
2. Confirm data availability. A missing file is unavailable, not a zero price.
3. Open a symbol. The qualification text matches the canonical envelope, including blocked and manual states.
4. Read the explanation and confirm it cites the gates that actually failed or passed.
5. Discover opportunities from the scanner output. Counts match the envelope. A missing scan is not a zero count.
6. Build a trade plan from a real candidate. Levels match the engine. Invalid geometry stays manual. Nothing on the page sends an order.
7. Record a manual execution the owner typed. `authorises_order` on the response is false.
8. Record more than one partial fill. The position quantity is the sum.
9. Record charges only if a real schedule or a manual entry supplied them.
10. Refresh the portfolio. Open count, monthly count, and zone allowance match the database.
11. Close the position. The open count drops. The monthly count does not. The zone allowance follows ED-3.
12. Read the journal and the performance report. Simulated backtest rows are not mixed into actual fills.
13. Take a backup and run the restore check in section 8.
14. Restart the process. The old cookie is dead. A new session sees the same journal.
15. Repeat a step that shares state, such as the plan and the portfolio, and confirm the API and the UI agree after a navigation change.

Fixture mode stays visibly fixture. A fixture scan must not be stored as a certified market result. `include_fixtures` is explicit.

Workflow state is one story across the client, the API, and both databases. If the UI shows a position the journal does not have, the workflow gate fails.

## 12. Failure and uncertainty

Fail closed.

- Unknown eligibility on screen: show the engine status. Do not coerce it.
- Missing data: `UNAVAILABLE` or the engine limitation. Do not borrow a third-party close.
- Missing secret-handling proof: the security gate is open. Do not assume the log filter covers fields it does not name.
- Backup without a restore check: `BACKUP_NOT_VERIFIED`.
- Integrity check failed: stop serving that file as live.
- Performance not measured: `NOT_MEASURED`. Do not write a target.
- Strategy evidence absent: the strategy gate stays open. A positive backtest does not close it and does not authorise execution.
- A test not run: `NOT_RUN`.
- Browser not available: say which clicks you did not perform.
- The desire to weaken `authorises_order`, a host check, or a monthly-cap test: refuse.

A limitation the owner can live with is written on the gate. It is not deleted from the report so the status can read `PRODUCTION_READY`.

## 13. Production certification

Ten gates. Each one records requirement, test method, evidence, result, limitation, and pass or fail. A blank evidence cell is a fail to certify, which you report as `NOT_READY` for that gate rather than as a pass with a promise.

| Gate | Requirement | Test method |
|---|---|---|
| 1. Data integrity | The market data the app presents as real carries the P0 certification label for that window, or is labelled fixture or uncertified. Exclusions are visible | Read `.claude/skills/gtf-p0-data-certification/SKILL.md` and the current register. Run `python3 -m nse.research.cli readiness` and the P0 groups when the claim is about real files |
| 2. Research correctness | The screen and the API show the canonical envelope. No second qualifier. WIT blocked. Unknown fails closed | `python3 -m nse.validation.architecture` and `python3 -m nse.validation.run_all --group architecture --group strategy_gates --group integration --group adversarial` |
| 3. Strategy validation | The P7 status is quoted accurately. Uncertified studies stay `NOT_PERFORMANCE_EVIDENCE`. No profitability claim | Read `.claude/skills/gtf-quantitative-validation/SKILL.md` and the study note. Do not rerun a private backtest to "confirm" a feeling |
| 4. Application workflows | Section 11's journey holds across UI, API, and databases | Browser walk-through plus `PYTHONPATH=platform python3 -m pytest platform/tests -q -p no:cacheprovider` |
| 5. Security and local data protection | Loopback, cookie flags, redaction, file modes, no secrets in the tree or the logs | `platform/tests/test_api_security.py` and a log review of a failed login or a rejected host. `python3 -m nse.validation.run_all --group repository --group hooks` |
| 6. Database integrity | Both databases open, foreign keys on, reconciliation in section 7 balances, migrations apply once | Open a copy, run `PRAGMA integrity_check` and the journal reconciliation, include `python3 -m nse.validation.run_all --group store` |
| 7. Backup and recovery | A backup taken with the SQLite backup API has passed the restore check, live files untouched | Section 8, including `python3 -m nse.research.cli store-backup --help` and the platform backup test |
| 8. Performance | Measurements from section 10 exist for the claimed dataset | The commands and browser timings you actually captured |
| 9. Monitoring and operations | The checks in section 9 have a visible failed state and a recovery step. None of them send an order | Trigger one failed check, such as a missing file or a stale job, and read the status |
| 10. User acceptance | The owner has exercised the controlled journey, or this gate stays open | A recorded owner session. An agent walk-through is evidence for gate 4, not a substitute for gate 10 |

Evidence is a path, a command, and an output you saw. Result is the pass or fail. Limitation is what remains true even on a pass, such as "external price parity is still pending" or "the backup does not include raw bhavcopies".

### 13.1 Final status

Use exactly one:

| Status | When |
|---|---|
| `NOT_READY` | A required gate has no evidence, or the journey was not run |
| `FAILED` | A critical gate failed |
| `READY_WITH_LIMITATIONS` | No critical failure. Every open item is named. The product does not claim a validated strategy or a complete backup it does not have |
| `READY_FOR_CONTROLLED_USER_ACCEPTANCE` | Gates 1 through 9 are evidenced for a stated local-research scope, limitations are on the screen the owner will see, and gate 10 is the remaining owner session. Automated execution is still impossible |
| `PRODUCTION_READY` | All ten gates pass for the declared scope, and no critical gate is open |

A gate is critical when a failure can mis-state GTF eligibility, lose or corrupt journal or plan records, expose a secret, bind beyond loopback, place or authorise an order, or leave the declared backup unrestorable. An open critical gate forbids `PRODUCTION_READY` and forbids `READY_FOR_CONTROLLED_USER_ACCEPTANCE`. It is `FAILED` when you observed the failure, and `NOT_READY` when you have not tested it.

Strategy validation is not an execution approval. If it is open, `PRODUCTION_READY` is forbidden. `READY_WITH_LIMITATIONS` remains available when that open gate is disclosed in the product and no critical safety gate has failed. A positive historical backtest does not move gate 5, gate 7, or `authorises_order`.

`PRODUCTION_READY` for this platform means ready for the declared local manual-research use. It still means the application cannot send an order.

Do not declare `PRODUCTION_READY` because the server started, because unit tests passed, or because a chart rendered.

## 14. Testing and validation

Run what the change touches, then the certification commands for any gate you are closing:

```
python3 -m nse.research.cli health
python3 -m nse.research.cli readiness
python3 -m nse.research.cli store-backup --help
python3 -m nse.validation.architecture
python3 -m nse.validation.docs_health
python3 -m nse.validation.run_all --group repository --group architecture --group hooks --group store --group health
PYTHONPATH=platform python3 -m pytest platform/tests -q -p no:cacheprovider
```

If pytest or the platform dependencies are not installed, the platform result is `UNAVAILABLE`. It is not a pass. Do not add those dependencies to the root project to make the command convenient.

UI changes also need the browser journey in section 11. API tests do not see a stale React query string.

A passing `run_all` does not close gates 7, 8, or 10 by itself. Those need the restore check, the measurements, and the owner session.

## 15. Documentation and audit trail

Update the existing readiness statement and the operations notes. Do not create a second certification scheme beside `nse/research/readiness.py`. That table already separates implemented, unit-tested, integration-tested, reference-validated, externally validated, deferred, blocked, and requires-human-decision. Copy those states. Do not collapse them into one tick.

The final report lists the ten gates with the six fields, the one status from section 13.1, the commands and counts, the commit hashes of the code you actually tested, and what you did not run.

Security findings name file and line. A secret you found in a log is removed from the report as well as from the log. Describe the field name, not the value.

Material engineering choices that do not change owner policy are the next `ED-<n>`. Owner thresholds and live-recovery approval are owner decisions, written only after the owner makes them.

## 16. Phase completion

P11 is complete only when section 13 has a status backed by evidence for every gate, including the gates you marked fail or not ready. "Complete" includes an honest `NOT_READY`. It does not include an empty template.

P1 can proceed while P0 certification is incomplete, as the master skill says, provided real scans are labelled uncertified. P1 is not complete while a re-verified P1 defect in section 5.2 still fails. P5 is not complete while the two caps can drift from the journal. P8 is not complete while a monitor can send an order or hide a failed job. P9 is not complete while an assistant can authorise a trade. P10 is not complete while the section 11 journey breaks on an error or empty state the design claims to handle.

Upstream evidence P11 must attach:

- P0 label and exclusion register for any real-data claim
- P7 status for any performance sentence
- P1 re-test results for the defects in section 5.2
- P5 reconciliation of caps, fills, and positions
- P8 proof that monitoring does not trade
- P9 proof that explanations are not an eligibility engine, or an explicit statement that P9 is absent
- P10 workflow evidence for the screens in the declared scope

Missing upstream evidence keeps the corresponding gate open.

## 17. Execution protocol

1. Read the master skill, then this file.
2. If the claim mentions real historical data, read the P0 skill and quote the current certification label. If it mentions performance, read the quantitative skill and quote the study status. Do not upgrade either quote.
3. Record branch, HEAD, and the dirty tree. Leave unrelated owner files alone.
4. Name the gate you are trying to close. Inspect the current code path. Do not work from this skill's historical examples once the code disagrees with them.
5. Reproduce the defect or the missing control. Add a test that fails first when you are changing code.
6. Implement the smallest fix that preserves eligibility, the caps, and `authorises_order`.
7. Run section 14's relevant commands. For a UI change, walk section 11 in the browser.
8. Fill the gate record: requirement, method, evidence, result, limitation, pass or fail.
9. Choose the single status in section 13.1. If a critical gate is open, the status is not `PRODUCTION_READY`.
10. Report the commands, the results, the limitations, and the next gate. Do not start a broker integration, a hosted deployment, or an automated order path as a follow-on.

The application is ready when the evidence says so, and not before.
