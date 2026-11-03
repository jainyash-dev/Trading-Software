"""Optional local research store (SQLite, standard library) and paper-trade journal.

The JSON/CSV reports (reports.py) stay the primary outputs. The store keeps an archive of
scans exactly as they were written (scan.json = reports.to_json(result)) so that a zone can
be followed across scans; it never computes a gate, a status or a level and is never a
second source of trading decisions (spec 6.4 single pathway; D3; CLAUDE.md 6.4).

Store rules:
  - schema versions are applied from MIGRATIONS (ordered, additive only). schema_migrations
    records version, name and the sha256 of each migration's SQL; a recorded checksum that
    differs from the code, or a recorded version the code does not know, raises
    MigrationDriftError (tamper / drift). No migration may DROP, DELETE, UPDATE without WHERE
    or ALTER TABLE ... DROP (destructive_statements; checked before any SQL runs);
  - archive tables are append-only (triggers refuse UPDATE and DELETE);
  - import_scan is idempotent by scan_key = sha256 of the canonical scan.json text; it stores
    statuses verbatim and refuses a candidate status outside models.STATUS_ORDER, a gate
    outcome outside models.OUTCOMES, or a status that does not follow from the scan's own
    gate outcomes by models.derive_status (a hand-edited or corrupted scan; no recomputation
    of any gate);
  - no clock is read: every time stored comes from the scan or the caller (contract rule 5).

Paper-trade journal (Rulebook Part 7 Chapter 5, RB 3707-3774): a manual research record of
what the owner decided. No execution, no broker, no order (D10, D17, D31).
  - an entry references a stored candidate (scan_key, symbol, zone_id); its status is read
    from the stored scan, never from the caller. BLOCKED, REJECTED and DATA_INSUFFICIENT
    candidates are refused (an automated gate failed or data was missing; RB 2380 "All
    checks pass"); MANUAL_REVIEW needs a non-empty manual_review_resolution note;
  - every models.CHECKLIST code must be confirmed explicitly true or false (spec section 8:
    always-manual checks); a false confirmation is recorded, not hidden, and counted in the
    summary as a rule-compliance exception (RB 3739, 3773);
  - the alert note is the owner's text (RB 2385); long only (D16 scope: long cash equity);
  - lifecycle events are appended, never updated, in chronological order. STOP_LOSS_HIT and
    ZONE_INVALIDATED are distinct kinds (approved R4: a stop touch is a trade event, a
    completed close beyond DL is a zone event). Once TRIGGERED the stop is locked
    (RB 2139): any later event carrying a different stop is refused. There is no
    add-to-position kind and a second TRIGGERED is refused (RB 2140: never average down).
  - journal_summary is journal arithmetic over the owner's own records (RB 3762-3774) and
    the 10 trades per month ceiling (RB 2392). It is not validation and not evidence of
    profitability; costs are not recorded, so P&L is gross.
"""

import datetime
import hashlib
import json
import math
import os
import re
import sqlite3
import sys

from nse.research import levels, models as m

IMPORTED = "IMPORTED"
ALREADY_PRESENT = "ALREADY_PRESENT"
MONTHLY_TRADE_CEILING = 10                       # RB 2392

# journal event kinds (no add-to-position kind exists: RB 2140)
PLANNED = "PLANNED"
TRIGGERED = "TRIGGERED"
STOP_LOSS_HIT = "STOP_LOSS_HIT"
TARGET_HIT = "TARGET_HIT"
CANCELLED = "CANCELLED"
EXPIRED = "EXPIRED"
CLOSED_MANUAL = "CLOSED_MANUAL"
ZONE_INVALIDATED = "ZONE_INVALIDATED"            # approved R4: distinct from STOP_LOSS_HIT
NOTE = "NOTE"
EVENT_KINDS = (PLANNED, TRIGGERED, STOP_LOSS_HIT, TARGET_HIT, CANCELLED, EXPIRED, CLOSED_MANUAL,
               ZONE_INVALIDATED, NOTE)
EXITS = (STOP_LOSS_HIT, TARGET_HIT, CLOSED_MANUAL)
PRICED = (TRIGGERED,) + EXITS
# journal state -> event kinds allowed in it
ALLOWED = {
    "PLANNED": (PLANNED, TRIGGERED, CANCELLED, EXPIRED, ZONE_INVALIDATED, NOTE),
    "OPEN": (STOP_LOSS_HIT, TARGET_HIT, CLOSED_MANUAL, ZONE_INVALIDATED, NOTE),
    "CLOSED": (NOTE,),
    "CANCELLED": (NOTE,),
    "EXPIRED": (NOTE,),
}
JOURNAL_REFUSED_STATUSES = (m.BLOCKED_STATUS, m.REJECTED, m.STATUS_DATA_INSUFFICIENT)
MIN_RR = levels.MIN_RR                   # RB 82, RF8: the one 2:1 threshold
ENTRY_FIELDS = ("symbol", "zone_id", "scan_key", "planned_entry", "planned_stop", "planned_target", "quantity",
                "alert_note", "checklist", "recorded_at")
ENTRY_OPTIONAL = ("manual_review_resolution",)
JOURNAL_NOTE = ("Journal arithmetic over the owner's own manual records (RB 3762-3774). Not validation, not "
                "evidence of profitability; costs are not recorded, so P&L is gross.")


class StoreError(ValueError):
    """Input the store cannot accept (malformed scan, unknown key, bad argument)."""


class MigrationDriftError(StoreError):
    """The database schema does not match the migrations in this code."""


class JournalRefused(StoreError):
    """A journal entry or event breaks a Rulebook rule the journal enforces."""


def _sql_list(values):
    return ", ".join("'%s'" % v for v in values)


def _append_only(table):
    return ("CREATE TRIGGER {t}_no_update BEFORE UPDATE ON {t} BEGIN SELECT RAISE(ABORT, '{t} is append-only'); END;\n"
            "CREATE TRIGGER {t}_no_delete BEFORE DELETE ON {t} BEGIN SELECT RAISE(ABORT, '{t} is append-only'); END;\n"
            ).format(t=table)


# literal lists, so a change to models.py cannot silently alter a recorded checksum; a test
# asserts they equal models.STATUS_ORDER / models.OUTCOMES / EVENT_KINDS
_V1_STATUSES = ("BLOCKED", "REJECTED", "DATA_INSUFFICIENT", "MANUAL_REVIEW", "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING")
_V1_OUTCOMES = ("PASS", "FAIL", "MANUAL", "DATA_INSUFFICIENT", "BLOCKED", "NOT_EVALUATED")
_V1_KINDS = ("PLANNED", "TRIGGERED", "STOP_LOSS_HIT", "TARGET_HIT", "CANCELLED", "EXPIRED", "CLOSED_MANUAL",
             "ZONE_INVALIDATED", "NOTE")
_GATE_COLUMNS = "".join("  %s TEXT NOT NULL CHECK (%s IN (%s)),\n" % (g, g, _sql_list(_V1_OUTCOMES))
                        for g in ("G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"))

_V1 = """
CREATE TABLE scans (
  scan_key TEXT PRIMARY KEY,
  as_of TEXT NOT NULL,
  generated_at TEXT,
  trade_type TEXT NOT NULL,
  universe TEXT NOT NULL,
  calendar TEXT NOT NULL,
  pipeline_version TEXT NOT NULL,
  engine_versions TEXT NOT NULL,
  limitations TEXT NOT NULL,
  raw_json TEXT NOT NULL
);
CREATE TABLE symbol_results (
  scan_key TEXT NOT NULL REFERENCES scans(scan_key),
  symbol TEXT NOT NULL,
  status TEXT NOT NULL,
  reasons TEXT NOT NULL,
  price REAL,
  provenance TEXT NOT NULL,
  limitations TEXT NOT NULL,
  PRIMARY KEY (scan_key, symbol)
);
CREATE TABLE candidates (
  candidate_id INTEGER PRIMARY KEY,
  scan_key TEXT NOT NULL REFERENCES scans(scan_key),
  symbol TEXT NOT NULL,
  zone_id TEXT NOT NULL,
  trade_type TEXT NOT NULL,
  execution_tf TEXT NOT NULL,
  as_of TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN (%(statuses)s)),
  core TEXT,
%(gates)s  status_reasons TEXT NOT NULL,
  manual_review TEXT NOT NULL,
  manual_checks TEXT NOT NULL,
  levels TEXT NOT NULL,
  zone TEXT NOT NULL,
  limitations TEXT NOT NULL,
  UNIQUE (scan_key, symbol, zone_id),
  FOREIGN KEY (scan_key, symbol) REFERENCES symbol_results(scan_key, symbol)
);
CREATE TABLE gate_results (
  candidate_id INTEGER NOT NULL REFERENCES candidates(candidate_id),
  gate TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK (outcome IN (%(outcomes)s)),
  reasons TEXT NOT NULL,
  manual_review TEXT NOT NULL,
  sources TEXT NOT NULL,
  PRIMARY KEY (candidate_id, gate)
);
CREATE TABLE blocked_zones (
  scan_key TEXT NOT NULL REFERENCES scans(scan_key),
  symbol TEXT NOT NULL,
  zone_id TEXT NOT NULL,
  tf TEXT,
  engine_status TEXT,
  overlay_status TEXT,
  disposition TEXT,
  reasons TEXT NOT NULL
);
CREATE TABLE findings (
  scan_key TEXT NOT NULL REFERENCES scans(scan_key),
  symbol TEXT NOT NULL,
  severity TEXT,
  code TEXT,
  detail TEXT,
  verified TEXT,
  raw TEXT NOT NULL
);
CREATE TABLE ingestion_events (
  event_id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,
  key TEXT NOT NULL,
  status TEXT NOT NULL,
  detail TEXT NOT NULL,
  recorded_at TEXT NOT NULL
);
CREATE TABLE alerts (
  alert_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  recorded_at TEXT NOT NULL
);
CREATE TABLE journal_entries (
  entry_id INTEGER PRIMARY KEY,
  scan_key TEXT NOT NULL REFERENCES scans(scan_key),
  symbol TEXT NOT NULL,
  zone_id TEXT NOT NULL,
  trade_type TEXT NOT NULL,
  direction TEXT NOT NULL CHECK (direction = 'LONG'),
  candidate_status TEXT NOT NULL CHECK (candidate_status IN ('MANUAL_REVIEW', 'ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING')),
  manual_review_resolution TEXT,
  candidate_levels TEXT NOT NULL,
  planned_entry REAL NOT NULL,
  planned_stop REAL NOT NULL,
  planned_target REAL NOT NULL,
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  alert_note TEXT NOT NULL,
  checklist TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  FOREIGN KEY (scan_key, symbol, zone_id) REFERENCES candidates(scan_key, symbol, zone_id)
);
CREATE TABLE journal_events (
  entry_id INTEGER NOT NULL REFERENCES journal_entries(entry_id),
  seq INTEGER NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN (%(kinds)s)),
  at TEXT NOT NULL,
  price REAL,
  stop_level REAL,
  note TEXT,
  PRIMARY KEY (entry_id, seq)
);
""" % {"statuses": _sql_list(_V1_STATUSES), "outcomes": _sql_list(_V1_OUTCOMES), "kinds": _sql_list(_V1_KINDS),
       "gates": _GATE_COLUMNS} + "".join(_append_only(t) for t in (
    "scans", "symbol_results", "candidates", "gate_results", "blocked_zones", "findings", "ingestion_events",
    "alerts", "journal_entries", "journal_events"))

# ordered (version, name, sql); append new versions, never edit a released one
MIGRATIONS = (
    (1, "v1_scans_candidates_journal", _V1),
)

_DESTRUCTIVE = (
    (re.compile(r"\bDROP\b", re.I), "DROP"),
    (re.compile(r"\bDELETE\s+FROM\b", re.I), "DELETE"),
    (re.compile(r"\bREPLACE\b", re.I), "REPLACE (deletes the conflicting row)"),
    (re.compile(r"\bALTER\s+TABLE\s+\w+\s+DROP\b", re.I), "ALTER TABLE ... DROP"),
    (re.compile(r"\bTRUNCATE\b", re.I), "TRUNCATE"),
)
_UPDATE = re.compile(r"\bUPDATE\s+\w+\s+SET\b(?P<rest>[^;]*)", re.I)


def destructive_statements(sql):
    """Destructive constructs in a migration's SQL (additive-only rule). A trigger that
    refuses UPDATE / DELETE ('BEFORE UPDATE ON t') is protective and is not matched."""
    found = [label for rx, label in _DESTRUCTIVE if rx.search(sql)]
    for u in _UPDATE.finditer(sql):
        if not re.search(r"\bWHERE\b", u.group("rest"), re.I):
            found.append("UPDATE without WHERE")
    return found


def _checksum(sql):
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


def _migrate(conn, migrations):
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                 "checksum TEXT NOT NULL)")
    conn.commit()
    code = {v: (n, s) for v, n, s in migrations}
    if [v for v, _, _ in migrations] != sorted(code) or len(code) != len(migrations):
        raise MigrationDriftError("migration versions must be unique and ascending")
    recorded = {v: (n, c) for v, n, c in conn.execute("SELECT version, name, checksum FROM schema_migrations")}
    for v, (name, digest) in sorted(recorded.items()):
        if v not in code:
            raise MigrationDriftError("database has migration %d (%s) that this code does not know" % (v, name))
        if digest != _checksum(code[v][1]):
            raise MigrationDriftError("migration %d (%s) checksum differs from the code: schema drift or tampering"
                                      % (v, name))
    for v, name, sql in migrations:
        if v in recorded:
            continue
        bad = destructive_statements(sql)
        if bad:
            raise MigrationDriftError("migration %d (%s) is not additive: %s" % (v, name, ", ".join(bad)))
        if not re.match(r"^[\w.-]+$", name):
            raise MigrationDriftError("migration name %r" % name)
        conn.executescript("BEGIN;\n%s\nINSERT INTO schema_migrations (version, name, checksum) VALUES (%d, '%s', '%s');"
                           "\nCOMMIT;" % (sql, v, name, _checksum(sql)))


def open_store(path, migrations=None):
    """Create or open the SQLite store at path and apply pending migrations."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        _migrate(conn, MIGRATIONS if migrations is None else migrations)
    except Exception:
        conn.close()
        raise
    return conn


def applied_migrations(conn):
    return [tuple(r) for r in conn.execute("SELECT version, name, checksum FROM schema_migrations ORDER BY version")]


# --- scans ----------------------------------------------------------------------------
def canonical_text(scan_dict):
    """The text reports.to_json writes for this scan (sort_keys, indent 1)."""
    return json.dumps(scan_dict, sort_keys=True, indent=1)


def scan_key(scan_dict):
    return hashlib.sha256(canonical_text(scan_dict).encode("utf-8")).hexdigest()


def _j(v):
    return json.dumps(v, sort_keys=True)


def _need(d, keys, what):
    if not isinstance(d, dict):
        raise StoreError("%s is not an object" % what)
    missing = [k for k in keys if k not in d]
    if missing:
        raise StoreError("%s lacks %s" % (what, ", ".join(missing)))


def _check_candidate(c, where):
    _need(c, ("symbol", "zone", "gates", "status", "trade_type", "execution_tf", "as_of", "status_reasons",
              "manual_review", "manual_checks", "levels", "limitations"), where)
    if c["status"] not in m.STATUS_ORDER:
        raise StoreError("%s: status %r is not one of %s" % (where, c["status"], ", ".join(m.STATUS_ORDER)))
    gates = c["gates"]
    if [g.get("gate") for g in gates] != list(m.GATES):
        raise StoreError("%s: gates must be G0-G8 in order" % where)
    try:
        objs = [m.GateResult(g["gate"], g["outcome"]) for g in gates]
    except (KeyError, ValueError) as e:
        raise StoreError("%s: %s" % (where, e))
    derived = m.derive_status(objs)
    if derived != c["status"]:
        raise StoreError("%s: status %s does not follow from its gate outcomes (%s); the scan file is inconsistent"
                         % (where, c["status"], derived))
    if "zone_id" not in c["zone"]:
        raise StoreError("%s: zone has no zone_id" % where)


def import_scan(conn, scan_dict):
    """Store one scan verbatim. Returns (IMPORTED | ALREADY_PRESENT, scan_key)."""
    _need(scan_dict, ("as_of", "generated_at", "trade_type", "universe", "calendar", "pipeline_version",
                      "engine_versions", "limitations", "symbols"), "scan")
    key = scan_key(scan_dict)
    if conn.execute("SELECT 1 FROM scans WHERE scan_key = ?", (key,)).fetchone():
        return ALREADY_PRESENT, key
    for s in scan_dict["symbols"]:
        _need(s, ("symbol", "status", "reasons", "price", "candidates", "blocked_zones", "findings", "provenance",
                  "limitations"), "symbol result")
        for i, c in enumerate(s["candidates"]):
            _check_candidate(c, "%s candidate %d" % (s["symbol"], i))
    with conn:
        conn.execute("INSERT INTO scans VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (key, scan_dict["as_of"], scan_dict["generated_at"], scan_dict["trade_type"],
                      scan_dict["universe"], scan_dict["calendar"], scan_dict["pipeline_version"],
                      _j(scan_dict["engine_versions"]), _j(scan_dict["limitations"]), canonical_text(scan_dict)))
        for s in scan_dict["symbols"]:
            conn.execute("INSERT INTO symbol_results VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (key, s["symbol"], s["status"], _j(s["reasons"]), s["price"], _j(s["provenance"]),
                          _j(s["limitations"])))
            for c in s["candidates"]:
                g = {x["gate"]: x["outcome"] for x in c["gates"]}
                cur = conn.execute(
                    "INSERT INTO candidates (scan_key, symbol, zone_id, trade_type, execution_tf, as_of, status, core, "
                    + ", ".join(m.GATES) + ", status_reasons, manual_review, manual_checks, levels, zone, limitations) "
                    "VALUES (" + ", ".join("?" * (8 + len(m.GATES) + 6)) + ")",
                    (key, c["symbol"], c["zone"]["zone_id"], c["trade_type"], c["execution_tf"], c["as_of"],
                     c["status"], c["zone"].get("core")) + tuple(g[x] for x in m.GATES)
                    + (_j(c["status_reasons"]), _j(c["manual_review"]), _j(c["manual_checks"]), _j(c["levels"]),
                       _j(c["zone"]), _j(c["limitations"])))
                for x in c["gates"]:
                    conn.execute("INSERT INTO gate_results VALUES (?, ?, ?, ?, ?, ?)",
                                 (cur.lastrowid, x["gate"], x["outcome"], _j(x.get("reasons", [])),
                                  _j(x.get("manual_review", [])), _j(x.get("sources", []))))
            for b in s["blocked_zones"]:
                conn.execute("INSERT INTO blocked_zones VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (key, s["symbol"], b.get("zone_id"), b.get("tf"), b.get("engine_status"),
                              b.get("overlay_status"), b.get("disposition"), _j(b.get("reasons", []))))
            for f in s["findings"]:
                conn.execute("INSERT INTO findings VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (key, s["symbol"], f.get("severity"), f.get("code"), f.get("detail"),
                              None if f.get("verified") is None else str(f.get("verified")), _j(f)))
    return IMPORTED, key


def _dt(text, what):
    if isinstance(text, datetime.datetime):
        return text
    try:
        return datetime.datetime.fromisoformat(text)
    except (TypeError, ValueError):
        raise StoreError("%s %r is not an ISO date-time" % (what, text))


def _before(a, b, what):
    """a < b, refusing to compare naive with aware times."""
    try:
        return a < b
    except TypeError:
        raise StoreError("%s: cannot compare a naive and a timezone-aware time" % what)


def _scan_row(r):
    d = dict(r)
    d.pop("raw_json")
    d["engine_versions"] = json.loads(d["engine_versions"])
    d["limitations"] = json.loads(d["limitations"])
    return d


def latest_scan(conn, as_of_max=None):
    """The stored scan with the latest as_of (at or before as_of_max when given); ties by
    scan_key. None when there is none."""
    rows = conn.execute("SELECT * FROM scans").fetchall()
    limit = None if as_of_max is None else _dt(as_of_max, "as_of_max")
    best = None
    for r in rows:
        t = _dt(r["as_of"], "scan as_of")
        if limit is not None and _before(limit, t, "latest_scan"):
            continue
        k = (t, r["scan_key"])
        if best is None or _before(best[0], k, "latest_scan"):
            best = (k, r)
    return None if best is None else _scan_row(best[1])


def scan_json(conn, key):
    r = conn.execute("SELECT raw_json FROM scans WHERE scan_key = ?", (key,)).fetchone()
    if r is None:
        raise StoreError("unknown scan_key %s" % key)
    return r["raw_json"]


def status_counts(conn, key):
    """Counts from the stored rows; they reconcile with reports.summary of the same scan."""
    scan_json(conn, key)
    cand = {r[0]: r[1] for r in conn.execute(
        "SELECT status, COUNT(*) FROM candidates WHERE scan_key = ? GROUP BY status ORDER BY status", (key,))}
    sym = {r[0]: r[1] for r in conn.execute(
        "SELECT status, COUNT(*) FROM symbol_results WHERE scan_key = ? GROUP BY status ORDER BY status", (key,))}
    one = lambda sql: conn.execute(sql, (key,)).fetchone()[0]
    return {"candidate_status_counts": cand, "candidate_records": sum(cand.values()),
            "symbol_status_counts": sym, "symbols_processed": sum(sym.values()),
            "blocked_zone_records": one("SELECT COUNT(*) FROM blocked_zones WHERE scan_key = ?"),
            "data_quality_findings": one("SELECT COUNT(*) FROM findings WHERE scan_key = ?")}


def zone_history(conn, symbol, zone_id):
    """For every stored scan that covered symbol, in as_of order: the zone's candidate status
    there, or that it was blocked by the overlay, or absent. A zone that was ACTIONABLE and
    is later tested simply stops being a candidate (D3); the store shows it, never revives it."""
    out = []
    for r in conn.execute("SELECT s.scan_key, s.as_of, s.trade_type, y.status FROM scans s JOIN symbol_results y "
                          "ON y.scan_key = s.scan_key WHERE y.symbol = ?", (symbol,)):
        c = conn.execute("SELECT status FROM candidates WHERE scan_key = ? AND symbol = ? AND zone_id = ?",
                         (r["scan_key"], symbol, zone_id)).fetchone()
        b = conn.execute("SELECT overlay_status, disposition, reasons FROM blocked_zones WHERE scan_key = ? AND "
                         "symbol = ? AND zone_id = ? ORDER BY tf, disposition", (r["scan_key"], symbol, zone_id)).fetchall()
        out.append({"scan_key": r["scan_key"], "as_of": r["as_of"], "trade_type": r["trade_type"],
                    "symbol_status": r["status"], "candidate_status": c["status"] if c else None,
                    "blocked": [{"overlay_status": x["overlay_status"], "disposition": x["disposition"],
                                 "reasons": json.loads(x["reasons"])} for x in b],
                    "presence": "CANDIDATE" if c else ("BLOCKED_BY_OVERLAY" if b else "ABSENT")})
    out.sort(key=lambda d: (_dt(d["as_of"], "scan as_of"), d["scan_key"]))
    return out


# --- acquisition ledger and alerts (generic append-only records) ----------------------
def record_ingestion_event(conn, kind, key, status, detail, recorded_at):
    for name, v in (("kind", kind), ("key", key), ("status", status), ("recorded_at", recorded_at)):
        if not isinstance(v, str) or not v:
            raise StoreError("%s must be a non-empty string" % name)
    _dt(recorded_at, "recorded_at")
    with conn:
        cur = conn.execute("INSERT INTO ingestion_events (kind, key, status, detail, recorded_at) VALUES (?, ?, ?, ?, ?)",
                           (kind, key, status, _j(detail), recorded_at))
    return cur.lastrowid


def ingestion_events(conn, kind=None):
    sql, args = "SELECT * FROM ingestion_events", ()
    if kind is not None:
        sql, args = sql + " WHERE kind = ?", (kind,)
    return [dict(r, detail=json.loads(r["detail"])) for r in conn.execute(sql + " ORDER BY event_id", args)]


def record_alert(conn, alert_id, payload, recorded_at):
    """Insert once. The same id with the same payload: ALREADY_PRESENT; with a different payload: refused."""
    _dt(recorded_at, "recorded_at")
    text = _j(payload)
    r = conn.execute("SELECT payload FROM alerts WHERE alert_id = ?", (alert_id,)).fetchone()
    if r is not None:
        if r["payload"] != text:
            raise StoreError("alert %s already stored with a different payload" % alert_id)
        return ALREADY_PRESENT
    with conn:
        conn.execute("INSERT INTO alerts VALUES (?, ?, ?)", (alert_id, text, recorded_at))
    return IMPORTED


def backup(conn, dest_path):
    """Online copy with the sqlite3 backup API. Refuses to overwrite an existing file."""
    if os.path.exists(dest_path):
        raise FileExistsError("backup destination exists, refusing to overwrite: %s" % dest_path)
    dest = sqlite3.connect(dest_path)
    try:
        conn.backup(dest)
    finally:
        dest.close()
    return dest_path


# --- paper-trade journal --------------------------------------------------------------
def _num(v, what):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise StoreError("%s must be a finite number" % what)
    return float(v)


def journal_add(conn, entry):
    """Record the owner's planned trade on a stored candidate. Returns the entry_id."""
    if not isinstance(entry, dict):
        raise StoreError("entry is not an object")
    unknown = sorted(set(entry) - set(ENTRY_FIELDS) - set(ENTRY_OPTIONAL))
    if unknown:
        raise StoreError("unknown entry fields: %s (the candidate status is read from the stored scan)"
                         % ", ".join(unknown))
    _need(entry, ENTRY_FIELDS, "journal entry")
    srow = conn.execute("SELECT as_of, trade_type FROM scans WHERE scan_key = ?", (entry["scan_key"],)).fetchone()
    if srow is None:
        raise StoreError("scan_key %s is not in the store (import the scan first)" % entry["scan_key"])
    c = conn.execute("SELECT status, levels FROM candidates WHERE scan_key = ? AND symbol = ? AND zone_id = ?",
                     (entry["scan_key"], entry["symbol"], entry["zone_id"])).fetchone()
    if c is None:
        raise JournalRefused("%s %s is not a candidate in scan %s" % (entry["symbol"], entry["zone_id"],
                                                                      entry["scan_key"]))
    status = c["status"]
    if status in JOURNAL_REFUSED_STATUSES:
        raise JournalRefused("candidate status %s at that scan: a Rulebook gate failed or data was missing "
                             "(RB 2380 all checks pass); no journal entry" % status)
    resolution = entry.get("manual_review_resolution")
    if resolution is not None and (not isinstance(resolution, str) or not resolution.strip()):
        raise StoreError("manual_review_resolution must be non-empty text when given")
    if status == m.MANUAL_REVIEW and not resolution:
        raise JournalRefused("candidate status MANUAL_REVIEW: a non-empty manual_review_resolution note is required")
    checklist = entry["checklist"]
    codes = [x[0] for x in m.CHECKLIST]
    if not isinstance(checklist, dict):
        raise StoreError("checklist must map every CHECKLIST code to true or false")
    missing = [k for k in codes if k not in checklist]
    extra = sorted(set(checklist) - set(codes))
    if missing or extra:
        raise JournalRefused("checklist must confirm exactly the CHECKLIST codes; missing: %s; unknown: %s"
                             % (", ".join(missing) or "none", ", ".join(extra) or "none"))
    not_bool = [k for k in codes if not isinstance(checklist[k], bool)]
    if not_bool:
        raise JournalRefused("checklist codes not explicitly true or false: %s" % ", ".join(not_bool))
    entry_p = _num(entry["planned_entry"], "planned_entry")
    stop = _num(entry["planned_stop"], "planned_stop")
    target = _num(entry["planned_target"], "planned_target")
    if not (stop < entry_p < target):
        raise StoreError("a long plan needs stop < entry < target")
    if (target - entry_p) / (entry_p - stop) < MIN_RR:
        raise JournalRefused("planned R:R %.4f is below 2:1 (RB 82, RF8)" % ((target - entry_p) / (entry_p - stop)))
    qty = entry["quantity"]
    if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
        raise StoreError("quantity must be a positive whole number of shares")
    note = entry["alert_note"]
    if not isinstance(note, str) or not note.strip():
        raise StoreError("alert_note (RB 2385) must be non-empty text")
    rec = _dt(entry["recorded_at"], "recorded_at")
    if _before(rec, _dt(srow["as_of"], "scan as_of"), "journal_add"):
        raise JournalRefused("recorded_at %s is before the scan's as_of %s" % (entry["recorded_at"], srow["as_of"]))
    # a later stored scan (as_of in (scan as_of, recorded_at]) that no longer lists the zone as a
    # candidate, or lists it with a refused status, supersedes the old scan: the zone may have been
    # tested or invalidated since (D3, R4). Review fix 2026-11-02.
    scan_t = _dt(srow["as_of"], "scan as_of")
    for h in zone_history(conn, entry["symbol"], entry["zone_id"]):
        t = _dt(h["as_of"], "scan as_of")
        if h["trade_type"] != srow["trade_type"] or not (_before(scan_t, t, "journal_add") and not _before(rec, t, "journal_add")):
            continue
        if h["presence"] != "CANDIDATE" or h["candidate_status"] in JOURNAL_REFUSED_STATUSES:
            raise JournalRefused("ZONE_NO_LONGER_CANDIDATE: the stored scan at %s shows %s %s as %s (%s); "
                                 "journal from the latest scan at or before recorded_at"
                                 % (h["as_of"], entry["symbol"], entry["zone_id"], h["presence"],
                                    h["candidate_status"] or h["symbol_status"]))
    with conn:
        cur = conn.execute(
            "INSERT INTO journal_entries (scan_key, symbol, zone_id, trade_type, direction, candidate_status, "
            "manual_review_resolution, candidate_levels, planned_entry, planned_stop, planned_target, quantity, "
            "alert_note, checklist, recorded_at) VALUES (?, ?, ?, ?, 'LONG', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (entry["scan_key"], entry["symbol"], entry["zone_id"], srow["trade_type"], status, resolution, c["levels"],
             entry_p, stop, target, qty, note, _j(checklist), entry["recorded_at"]))
        conn.execute("INSERT INTO journal_events VALUES (?, 1, ?, ?, NULL, ?, NULL)",
                     (cur.lastrowid, PLANNED, entry["recorded_at"], stop))
    return cur.lastrowid


def _state(events):
    """(state, current stop, fill price, locked stop) from events in order."""
    state, stop, fill, locked = "PLANNED", None, None, None
    for e in events:
        if e["stop_level"] is not None:
            stop = e["stop_level"]
        k = e["kind"]
        if k == TRIGGERED:
            state, fill, locked = "OPEN", e["price"], stop
        elif k in EXITS:
            state = "CLOSED"
        elif k in (CANCELLED, EXPIRED):
            state = k
    return state, stop, fill, locked


def journal_events(conn, entry_id):
    return [dict(r) for r in conn.execute("SELECT * FROM journal_events WHERE entry_id = ? ORDER BY seq", (entry_id,))]


def journal_event(conn, entry_id, kind, at, price=None, note=None, stop_level=None):
    """Append one lifecycle event. Returns its seq."""
    if conn.execute("SELECT 1 FROM journal_entries WHERE entry_id = ?", (entry_id,)).fetchone() is None:
        raise StoreError("unknown journal entry %s" % entry_id)
    if kind not in EVENT_KINDS:
        raise StoreError("event kind %r is not one of %s (there is no add-to-position kind: RB 2140)"
                         % (kind, ", ".join(EVENT_KINDS)))
    events = journal_events(conn, entry_id)
    t = _dt(at, "at")
    if _before(t, _dt(events[-1]["at"], "previous event"), "journal_event"):
        raise JournalRefused("events must be chronological: %s is before the previous event at %s"
                             % (at, events[-1]["at"]))
    state, stop, _, locked = _state(events)
    if kind == TRIGGERED and state == "OPEN":
        raise JournalRefused("entry already TRIGGERED: adding to a position is not recorded (RB 2140 never average down)")
    if kind not in ALLOWED[state]:
        raise JournalRefused("%s is not allowed after the entry is %s" % (kind, state))
    if price is not None:
        price = _num(price, "price")
    if kind in PRICED and price is None:
        raise StoreError("%s needs a price" % kind)
    if stop_level is not None:
        stop_level = _num(stop_level, "stop_level")
        if state != "PLANNED" and stop_level != (locked if locked is not None else stop):
            raise JournalRefused("stop-loss is permanently locked once the trade triggers (RB 2139)")
        if state == "PLANNED" and kind not in (PLANNED, TRIGGERED):
            raise StoreError("a stop revision before the trigger is a PLANNED event")
    if note is not None and not isinstance(note, str):
        raise StoreError("note must be text")
    if kind == TRIGGERED:                      # RB 2392, 2408: a ceiling of 10 trades per month
        t = _dt(at, "at")
        taken = 0
        for r in conn.execute("SELECT at FROM journal_events WHERE kind = ?", (TRIGGERED,)):
            u = _dt(r["at"], "TRIGGERED at")
            taken += (u.year, u.month) == (t.year, t.month)
        if taken >= MONTHLY_TRADE_CEILING:
            raise JournalRefused("%d trades already TRIGGERED in %04d-%02d: 10 is the monthly maximum (RB 2392, 2408)"
                                 % (taken, t.year, t.month))
    seq = events[-1]["seq"] + 1
    with conn:
        conn.execute("INSERT INTO journal_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (entry_id, seq, kind, at, price, stop_level, note))
    return seq


def _month(text):
    if not re.match(r"^\d{4}-\d{2}$", text or ""):
        raise StoreError("month must be YYYY-MM")
    y, mo = int(text[:4]), int(text[5:])
    if not 1 <= mo <= 12:
        raise StoreError("month must be YYYY-MM")
    return y, mo


def journal_summary(conn, month):
    """Trades taken (TRIGGERED) in month against the RB 2392 ceiling, and arithmetic of the
    closed ones (RB 3762-3774). Metrics needing data the journal does not hold are listed."""
    y, mo = _month(month)
    trades = []
    for e in conn.execute("SELECT * FROM journal_entries ORDER BY entry_id"):
        events = journal_events(conn, e["entry_id"])
        trig = [x for x in events if x["kind"] == TRIGGERED]
        if not trig:
            continue
        t = _dt(trig[0]["at"], "TRIGGERED at")
        if (t.year, t.month) != (y, mo):
            continue
        state, _, fill, locked = _state(events)
        exits = [x for x in events if x["kind"] in EXITS]
        rec = {"entry_id": e["entry_id"], "symbol": e["symbol"], "zone_id": e["zone_id"],
               "candidate_status": e["candidate_status"], "state": state, "fill_price": fill, "locked_stop": locked,
               "exit_kind": None, "exit_price": None, "r_multiple": None, "gross_pnl": None,
               "checklist_false": sorted(k for k, v in json.loads(e["checklist"]).items() if v is False),
               "zone_invalidated": any(x["kind"] == ZONE_INVALIDATED for x in events)}
        if exits:
            x = exits[0]
            rec["exit_kind"], rec["exit_price"] = x["kind"], x["price"]
            risk = fill - locked
            rec["r_multiple"] = round((x["price"] - fill) / risk, 4) if risk > 0 else None
            rec["gross_pnl"] = round((x["price"] - fill) * e["quantity"], 2)
        trades.append(rec)
    closed = [t for t in trades if t["exit_kind"]]
    rs = [t["r_multiple"] for t in closed if t["r_multiple"] is not None]
    won = sum(t["gross_pnl"] for t in closed if t["gross_pnl"] > 0)
    lost = -sum(t["gross_pnl"] for t in closed if t["gross_pnl"] < 0)
    wins = sum(1 for t in closed if t["gross_pnl"] > 0)
    return {
        "month": month, "trades_taken": len(trades), "ceiling": MONTHLY_TRADE_CEILING,
        "over_ceiling": len(trades) > MONTHLY_TRADE_CEILING, "ceiling_source": "RB 2392",
        "closed": len(closed), "open": len(trades) - len(closed), "wins": wins,
        "losses": sum(1 for t in closed if t["gross_pnl"] < 0),
        "win_rate_pct": round(100.0 * wins / len(closed), 2) if closed else None,
        "r_multiples": rs, "average_r": round(sum(rs) / len(rs), 4) if rs else None,
        "gross_pnl": round(won - lost, 2) if closed else None,
        "profit_factor": round(won / lost, 4) if lost > 0 else None,
        "checklist_exceptions": sum(1 for t in trades if t["checklist_false"]),
        "not_computed": ["ROI_PCT: starting capital is not recorded", "RULE_COMPLIANCE_RATE: rules-followed and "
                         "remark columns (RB 3739-3740) are not recorded", "COSTS: not recorded, P&L is gross"],
        "trades": trades, "note": JOURNAL_NOTE,
    }


# --- CLI ------------------------------------------------------------------------------
def _run(fn):
    try:
        out = fn()
    except (JournalRefused, MigrationDriftError) as e:
        print("refused: %s" % e, file=sys.stderr)
        return 1
    except (StoreError, OSError, ValueError, TypeError, sqlite3.Error) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    print(json.dumps(out, sort_keys=True, indent=1))
    return 0


def _with_store(path, fn):
    def go():
        conn = open_store(path)
        try:
            return fn(conn)
        finally:
            conn.close()
    return go


def _read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def cmd_import(args):
    def f(conn):
        status, key = import_scan(conn, _read_json(args.scan))
        return {"result": status, "scan_key": key, "counts": status_counts(conn, key)}
    return _run(_with_store(args.db, f))


def cmd_zone_history(args):
    return _run(_with_store(args.db, lambda conn: zone_history(conn, args.symbol, args.zone)))


def cmd_backup(args):
    return _run(_with_store(args.db, lambda conn: {"backup": backup(conn, args.dest)}))


def cmd_journal_add(args):
    return _run(_with_store(args.db, lambda conn: {"entry_id": journal_add(conn, _read_json(args.entry))}))


def cmd_journal_event(args):
    return _run(_with_store(args.db, lambda conn: {"entry_id": args.entry_id, "seq": journal_event(
        conn, args.entry_id, args.kind, args.at, price=args.price, note=args.note, stop_level=args.stop)}))


def cmd_journal_summary(args):
    return _run(_with_store(args.db, lambda conn: journal_summary(conn, args.month)))


def add_commands(subparsers):
    p = subparsers.add_parser("store-import", help="archive a scan.json in the local SQLite store (idempotent)")
    p.add_argument("--db", required=True)
    p.add_argument("--scan", required=True, help="scan.json written by the scan command")
    p.set_defaults(func=cmd_import)
    p = subparsers.add_parser("store-zone-history", help="one zone's status across stored scans")
    p.add_argument("--db", required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--zone", required=True, help="zone_id as printed in candidates.csv")
    p.set_defaults(func=cmd_zone_history)
    p = subparsers.add_parser("store-backup", help="copy the store with the SQLite backup API (never overwrites)")
    p.add_argument("--db", required=True)
    p.add_argument("--dest", required=True)
    p.set_defaults(func=cmd_backup)
    p = subparsers.add_parser("journal-add", help="record a paper-trade plan on a stored candidate (no execution)")
    p.add_argument("--db", required=True)
    p.add_argument("--entry", required=True, help="entry JSON: " + ", ".join(ENTRY_FIELDS))
    p.set_defaults(func=cmd_journal_add)
    p = subparsers.add_parser("journal-event", help="append a lifecycle event to a journal entry")
    p.add_argument("--db", required=True)
    p.add_argument("--entry-id", required=True, type=int)
    p.add_argument("--kind", required=True, choices=EVENT_KINDS)
    p.add_argument("--at", required=True, help="ISO time of the event (no clock is read)")
    p.add_argument("--price", type=float)
    p.add_argument("--stop", type=float, help="stop revision (PLANNED only; locked after TRIGGERED, RB 2139)")
    p.add_argument("--note")
    p.set_defaults(func=cmd_journal_event)
    p = subparsers.add_parser("journal-summary", help="monthly journal arithmetic and the 10-trade ceiling")
    p.add_argument("--db", required=True)
    p.add_argument("--month", required=True, help="YYYY-MM")
    p.set_defaults(func=cmd_journal_summary)
