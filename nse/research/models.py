"""Shared vocabulary and result models for the research pipeline.

Statuses and gate names follow nse/docs/IMPLEMENTATION_SPECIFICATION.md section 8. A
gate outcome is never a bare boolean: PASS, FAIL, MANUAL (inconclusive, a person
decides), DATA_INSUFFICIENT (the input needed is missing), BLOCKED (the capability is
not approved for use) or NOT_EVALUATED (an earlier gate stopped the evaluation).
Unknown is never PASS.
"""

import datetime
import hashlib
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List

PIPELINE_VERSION = "1.0.0"

# --- gate outcomes ------------------------------------------------------------------
PASS = "PASS"
FAIL = "FAIL"
MANUAL = "MANUAL"
DATA_INSUFFICIENT = "DATA_INSUFFICIENT"
BLOCKED = "BLOCKED"
NOT_EVALUATED = "NOT_EVALUATED"
OUTCOMES = (PASS, FAIL, MANUAL, DATA_INSUFFICIENT, BLOCKED, NOT_EVALUATED)

GATES = ("G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8")
GATE_TITLES = {
    "G0": "Data and history readiness",
    "G1": "Fresh, unbreached execution-timeframe demand zone (MTF overlay)",
    "G2": "Core score 7/7",
    "G3": "Location (curve)",
    "G4": "Trend and alignment matrix",
    "G5": "Higher-timeframe conflict",
    "G6": "Coinciding / aggressive",
    "G7": "Entry, stop-loss, target and R:R",
    "G8": "Red flags and essential checks",
}

# --- candidate statuses (spec section 8), most restrictive first -----------------------
BLOCKED_STATUS = "BLOCKED"                    # capability not approved (e.g. intraday, M4b)
REJECTED = "REJECTED"                         # an automated gate failed
STATUS_DATA_INSUFFICIENT = "DATA_INSUFFICIENT"
MANUAL_REVIEW = "MANUAL_REVIEW"               # at least one gate is inconclusive
ACTIONABLE = "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING"
STATUS_ORDER = (BLOCKED_STATUS, REJECTED, STATUS_DATA_INSUFFICIENT, MANUAL_REVIEW, ACTIONABLE)
# No status means "validated" or "approved": external validation is pending (readiness.py)
# and the scanner never approves a trade.

# --- trade types (D16) --------------------------------------------------------------
MIT = "MIT"
WIT_75 = "WIT-75"
WIT_125 = "WIT-125"
TRADE_TYPES = (MIT, WIT_75, WIT_125)

# roles per trade type: location / trend gate / trend context / execution / target TF
ROLES = {
    MIT: {"location": "M", "trend_gate": "W", "trend_context": ("M",), "execution": "D",
          "target": "W", "target_reference": "M", "coinciding": "M",
          "conflict_reject": ("M", "Q", "HY"), "conflict_evidence": ("W", "Y")},
    WIT_75: {"location": "W", "trend_gate": "D", "trend_context": (), "execution": "75m",
             "target": "D", "target_reference": None, "coinciding": "W",
             "conflict_reject": ("M", "Q", "HY"), "conflict_evidence": ("W", "Y")},
    WIT_125: {"location": "W", "trend_gate": "D", "trend_context": (), "execution": "125m",
              "target": "D", "target_reference": None, "coinciding": "W",
              "conflict_reject": ("M", "Q", "HY"), "conflict_evidence": ("W", "Y")},
}
TDA_TIMEFRAMES = ("Y", "HY", "Q", "M", "W", "D")

# --- zone freshness as the overlay sees it ------------------------------------------
Z_FRESH = "FRESH"                             # overlay status FRESH, no unresolved flag
Z_TESTED = "TESTED"
Z_INVALIDATED = "INVALIDATED"
Z_UNKNOWN = "UNKNOWN"                         # gap, unverified session, pending, manual flag

# --- limitations every result can carry ---------------------------------------------
CALENDAR_UNVALIDATED = "CALENDAR_UNVALIDATED"                 # D28; no calendar given
CORPORATE_ACTIONS_UNVERIFIED = "CORPORATE_ACTIONS_UNVERIFIED"  # B7
SESSION_TIMES_ASSUMED = "SESSION_TIMES_ASSUMED"               # audit L7
TRADINGVIEW_PARITY_UNVERIFIED = "TRADINGVIEW_PARITY_UNVERIFIED"  # B8, B10
UNIVERSE_UNVERIFIED = "UNIVERSE_UNVERIFIED"                   # B11 / D1 constituent file
MEMBERSHIP_BEFORE_PROVISIONAL_WINDOW = "MEMBERSHIP_BEFORE_PROVISIONAL_WINDOW"  # D59
IDENTITY_UNVERIFIED = "IDENTITY_UNVERIFIED"                   # B11 instrument records (ED-21)
EXCLUDED_SESSION_UNOBSERVED = "EXCLUDED_SESSION_UNOBSERVED"   # D33 + D52: excluded session, no EOD file held
HISTORY_STARTS_AFTER_UNRESOLVED_DATE = "HISTORY_STARTS_AFTER_UNRESOLVED_DATE"   # D54, ED-44
PRICE_ADJUSTMENT_UNKNOWN = "PRICE_ADJUSTMENT_UNKNOWN"         # user CSV input
NOT_EXTERNALLY_VALIDATED = "NOT_EXTERNALLY_VALIDATED"
# an ignored in-progress candle has already reached the zone's proximal line: freshness
# after it is unknown until the candle completes (D23, spec 6.2); G1 MANUAL, never PASS
INCOMPLETE_CANDLE_TOUCH = "INCOMPLETE_CANDLE_TOUCH"



def source_verified(csv_path, source, source_file, source_sha256):
    """A record's provenance counts as verified only when its source is named and the file
    it cites exists (relative to the CSV's folder, or absolute) and hashes to the recorded
    SHA-256. A well-formed hash string alone proves nothing (audit 2026-11-06)."""
    sha = (source_sha256 or "").strip().lower()
    if not (source or "").strip() or not (source_file or "").strip() or len(sha) != 64:
        return False
    path = source_file.strip()
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.abspath(csv_path)), path)
    if not os.path.isfile(path):
        return False
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest() == sha


# --- owner-approved portfolio policy (DECISION_LOG D42, D45, D46) -----------------------
# USER_STATED operating constraints, not Rulebook rules (the Rulebook's own ceiling is 10
# trades per month, RB 2392). The journal enforces them; the backtest refuses a model that
# exceeds them (D45).
OWNER_MAX_OPEN_POSITIONS = 10
OWNER_MONTHLY_TRADE_CAP = 10
OWNER_ENTRY_EXPIRY_SESSIONS = 10
# IST has had no daylight saving since 1945, so a fixed offset is exact for every date the
# system handles (no tzdata dependency).
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30), "IST")


def ist_month(t):
    """(year, month) of t in IST (D42, D46: the monthly cap counts the first fill/trigger
    time converted to IST; the month runs from 00:00 IST on day 1). A naive time is already
    exchange-local IST (every candle and journal time in this system is)."""
    if t.tzinfo is not None and t.utcoffset() is not None:
        t = t.astimezone(IST)
    return t.year, t.month

# --- always-manual checklist for an actionable candidate (spec section 8) -------------
CHECKLIST = (
    ("EXPLOSIVE_RELATIVE_SIZE_CONTEXT", "Explosive leg-out relative size and context", "D8; RB 740-741"),
    ("GAP_MEANINGFULNESS", "Gap meaningfulness", "RB 941, 2974"),
    ("AUTHENTICITY", "Zone authenticity / reaction zone", "RB 594-631 RF7"),
    ("GARBAGE_CHART", "Chart is not garbage", "RB RF4"),
    ("LOTL", "Left of the left (LOTL)", "spec section 8"),
    ("CAME_FROM", "Where is price coming from", "RB 1316"),
    ("TARGET_QUALITY", "Target zone quality", "spec 6.4"),
    ("BUFFER_SELECTION", "Entry and SL buffer selection within the printed tiers", "D7; B9"),
    ("SECTOR", "Sector support (not evaluated, D6)", "D6; RB 484-499"),
    ("CORPORATE_ACTIONS", "Prices are not distorted by a split, bonus or other corporate action", "B7"),
    ("TRADER_STATE", "Trader state: RF5 emotion, RF9 mental state, RF10 scared money, Essential Check 10", "RB 594-631"),
)


@dataclass
class GateResult:
    gate: str
    outcome: str
    reasons: List[str] = field(default_factory=list)       # machine codes with short text
    manual_review: List[str] = field(default_factory=list)  # items that make it MANUAL
    evidence: Dict[str, object] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)        # RB / PS / D / spec references

    def __post_init__(self):
        if self.gate not in GATES:
            raise ValueError("unknown gate %r" % self.gate)
        if self.outcome not in OUTCOMES:
            raise ValueError("unknown gate outcome %r" % self.outcome)


@dataclass
class CandidateResult:
    """One execution zone of one symbol, evaluated through G0-G8."""
    symbol: str
    trade_type: str
    execution_tf: str
    as_of: str
    zone: Dict[str, object]
    gates: List[GateResult]
    status: str
    status_reasons: List[str]
    manual_review: List[str]
    manual_checks: List[Dict[str, str]]
    evidence_for: List[str]
    evidence_against: List[str]
    levels: Dict[str, object]
    limitations: List[str]

    def gate(self, name):
        for g in self.gates:
            if g.gate == name:
                return g
        raise KeyError(name)

    def to_dict(self):
        return asdict(self)


def derive_status(gates):
    """Final status from gate outcomes. The most restrictive outcome wins, so a later
    PASS can never override an earlier FAIL, DATA_INSUFFICIENT or MANUAL, and a result
    with a NOT_EVALUATED gate can never be actionable."""
    outcomes = [g.outcome for g in gates]
    if len(gates) != len(GATES) or [g.gate for g in gates] != list(GATES):
        raise ValueError("every gate G0-G8 must be present, in order")
    if BLOCKED in outcomes:
        return BLOCKED_STATUS
    if FAIL in outcomes:
        return REJECTED
    if DATA_INSUFFICIENT in outcomes:
        return STATUS_DATA_INSUFFICIENT
    if MANUAL in outcomes or NOT_EVALUATED in outcomes:
        return MANUAL_REVIEW
    return ACTIONABLE
