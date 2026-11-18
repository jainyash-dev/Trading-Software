"""Optional local research store (SQLite, standard library) and paper-trade journal.

The JSON/CSV reports (reports.py) stay the primary outputs. The store keeps an archive of
scans exactly as they were written (scan.json = reports.to_json(result)) so that a zone can
be followed across scans; it never computes a gate, a status or a level and is never a
second source of trading decisions (spec 6.4 single pathway; D3; master prompt 6.4).

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
    profitability. With no charge rows, P&L stays gross. Itemised charges are stored only
    when the owner enters them or supplies a dated schedule (nse/research/charges.py).
"""

import datetime
import hashlib
import json
import math
import os
import re
import sqlite3
import sys

from nse.research import charges, journal_taxonomy, levels, models as m

IMPORTED = "IMPORTED"
ALREADY_PRESENT = "ALREADY_PRESENT"
MONTHLY_TRADE_CEILING = m.OWNER_MONTHLY_TRADE_CAP  # RB 2392, 2408; D46

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
JOURNAL_NOTE = ("Journal arithmetic over the owner's own manual records (RB 3762-3774). "
                "JOURNAL_DESCRIPTIVE only. Not validation, not evidence of profitability. "
                "Gross P&L is always gross. Net P&L is set only when charge completeness supports it "
                "(ACTUAL or ESTIMATED). Absent charges stay ABSENT and are never treated as zero.")


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

# v2 (2026-11-08, ED-3): the owner's record that a planned order was actually submitted
# (manually, e.g. a Kite GTT; nothing here sends anything). One row per entry, append-only.
_V2 = """CREATE TABLE journal_orders (
  entry_id INTEGER NOT NULL PRIMARY KEY REFERENCES journal_entries(entry_id),
  submitted_at TEXT NOT NULL,
  order_ref TEXT,
  note TEXT
);
""" + _append_only("journal_orders")

# v3 (2026-11-08, QA): INSERT OR REPLACE deletes the conflicting row without firing the
# delete trigger, so a second submission row is refused before conflict resolution. Entries
# that existed before submissions could be recorded are snapshotted: for them "CANCELLED and
# no submission row" does not show the order was never submitted (ED-3).
_V3 = """CREATE TRIGGER journal_orders_one_row BEFORE INSERT ON journal_orders
  WHEN EXISTS (SELECT 1 FROM journal_orders WHERE entry_id = NEW.entry_id)
  BEGIN SELECT RAISE(ABORT, 'journal_orders has one row per entry and is append-only'); END;
CREATE TABLE journal_legacy_entries (entry_id INTEGER NOT NULL PRIMARY KEY);
INSERT INTO journal_legacy_entries (entry_id)
  SELECT entry_id FROM journal_entries WHERE entry_id NOT IN (SELECT entry_id FROM journal_orders);
""" + _append_only("journal_legacy_entries")

# v4 (P1): execution prints and itemised charges are their own rows. A second TRIGGERED
# remains refused (RB 2140). Several prints of one submitted order are not a second order.
# Idempotency keys make a retry of the same body return the first result.
_V4 = """CREATE TABLE journal_executions (
  entry_id INTEGER NOT NULL REFERENCES journal_entries(entry_id),
  print_key TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('ENTRY', 'EXIT')),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  price REAL NOT NULL,
  at TEXT NOT NULL,
  note TEXT,
  PRIMARY KEY (entry_id, print_key)
);
CREATE TABLE journal_charges (
  entry_id INTEGER NOT NULL REFERENCES journal_entries(entry_id),
  charge_key TEXT NOT NULL,
  component TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
  amount_paise INTEGER NOT NULL CHECK (amount_paise >= 0),
  basis TEXT NOT NULL,
  source TEXT NOT NULL,
  estimated INTEGER NOT NULL CHECK (estimated IN (0, 1)),
  at TEXT NOT NULL,
  PRIMARY KEY (entry_id, charge_key)
);
CREATE TABLE journal_idempotency (
  request_key TEXT NOT NULL PRIMARY KEY,
  operation TEXT NOT NULL,
  entry_id INTEGER,
  result_json TEXT NOT NULL
);
""" + "".join(_append_only(t) for t in ("journal_executions", "journal_charges", "journal_idempotency"))

# v5 (P6): review notes, Rulebook-aligned classifications, attachment metadata.
# File bytes live outside SQLite under the platform data directory; this table is the
# auditable reference. Review rows are append-only and never rewrite execution facts.
_V5 = """CREATE TABLE journal_notes (
  entry_id INTEGER NOT NULL REFERENCES journal_entries(entry_id),
  note_key TEXT NOT NULL,
  at TEXT NOT NULL,
  kind TEXT NOT NULL,
  body TEXT NOT NULL,
  actor TEXT NOT NULL,
  PRIMARY KEY (entry_id, note_key)
);
CREATE TABLE journal_reviews (
  entry_id INTEGER NOT NULL REFERENCES journal_entries(entry_id),
  review_key TEXT NOT NULL,
  at TEXT NOT NULL,
  review_status TEXT NOT NULL,
  outcome_class TEXT NOT NULL,
  mistake_category TEXT NOT NULL,
  taxonomy_version TEXT NOT NULL,
  setup_label TEXT,
  rule_refs TEXT,
  note TEXT,
  actor TEXT NOT NULL,
  PRIMARY KEY (entry_id, review_key)
);
CREATE TABLE journal_attachments (
  entry_id INTEGER NOT NULL REFERENCES journal_entries(entry_id),
  attachment_id TEXT NOT NULL,
  at TEXT NOT NULL,
  filename TEXT NOT NULL,
  content_type TEXT NOT NULL,
  size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
  sha256 TEXT NOT NULL,
  storage_name TEXT NOT NULL,
  note TEXT,
  missing INTEGER NOT NULL CHECK (missing IN (0, 1)),
  PRIMARY KEY (entry_id, attachment_id)
);
""" + "".join(_append_only(t) for t in ("journal_notes", "journal_reviews", "journal_attachments"))

# ordered (version, name, sql); append new versions, never edit a released one
MIGRATIONS = (
    (1, "v1_scans_candidates_journal", _V1),
    (2, "v2_journal_order_submissions", _V2),
    (3, "v3_journal_order_guard_and_legacy_entries", _V3),
    (4, "v4_journal_executions_charges", _V4),
    (5, "v5_journal_notes_reviews_attachments", _V5),
)

ATTACHMENT_CONTENT_TYPES = ("image/png", "image/jpeg", "image/webp", "image/gif")
ATTACHMENT_MAX_BYTES = 5 * 1024 * 1024
_SAFE_FILENAME = re.compile(r"^[A-Za-z0-9._-]{1,180}$")

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


def _readonly_uri(path):
    """A SQLite read-only file URI. The path is percent-encoded without a network library."""
    parts = []
    for byte in os.path.abspath(path).encode("utf-8"):
        char = chr(byte)
        if char.isascii() and (char.isalnum() or char in "/-._~"):
            parts.append(char)
        else:
            parts.append("%%%02X" % byte)
    return "file:%s?mode=ro" % "".join(parts)


def open_readonly(path):
    """Open an existing store for queries only. Does not create the file or apply migrations.

    A research read must not upgrade a journal as a side effect. If the schema is older
    than this code, the query fails and the caller keeps the file unchanged.
    """
    if not os.path.isfile(path):
        raise StoreError("journal database does not exist: %s" % path)
    uri = _readonly_uri(path)
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='journal_entries'").fetchone() is None:
        conn.close()
        raise StoreError("journal tables are missing in %s" % path)
    return conn


def open_store(path, migrations=None):
    """Create or open the SQLite store at path and apply pending migrations."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 8000")
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
    os.chmod(dest_path, 0o600)
    return dest_path


# --- paper-trade journal --------------------------------------------------------------
def _num(v, what):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise StoreError("%s must be a finite number" % what)
    return float(v)


class _Immediate:
    """BEGIN IMMEDIATE, then commit, or roll back when the body raises.

    The reserved lock is taken before a monthly count or a zone reservation is
    decided. A deferred read outside that lock is how two connections both
    committed (D42, ED-3).
    """

    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        self.conn.execute("PRAGMA busy_timeout = 8000")
        if self.conn.in_transaction:
            raise StoreError("journal write started inside an open transaction")
        self.conn.execute("BEGIN IMMEDIATE")
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.conn.commit()
        elif self.conn.in_transaction:
            self.conn.rollback()
        return False


def _request_key(value):
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise StoreError("request_key must be 1..200 characters")
    return value.strip()


def _has_table(conn, name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)).fetchone() is not None


def _stored_request(conn, key, operation, fingerprint):
    key = _request_key(key)
    if key is None or not _has_table(conn, "journal_idempotency"):
        return None
    row = conn.execute(
        "SELECT operation, result_json FROM journal_idempotency WHERE request_key = ?", (key,)).fetchone()
    if row is None:
        return None
    if row["operation"] != operation:
        raise JournalRefused("IDEMPOTENCY_CONFLICT: request_key was used for %s" % row["operation"])
    stored = json.loads(row["result_json"])
    if stored.get("fingerprint") != fingerprint:
        raise JournalRefused("IDEMPOTENCY_CONFLICT: request_key was used for a different body")
    return stored


def _remember(conn, key, operation, result):
    key = _request_key(key)
    if key is None or not _has_table(conn, "journal_idempotency"):
        return
    conn.execute(
        "INSERT INTO journal_idempotency (request_key, operation, entry_id, result_json) VALUES (?, ?, ?, ?)",
        (key, operation, result.get("entry_id"), _j(result)))


def journal_add(conn, entry, request_key=None):
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
    # The superseded-scan check and the one-order reservation commit together. A plan that
    # was never submitted and was CANCELLED does not hold the zone (ED-3). A permanent
    # unique index would keep that cancelled plan from releasing the zone, so the rule
    # stays in this transaction instead.
    fingerprint = _j({
        "scan_key": entry["scan_key"], "symbol": entry["symbol"], "zone_id": entry["zone_id"],
        "planned_entry": entry_p, "planned_stop": stop, "planned_target": target, "quantity": qty,
        "alert_note": note, "checklist": checklist, "recorded_at": entry["recorded_at"],
        "manual_review_resolution": resolution,
    })
    with _Immediate(conn):
        replay = _stored_request(conn, request_key, "journal_add", fingerprint)
        if replay is not None:
            return replay["entry_id"]
        _refuse_if_superseded(conn, entry["symbol"], entry["zone_id"], srow["trade_type"],
                              _dt(srow["as_of"], "scan as_of"), rec,
                              "journal from the latest scan at or before recorded_at")
        for prior in conn.execute(
                "SELECT entry_id FROM journal_entries WHERE symbol = ? AND zone_id = ? AND trade_type = ?",
                (entry["symbol"], entry["zone_id"], srow["trade_type"])):
            held = _holds_zone(conn, prior["entry_id"])
            if held:
                raise JournalRefused("ONE_ORDER_PER_ZONE: journal entry %d on %s %s: %s"
                                     % (prior["entry_id"], entry["symbol"], entry["zone_id"], held))
        cur = conn.execute(
            "INSERT INTO journal_entries (scan_key, symbol, zone_id, trade_type, direction, candidate_status, "
            "manual_review_resolution, candidate_levels, planned_entry, planned_stop, planned_target, quantity, "
            "alert_note, checklist, recorded_at) VALUES (?, ?, ?, ?, 'LONG', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (entry["scan_key"], entry["symbol"], entry["zone_id"], srow["trade_type"], status, resolution, c["levels"],
             entry_p, stop, target, qty, note, _j(checklist), entry["recorded_at"]))
        conn.execute("INSERT INTO journal_events VALUES (?, 1, ?, ?, NULL, ?, NULL)",
                     (cur.lastrowid, PLANNED, entry["recorded_at"], stop))
        _remember(conn, request_key, "journal_add", {"entry_id": cur.lastrowid, "fingerprint": fingerprint})
        entry_id = cur.lastrowid
    return entry_id


def _refuse_if_superseded(conn, symbol, zone_id, trade_type, scan_t, until, advice):
    """JournalRefused when a stored scan with as_of in (scan_t, until] no longer lists the
    zone as a candidate in an allowed status (D3, R4; RB 2530-2538 before a trigger)."""
    for h in zone_history(conn, symbol, zone_id):
        t = _dt(h["as_of"], "scan as_of")
        if h["trade_type"] != trade_type or not (_before(scan_t, t, "journal") and not _before(until, t, "journal")):
            continue
        if h["presence"] != "CANDIDATE" or h["candidate_status"] in JOURNAL_REFUSED_STATUSES:
            raise JournalRefused("ZONE_NO_LONGER_CANDIDATE: the stored scan at %s shows %s %s as %s (%s); %s"
                                 % (h["as_of"], symbol, zone_id, h["presence"],
                                    h["candidate_status"] or h["symbol_status"], advice))


def _execution_rows(conn, entry_id):
    if not _has_table(conn, "journal_executions"):
        return []
    return [dict(r) for r in conn.execute(
        "SELECT * FROM journal_executions WHERE entry_id = ? ORDER BY rowid", (entry_id,))]


def _charge_rows(conn, entry_id):
    if not _has_table(conn, "journal_charges"):
        return []
    return [dict(r) for r in conn.execute(
        "SELECT * FROM journal_charges WHERE entry_id = ? ORDER BY rowid", (entry_id,))]


def _visible(rows, t, what):
    if t is None:
        return list(rows)
    return [row for row in rows if not _before(t, _dt(row["at"], what), what)]


def position_book(conn, entry_id, planned_qty, events, t=None):
    """Requested, executed and still-open quantity.

    A journal with no execution rows keeps the old meaning: TRIGGERED fills the whole
    planned quantity. Execution rows are the prints. Quantity that was not printed is
    not a fill. An exit at exactly t still leaves the position open, matching the
    previous open-position count. Unrealised P&L is UNAVAILABLE: there is no mark price.
    """
    visible_events = _visible(events, t, "event at")
    triggers = [event for event in visible_events if event["kind"] == TRIGGERED]
    exits = [event for event in visible_events if event["kind"] in EXITS]
    prints = _visible(_execution_rows(conn, entry_id), t, "execution at")
    entry_prints = [row for row in prints if row["side"] == "ENTRY"]
    if t is None:
        exit_prints = [row for row in prints if row["side"] == "EXIT"]
        exit_closed = bool(exits)
    else:
        exit_prints = [row for row in prints if row["side"] == "EXIT"
                       and _before(_dt(row["at"], "execution at"), t, "position")]
        exit_closed = bool(exits) and _before(_dt(exits[0]["at"], "exit at"), t, "position")
    exit_qty = sum(row["quantity"] for row in exit_prints)
    exit_value = sum(row["quantity"] * row["price"] for row in exit_prints)
    if entry_prints:
        entry_qty = sum(row["quantity"] for row in entry_prints)
        entry_value = sum(row["quantity"] * row["price"] for row in entry_prints)
        source = "prints"
    elif triggers:
        entry_qty = planned_qty
        entry_value = planned_qty * (triggers[0]["price"] or 0.0)
        source = "legacy_full_fill"
        if exit_closed:
            exit_qty = planned_qty
            exit_value = planned_qty * (exits[0]["price"] or 0.0)
        elif not exit_prints:
            exit_qty = 0
            exit_value = 0.0
    else:
        entry_qty = 0
        entry_value = 0.0
        exit_qty = 0
        exit_value = 0.0
        source = "unfilled"
    if source == "prints" and exit_closed and exits and exits[0]["price"] is not None:
        remainder = entry_qty - exit_qty
        if remainder > 0:
            exit_value += remainder * exits[0]["price"]
            exit_qty = entry_qty
    if exit_qty > entry_qty:
        exit_qty = entry_qty
    open_qty = 0 if source == "legacy_full_fill" and exit_closed else entry_qty - exit_qty
    if source == "prints":
        unfilled = max(planned_qty - entry_qty, 0)
    elif source == "unfilled":
        unfilled = planned_qty
    else:
        unfilled = 0
    realised = None
    if entry_qty and exit_qty:
        realised = round(exit_value - (entry_value / entry_qty) * exit_qty, 2)
    return {
        "source": source,
        "requested_quantity": planned_qty,
        "executed_entry_quantity": entry_qty,
        "executed_exit_quantity": exit_qty,
        "open_quantity": open_qty,
        "unfilled_quantity": unfilled,
        "average_entry_price": round(entry_value / entry_qty, 4) if entry_qty else None,
        "average_exit_price": round(exit_value / exit_qty, 4) if exit_qty else None,
        "realised_pnl": realised,
        "unrealised": "UNAVAILABLE",
        "counts_as_open": bool(triggers) and open_qty > 0,
        "triggered": bool(triggers),
    }


def _open_positions(conn, t):
    """Open positions at t. Closing one frees a slot and does not refund the monthly cap.

    An exit at t still counts as open. A partial fill counts as one position while any
    printed quantity remains. Unfilled planned quantity does not.
    """
    n = 0
    for entry in conn.execute("SELECT entry_id, quantity FROM journal_entries"):
        book = position_book(conn, entry["entry_id"], entry["quantity"],
                             journal_events(conn, entry["entry_id"]), t)
        if book["counts_as_open"]:
            n += 1
    return n


def _peak_open_from(conn, start):
    """Highest open-position count at `start` or any later TRIGGERED/EXIT time.

    A new fill at `start` stays open for every later moment until it exits. Counting
    only at `start` would miss later-dated opens and let a backdated fill exceed D42.
    """
    moments = [start]
    kinds = (TRIGGERED,) + tuple(EXITS)
    for row in conn.execute(
            "SELECT at FROM journal_events WHERE kind IN (%s)" % ",".join("?" * len(kinds)),
            kinds):
        moment = _dt(row["at"], "event at")
        if not _before(moment, start, "peak open"):
            moments.append(moment)
    return max(_open_positions(conn, moment) for moment in moments)


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


def order_submission(conn, entry_id):
    r = conn.execute("SELECT * FROM journal_orders WHERE entry_id = ?", (entry_id,)).fetchone()
    return dict(r) if r else None


def _zone_allowance(conn, entry_id, events, at):
    """Why this entry holds its zone's one-order allowance, or None (ED-3).

    at is None when journal_add is enforcing the rule against every stored event.
    A timestamp restricts the read to events at or before that time, so a later
    cancellation or submission cannot change an earlier research snapshot (D44).
    """
    if at is not None:
        events = [e for e in events if not _before(at, _dt(e["at"], "event at"), "zone allowance")]
    if not events:
        return None
    state = _state(events)[0]
    sub = order_submission(conn, entry_id)
    submitted = sub is not None and (at is None or not _before(
        at, _dt(sub["submitted_at"], "submitted_at"), "zone allowance"))
    if submitted:
        return "an order was submitted at %s (now %s); it keeps the allowance" % (sub["submitted_at"], state)
    if state in ("OPEN", "CLOSED"):
        return "the order triggered (now %s)" % state
    if state == EXPIRED:
        # expiry belongs to a live order; a plan never submitted is recorded as CANCELLED
        return "EXPIRED (expiry implies a live order; record CANCELLED for a plan never submitted)"
    if state == "PLANNED":
        return "a plan is still pending on the zone"
    if conn.execute("SELECT 1 FROM journal_legacy_entries WHERE entry_id = ?", (entry_id,)).fetchone():
        return ("CANCELLED before order submissions were recorded (pre-v2 journal): whether an order was "
                "submitted is unknown, so the zone stays used")
    return None


def _holds_zone(conn, entry_id):
    """Why an earlier entry still holds its zone's one-order allowance, or None (ED-3)."""
    return _zone_allowance(conn, entry_id, journal_events(conn, entry_id), None)


def journal_order_submitted(conn, entry_id, at, order_ref=None, note=None, request_key=None):
    """Record that the owner actually submitted the planned order outside this system (manual
    Kite / GTT, B12; nothing is sent). From then on the zone's one-order allowance is used,
    even if the order is later cancelled or expires (ED-3)."""
    for v, what in ((order_ref, "order_ref"), (note, "note")):
        if v is not None and not isinstance(v, str):
            raise StoreError("%s must be text" % what)
    _dt(at, "at")
    fingerprint = _j({"entry_id": entry_id, "at": at, "order_ref": order_ref, "note": note})
    with _Immediate(conn):
        if conn.execute("SELECT 1 FROM journal_entries WHERE entry_id = ?", (entry_id,)).fetchone() is None:
            raise StoreError("unknown journal entry %s" % entry_id)
        replay = _stored_request(conn, request_key, "journal_order_submitted", fingerprint)
        if replay is not None:
            return replay["entry_id"]
        if order_submission(conn, entry_id):
            raise JournalRefused("entry %d already has a submitted order" % entry_id)
        events = journal_events(conn, entry_id)
        state = _state(events)[0]
        if state != "PLANNED":
            raise JournalRefused("an order can only be submitted while the entry is PLANNED (it is %s)" % state)
        t = _dt(at, "at")
        if _before(t, _dt(events[-1]["at"], "previous event"), "journal_order_submitted"):
            raise JournalRefused("submitted_at %s is before the previous event at %s" % (at, events[-1]["at"]))
        conn.execute("INSERT INTO journal_orders VALUES (?, ?, ?, ?)", (entry_id, at, order_ref, note))
        _remember(conn, request_key, "journal_order_submitted", {"entry_id": entry_id, "fingerprint": fingerprint})
    return entry_id


def journal_events(conn, entry_id):
    return [dict(r) for r in conn.execute("SELECT * FROM journal_events WHERE entry_id = ? ORDER BY seq", (entry_id,))]


ENTRY_EXPIRY_SESSIONS = m.OWNER_ENTRY_EXPIRY_SESSIONS  # D42: pending orders expire after 10 verified sessions


def verified_sessions_after(calendar, submitted_at, fill_at):
    """Verified trading sessions strictly after the submission date, through the fill date.

    The fill date counts when it is a trading session. An unresolved calendar date raises
    the calendar's own error and is not classified here.
    """
    start = _dt(submitted_at, "submitted_at")
    end = _dt(fill_at, "TRIGGERED at")
    day = start.date() + datetime.timedelta(days=1)
    last = end.date()
    count = 0
    while day <= last:
        if calendar.is_trading_day(day):
            count += 1
        day += datetime.timedelta(days=1)
    return count


def journal_event(conn, entry_id, kind, at, price=None, note=None, stop_level=None, *,
                  calendar=None, revalidated=False, request_key=None):
    """Append one lifecycle event. Returns its seq.

    A repeated call with the same body, or the same request_key, returns the original
    seq and does not insert another row. A later TRIGGERED on an open trade is still
    refused (RB 2140). The monthly count and the insert commit together (D42).
    """
    if kind not in EVENT_KINDS:
        raise StoreError("event kind %r is not one of %s (there is no add-to-position kind: RB 2140)"
                         % (kind, ", ".join(EVENT_KINDS)))
    if price is not None:
        price = _num(price, "price")
    if kind in PRICED and price is None:
        raise StoreError("%s needs a price" % kind)
    if stop_level is not None:
        stop_level = _num(stop_level, "stop_level")
    if note is not None and not isinstance(note, str):
        raise StoreError("note must be text")
    t = _dt(at, "at")
    fingerprint = _j({"entry_id": entry_id, "kind": kind, "at": at, "price": price,
                      "note": note, "stop_level": stop_level})
    with _Immediate(conn):
        if conn.execute("SELECT 1 FROM journal_entries WHERE entry_id = ?", (entry_id,)).fetchone() is None:
            raise StoreError("unknown journal entry %s" % entry_id)
        replay = _stored_request(conn, request_key, "journal_event", fingerprint)
        if replay is not None:
            return replay["seq"]
        events = journal_events(conn, entry_id)
        same = _matching_event(events, kind, at, price, note, stop_level)
        if same is not None:
            _remember(conn, request_key, "journal_event",
                      {"entry_id": entry_id, "seq": same, "fingerprint": fingerprint})
            return same
        if _before(t, _dt(events[-1]["at"], "previous event"), "journal_event"):
            raise JournalRefused("events must be chronological: %s is before the previous event at %s"
                                 % (at, events[-1]["at"]))
        sub = order_submission(conn, entry_id)
        if sub and _before(t, _dt(sub["submitted_at"], "submitted_at"), "journal_event"):
            raise JournalRefused("events must be chronological: %s is before the order's submission at %s"
                                 % (at, sub["submitted_at"]))
        state, stop, _, locked = _state(events)
        if kind == TRIGGERED and state == "OPEN":
            raise JournalRefused("entry already TRIGGERED: adding to a position is not recorded "
                                 "(RB 2140 never average down)")
        if kind not in ALLOWED[state]:
            raise JournalRefused("%s is not allowed after the entry is %s" % (kind, state))
        if stop_level is not None:
            if state != "PLANNED" and stop_level != (locked if locked is not None else stop):
                raise JournalRefused("stop-loss is permanently locked once the trade triggers (RB 2139)")
            if state == "PLANNED" and kind not in (PLANNED, TRIGGERED):
                raise StoreError("a stop revision before the trigger is a PLANNED event")
        if kind == TRIGGERED:
            _refuse_new_trigger(conn, entry_id, t, at, calendar, revalidated, note)
        seq = events[-1]["seq"] + 1
        conn.execute("INSERT INTO journal_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (entry_id, seq, kind, at, price, stop_level, note))
        _remember(conn, request_key, "journal_event",
                  {"entry_id": entry_id, "seq": seq, "fingerprint": fingerprint})
    return seq


def _same_number(left, right):
    if left is None or right is None:
        return left is None and right is None
    return float(left) == float(right)


def _matching_event(events, kind, at, price, note, stop_level):
    for event in events:
        if event["kind"] != kind or event["at"] != at or event["note"] != note:
            continue
        if _same_number(event["price"], price) and _same_number(event["stop_level"], stop_level):
            return event["seq"]
    return None


def _refuse_new_trigger(conn, entry_id, t, at, calendar, revalidated, note):
    """Monthly cap, open-position cap, expiry and a superseded setup. Caller holds the write lock."""
    month = m.ist_month(t)
    taken = 0
    for row in conn.execute("SELECT at FROM journal_events WHERE kind = ?", (TRIGGERED,)):
        taken += m.ist_month(_dt(row["at"], "TRIGGERED at")) == month
    if taken >= MONTHLY_TRADE_CEILING:
        raise JournalRefused("%d trades already TRIGGERED in IST month %04d-%02d: 10 is the monthly maximum "
                             "(RB 2392, 2408; D46)" % ((taken,) + month))
    _refuse_expired_fill(conn, entry_id, t, calendar, revalidated, note)
    # A fill at t remains open for every later moment until it exits. Refuse when any
    # of those moments is already at the open-position cap (D42).
    open_peak = _peak_open_from(conn, t)
    if open_peak >= m.OWNER_MAX_OPEN_POSITIONS:
        raise JournalRefused("MAX_OPEN_POSITIONS: %d positions are already open at or after %s; "
                             "the owner limit is %d (D42)"
                             % (open_peak, at, m.OWNER_MAX_OPEN_POSITIONS))
    ent = conn.execute("SELECT j.symbol, j.zone_id, j.trade_type, s.as_of FROM journal_entries j "
                       "JOIN scans s ON s.scan_key = j.scan_key WHERE j.entry_id = ?", (entry_id,)).fetchone()
    local = t.astimezone(m.IST) if t.tzinfo is not None and t.utcoffset() is not None else t
    day_start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    _refuse_if_superseded(conn, ent["symbol"], ent["zone_id"], ent["trade_type"],
                          _dt(ent["as_of"], "scan as_of"),
                          day_start - datetime.timedelta(microseconds=1),
                          "the setup was invalid before the fill date; if no order was live, record CANCELLED "
                          "(RB 2530-2538)")


def _refuse_expired_fill(conn, entry_id, fill_at, calendar, revalidated, note):
    """D42 / FR-6.9. A fill after 10 verified sessions needs an explicit revalidation note.

    After submission, a calendar is required. Missing calendar never extends the order.
    EXPIRED remains a separate event the owner can record. This function does not contact
    a broker.
    """
    submission = order_submission(conn, entry_id)
    if submission is None:
        return
    if calendar is None:
        raise JournalRefused("ORDER_EXPIRY_UNRESOLVED: a trading calendar is required to count "
                             "verified sessions after submission (D42)")
    try:
        sessions = verified_sessions_after(calendar, submission["submitted_at"], fill_at)
    except Exception as exc:
        raise JournalRefused("ORDER_EXPIRY_UNRESOLVED: the calendar could not classify the sessions "
                             "between submission and fill (%s)" % exc)
    if sessions <= ENTRY_EXPIRY_SESSIONS:
        return
    if revalidated and isinstance(note, str) and note.strip():
        return
    raise JournalRefused("ORDER_EXPIRED: %d verified sessions after the submission on %s; the limit is %d. "
                         "Record EXPIRED, or record the fill with revalidated and a note that the pre-trade "
                         "conditions were checked again. This application does not cancel a Kite order."
                         % (sessions, submission["submitted_at"], ENTRY_EXPIRY_SESSIONS))


def _month(text):
    if not re.match(r"^\d{4}-\d{2}$", text or ""):
        raise StoreError("month must be YYYY-MM")
    y, mo = int(text[:4]), int(text[5:])
    if not 1 <= mo <= 12:
        raise StoreError("month must be YYYY-MM")
    return y, mo


def journal_execution(conn, entry_id, side, quantity, price, at, print_key, note=None, *,
                      calendar=None, revalidated=False, request_key=None):
    """Record one print. The first ENTRY print is the single TRIGGERED trade.

    Later ENTRY prints of that same order are not a second trade and not a second
    position (RB 2140). EXIT prints reduce open quantity. They do not release the
    monthly allowance or the zone. Nothing is sent to a broker.
    """
    if side not in ("ENTRY", "EXIT"):
        raise StoreError("side must be ENTRY or EXIT")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise StoreError("quantity must be a positive whole number of shares")
    price = _num(price, "price")
    if price <= 0:
        raise StoreError("price must be positive")
    if not isinstance(print_key, str) or not print_key.strip() or len(print_key) > 200:
        raise StoreError("print_key must be 1..200 characters")
    print_key = print_key.strip()
    if note is not None and not isinstance(note, str):
        raise StoreError("note must be text")
    _dt(at, "at")
    if request_key is None:
        request_key = "print:" + print_key
    fingerprint = _j({"entry_id": entry_id, "side": side, "quantity": quantity, "price": price,
                      "at": at, "print_key": print_key, "note": note})
    with _Immediate(conn):
        row = conn.execute("SELECT quantity FROM journal_entries WHERE entry_id = ?", (entry_id,)).fetchone()
        if row is None:
            raise StoreError("unknown journal entry %s" % entry_id)
        replay = _stored_request(conn, request_key, "journal_execution", fingerprint)
        if replay is not None:
            found = {"entry_id": replay["entry_id"], "print_key": replay["print_key"], "already_present": True}
            found["book"] = position_book(conn, entry_id, row["quantity"], journal_events(conn, entry_id), None)
            return found
        existing = conn.execute(
            "SELECT * FROM journal_executions WHERE entry_id = ? AND print_key = ?",
            (entry_id, print_key)).fetchone()
        if existing is not None:
            same = (existing["side"] == side and existing["quantity"] == quantity
                    and float(existing["price"]) == float(price) and existing["at"] == at
                    and existing["note"] == note)
            if not same:
                raise JournalRefused("DUPLICATE_PRINT: print_key %s is already stored with a different body"
                                     % print_key)
            _remember(conn, request_key, "journal_execution",
                      {"entry_id": entry_id, "print_key": print_key, "fingerprint": fingerprint})
            return {"entry_id": entry_id, "print_key": print_key, "already_present": True,
                    "book": position_book(conn, entry_id, row["quantity"], journal_events(conn, entry_id), None)}
        planned = row["quantity"]
        events = journal_events(conn, entry_id)
        prints = _execution_rows(conn, entry_id)
        entry_qty = sum(item["quantity"] for item in prints if item["side"] == "ENTRY")
        exit_qty = sum(item["quantity"] for item in prints if item["side"] == "EXIT")
        state = _state(events)[0]
        t = _dt(at, "at")
        if events and _before(t, _dt(events[-1]["at"], "previous event"), "journal_execution"):
            raise JournalRefused("events must be chronological: %s is before the previous event at %s"
                                 % (at, events[-1]["at"]))
        if prints and _before(t, _dt(prints[-1]["at"], "previous print"), "journal_execution"):
            raise JournalRefused("prints must be chronological: %s is before the previous print at %s"
                                 % (at, prints[-1]["at"]))
        triggered = any(event["kind"] == TRIGGERED for event in events)
        if side == "ENTRY":
            if triggered and not any(item["side"] == "ENTRY" for item in prints):
                raise JournalRefused("FULL_FILL_ALREADY_RECORDED: the TRIGGERED event is the full planned quantity; "
                                     "an exit print can reduce it")
            if entry_qty + quantity > planned:
                raise JournalRefused("QUANTITY_EXCEEDS_ORDER: %d shares would exceed the planned %d"
                                     % (entry_qty + quantity, planned))
            if not triggered:
                if state != "PLANNED":
                    raise JournalRefused("an entry print is not allowed after the entry is %s" % state)
                _refuse_new_trigger(conn, entry_id, t, at, calendar, revalidated, note)
                conn.execute("INSERT INTO journal_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (entry_id, events[-1]["seq"] + 1, TRIGGERED, at, price, None, note))
        else:
            filled = entry_qty if entry_qty else (planned if triggered else 0)
            if filled <= 0:
                raise JournalRefused("NO_FILL: an exit print needs executed quantity")
            if exit_qty + quantity > filled:
                raise JournalRefused("EXIT_EXCEEDS_FILL: %d shares would exceed the executed %d"
                                     % (exit_qty + quantity, filled))
        conn.execute(
            "INSERT INTO journal_executions (entry_id, print_key, side, quantity, price, at, note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (entry_id, print_key, side, quantity, price, at, note))
        _remember(conn, request_key, "journal_execution",
                  {"entry_id": entry_id, "print_key": print_key, "fingerprint": fingerprint})
        book = position_book(conn, entry_id, planned, journal_events(conn, entry_id), None)
    return {"entry_id": entry_id, "print_key": print_key, "already_present": False, "book": book}


def journal_record_charges(conn, entry_id, lines, *, at, source, estimated, request_key=None):
    """Store owner-entered or schedule-estimated charge lines. A missing line is not filled in."""
    if not isinstance(source, str) or not source.strip():
        raise StoreError("charge source is required")
    if estimated not in (True, False):
        raise StoreError("estimated must be true or false")
    _dt(at, "at")
    if not isinstance(lines, list) or not lines:
        raise StoreError("at least one charge line is required")
    cleaned = []
    for line in lines:
        if not isinstance(line, dict):
            raise StoreError("charge line is not an object")
        component = line.get("component")
        side = line.get("side")
        if component not in charges.COMPONENTS:
            raise StoreError("unknown charge component %r" % (component,))
        if side not in ("BUY", "SELL"):
            raise StoreError("charge side must be BUY or SELL")
        amount = line.get("amount_paise")
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise StoreError("amount_paise must be a non-negative integer")
        basis = line.get("basis")
        key = line.get("charge_key")
        if not isinstance(basis, str) or not basis.strip():
            raise StoreError("charge basis is required")
        if not isinstance(key, str) or not key.strip() or len(key) > 200:
            raise StoreError("charge_key must be 1..200 characters")
        cleaned.append((key.strip(), component, side, amount, basis.strip()))
    fingerprint = _j({"entry_id": entry_id, "at": at, "source": source.strip(), "estimated": bool(estimated),
                      "lines": cleaned})
    with _Immediate(conn):
        if conn.execute("SELECT 1 FROM journal_entries WHERE entry_id = ?", (entry_id,)).fetchone() is None:
            raise StoreError("unknown journal entry %s" % entry_id)
        replay = _stored_request(conn, request_key, "journal_charges", fingerprint)
        if replay is not None:
            return {"entry_id": entry_id, "charge_keys": replay.get("charge_keys", []), "already_present": True,
                    "estimated": bool(estimated)}
        for key, component, side, amount, basis in cleaned:
            current = conn.execute(
                "SELECT amount_paise, component, side FROM journal_charges WHERE entry_id = ? AND charge_key = ?",
                (entry_id, key)).fetchone()
            if current is not None:
                if current["amount_paise"] == amount and current["component"] == component and current["side"] == side:
                    continue
                raise JournalRefused("DUPLICATE_CHARGE: %s is already stored with a different amount" % key)
            conn.execute(
                "INSERT INTO journal_charges (entry_id, charge_key, component, side, amount_paise, basis, source, "
                "estimated, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (entry_id, key, component, side, amount, basis, source.strip(), 1 if estimated else 0, at))
        keys = [key for key, _component, _side, _amount, _basis in cleaned]
        _remember(conn, request_key, "journal_charges",
                  {"entry_id": entry_id, "charge_keys": keys, "fingerprint": fingerprint})
    return {"entry_id": entry_id, "charge_keys": keys, "already_present": False, "estimated": bool(estimated)}


def journal_apply_schedule(conn, entry_id, schedule, *, side, quantity, price, at, print_key):
    """Estimate charges from a caller-supplied dated schedule. No rate is invented."""
    try:
        quoted = charges.quote(schedule, side=side, quantity=quantity, price=price, trade_date=_dt(at, "at"))
    except charges.ChargeScheduleError as exc:
        raise StoreError(str(exc)) from exc
    lines = [{
        "component": line["component"],
        "side": side,
        "amount_paise": line["amount_paise"],
        "basis": "%s; coverage %s; %s to %s" % (
            line["basis"], quoted["coverage"], quoted["effective_from"], quoted["effective_to"]),
        "charge_key": "%s:%s:%s" % (print_key, side, line["component"]),
    } for line in quoted["lines"]]
    return journal_record_charges(
        conn, entry_id, lines, at=at, source=quoted["source"], estimated=True,
        request_key="schedule:%s:%s:%s" % (entry_id, print_key, side))


def _charge_state(rows):
    if not rows:
        return "ABSENT"
    flags = {bool(row["estimated"]) for row in rows}
    if flags == {False}:
        return "ACTUAL"
    if flags == {True}:
        return "ESTIMATED"
    return "MIXED"


def _note_rows(conn, entry_id):
    if not _has_table(conn, "journal_notes"):
        return []
    return [dict(r) for r in conn.execute(
        "SELECT * FROM journal_notes WHERE entry_id = ? ORDER BY rowid", (entry_id,))]


def _review_rows(conn, entry_id):
    if not _has_table(conn, "journal_reviews"):
        return []
    return [dict(r) for r in conn.execute(
        "SELECT * FROM journal_reviews WHERE entry_id = ? ORDER BY rowid", (entry_id,))]


def _attachment_rows(conn, entry_id):
    if not _has_table(conn, "journal_attachments"):
        return []
    rows = []
    for r in conn.execute(
            "SELECT * FROM journal_attachments WHERE entry_id = ? ORDER BY rowid", (entry_id,)):
        item = dict(r)
        item["missing"] = bool(item["missing"])
        rows.append(item)
    return rows


def _latest_review(rows):
    if not rows:
        return {
            "review_status": "NOT_REVIEWED",
            "outcome_class": "NOT_REVIEWED",
            "mistake_category": "NOT_REVIEWED",
            "taxonomy_version": journal_taxonomy.TAXONOMY_VERSION,
            "setup_label": None,
            "rule_refs": [],
            "note": None,
            "at": None,
            "review_key": None,
        }
    latest = rows[-1]
    refs = []
    raw = latest.get("rule_refs")
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                refs = [str(x) for x in parsed]
        except json.JSONDecodeError:
            refs = []
    return {
        "review_status": latest["review_status"],
        "outcome_class": latest["outcome_class"],
        "mistake_category": latest["mistake_category"],
        "taxonomy_version": latest["taxonomy_version"],
        "setup_label": latest.get("setup_label"),
        "rule_refs": refs,
        "note": latest.get("note"),
        "at": latest["at"],
        "review_key": latest["review_key"],
        "actor": latest.get("actor"),
    }


def _setup_from_entry(entry):
    """Reliable setup dimensions from stored entry fields only. Never invents pattern."""
    trade_type = entry["trade_type"]
    pattern = "UNKNOWN"
    core = "UNKNOWN"
    raw = entry["candidate_levels"]
    if isinstance(raw, str) and raw.strip():
        try:
            levels_obj = json.loads(raw)
        except json.JSONDecodeError:
            levels_obj = None
        if isinstance(levels_obj, dict):
            zone = levels_obj.get("zone") if isinstance(levels_obj.get("zone"), dict) else levels_obj
            if isinstance(zone, dict):
                pattern = zone.get("pattern") or levels_obj.get("pattern") or "UNKNOWN"
                core = zone.get("core") or levels_obj.get("core") or "UNKNOWN"
            else:
                pattern = levels_obj.get("pattern") or "UNKNOWN"
                core = levels_obj.get("core") or "UNKNOWN"
    return {"trade_type": trade_type, "pattern": pattern, "core": core}


def journal_add_note(conn, entry_id, *, note_key, at, kind, body, actor="owner", request_key=None):
    """Append a typed review note. Does not alter execution facts."""
    if kind not in journal_taxonomy.NOTE_KINDS:
        raise StoreError("unknown note kind %r" % (kind,))
    if not isinstance(note_key, str) or not note_key.strip() or len(note_key) > 200:
        raise StoreError("note_key must be 1..200 characters")
    if not isinstance(body, str) or not body.strip():
        raise StoreError("note body must be non-empty text")
    if not isinstance(actor, str) or not actor.strip():
        raise StoreError("actor must be non-empty text")
    _dt(at, "at")
    fingerprint = _j({"entry_id": entry_id, "note_key": note_key, "at": at, "kind": kind,
                      "body": body, "actor": actor})
    with _Immediate(conn):
        if conn.execute("SELECT 1 FROM journal_entries WHERE entry_id = ?", (entry_id,)).fetchone() is None:
            raise StoreError("unknown journal entry %s" % entry_id)
        replay = _stored_request(conn, request_key, "journal_note", fingerprint)
        if replay is not None:
            return {"entry_id": entry_id, "note_key": note_key, "already_present": True}
        existing = conn.execute(
            "SELECT body, kind FROM journal_notes WHERE entry_id = ? AND note_key = ?",
            (entry_id, note_key.strip())).fetchone()
        if existing is not None:
            if existing["body"] == body and existing["kind"] == kind:
                return {"entry_id": entry_id, "note_key": note_key.strip(), "already_present": True}
            raise JournalRefused("DUPLICATE_NOTE: %s already stored with different content" % note_key)
        conn.execute(
            "INSERT INTO journal_notes (entry_id, note_key, at, kind, body, actor) VALUES (?, ?, ?, ?, ?, ?)",
            (entry_id, note_key.strip(), at, kind, body.strip(), actor.strip()))
        _remember(conn, request_key, "journal_note",
                  {"entry_id": entry_id, "note_key": note_key.strip(), "fingerprint": fingerprint})
    return {"entry_id": entry_id, "note_key": note_key.strip(), "already_present": False}


def journal_add_review(conn, entry_id, *, review_key, at, review_status, outcome_class,
                       mistake_category, note=None, setup_label=None, rule_refs=None,
                       actor="owner", request_key=None):
    """Append an owner review classification. Never rewrites fills or planned levels."""
    try:
        journal_taxonomy.validate_review(
            review_status=review_status, outcome_class=outcome_class,
            mistake_category=mistake_category, taxonomy_version=journal_taxonomy.TAXONOMY_VERSION)
    except ValueError as exc:
        raise StoreError(str(exc)) from exc
    if not isinstance(review_key, str) or not review_key.strip() or len(review_key) > 200:
        raise StoreError("review_key must be 1..200 characters")
    if note is not None and (not isinstance(note, str) or not note.strip()):
        raise StoreError("review note must be non-empty text when given")
    if setup_label is not None and (not isinstance(setup_label, str) or not setup_label.strip()):
        raise StoreError("setup_label must be non-empty text when given")
    if not isinstance(actor, str) or not actor.strip():
        raise StoreError("actor must be non-empty text")
    refs = []
    if rule_refs is not None:
        if not isinstance(rule_refs, list) or any(not isinstance(x, str) or not x.strip() for x in rule_refs):
            raise StoreError("rule_refs must be a list of non-empty strings (owner citations)")
        refs = [x.strip() for x in rule_refs]
    _dt(at, "at")
    fingerprint = _j({
        "entry_id": entry_id, "review_key": review_key, "at": at, "review_status": review_status,
        "outcome_class": outcome_class, "mistake_category": mistake_category,
        "taxonomy_version": journal_taxonomy.TAXONOMY_VERSION, "setup_label": setup_label,
        "rule_refs": refs, "note": note, "actor": actor,
    })
    with _Immediate(conn):
        if conn.execute("SELECT 1 FROM journal_entries WHERE entry_id = ?", (entry_id,)).fetchone() is None:
            raise StoreError("unknown journal entry %s" % entry_id)
        replay = _stored_request(conn, request_key, "journal_review", fingerprint)
        if replay is not None:
            return {"entry_id": entry_id, "review_key": review_key.strip(), "already_present": True}
        existing = conn.execute(
            "SELECT review_status, outcome_class, mistake_category FROM journal_reviews "
            "WHERE entry_id = ? AND review_key = ?",
            (entry_id, review_key.strip())).fetchone()
        if existing is not None:
            if (existing["review_status"] == review_status and existing["outcome_class"] == outcome_class
                    and existing["mistake_category"] == mistake_category):
                return {"entry_id": entry_id, "review_key": review_key.strip(), "already_present": True}
            raise JournalRefused("DUPLICATE_REVIEW: %s already stored with different classification" % review_key)
        conn.execute(
            "INSERT INTO journal_reviews (entry_id, review_key, at, review_status, outcome_class, "
            "mistake_category, taxonomy_version, setup_label, rule_refs, note, actor) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (entry_id, review_key.strip(), at, review_status, outcome_class, mistake_category,
             journal_taxonomy.TAXONOMY_VERSION,
             None if setup_label is None else setup_label.strip(),
             _j(refs), None if note is None else note.strip(), actor.strip()))
        _remember(conn, request_key, "journal_review",
                  {"entry_id": entry_id, "review_key": review_key.strip(), "fingerprint": fingerprint})
    return {"entry_id": entry_id, "review_key": review_key.strip(), "already_present": False,
            "taxonomy_version": journal_taxonomy.TAXONOMY_VERSION}


def journal_register_attachment(conn, entry_id, *, attachment_id, at, filename, content_type,
                                size_bytes, sha256, storage_name, note=None, missing=False,
                                request_key=None):
    """Register attachment metadata. Bytes are stored by the platform, not in this row."""
    if not isinstance(attachment_id, str) or not attachment_id.strip() or len(attachment_id) > 200:
        raise StoreError("attachment_id must be 1..200 characters")
    if content_type not in ATTACHMENT_CONTENT_TYPES:
        raise StoreError("unsupported attachment content_type %r" % (content_type,))
    if not isinstance(filename, str) or not _SAFE_FILENAME.match(filename):
        raise StoreError("filename must be a safe basename (letters, digits, . _ -)")
    if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes < 0:
        raise StoreError("size_bytes must be a non-negative integer")
    if size_bytes > ATTACHMENT_MAX_BYTES:
        raise StoreError("attachment exceeds %d bytes" % ATTACHMENT_MAX_BYTES)
    if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise StoreError("sha256 must be a 64-character lowercase hex digest")
    if not isinstance(storage_name, str) or not _SAFE_FILENAME.match(storage_name):
        raise StoreError("storage_name must be a safe basename")
    if note is not None and (not isinstance(note, str) or not note.strip()):
        raise StoreError("attachment note must be non-empty text when given")
    if missing not in (True, False):
        raise StoreError("missing must be true or false")
    _dt(at, "at")
    fingerprint = _j({
        "entry_id": entry_id, "attachment_id": attachment_id, "at": at, "filename": filename,
        "content_type": content_type, "size_bytes": size_bytes, "sha256": sha256,
        "storage_name": storage_name, "note": note, "missing": bool(missing),
    })
    with _Immediate(conn):
        if conn.execute("SELECT 1 FROM journal_entries WHERE entry_id = ?", (entry_id,)).fetchone() is None:
            raise StoreError("unknown journal entry %s" % entry_id)
        replay = _stored_request(conn, request_key, "journal_attachment", fingerprint)
        if replay is not None:
            return {"entry_id": entry_id, "attachment_id": attachment_id.strip(), "already_present": True}
        existing = conn.execute(
            "SELECT sha256, size_bytes FROM journal_attachments WHERE entry_id = ? AND attachment_id = ?",
            (entry_id, attachment_id.strip())).fetchone()
        if existing is not None:
            if existing["sha256"] == sha256 and existing["size_bytes"] == size_bytes:
                return {"entry_id": entry_id, "attachment_id": attachment_id.strip(), "already_present": True}
            raise JournalRefused("DUPLICATE_ATTACHMENT: %s already stored with different bytes" % attachment_id)
        conn.execute(
            "INSERT INTO journal_attachments (entry_id, attachment_id, at, filename, content_type, "
            "size_bytes, sha256, storage_name, note, missing) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (entry_id, attachment_id.strip(), at, filename, content_type, size_bytes, sha256,
             storage_name, None if note is None else note.strip(), 1 if missing else 0))
        _remember(conn, request_key, "journal_attachment",
                  {"entry_id": entry_id, "attachment_id": attachment_id.strip(), "fingerprint": fingerprint})
    return {"entry_id": entry_id, "attachment_id": attachment_id.strip(), "already_present": False}


def journal_entry_detail(conn, entry_id):
    """Canonical read model for one journal entry. Never invents fills or charges."""
    row = conn.execute("SELECT * FROM journal_entries WHERE entry_id = ?", (entry_id,)).fetchone()
    if row is None:
        raise StoreError("unknown journal entry %s" % entry_id)
    entry = dict(row)
    events = journal_events(conn, entry_id)
    state, stop, fill, locked = _state(events)
    executions = _execution_rows(conn, entry_id)
    charges_rows = _charge_rows(conn, entry_id)
    notes = _note_rows(conn, entry_id)
    reviews = _review_rows(conn, entry_id)
    attachments = _attachment_rows(conn, entry_id)
    book = position_book(conn, entry_id, entry["quantity"], events, None)
    review = _latest_review(reviews)
    setup = _setup_from_entry(entry)
    if review.get("setup_label"):
        setup["setup_label"] = review["setup_label"]
    return {
        "entry": entry,
        "state": state,
        "current_stop": stop,
        "fill_price": fill,
        "locked_stop": locked,
        "order": order_submission(conn, entry_id),
        "events": events,
        "executions": executions,
        "charges": charges_rows,
        "charges_state": _charge_state(charges_rows),
        "book": book,
        "notes": notes,
        "reviews": reviews,
        "review": review,
        "attachments": attachments,
        "setup": setup,
        "authorises_order": False,
        "evidence_class": "JOURNAL_DESCRIPTIVE",
    }


def journal_query(conn, filters=None):
    """Filter canonical journal rows. Missing filter fields are not fabricated."""
    filters = dict(filters or {})
    unknown = sorted(set(filters) - {
        "symbol", "state", "month", "trade_type", "direction", "review_status",
        "mistake_category", "outcome_class", "setup_label", "open", "charges_state",
        "limit", "offset", "sort", "order",
    })
    if unknown:
        raise StoreError("unknown journal filter fields: %s" % ", ".join(unknown))
    limit = filters.get("limit", 100)
    offset = filters.get("offset", 0)
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1 or limit > 500:
        raise StoreError("limit must be an integer 1..500")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise StoreError("offset must be a non-negative integer")
    sort = filters.get("sort") or "entry_id"
    order = (filters.get("order") or "asc").lower()
    if sort not in ("entry_id", "symbol", "recorded_at"):
        raise StoreError("sort must be entry_id, symbol, or recorded_at")
    if order not in ("asc", "desc"):
        raise StoreError("order must be asc or desc")
    month = filters.get("month")
    month_pair = _month(month) if month is not None else None
    rows = []
    for entry in conn.execute("SELECT * FROM journal_entries ORDER BY entry_id"):
        detail = journal_entry_detail(conn, entry["entry_id"])
        item = {
            "entry_id": entry["entry_id"],
            "symbol": entry["symbol"],
            "zone_id": entry["zone_id"],
            "trade_type": entry["trade_type"],
            "direction": entry["direction"],
            "planned_entry": entry["planned_entry"],
            "planned_stop": entry["planned_stop"],
            "planned_target": entry["planned_target"],
            "quantity": entry["quantity"],
            "recorded_at": entry["recorded_at"],
            "state": detail["state"],
            "book": detail["book"],
            "charges_state": detail["charges_state"],
            "review": detail["review"],
            "setup": detail["setup"],
            "events": detail["events"],
            "executions": detail["executions"],
            "order": detail["order"],
        }
        if filters.get("symbol"):
            needle = str(filters["symbol"]).strip().upper()
            if needle not in entry["symbol"].upper():
                continue
        if filters.get("state") and detail["state"] != filters["state"]:
            continue
        if filters.get("trade_type") and entry["trade_type"] != filters["trade_type"]:
            continue
        if filters.get("direction") and entry["direction"] != filters["direction"]:
            continue
        if filters.get("review_status") and detail["review"]["review_status"] != filters["review_status"]:
            continue
        if filters.get("mistake_category") and detail["review"]["mistake_category"] != filters["mistake_category"]:
            continue
        if filters.get("outcome_class") and detail["review"]["outcome_class"] != filters["outcome_class"]:
            continue
        if filters.get("setup_label"):
            label = detail["setup"].get("setup_label") or detail["review"].get("setup_label")
            if label != filters["setup_label"]:
                continue
        if filters.get("charges_state") and detail["charges_state"] != filters["charges_state"]:
            continue
        if "open" in filters and filters["open"] is not None:
            want_open = bool(filters["open"])
            if bool(detail["book"]["counts_as_open"]) != want_open:
                continue
        if month_pair is not None:
            trig = [e for e in detail["events"] if e["kind"] == TRIGGERED]
            if not trig:
                continue
            if m.ist_month(_dt(trig[0]["at"], "TRIGGERED at")) != month_pair:
                continue
        rows.append(item)
    reverse = order == "desc"
    if sort == "entry_id":
        rows.sort(key=lambda r: r["entry_id"], reverse=reverse)
    elif sort == "symbol":
        rows.sort(key=lambda r: (r["symbol"], r["entry_id"]), reverse=reverse)
    else:
        rows.sort(key=lambda r: (r["recorded_at"], r["entry_id"]), reverse=reverse)
    total = len(rows)
    page = rows[offset:offset + limit]
    return {
        "entries": page,
        "total": total,
        "limit": limit,
        "offset": offset,
        "sort": sort,
        "order": order,
        "filters": {k: v for k, v in filters.items() if k not in ("limit", "offset", "sort", "order")},
        "authorises_order": False,
        "evidence_class": "JOURNAL_DESCRIPTIVE",
        "note": "Results are canonical research-journal rows. Empty results are not errors.",
    }


def journal_planned_versus_actual(conn, entry_id):
    """Compare immutable planned snapshot with recorded prints. Never invents fills."""
    detail = journal_entry_detail(conn, entry_id)
    entry = detail["entry"]
    book = detail["book"]
    executions = detail["executions"]
    entry_prints = [row for row in executions if row.get("side") == "ENTRY"]
    exit_prints = [row for row in executions if row.get("side") == "EXIT"]
    planned = {
        "entry": entry["planned_entry"],
        "stop": entry["planned_stop"],
        "target": entry["planned_target"],
        "quantity": entry["quantity"],
        "recorded_at": entry["recorded_at"],
    }
    actual_avg = book.get("average_entry_price")
    actual_qty = book.get("executed_entry_quantity")
    entry_delta = None if actual_avg is None else float(actual_avg) - float(planned["entry"])
    qty_delta = None if actual_qty is None else actual_qty - int(planned["quantity"])
    exit_prices = [row["price"] for row in exit_prints]
    return {
        "state": "COMPARED" if entry_prints or exit_prints else "PLANNED_ONLY",
        "lifecycle_state": detail["state"],
        "planned": planned,
        "actual": {
            "entry_prints": len(entry_prints),
            "exit_prints": len(exit_prints),
            "executed_entry_quantity": actual_qty,
            "executed_exit_quantity": book.get("executed_exit_quantity"),
            "average_entry_price": actual_avg,
            "open_quantity": book.get("open_quantity"),
            "unfilled_quantity": book.get("unfilled_quantity"),
            "realised_pnl": book.get("realised_pnl"),
            "locked_stop": detail["locked_stop"],
            "exit_prices": exit_prices,
            "charges_state": detail["charges_state"],
            "charges_paise": sum(r["amount_paise"] for r in detail["charges"]),
        },
        "deltas": {
            "entry_price": entry_delta,
            "quantity_filled_vs_planned": qty_delta,
        },
        "authorises_order": False,
        "evidence_class": "JOURNAL_DESCRIPTIVE",
        "note": "Original planned values are immutable journal_entries columns. "
                "Fills are owner-recorded prints. Deviations are facts, not automatic mistakes.",
    }


def _query_all_entries(conn, filters=None):
    """Collect every matching journal row for reporting/export. Never silently truncates."""
    base = dict(filters or {})
    base.pop("limit", None)
    base.pop("offset", None)
    page_size = 500
    offset = 0
    rows = []
    total = None
    while True:
        page = journal_query(conn, dict(base, limit=page_size, offset=offset))
        if total is None:
            total = page["total"]
        rows.extend(page["entries"])
        if len(rows) >= total or not page["entries"]:
            break
        offset += page_size
    return {
        "entries": rows,
        "total": total if total is not None else 0,
        "filters": page.get("filters", {}) if total is not None else {},
        "truncated": False,
        "authorises_order": False,
        "evidence_class": "JOURNAL_DESCRIPTIVE",
    }


def journal_performance(conn, filters=None):
    """Descriptive journal arithmetic. Not certified strategy performance."""
    queried = _query_all_entries(conn, filters)
    entries = queried["entries"]
    closed = [e for e in entries if e["state"] == "CLOSED"]
    open_rows = [e for e in entries if e["book"]["counts_as_open"]]
    partial = [e for e in entries if e["book"].get("executed_exit_quantity") and e["book"]["counts_as_open"]]
    gross_values = []
    for e in closed:
        pnl = e["book"].get("realised_pnl")
        if pnl is not None:
            gross_values.append(pnl)
    wins = [v for v in gross_values if v > 0]
    losses = [v for v in gross_values if v < 0]
    charges_complete = [e for e in closed if e["charges_state"] == "ACTUAL"]
    charges_incomplete = [e for e in closed if e["charges_state"] != "ACTUAL"]
    gross = round(sum(gross_values), 2) if gross_values else None
    known_charges_paise = 0
    for e in closed:
        detail = journal_entry_detail(conn, e["entry_id"])
        known_charges_paise += sum(r["amount_paise"] for r in detail["charges"])
    net = None
    net_state = "UNAVAILABLE"
    if gross is not None and closed and len(charges_incomplete) == 0 and charges_complete:
        net = round(gross - known_charges_paise / 100.0, 2)
        net_state = "ACTUAL"
    elif gross is not None and any(e["charges_state"] == "ESTIMATED" for e in closed) and not any(
            e["charges_state"] == "ABSENT" for e in closed):
        net = round(gross - known_charges_paise / 100.0, 2)
        net_state = "ESTIMATED"
    elif gross is not None:
        net_state = "INCOMPLETE_COSTS"

    def _bucket(key_fn):
        groups = {}
        for e in entries:
            key = key_fn(e) or "UNKNOWN"
            groups.setdefault(key, []).append(e)
        out = {}
        for key, rows in sorted(groups.items()):
            closed_g = [r for r in rows if r["state"] == "CLOSED"]
            pnls = [r["book"]["realised_pnl"] for r in closed_g if r["book"].get("realised_pnl") is not None]
            out[key] = {
                "trades": len(rows),
                "completed": len(closed_g),
                "open": sum(1 for r in rows if r["book"]["counts_as_open"]),
                "wins": sum(1 for v in pnls if v > 0),
                "losses": sum(1 for v in pnls if v < 0),
                "gross_realised_pnl": round(sum(pnls), 2) if pnls else None,
                "incomplete_cost_count": sum(1 for r in closed_g if r["charges_state"] != "ACTUAL"),
                "sample_size": len(pnls),
                "evidence_class": "JOURNAL_DESCRIPTIVE",
            }
        return out

    reviewed = sum(1 for e in entries if e["review"]["review_status"] == "REVIEWED")
    return {
        "evidence_class": "JOURNAL_DESCRIPTIVE",
        "limitations": [
            "Not certified strategy performance.",
            "Not R4 evidence.",
            "Open trades are excluded from win/loss counts.",
            "Net PnL is set only when charge completeness supports it.",
        ],
        "totals": {
            "recorded_trades": len(entries),
            "open_trades": len(open_rows),
            "closed_trades": len(closed),
            "partially_exited_trades": len(partial),
            "wins": len(wins),
            "losses": len(losses),
            "gross_realised_pnl": gross,
            "known_charges_paise": None if not closed else known_charges_paise,
            "net_realised_pnl": net,
            "net_state": net_state,
            "average_win": round(sum(wins) / len(wins), 2) if wins else None,
            "average_loss": round(sum(losses) / len(losses), 2) if losses else None,
            "largest_win": max(wins) if wins else None,
            "largest_loss": min(losses) if losses else None,
            "reviewed": reviewed,
            "unreviewed": len(entries) - reviewed,
        },
        "by_trade_type": _bucket(lambda e: e["trade_type"]),
        "by_mistake_category": _bucket(lambda e: e["review"]["mistake_category"]),
        "by_outcome_class": _bucket(lambda e: e["review"]["outcome_class"]),
        "by_setup_label": _bucket(lambda e: e["setup"].get("setup_label") or e["trade_type"]),
        "filters": queried["filters"],
        "truncated": False,
        "matched_total": queried["total"],
        "authorises_order": False,
        "note": JOURNAL_NOTE,
    }


def journal_export(conn, filters=None, *, include_attachments_manifest=True):
    """Machine-readable export of filtered journal rows. Attachments are referenced, not embedded."""
    queried = _query_all_entries(conn, filters)
    rows = []
    for item in queried["entries"]:
        detail = journal_entry_detail(conn, item["entry_id"])
        comparison = journal_planned_versus_actual(conn, item["entry_id"])
        rows.append({
            "entry_id": item["entry_id"],
            "symbol": item["symbol"],
            "zone_id": item["zone_id"],
            "trade_type": item["trade_type"],
            "direction": item["direction"],
            "lifecycle_state": detail["state"],
            "planned": comparison["planned"],
            "actual": comparison["actual"],
            "deltas": comparison["deltas"],
            "events": detail["events"],
            "executions": detail["executions"],
            "charges": detail["charges"],
            "charges_state": detail["charges_state"],
            "book": detail["book"],
            "notes": detail["notes"],
            "review": detail["review"],
            "reviews": detail["reviews"],
            "setup": detail["setup"],
            "attachments": detail["attachments"] if include_attachments_manifest else [],
            "attachments_included": bool(include_attachments_manifest),
            "evidence_class": "JOURNAL_DESCRIPTIVE",
        })
    return {
        "format": "gtf-journal-export-v1",
        "evidence_class": "JOURNAL_DESCRIPTIVE",
        "total": len(rows),
        "filters": queried["filters"],
        "truncated": False,
        "attachments_embedded": False,
        "rows": rows,
        "authorises_order": False,
        "note": "Attachment bytes are not embedded. The attachments array is a manifest of references.",
    }


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
        if m.ist_month(t) != (y, mo):
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
            rec["r_multiple"] = round((x["price"] - fill) / risk, 4) if risk and risk > 0 else None
            rec["gross_pnl"] = round((x["price"] - fill) * e["quantity"], 2)
        book = position_book(conn, e["entry_id"], e["quantity"], events, None)
        charge_rows = _charge_rows(conn, e["entry_id"])
        rec.update({
            "requested_quantity": book["requested_quantity"],
            "executed_entry_quantity": book["executed_entry_quantity"],
            "open_quantity": book["open_quantity"],
            "unfilled_quantity": book["unfilled_quantity"],
            "average_entry_price": book["average_entry_price"],
            "position_open": book["counts_as_open"],
            "fill_source": book["source"],
            "realised_pnl": book["realised_pnl"],
            "unrealised": "UNAVAILABLE",
            "charges_paise": sum(row["amount_paise"] for row in charge_rows),
            "charges_state": _charge_state(charge_rows),
        })
        if book["source"] != "legacy_full_fill":
            rec["fill_price"] = book["average_entry_price"]
            rec["gross_pnl"] = None if book["counts_as_open"] else book["realised_pnl"]
            rec["r_multiple"] = None
        trades.append(rec)
    closed = [t for t in trades if not t["position_open"]]
    rs = [t["r_multiple"] for t in closed if t["r_multiple"] is not None]
    won = sum(t["gross_pnl"] for t in closed if t["gross_pnl"] is not None and t["gross_pnl"] > 0)
    lost = -sum(t["gross_pnl"] for t in closed if t["gross_pnl"] is not None and t["gross_pnl"] < 0)
    wins = sum(1 for t in closed if t["gross_pnl"] is not None and t["gross_pnl"] > 0)
    states = {t["charges_state"] for t in trades} or {"ABSENT"}
    if states == {"ABSENT"}:
        month_state = "ABSENT"
    elif "ABSENT" in states or "MIXED" in states or states == {"ACTUAL", "ESTIMATED"}:
        month_state = "PARTIAL" if "ABSENT" in states else "MIXED"
    elif states == {"ACTUAL"}:
        month_state = "ACTUAL"
    else:
        month_state = "ESTIMATED"
    gross = round(won - lost, 2) if closed else None
    closed_paise = sum(t["charges_paise"] for t in closed)
    actual_net = None
    estimated_net = None
    if gross is not None and month_state == "ACTUAL" and all(t["charges_state"] == "ACTUAL" for t in closed):
        actual_net = round(gross - closed_paise / 100.0, 2)
    if gross is not None and month_state == "ESTIMATED" and all(t["charges_state"] == "ESTIMATED" for t in closed):
        estimated_net = round(gross - closed_paise / 100.0, 2)
    if month_state == "ABSENT":
        costs_line = "COSTS: not recorded, P&L is gross"
    else:
        costs_line = ("COSTS: itemised charges are separate from gross_pnl; "
                      "net is set only when the state is ACTUAL or ESTIMATED")
    return {
        "month": month, "trades_taken": len(trades), "ceiling": MONTHLY_TRADE_CEILING,
        "over_ceiling": len(trades) > MONTHLY_TRADE_CEILING, "ceiling_source": "RB 2392",
        "closed": len(closed), "open": len(trades) - len(closed), "wins": wins,
        "losses": sum(1 for t in closed if t["gross_pnl"] is not None and t["gross_pnl"] < 0),
        "win_rate_pct": round(100.0 * wins / len(closed), 2) if closed else None,
        "r_multiples": rs, "average_r": round(sum(rs) / len(rs), 4) if rs else None,
        "gross_pnl": gross,
        "profit_factor": round(won / lost, 4) if lost > 0 else None,
        "checklist_exceptions": sum(1 for t in trades if t["checklist_false"]),
        "not_computed": ["ROI_PCT: starting capital is not recorded", "RULE_COMPLIANCE_RATE: rules-followed and "
                         "remark columns (RB 3739-3740) are not recorded", costs_line],
        "charges_state": month_state,
        "charges_paise": None if month_state == "ABSENT" else sum(t["charges_paise"] for t in trades),
        "actual_net_pnl": actual_net,
        "estimated_net_pnl": estimated_net,
        "trades": trades, "note": JOURNAL_NOTE,
    }


def portfolio_at(conn, at):
    """Read-only journal state at `at` for research planning. Writes nothing.

    Monthly trades are TRIGGERED events in the IST month of `at` whose event time is
    at or before `at`. An exit does not reduce that count (D42, D46). Open positions
    use `_open_positions`, which already ignores a trigger or exit after `at`. Zone
    allowance uses `_zone_allowance` on events known at `at`: a submitted order keeps
    the allowance, and a plan that was never submitted does not, once it is CANCELLED.
    """
    t = _dt(at, "at")
    month = m.ist_month(t)
    triggered = 0
    for r in conn.execute("SELECT at FROM journal_events WHERE kind = ?", (TRIGGERED,)):
        ev = _dt(r["at"], "TRIGGERED at")
        if _before(t, ev, "portfolio_at"):
            continue
        if m.ist_month(ev) == month:
            triggered += 1
    holding = []
    for e in conn.execute(
            "SELECT entry_id, symbol, zone_id, trade_type, quantity, recorded_at, "
            "planned_entry, planned_stop, planned_target "
            "FROM journal_entries ORDER BY entry_id"):
        if _before(t, _dt(e["recorded_at"], "recorded_at"), "portfolio_at"):
            continue
        events = journal_events(conn, e["entry_id"])
        reason = _zone_allowance(conn, e["entry_id"], events, t)
        if reason:
            visible = _visible(events, t, "event at")
            book = position_book(conn, e["entry_id"], e["quantity"], events, t)
            state, current_stop, _fill, locked_stop = _state(visible)
            holding.append({
                "entry_id": e["entry_id"], "symbol": e["symbol"], "zone_id": e["zone_id"],
                "trade_type": e["trade_type"], "reason": reason, "state": state,
                "counts_as_open": book["counts_as_open"], "open_quantity": book["open_quantity"],
                "executed_entry_quantity": book["executed_entry_quantity"],
                "executed_exit_quantity": book["executed_exit_quantity"],
                "unfilled_quantity": book["unfilled_quantity"],
                "requested_quantity": book["requested_quantity"],
                "average_entry_price": book["average_entry_price"],
                "average_exit_price": book["average_exit_price"],
                "realised_pnl": book["realised_pnl"],
                "unrealised": book["unrealised"],
                "fill_source": book["source"],
                "planned_entry": e["planned_entry"],
                "planned_stop": e["planned_stop"],
                "planned_target": e["planned_target"],
                "locked_stop": locked_stop if locked_stop is not None else current_stop,
            })
    return {
        "as_of": t.isoformat(), "ist_month": "%04d-%02d" % month,
        "trades_triggered_this_month": triggered, "monthly_cap": m.OWNER_MONTHLY_TRADE_CAP,
        "open_positions": _open_positions(conn, t), "open_position_cap": m.OWNER_MAX_OPEN_POSITIONS,
        "zones_holding_allowance": holding, "source": "journal", "counts_events_after_as_of": False,
        "note": "Read only. Counts use journal event times at or before as_of. A closed position releases "
                "only the open-position slot. A submitted order keeps the zone allowance (ED-3). "
                "This record is not an order. Valuation is not computed here.",
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


def cmd_journal_order(args):
    return _run(_with_store(args.db, lambda conn: {"entry_id": journal_order_submitted(
        conn, args.entry_id, args.at, order_ref=args.order_ref, note=args.note)}))


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
    p = subparsers.add_parser("journal-order-submitted",
                              help="record that the planned order was submitted manually (Kite/GTT; nothing is sent)")
    p.add_argument("--db", required=True)
    p.add_argument("--entry-id", required=True, type=int)
    p.add_argument("--at", required=True, help="ISO time the order was submitted (no clock is read)")
    p.add_argument("--order-ref", help="the broker's order or GTT reference, as text")
    p.add_argument("--note")
    p.set_defaults(func=cmd_journal_order)
    p = subparsers.add_parser("journal-summary", help="monthly journal arithmetic and the 10-trade ceiling")
    p.add_argument("--db", required=True)
    p.add_argument("--month", required=True, help="YYYY-MM")
    p.set_defaults(func=cmd_journal_summary)
