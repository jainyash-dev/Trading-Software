"""Build the Phase 01 T-001 owner worksheet (read-only on all canonical data).

    python3 docs/product-discovery/phase-01/tools/build_t001_worksheet.py

Reads nse/data/universe/ (review file, verifier packet, transcription files, evidence
registry) and runs membership.convert in memory. Writes only
docs/product-discovery/phase-01/T001_nifty100_owner_worksheet.csv and prints a summary.

The worksheet is NOT the review file. Its proposed_* columns are recommendations; its
owner_* columns are blank for the owner. Decisions take effect only when the owner copies
them into nse/data/universe/nifty100_review.csv (README there, section "How to review").
"""

import csv
import hashlib
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
from nse.research import instruments, membership as ms  # noqa: E402

U = os.path.join(ROOT, "nse", "data", "universe")
OUT = os.path.join(ROOT, "docs", "product-discovery", "phase-01", "T001_nifty100_owner_worksheet.csv")
IMAGE_ONLY = {"ind_prs23082021.pdf"}           # evidence/sources.csv: "NOT TRANSCRIBED (image-only PDF)"
LIVE_LISTS = {"symbolchange.csv"}               # NSE live list, copy retrieved 2026-11-09

COLUMNS = ["row_id", "row_sha256", "row_type", "symbol", "isin", "event_id", "action", "reason",
           "effective_date", "announcement_date", "source_doc", "source_file", "source_file_hash_check",
           "verifier_verdict", "verifier_detail", "periods_starting", "periods_ending", "affects_all_periods",
           "identity_finding", "evidence_status", "review_priority", "proposed_action", "proposed_reason",
           "existing_decision", "owner_decision", "owner_reviewer", "owner_reviewed_on", "owner_notes"]


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main():
    review = list(csv.DictReader(open(os.path.join(U, "nifty100_review.csv"), encoding="utf-8")))
    packet = {r["row_key"]: r for r in csv.DictReader(open(os.path.join(U, "nifty100_review_packet.csv"), encoding="utf-8"))}
    registry = {r["file_name"].split("/")[-1]: r["sha256"]
                for r in csv.DictReader(open(os.path.join(U, "evidence", "sources.csv"), encoding="utf-8"))}

    # transcription rows by key, exactly as membership parses them
    problems = []
    rows = {r.key: r for r in ms._baseline(os.path.join(U, "nifty100_baseline.csv"), problems)
            + ms._changes(os.path.join(U, "nifty100_changes.csv"), problems)}
    exceptions = {("exception:%s" % r["effective_date"]): r
                  for r in csv.DictReader(open(os.path.join(U, "nifty100_count_exceptions.csv"), encoding="utf-8"))}
    assert not problems, problems

    # periods per row: capture each period as the converter emits it
    starts, ends, ident = defaultdict(list), defaultdict(list), {}
    original = ms._out_row

    def capture(p, reviewed=True):
        label = "%s %s %s..%s" % (p.start.symbol, p.start.isin, p.start.date, p.end.date if p.end else "open")
        starts[p.start.key].append(label)
        if p.end is not None:
            ends[p.end.key].append(label)
        if p.identity:
            ident[p.start.key] = "; ".join("%s: %s" % (f["code"], f["detail"]) for f in p.identity)
        return original(p, reviewed)

    ms._out_row = capture
    try:
        conv = ms.convert(os.path.join(U, "nifty100_baseline.csv"), os.path.join(U, "nifty100_changes.csv"),
                          count_exceptions_path=os.path.join(U, "nifty100_count_exceptions.csv"),
                          review_path=os.path.join(U, "nifty100_review.csv"),
                          instrument_records=instruments.load(os.path.join(U, "instrument_records.csv")))
    finally:
        ms._out_row = original

    out = []
    for rv in review:
        key = rv["row_key"]
        pk = packet.get(key, {})
        verdict = pk.get("verifier_verdict", "ABSENT")
        rec = {c: "" for c in COLUMNS}
        rec.update(row_id=key, row_sha256=rv["row_sha256"], verifier_verdict=verdict,
                   verifier_detail=(pk.get("detail") or "")[:300], existing_decision=rv["decision"] or "BLANK")
        if key.startswith("exception:"):
            e = exceptions[key]
            doc = e["source_doc_id"]
            path = os.path.join(U, "evidence", "releases", doc)
            ok = os.path.isfile(path) and sha(path) == registry.get(doc)
            rec.update(row_type="COUNT_EXCEPTION", effective_date=e["effective_date"], source_doc=doc,
                       source_file="evidence/releases/" + doc,
                       source_file_hash_check="MATCH" if ok else "MISSING_OR_MISMATCH",
                       action="COUNT=%s" % e["members"], reason=e["basis"][:200], affects_all_periods="YES")
        else:
            r = rows[key]
            fname = os.path.basename(r.source_file)
            ok = os.path.isfile(r.source_file) and sha(r.source_file) == r.source_sha256
            rec.update(row_type="BASELINE" if r.kind == "BASELINE" else "CHANGE", symbol=r.symbol, isin=r.isin,
                       event_id=r.event_id, action=r.kind, reason=r.reason, effective_date=r.date.isoformat(),
                       announcement_date=r.announced.isoformat() if r.announced else "",
                       source_doc=r.source_doc_id or fname, source_file=os.path.relpath(r.source_file, U),
                       source_file_hash_check="MATCH" if ok else "MISSING_OR_MISMATCH",
                       periods_starting=" | ".join(starts.get(key, [])), periods_ending=" | ".join(ends.get(key, [])),
                       affects_all_periods="NO", identity_finding=ident.get(key, ""))
        hash_ok = rec["source_file_hash_check"] == "MATCH"
        src = os.path.basename(rec["source_file"])
        if verdict == "ABSENT" or not hash_ok:
            status, prio, action, why = ("EVIDENCE_ABSENT", "P1", "OWNER_DECISION_REQUIRED",
                                         "no verifier verdict or the cited file is missing / does not match its hash")
        elif verdict == "INFERENCE":
            status, prio, action, why = ("EVIDENCE_INCOMPLETE", "P2", "OWNER_JUDGEMENT_REQUIRED",
                                         "release prints the dummy symbol and date verbatim; the ISIN is inferred from the "
                                         "later listing by entity name only. ACCEPT accepts that inference; the period stays "
                                         "unverified either way while the dummy symbol has no identity record")
        elif src in IMAGE_ONLY:
            status, prio, action, why = ("EVIDENCE_CONFIRMED_VISUAL_READ", "P2", "ACCEPT_AFTER_VISUAL_CHECK",
                                         "image-only PDF read visually by the verifier; check page 5 section 3) NIFTY 100 yourself")
        elif rec["row_type"] == "COUNT_EXCEPTION":
            status, prio, action, why = ("EVIDENCE_CONFIRMED", "P1", "ACCEPT_RECOMMENDED",
                                         "count derived from the cited release; every one of the 25 exceptions must be ACCEPTED "
                                         "or no period can be verified (membership.convert exceptions_ok)")
        elif src in LIVE_LISTS:
            status, prio, action, why = ("EVIDENCE_CONFIRMED_LIVE_LIST", "P3", "ACCEPT_RECOMMENDED",
                                         "same-ISIN symbol change in NSE's live symbolchange.csv (copy of 2026-11-09, hash matches)")
        else:
            status, prio, action, why = ("EVIDENCE_CONFIRMED", "P3", "ACCEPT_RECOMMENDED",
                                         "verifier VERIFIED against the cited official document; file hash matches")
        if rec["identity_finding"]:
            why += "; NOTE: the period this row starts stays UNVERIFIED after acceptance (identity finding)"
        rec.update(evidence_status=status, review_priority=prio, proposed_action=action, proposed_reason=why)
        out.append(rec)

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(out)
    print("rows", len(out), "periods", conv.report["periods"], "review", conv.report["review"]["status"])
    print("evidence_status", dict(Counter(r["evidence_status"] for r in out)))
    print("priority", dict(Counter(r["review_priority"] for r in out)))
    print("proposed_action", dict(Counter(r["proposed_action"] for r in out)))
    print("hash_check", dict(Counter(r["source_file_hash_check"] for r in out)))
    print("rows_with_identity_finding", sum(1 for r in out if r["identity_finding"]))
    print("rows_starting_no_period", sum(1 for r in out if r["row_type"] != "COUNT_EXCEPTION" and not r["periods_starting"]))


if __name__ == "__main__":
    main()
