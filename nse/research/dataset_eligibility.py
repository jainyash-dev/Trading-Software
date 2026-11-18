"""Symbol-date eligibility for the historical research dataset.

Each symbol-date is judged on its own gates. An unresolved symbol removes that
symbol's affected dates. It does not change another symbol's gate results.
Passing rows are a certified subset. They are the complete Nifty 100 only when
the caller states that index-wide membership evidence is resolved and every
required member on that date passes. Count approval and mapping approval are
not that statement. This module does not approve a trade: authorises_order is
false on every result.
"""

ELIGIBLE = "ELIGIBLE"
EXCLUDED_MEMBERSHIP = "EXCLUDED_MEMBERSHIP"
EXCLUDED_IDENTITY = "EXCLUDED_IDENTITY"
EXCLUDED_CORPORATE_ACTION = "EXCLUDED_CORPORATE_ACTION"
EXCLUDED_CALENDAR = "EXCLUDED_CALENDAR"
EXCLUDED_EOD = "EXCLUDED_EOD"
EXCLUDED_PRICE = "EXCLUDED_PRICE"
EXCLUDED_GTF = "EXCLUDED_GTF"

MEMBERSHIP_VERIFIED = "VERIFIED"
IDENTITY_RESOLVED = "RESOLVED"
CA_COVERED_EVENTS = "COVERED_WITH_VERIFIED_EVENTS"   # NOT passing (D62): events parsed, completeness unproved
CA_COVERED_NONE = "COVERED_NO_EVENTS_PROVED"         # a source proves the window and the absence of events
CA_COMPLETE = "CA_COMPLETENESS_VERIFIED"             # D62: a source proves the window complete
CALENDAR_TRADING_DAY = "TRADING_DAY"
EOD_ACCEPTED = "ACCEPTED"
PRICE_CONTINUOUS = "CONTINUOUS"
GTF_PASS = "PASS"

LABEL_SUBSET = "CERTIFIED_SUBSET"
LABEL_NONE = "NO_CERTIFIED_SYMBOL_DATES"
LABEL_FULL = "COMPLETE_NIFTY100"

# A value outside the passing set fails closed, including a missing gate.
_GATES = (
    ("membership", frozenset({MEMBERSHIP_VERIFIED}), EXCLUDED_MEMBERSHIP),
    ("identity", frozenset({IDENTITY_RESOLVED}), EXCLUDED_IDENTITY),
    # D62: response integrity is not completeness; only proved completeness passes
    ("corporate_action", frozenset({CA_COMPLETE, CA_COVERED_NONE}), EXCLUDED_CORPORATE_ACTION),
    ("calendar", frozenset({CALENDAR_TRADING_DAY}), EXCLUDED_CALENDAR),
    ("eod", frozenset({EOD_ACCEPTED}), EXCLUDED_EOD),
    ("price_continuity", frozenset({PRICE_CONTINUOUS}), EXCLUDED_PRICE),
    ("gtf", frozenset({GTF_PASS}), EXCLUDED_GTF),
)


# The six data gates of the P0 data certification (owner decision D63). P0 data
# certification does not require the GTF gate; a data-certified symbol-date is not a
# GTF trade-eligible one. Without required_gates every gate below is required, as before.
DATA_GATES = ("membership", "identity", "corporate_action", "calendar", "eod", "price_continuity")


def passing_gates():
    """One passing value per gate, for tests and for a caller that has proved each one."""
    return {
        "membership": MEMBERSHIP_VERIFIED,
        "identity": IDENTITY_RESOLVED,
        "corporate_action": CA_COMPLETE,
        "calendar": CALENDAR_TRADING_DAY,
        "eod": EOD_ACCEPTED,
        "price_continuity": PRICE_CONTINUOUS,
        "gtf": GTF_PASS,
    }


def classify_symbol_date(symbol, trade_date, isin, gates, evidence="", required_gates=None):
    """One symbol on one date. `gates` maps each gate name to its status string.

    The first failed gate in `_GATES` order is the blocking gate. Every failed
    gate is named in the reason. A missing gate is UNKNOWN and fails.
    required_gates: names from `_GATES` to evaluate (e.g. DATA_GATES); default all.
    An unknown name is refused rather than ignored.
    """
    required = _required(required_gates)
    symbol = (symbol or "").strip().upper()
    day = str(trade_date)
    failed = []
    seen = {}
    for name, ok, code in _GATES:
        if name not in required:
            continue
        value = (gates or {}).get(name) or "UNKNOWN"
        seen[name] = value
        if value not in ok:
            failed.append((name, code, value))
    if not failed:
        return {
            "symbol": symbol, "trade_date": day, "isin": isin or "",
            "final_eligibility": ELIGIBLE, "blocking_gate": "", "exclusion_reason": "",
            "failed_gates": "", "gate_results": seen, "evidence": evidence,
            "authorises_order": False,
        }
    blocking, code, value = failed[0]
    detail = ", ".join("%s=%s" % (name, got) for name, _, got in failed)
    reason = "%s %s: blocked at %s (%s). Failed gates: %s." % (symbol, day, blocking, value, detail)
    if evidence:
        reason = "%s Evidence: %s." % (reason, evidence)
    return {
        "symbol": symbol, "trade_date": day, "isin": isin or "",
        "final_eligibility": code, "blocking_gate": blocking, "exclusion_reason": reason,
        "failed_gates": detail, "gate_results": seen, "evidence": evidence,
        "authorises_order": False,
    }


def _required(required_gates):
    names = tuple(name for name, _, _ in _GATES)
    if required_gates is None:
        return frozenset(names)
    unknown = sorted(set(required_gates) - set(names))
    missing = sorted(set(DATA_GATES) - set(required_gates))
    if unknown or missing:
        # every data gate is always required: a subset cannot certify on fewer gates
        raise ValueError("required_gates must include every gate in %s and name only gates in %s; "
                         "unknown %s, missing %s" % (DATA_GATES, names, unknown, missing))
    return frozenset(required_gates)


def certify_members(rows, index_evidence_resolved=False, required_symbols=None, required_gates=None):
    """Label a set of symbol-dates that share one trade date.

    `index_evidence_resolved` must be supplied by a caller that has checked the
    index-wide membership evidence. This function never sets it from a count
    approval, a mapping approval, or from the rows themselves.
    """
    classified = []
    for row in rows:
        classified.append(classify_symbol_date(
            row["symbol"], row["trade_date"], row.get("isin", ""), row.get("gates") or {},
            row.get("evidence", ""), required_gates=required_gates))
    eligible = [r for r in classified if r["final_eligibility"] == ELIGIBLE]
    excluded = [r for r in classified if r["final_eligibility"] != ELIGIBLE]
    required = set(required_symbols) if required_symbols is not None else {r["symbol"] for r in classified}
    eligible_symbols = {r["symbol"] for r in eligible}
    excluded_symbols = {r["symbol"] for r in excluded}
    full = (bool(index_evidence_resolved) and bool(classified) and not excluded_symbols
            and required <= eligible_symbols)
    if full:
        label = LABEL_FULL
    elif eligible:
        label = LABEL_SUBSET
    else:
        label = LABEL_NONE
    return {
        "label": label,
        "full_index_certified": full,
        "complete_nifty100": full,
        "index_evidence_resolved": bool(index_evidence_resolved),
        "rows": classified,
        "eligible_count": len(eligible),
        "excluded_count": len(excluded),
        "authorises_order": False,
    }
