"""Point-in-time membership converter tests (nse/research/membership.py; D1, D31, B11).

Every baseline, change file, ISIN and document here is SYNTHETIC (made-up symbols and
ISINs). Expected behaviour comes from nse/docs/REAL_DATA_READINESS.md section 5: exact
headers, ISIN shape, announcement <= effective, balanced events, ADD not a member and
REMOVE a member, exactly N members after every effective date, roll forward only, and
verified provenance only for a held file with a matching SHA-256. Most cases use N=4 via
the expected_members parameter; one case uses the Nifty 100 default of 100.
"""

import csv
import datetime
import hashlib
import os
import shutil
import tempfile
import unittest

from nse.research import instruments as ins, membership as ms, models as m, universe

D = datetime.date
DOC = b"SYNTHETIC index notice"
SHA = hashlib.sha256(DOC).hexdigest()
BASE_HEADER = ",".join(ms.BASELINE_COLUMNS)
CHG_HEADER = ",".join(ms.CHANGES_COLUMNS)
AS_OF = "2022-01-03"


def isin(n):
    return "INE%09d" % n


def brow(sym, n, as_of=AS_OF, index="NIFTY 100", verified=True, isin_value=None):
    src, f, sha = ("SYNTHETIC factsheet", "doc.pdf", SHA) if verified else ("", "", "")
    return ",".join([index, as_of, sym, isin_value or isin(n), "EQ", src, "FS-1", f, sha, "2026-01-01",
                     "SYNTHETIC"])


def crow(eid, action, sym, n, eff="2022-03-31", ann="2022-02-25", replaces="", reason="RECONSTITUTION",
         index="NIFTY 100", verified=True, isin_value=None):
    src, f, sha = ("SYNTHETIC notice", "doc.pdf", SHA) if verified else ("", "", "")
    return ",".join([eid, index, ann, eff, action, sym, isin_value or isin(n), "EQ", replaces, reason, src,
                     "N-" + eid, f, sha, "2026-01-01", "SYNTHETIC; effective_date as transcribed"])


FOUR = [brow("AAA", 1), brow("BBB", 2), brow("CCC", 3), brow("DDD", 4)]
EVENT1 = [crow("E1", "REMOVE", "BBB", 2), crow("E1", "ADD", "EEE", 5, replaces=isin(2))]
EVENT2 = [crow("E2", "REMOVE", "EEE", 5, eff="2022-09-30", ann="2022-08-26"),
          crow("E2", "ADD", "FFF", 6, eff="2022-09-30", ann="2022-08-26", replaces=isin(5))]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        with open(os.path.join(self.tmp, "doc.pdf"), "wb") as fh:
            fh.write(DOC)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, name, header, rows):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(header + "\n" + "".join(r + "\n" for r in rows))
        return path

    def convert(self, base=FOUR, changes=(), n=4, base_header=BASE_HEADER, chg_header=CHG_HEADER, records=None,
                reviewed=True):
        # D49 (owner 2026-11-09, specification correction): verification also needs an accepted
        # human review of these exact files; most tests are about the rows, so they pass one
        b = self.write("nifty100_baseline.csv", base_header, base)
        c = self.write("nifty100_changes.csv", chg_header, list(changes))
        try:
            review = self.review(b, c) if reviewed else None
        except ms.MembershipError:
            review = None                     # an invalid fixture: convert must report every problem
        return ms.convert(b, c, expected_members=n, instrument_records=records, review_path=review)

    def review(self, b, c, x=None, decision="ACCEPTED", reviewer="SYNTHETIC REVIEWER", on="2026-11-09",
               override=None):
        """A SYNTHETIC per-row review (D53): every template row decided; override maps a row
        key to (decision, row_sha256) to model a rejected or stale decision."""
        rows = []
        for t in ms.review_template(b, c, x):
            dec, sha = (override or {}).get(t["row_key"], (decision, t["row_sha256"]))
            # Scope columns stay blank unless a test sets them. A legacy ACCEPTED is not
            # copied into count_approval or mapping_approval.
            rows.append(",".join([t["row_key"], sha, dec, reviewer, on, "SYNTHETIC", "", ""]))
        return self.write("nifty100_review.csv", ",".join(ms.REVIEW_COLUMNS), rows)

    def refused(self, needle, **kw):
        with self.assertRaises(ms.MembershipError) as cm:
            self.convert(**kw)
        self.assertTrue(any(needle in p for p in cm.exception.problems), cm.exception.problems)
        return cm.exception.problems

    def to_universe(self, conv, sub="out"):
        folder = os.path.join(self.tmp, sub)
        os.makedirs(folder, exist_ok=True)
        return universe.load(ms.write(conv.rows, os.path.join(folder, "universe.csv")))


class Validation(Base):
    """SYNTHETIC: one refused input per rule in REAL_DATA_READINESS section 5."""

    def test_baseline_header_exact(self):
        self.refused("header must be exactly", base_header=BASE_HEADER.replace("symbol,isin", "isin,symbol"))

    def test_changes_header_exact(self):
        self.refused("header must be exactly", changes=EVENT1, chg_header=CHG_HEADER + ",extra")

    def test_isin_shape(self):
        self.refused("is not IN + 10", base=FOUR[:3] + [brow("DDD", 4, isin_value="US0000000001")])
        self.refused("is not IN + 10", changes=[EVENT1[0], crow("E1", "ADD", "EEE", 5, isin_value="INE12")])

    def test_dates_iso(self):
        self.refused("as_of_date '03/01/2022'", base=FOUR[:3] + [brow("DDD", 4, as_of="03/01/2022")])
        self.refused("effective_date", changes=[crow("E1", "REMOVE", "BBB", 2, eff="2022-3-31"), EVENT1[1]])

    def test_announcement_not_after_effective(self):
        self.refused("is after effective_date",
                     changes=[crow("E1", "REMOVE", "BBB", 2, ann="2022-04-01"), EVENT1[1]])

    def test_action_vocabulary(self):
        self.refused("action 'DROP'", changes=[crow("E1", "DROP", "BBB", 2), EVENT1[1]])

    def test_reason_vocabulary(self):
        self.refused("reason 'REBALANCE'", changes=[crow("E1", "REMOVE", "BBB", 2, reason="REBALANCE"), EVENT1[1]])

    def test_one_index_name(self):
        self.refused("index_name must be one value", changes=[crow("E1", "REMOVE", "BBB", 2, index="NIFTY 50"),
                                                              EVENT1[1]])

    def test_event_add_remove_balanced(self):
        self.refused("1 ADD and 0 REMOVE", changes=[EVENT1[1]])

    def test_replaces_isin_is_remove_in_same_event(self):
        self.refused("replaces_isin %s is not a REMOVE" % isin(3),
                     changes=[EVENT1[0], crow("E1", "ADD", "EEE", 5, replaces=isin(3))])

    def test_one_effective_date_per_event(self):
        self.refused("one effective_date per event",
                     changes=[EVENT1[0], crow("E1", "ADD", "EEE", 5, eff="2022-04-01")])

    def test_add_must_not_be_member(self):
        self.refused("is already a member", changes=[EVENT1[0], crow("E1", "ADD", "CCC", 3)])

    def test_remove_must_be_member(self):
        self.refused("is not a member", changes=[crow("E1", "REMOVE", "ZZZ", 9), crow("E1", "ADD", "EEE", 5)])

    def test_baseline_duplicate_isin(self):
        self.refused("duplicate isin", base=FOUR[:3] + [brow("DDD", 3)])

    def test_baseline_duplicate_symbol(self):
        self.refused("duplicate symbol", base=FOUR[:3] + [brow("CCC", 4)])

    def test_baseline_member_count(self):
        self.refused("has 3 members, expected 4", base=FOUR[:3])

    def test_member_count_after_each_effective_date(self):
        # balanced per event, but two events on one day remove the same stock twice in effect
        # (second REMOVE is not a member), leaving an unbalanced composition
        problems = self.refused("expected 4", changes=EVENT1 + [crow("E3", "REMOVE", "BBB", 2),
                                                                crow("E3", "ADD", "GGG", 7)])
        self.assertTrue(any("is not a member" in p for p in problems))

    def test_change_on_or_before_baseline_refused(self):
        self.refused("rolls forward only", changes=[crow("E1", "REMOVE", "BBB", 2, eff=AS_OF, ann="2021-12-01"),
                                                    crow("E1", "ADD", "EEE", 5, eff=AS_OF, ann="2021-12-01")])

    def test_every_problem_reported_and_nothing_converted(self):
        with self.assertRaises(ms.MembershipError) as cm:
            self.convert(base=FOUR[:3] + [brow("CCC", 3)],
                         changes=[crow("E1", "DROP", "BBB", 2, reason="X")])
        self.assertGreaterEqual(len(cm.exception.problems), 4)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "out")))


class Conversion(Base):
    """SYNTHETIC happy paths: rolling membership, inclusive boundaries, provenance."""

    def test_two_events_roll_forward(self):
        conv = self.convert(changes=EVENT1 + EVENT2)
        rep = conv.report
        self.assertEqual(rep["members_by_date"], {AS_OF: 4, "2022-03-31": 4, "2022-09-30": 4})
        self.assertEqual(rep["events_applied"], ["E1", "E2"])
        self.assertEqual(rep["unverified_rows"], [])
        self.assertEqual(rep["unverified_periods"], 0)
        u = self.to_universe(conv)
        self.assertEqual([r.symbol for r in u.members(D(2022, 1, 3))], ["AAA", "BBB", "CCC", "DDD"])
        self.assertEqual([r.symbol for r in u.members(D(2022, 6, 1))], ["AAA", "CCC", "DDD", "EEE"])
        self.assertEqual([r.symbol for r in u.members(D(2022, 10, 1))], ["AAA", "CCC", "DDD", "FFF"])
        self.assertEqual(u.members(D(2022, 1, 2)), [])          # nothing claimed before the baseline
        self.assertEqual(u.limitations(D(2022, 6, 1)), [])
        for d in (D(2022, 1, 3), D(2022, 3, 30), D(2022, 3, 31), D(2022, 9, 30), D(2023, 1, 1)):
            self.assertEqual(u.balance(d, 4), (4, True))

    def test_inclusive_boundaries(self):
        u = self.to_universe(self.convert(changes=EVENT1))
        on = lambda d: {r.symbol for r in u.members(d)}
        self.assertIn("BBB", on(D(2022, 3, 30)))                # effective_date - 1: still a member
        self.assertNotIn("BBB", on(D(2022, 3, 31)))             # effective_date: gone
        self.assertNotIn("EEE", on(D(2022, 3, 30)))
        self.assertIn("EEE", on(D(2022, 3, 31)))                # ADD is a member on effective_date

    def test_rows_keep_source_and_isin(self):
        conv = self.convert(changes=EVENT1)
        bbb = [r for r in conv.rows if r["symbol"] == "BBB"][0]
        self.assertEqual((bbb["effective_from"], bbb["effective_to"], bbb["isin"]), (AS_OF, "2022-03-30", isin(2)))
        self.assertEqual(bbb["source"], "SYNTHETIC factsheet")
        self.assertEqual(bbb["source_sha256"], SHA)
        self.assertIn("event E1 REMOVE", bbb["notes"])
        u = self.to_universe(conv)
        self.assertEqual({r.isin for r in u.members(D(2022, 4, 1))}, {isin(1), isin(3), isin(4), isin(5)})

    def test_round_trip_through_universe_load(self):
        conv = self.convert(changes=EVENT1 + EVENT2)
        u = self.to_universe(conv, sub="nested/deeper")         # source_file relativised to the output folder
        self.assertEqual(len(u.rows), len(conv.rows))
        self.assertTrue(all(r.verified for r in u.rows))
        got = sorted((r.symbol, r.isin, r.effective_from.isoformat(),
                      r.effective_to.isoformat() if r.effective_to else "") for r in u.rows)
        want = sorted((r["symbol"], r["isin"], r["effective_from"], r["effective_to"]) for r in conv.rows)
        self.assertEqual(got, want)

    def test_unverified_source_gives_universe_unverified(self):
        changes = [EVENT1[0], crow("E1", "ADD", "EEE", 5, replaces=isin(2), verified=False)]
        conv = self.convert(changes=changes)
        self.assertEqual([r["symbol"] for r in conv.report["unverified_rows"]], ["EEE"])
        u = self.to_universe(conv)
        self.assertEqual(u.limitations(D(2022, 3, 30)), [])
        self.assertEqual(u.limitations(D(2022, 3, 31)), [m.UNIVERSE_UNVERIFIED])

    def test_unverified_remove_makes_ended_period_unverified(self):
        changes = [crow("E1", "REMOVE", "BBB", 2, verified=False), EVENT1[1]]
        u = self.to_universe(self.convert(changes=changes))
        self.assertEqual(u.limitations(D(2022, 3, 1)), [m.UNIVERSE_UNVERIFIED])

    def test_hash_mismatch_is_unverified(self):
        with open(os.path.join(self.tmp, "doc.pdf"), "ab") as fh:
            fh.write(b" altered")
        conv = self.convert()
        self.assertEqual(len(conv.report["unverified_rows"]), 4)
        self.assertEqual(self.to_universe(conv).limitations(D(2022, 1, 3)), [m.UNIVERSE_UNVERIFIED])

    def test_baseline_only(self):
        b = self.write("nifty100_baseline.csv", BASE_HEADER, FOUR)
        conv = ms.convert(b, None, expected_members=4)
        self.assertEqual(conv.report["members_by_date"], {AS_OF: 4})

    def test_one_hundred_members(self):
        base = [brow("S%03d" % k, k) for k in range(1, 101)]
        changes = [crow("E1", "REMOVE", "S001", 1), crow("E1", "REMOVE", "S002", 2),
                   crow("E1", "ADD", "N001", 201, replaces=isin(1)), crow("E1", "ADD", "N002", 202, replaces=isin(2))]
        conv = self.convert(base=base, changes=changes, n=ms.DEFAULT_MEMBERS)
        self.assertEqual(conv.report["members_by_date"], {AS_OF: 100, "2022-03-31": 100})
        u = self.to_universe(conv)
        self.assertEqual(u.balance(D(2022, 3, 31), 100), (100, True))
        self.assertNotIn("S001", {r.symbol for r in u.members(D(2022, 3, 31))})
        with self.assertRaises(ms.MembershipError):
            self.convert(base=base[:99], n=ms.DEFAULT_MEMBERS)

    def test_members_without_data(self):
        u = self.to_universe(self.convert(changes=EVENT1))
        avail = {D(2022, 3, 30): {"AAA", "BBB", "CCC", "DDD"}, D(2022, 3, 31): {"AAA", "CCC", "DDD"}}
        self.assertEqual(ms.members_without_data(u, avail), {"2022-03-31": ["EEE"]})


class Identity(Base):
    """SYNTHETIC instrument records: identity findings mark a period unverified, never raise."""

    def records(self, rows):
        path = self.write("records.csv", ",".join(ins.COLUMNS), rows)
        return ins.load(path)

    def listing(self, sym, isin_value, verified=True):
        src, f, sha = ("SYNTHETIC listing", "doc.pdf", SHA) if verified else ("", "", "")
        return ",".join(["LISTING", sym, "", isin_value, "EQ", "2000-01-01", "", src, f, sha, "2026-01-01",
                         "SYNTHETIC"])

    def test_all_resolve(self):
        recs = self.records([self.listing(s, isin(k)) for s, k in
                             (("AAA", 1), ("BBB", 2), ("CCC", 3), ("DDD", 4), ("EEE", 5))])
        conv = self.convert(changes=EVENT1, records=recs)
        self.assertEqual(conv.report["identity_findings"], [])
        self.assertEqual(self.to_universe(conv).limitations(D(2022, 4, 1)), [])

    def test_mismatch_and_unknown(self):
        recs = self.records([self.listing("AAA", isin(1)), self.listing("BBB", isin(2)),
                             self.listing("CCC", isin(99)), self.listing("DDD", isin(4))])
        conv = self.convert(changes=EVENT1, records=recs)
        codes = {(f["symbol"], f["code"]) for f in conv.report["identity_findings"]}
        self.assertEqual(codes, {("CCC", ins.ISIN_RECORD_MISMATCH), ("EEE", ins.UNKNOWN_INSTRUMENT)})
        ccc = [r for r in conv.rows if r["symbol"] == "CCC"][0]
        self.assertEqual(ccc["source_sha256"], "")
        self.assertIn(SHA, ccc["notes"])                        # transcribed hash kept, not used
        u = self.to_universe(conv)
        self.assertEqual(u.limitations(D(2022, 1, 3)), [m.UNIVERSE_UNVERIFIED])
        self.assertEqual(conv.report["unverified_periods"], 2)

    def test_unverified_identity_record(self):
        recs = self.records([self.listing("AAA", isin(1), verified=False), self.listing("BBB", isin(2)),
                             self.listing("CCC", isin(3)), self.listing("DDD", isin(4))])
        conv = self.convert(records=recs)
        self.assertEqual([f["code"] for f in conv.report["identity_findings"]], [ins.UNVERIFIED])


if __name__ == "__main__":
    unittest.main()


class CountExceptions(unittest.TestCase):
    """ED-22: an official count other than N (e.g. NIFTY 100 from 29 Sep 2023: six inclusions,
    five exclusions) is accepted only when declared for that date. SYNTHETIC files."""

    def setUp(self):
        self.h = Validation("test_event_add_remove_balanced")
        self.h.setUp()
        self.addCleanup(self.h.tearDown)
        self.extra = EVENT1 + [crow("E1", "ADD", "FFF", 6)]          # 2 ADD, 1 REMOVE -> 5 members

    def convert(self, exceptions):
        b = self.h.write("nifty100_baseline.csv", BASE_HEADER, FOUR)
        c = self.h.write("nifty100_changes.csv", CHG_HEADER, self.extra)
        return ms.convert(b, c, expected_members=4, count_exceptions=exceptions)

    def test_undeclared_imbalance_is_refused(self):
        with self.assertRaises(ms.MembershipError) as cm:
            self.convert(None)
        self.assertTrue(any("2 ADD and 1 REMOVE" in p for p in cm.exception.problems))

    def test_declared_exception_is_accepted_and_reported(self):
        conv = self.convert({D(2022, 3, 31): 5})
        self.assertEqual(conv.report["members_by_date"]["2022-03-31"], 5)
        self.assertEqual(conv.report["count_exceptions_used"], {"2022-03-31": 5})
        u = self.h.to_universe(conv)
        self.assertEqual(u.balance(D(2022, 3, 31), 5), (5, True))
        self.assertEqual(u.balance(D(2022, 3, 30), 4), (4, True))

    def test_a_declared_count_must_match_exactly(self):
        with self.assertRaises(ms.MembershipError) as cm:
            self.convert({D(2022, 3, 31): 6})
        self.assertTrue(any("expected 6 (declared exception)" in p for p in cm.exception.problems))


class ReviewGate(unittest.TestCase):
    """D49 / D53: a period is verified only when its own rows are ACCEPTED, row by row."""

    def setUp(self):
        self.h = Validation("test_event_add_remove_balanced")
        self.h.setUp()
        self.addCleanup(self.h.tearDown)
        self.b = self.h.write("nifty100_baseline.csv", BASE_HEADER, FOUR)
        self.c = self.h.write("nifty100_changes.csv", CHG_HEADER, EVENT1)

    def run_with(self, review):
        conv = ms.convert(self.b, self.c, expected_members=4, review_path=review)
        return conv, self.h.to_universe(conv)

    def key(self, prefix):
        return [t for t in ms.review_template(self.b, self.c) if t["row_key"].startswith(prefix)][0]

    def test_without_review_every_period_is_unverified(self):
        conv, u = self.run_with(None)
        self.assertEqual(conv.report["review"]["status"], "NOT_REVIEWED")
        self.assertEqual(conv.report["unverified_periods"], conv.report["periods"])
        self.assertEqual(u.limitations(D(2022, 6, 1)), [m.UNIVERSE_UNVERIFIED])

    def test_every_row_accepted_verifies(self):
        conv, u = self.run_with(self.h.review(self.b, self.c))
        self.assertEqual((conv.report["review"]["status"], conv.report["review"]["accepted"]), ("COMPLETE", 6))
        self.assertEqual(u.limitations(D(2022, 6, 1)), [])

    def test_a_template_is_undecided_and_verifies_nothing(self):
        rows = ms.review_template(self.b, self.c)
        self.assertEqual(set(r["decision"] for r in rows), {""})
        path = self.h.write("nifty100_review.csv", ",".join(ms.REVIEW_COLUMNS),
                            [",".join(r[c] for c in ms.REVIEW_COLUMNS) for r in rows])
        conv, u = self.run_with(path)
        self.assertEqual(conv.report["unverified_periods"], conv.report["periods"])

    def test_only_the_periods_of_a_rejected_row_stay_unverified(self):
        t = self.key("change:E1:ADD:EEE")
        conv, u = self.run_with(self.h.review(self.b, self.c, override={t["row_key"]: ("REJECTED", t["row_sha256"])}))
        self.assertEqual(conv.report["review"]["rejected"], [t["row_key"]])
        self.assertEqual(u.limitations(D(2022, 3, 1)), [])                  # before EEE joins
        self.assertEqual(u.limitations(D(2022, 6, 1)), [m.UNIVERSE_UNVERIFIED])

    def test_a_decision_on_other_row_contents_does_not_count(self):
        t = self.key("baseline:AAA")
        conv, u = self.run_with(self.h.review(self.b, self.c, override={t["row_key"]: ("ACCEPTED", "0" * 64)}))
        self.assertEqual(conv.report["review"]["stale_hash"], [t["row_key"]])
        self.assertEqual(u.limitations(D(2022, 6, 1)), [m.UNIVERSE_UNVERIFIED])

    def test_incomplete_decisions_are_problems_not_acceptances(self):
        for kw in ({"reviewer": ""}, {"on": "yesterday"}, {"decision": "MAYBE"}):
            with self.subTest(**kw):
                conv, u = self.run_with(self.h.review(self.b, self.c, **kw))
                self.assertTrue(conv.report["review"]["problems"])
                self.assertEqual(u.limitations(D(2022, 6, 1)), [m.UNIVERSE_UNVERIFIED])

    def test_editing_a_row_after_review_voids_only_that_row(self):
        review = self.h.review(self.b, self.c)
        with open(self.c, "w") as fh:
            fh.write(CHG_HEADER + "\n" + EVENT1[0] + "\n" + EVENT1[1].replace("SYNTHETIC", "EDITED") + "\n")
        conv, u = self.run_with(review)
        self.assertEqual(len(conv.report["review"]["stale_hash"]), 1)
        self.assertEqual(u.limitations(D(2022, 3, 1)), [])
        self.assertEqual(u.limitations(D(2022, 6, 1)), [m.UNIVERSE_UNVERIFIED])

class Renames(unittest.TestCase):
    """A member's symbol change keeps its seat (ISIN), splitting the period by symbol. SYNTHETIC."""

    def setUp(self):
        self.h = Validation("test_event_add_remove_balanced")
        self.h.setUp()
        self.addCleanup(self.h.tearDown)

    def conv(self, changes):
        b = self.h.write("nifty100_baseline.csv", BASE_HEADER, FOUR)
        c = self.h.write("nifty100_changes.csv", CHG_HEADER, changes)
        return ms.convert(b, c, expected_members=4, review_path=self.h.review(b, c))

    def test_rename_splits_the_period_and_keeps_the_count(self):
        conv = self.conv([crow("R1", "RENAME", "BBX", 2, eff="2022-02-07", ann="2022-02-07")])
        u = self.h.to_universe(conv)
        self.assertEqual([x.symbol for x in u.members(D(2022, 2, 6))], ["AAA", "BBB", "CCC", "DDD"])
        self.assertEqual([x.symbol for x in u.members(D(2022, 2, 7))], ["AAA", "BBX", "CCC", "DDD"])
        self.assertEqual(set(x.isin for x in u.members(D(2022, 2, 7))), set(isin(n) for n in (1, 2, 3, 4)))
        self.assertEqual(conv.report["members_by_date"]["2022-02-07"], 4)

    def test_rename_of_a_non_member_is_refused(self):
        with self.assertRaises(ms.MembershipError) as cm:
            self.conv([crow("R1", "RENAME", "ZZZ", 9, eff="2022-02-07", ann="2022-02-07")])
        self.assertTrue(any("RENAME" in p and "is not a member" in p for p in cm.exception.problems))


class ReviewCoversExceptions(unittest.TestCase):
    """The count exceptions a conversion uses are reviewed rows too; duplicates refused."""

    def setUp(self):
        self.h = Validation("test_event_add_remove_balanced")
        self.h.setUp()
        self.addCleanup(self.h.tearDown)

    def test_an_unaccepted_exception_leaves_every_period_unverified(self):
        b = self.h.write("nifty100_baseline.csv", BASE_HEADER, FOUR)
        c = self.h.write("nifty100_changes.csv", CHG_HEADER, EVENT1 + [crow("E1", "ADD", "FFF", 6)])
        x = self.h.write("exceptions.csv", ",".join(ms.COUNT_EXCEPTION_COLUMNS), ["2022-03-31,5,doc.pdf,SYNTHETIC"])
        conv = ms.convert(b, c, expected_members=4, count_exceptions_path=x, review_path=self.h.review(b, c, x))
        self.assertEqual(conv.report["review"]["status"], "COMPLETE")
        self.assertEqual(conv.report["unverified_periods"], 0)
        t = [r for r in ms.review_template(b, c, x) if r["row_key"] == "exception:2022-03-31"][0]
        review = self.h.review(b, c, x, override={t["row_key"]: ("REJECTED", t["row_sha256"])})
        conv = ms.convert(b, c, expected_members=4, count_exceptions_path=x, review_path=review)
        self.assertFalse(conv.report["review"]["count_exceptions_accepted"])
        self.assertEqual(conv.report["unverified_periods"], conv.report["periods"])

    def test_a_date_declared_twice_is_refused(self):
        x = self.h.write("exceptions.csv", ",".join(ms.COUNT_EXCEPTION_COLUMNS),
                         ["2022-03-31,5,doc.pdf,A", "2022-03-31,6,doc.pdf,B"])
        with self.assertRaises(ms.MembershipError):
            ms.load_count_exceptions(x)


class IsinChanges(unittest.TestCase):
    """A member's ISIN change (e.g. a face-value split) keeps its seat. SYNTHETIC."""

    def setUp(self):
        self.h = Validation("test_event_add_remove_balanced")
        self.h.setUp()
        self.addCleanup(self.h.tearDown)

    def conv(self, changes):
        b = self.h.write("nifty100_baseline.csv", BASE_HEADER, FOUR)
        c = self.h.write("nifty100_changes.csv", CHG_HEADER, changes)
        return ms.convert(b, c, expected_members=4, review_path=self.h.review(b, c))

    def test_isin_change_splits_the_period_and_keeps_the_seat(self):
        conv = self.conv([crow("I1", "ISIN_CHANGE", "BBB", 7, eff="2022-02-07", ann="2022-02-07", replaces=isin(2))])
        u = self.h.to_universe(conv)
        self.assertEqual(set(x.isin for x in u.members(D(2022, 2, 6))), set(isin(n) for n in (1, 2, 3, 4)))
        self.assertEqual(set(x.isin for x in u.members(D(2022, 2, 7))), set(isin(n) for n in (1, 7, 3, 4)))
        self.assertEqual([x.symbol for x in u.members(D(2022, 2, 7))], ["AAA", "BBB", "CCC", "DDD"])
        self.assertEqual(conv.report["members_by_date"]["2022-02-07"], 4)

    def test_isin_change_of_a_non_member_is_refused(self):
        with self.assertRaises(ms.MembershipError) as cm:
            self.conv([crow("I1", "ISIN_CHANGE", "ZZZ", 7, eff="2022-02-07", ann="2022-02-07", replaces=isin(9))])
        self.assertTrue(any("ISIN_CHANGE" in p for p in cm.exception.problems))


class ApprovalScopes(unittest.TestCase):
    """ED-48. SYNTHETIC files. count_approval and mapping_approval never verify a period.
    decision ACCEPTED keeps its previous meaning. Nothing is copied from one field to another."""

    def setUp(self):
        self.h = Validation("test_event_add_remove_balanced")
        self.h.setUp()
        self.addCleanup(self.h.tearDown)

    def files(self, base, changes, exceptions=None):
        b = self.h.write("nifty100_baseline.csv", BASE_HEADER, base)
        c = self.h.write("nifty100_changes.csv", CHG_HEADER, changes)
        x = None
        if exceptions is not None:
            x = self.h.write("exceptions.csv", ",".join(ms.COUNT_EXCEPTION_COLUMNS), exceptions)
        return b, c, x

    def scoped(self, b, c, x, scopes, decision_for=(), reviewer="SYNTHETIC REVIEWER", on="2026-11-11"):
        """Blank decision except keys in decision_for. scopes maps a key to (count, mapping)."""
        rows = []
        for t in ms.review_template(b, c, x):
            dec = "ACCEPTED" if t["row_key"] in decision_for else ""
            ca, ma = scopes.get(t["row_key"], ("", ""))
            rows.append(",".join([t["row_key"], t["row_sha256"], dec, reviewer, on, "SYNTHETIC", ca, ma]))
        return self.h.write("review.csv", ",".join(ms.REVIEW_COLUMNS), rows)

    def convert(self, b, c, x, review, records=None, n=4):
        return ms.convert(b, c, expected_members=n, instrument_records=records,
                          count_exceptions_path=x, review_path=review)

    def hashes(self, conv):
        return {r["symbol"]: r["source_sha256"] for r in conv.rows}

    def test_count_approval_of_every_exception_verifies_no_period(self):
        # One used exception plus 24 unused rows: 25 count approvals, no membership decision.
        used = "2022-03-31,5,doc.pdf,SYNTHETIC"
        extra = ["2024-01-%02d,5,doc.pdf,SYNTHETIC unused" % n for n in range(1, 25)]
        changes = [crow("E1", "ADD", "FFF", 6)]
        b, c, x = self.files(FOUR, changes, [used] + extra)
        keys = [t["row_key"] for t in ms.review_template(b, c, x) if t["row_key"].startswith("exception:")]
        self.assertEqual(len(keys), 25)
        conv = self.convert(b, c, x, self.scoped(b, c, x, {k: (ms.APPROVED, "") for k in keys}))
        self.assertTrue(conv.report["review"]["count_exceptions_accepted"])
        self.assertEqual(conv.report["review"]["count_approvals"], ["exception:2022-03-31"])
        self.assertEqual(conv.report["review"]["mapping_approvals"], [])
        self.assertEqual(conv.report["review"]["accepted"], 0)
        self.assertTrue(all(sha == "" for sha in self.hashes(conv).values()))
        self.assertEqual(conv.report["unverified_periods"], conv.report["periods"])

    def test_mapping_approval_does_not_certify_open_ended_additions(self):
        # Two adds and no removal: the same shape as BANKBARODA and CHOLAFIN after E03.
        changes = [crow("E03", "ADD", "BANK", 11), crow("E03", "ADD", "CHOLA", 12)]
        b, c, x = self.files(FOUR, changes, ["2022-03-31,6,doc.pdf,SYNTHETIC"])
        template = ms.review_template(b, c, x)
        adds = [t["row_key"] for t in template if ":ADD:" in t["row_key"]]
        exc = [t["row_key"] for t in template if t["row_key"].startswith("exception:")]
        scopes = {k: ("", ms.APPROVED) for k in adds}
        scopes.update({k: (ms.APPROVED, "") for k in exc})
        conv = self.convert(b, c, x, self.scoped(b, c, x, scopes))
        self.assertEqual(sorted(self.hashes(conv)), ["AAA", "BANK", "BBB", "CCC", "CHOLA", "DDD"])
        self.assertTrue(all(sha == "" for sha in self.hashes(conv).values()))
        self.assertEqual(conv.report["review"]["mapping_approvals"], sorted(adds))
        self.assertTrue(conv.report["review"]["count_exceptions_accepted"])
        self.assertEqual(self.h.to_universe(conv).limitations(D(2022, 6, 1)), [m.UNIVERSE_UNVERIFIED])

    def test_mapping_approval_records_five_additions_and_five_exclusions(self):
        base = [brow(sym, n) for n, sym in enumerate("ABCDE", 1)]
        changes = [crow("E03", "REMOVE", sym, n) for n, sym in enumerate("ABCDE", 1)]
        changes += [crow("E03", "ADD", "N%d" % n, 10 + n, replaces=isin(n)) for n in range(1, 6)]
        b, c, x = self.files(base, changes, None)
        keys = [t["row_key"] for t in ms.review_template(b, c) if t["row_key"].startswith("change:E03:")]
        adds = [k for k in keys if ":ADD:" in k]
        removes = [k for k in keys if ":REMOVE:" in k]
        self.assertEqual((len(adds), len(removes)), (5, 5))
        conv = self.convert(b, c, x, self.scoped(b, c, x, {k: ("", ms.APPROVED) for k in keys}), n=5)
        self.assertEqual(conv.report["review"]["mapping_approvals"], sorted(keys))
        self.assertEqual(conv.report["review"]["accepted"], 0)
        self.assertTrue(all(sha == "" for sha in self.hashes(conv).values()))

    def test_full_membership_still_requires_decision_accepted(self):
        changes = [crow("E03", "ADD", "BANK", 11)]
        b, c, x = self.files(FOUR, changes, ["2022-03-31,5,doc.pdf,SYNTHETIC"])
        template = {t["row_key"]: t for t in ms.review_template(b, c, x)}
        add = [k for k in template if k.startswith("change:E03:ADD:")][0]
        exc = [k for k in template if k.startswith("exception:")][0]
        scopes = {add: ("", ms.APPROVED), exc: (ms.APPROVED, "")}
        mapped = self.convert(b, c, x, self.scoped(b, c, x, scopes))
        self.assertEqual(self.hashes(mapped)["BANK"], "")
        # The same mapping, plus decision ACCEPTED on every membership row and the exception
        # left to the legacy field, verifies the open period. Mapping approval is not enough.
        full = self.convert(b, c, x, self.h.review(b, c, x))
        self.assertEqual(self.hashes(full)["BANK"], SHA)
        self.assertEqual(full.report["review"]["mapping_approvals"], [])
        self.assertEqual(full.report["review"]["count_approvals"], [])
        self.assertTrue(full.report["review"]["count_exceptions_accepted"])
        self.assertEqual(self.h.to_universe(full).limitations(D(2022, 6, 1)), [])

    def test_unresolved_identity_blocks_that_symbol_and_the_index_only(self):
        # GRASIM has no instrument record. AAA's own period stays verified.
        base = [brow("AAA", 1), brow("GRASIM", 2), brow("CCC", 3), brow("DDD", 4)]
        b, c, x = self.files(base, [], None)
        recs = self.h.write("records.csv", ",".join(ins.COLUMNS), [
            ",".join(["LISTING", sym, "", isin(n), "EQ", "2000-01-01", "", "SYNTHETIC listing", "doc.pdf", SHA,
                      "2026-01-01", "SYNTHETIC"])
            for sym, n in (("AAA", 1), ("CCC", 3), ("DDD", 4))])
        conv = self.convert(b, c, x, self.h.review(b, c), records=ins.load(recs))
        got = self.hashes(conv)
        self.assertEqual(got["GRASIM"], "")
        self.assertEqual(got["AAA"], SHA)
        self.assertIn("UNKNOWN_INSTRUMENT", [r for r in conv.rows if r["symbol"] == "GRASIM"][0]["notes"])
        self.assertNotIn("UNKNOWN_INSTRUMENT", [r for r in conv.rows if r["symbol"] == "AAA"][0]["notes"])
        u = self.h.to_universe(conv)
        self.assertTrue(next(r for r in u.rows if r.symbol == "AAA").verified)
        self.assertFalse(next(r for r in u.rows if r.symbol == "GRASIM").verified)
        self.assertEqual(u.limitations(D(2022, 6, 1)), [m.UNIVERSE_UNVERIFIED])

    def test_a_dummy_seat_is_not_approved_by_count_or_mapping(self):
        changes = [crow("E09", "ADD", "DUMMYX", 20)]
        b, c, x = self.files(FOUR, changes, ["2022-03-31,5,doc.pdf,SYNTHETIC"])
        template = ms.review_template(b, c, x)
        dummy = [t["row_key"] for t in template if "DUMMYX" in t["row_key"]][0]
        exc = [t["row_key"] for t in template if t["row_key"].startswith("exception:")][0]
        conv = self.convert(b, c, x, self.scoped(b, c, x, {exc: (ms.APPROVED, ""), dummy: ("", ms.APPROVED)}))
        self.assertEqual(self.hashes(conv)["DUMMYX"], "")
        self.assertNotIn(dummy, conv.report["review"]["count_approvals"])
        self.assertIn(dummy, conv.report["review"]["mapping_approvals"])
        self.assertEqual(conv.report["review"]["accepted"], 0)
        # A count approval written on the dummy change row is the wrong scope and approves nothing.
        bad = self.convert(b, c, x, self.scoped(b, c, x, {dummy: (ms.APPROVED, "")}))
        self.assertTrue(any("count_approval applies only to an exception row" in p
                            for p in bad.report["review"]["problems"]))
        self.assertEqual(self.hashes(bad)["DUMMYX"], "")
        self.assertFalse(bad.report["review"]["count_exceptions_accepted"])

    def test_unknown_membership_and_identity_stay_unverified(self):
        base = [brow("AAA", 1, verified=False), brow("BBB", 2), brow("CCC", 3), brow("DDD", 4)]
        changes = [crow("E03", "ADD", "EEE", 5)]
        b, c, x = self.files(base, changes, ["2022-03-31,5,doc.pdf,SYNTHETIC"])
        template = ms.review_template(b, c, x)
        scopes = {t["row_key"]: (ms.APPROVED, "") if t["row_key"].startswith("exception:") else ("", ms.APPROVED)
                  for t in template if t["row_key"].startswith(("exception:", "change:"))}
        # Scope approvals do not repair an unverified source, and a missing reviewer does not count.
        missing = self.scoped(b, c, x, scopes, reviewer="")
        conv = self.convert(b, c, x, missing)
        self.assertTrue(conv.report["review"]["problems"])
        self.assertFalse(conv.report["review"]["count_exceptions_accepted"])
        self.assertTrue(all(sha == "" for sha in self.hashes(conv).values()))
        # A well-formed full decision still withholds the unverified source and an unknown instrument.
        recs = ins.load(self.h.write("records.csv", ",".join(ins.COLUMNS), [
            ",".join(["LISTING", "BBB", "", isin(2), "EQ", "2000-01-01", "", "SYNTHETIC listing", "doc.pdf", SHA,
                      "2026-01-01", "SYNTHETIC"])]))
        conv = self.convert(b, c, x, self.h.review(b, c, x), records=recs)
        self.assertEqual(self.hashes(conv)["AAA"], "")
        self.assertEqual(self.hashes(conv)["EEE"], "")
        self.assertEqual(self.hashes(conv)["BBB"], SHA)

    def test_legacy_accepted_rows_keep_their_meaning_and_are_not_copied(self):
        changes = [crow("E1", "ADD", "FFF", 6)]
        b, c, x = self.files(FOUR, changes, ["2022-03-31,5,doc.pdf,SYNTHETIC"])
        legacy = []
        only_count = []
        for t in ms.review_template(b, c, x):
            legacy.append(",".join([t["row_key"], t["row_sha256"], "ACCEPTED", "SYNTHETIC REVIEWER",
                                     "2026-11-09", "SYNTHETIC"]))
            dec = "ACCEPTED" if t["row_key"].startswith("exception:") else ""
            only_count.append(",".join([t["row_key"], t["row_sha256"], dec, "SYNTHETIC REVIEWER",
                                         "2026-11-09", "SYNTHETIC"]))
        header = ",".join(ms.LEGACY_REVIEW_COLUMNS)
        conv = self.convert(b, c, x, self.h.write("legacy.csv", header, legacy))
        self.assertEqual(conv.report["unverified_periods"], 0)
        self.assertEqual(conv.report["review"]["count_approvals"], [])
        self.assertEqual(conv.report["review"]["mapping_approvals"], [])
        self.assertTrue(conv.report["review"]["count_exceptions_accepted"])
        # The old exception ACCEPTED is the count gate only. It does not become a scope field,
        # and it does not verify a period whose membership rows are undecided.
        held = self.convert(b, c, x, self.h.write("count-only.csv", header, only_count))
        self.assertTrue(held.report["review"]["count_exceptions_accepted"])
        self.assertEqual(held.report["review"]["count_approvals"], [])
        self.assertTrue(all(sha == "" for sha in self.hashes(held).values()))


class RecordedOwnerApprovals(unittest.TestCase):
    """Canonical ledger after the 2026-11-11 owner approvals (Yash Jain).

    `count_approval` APPROVED is the count-arithmetic decision. `mapping_approval`
    APPROVED is the E03 symbol-and-direction decision. `decision` is the membership-period
    decision and stays blank, so the converter verifies no period. The values are the
    owner's; this test only checks that the file and the converter keep them apart.
    """

    REVIEWER = "Yash Jain"
    ON = "2026-11-11"
    E03 = (
        "change:E03:REMOVE:ABBOTINDIA:INE358A01014",
        "change:E03:REMOVE:ALKEM:INE540L01014",
        "change:E03:REMOVE:MRF:INE883A01011",
        "change:E03:REMOVE:PETRONET:INE347G01014",
        "change:E03:REMOVE:UBL:INE686F01025",
        "change:E03:ADD:BANKBARODA:INE028A01039",
        "change:E03:ADD:CHOLAFIN:INE121A01024",
        "change:E03:ADD:JINDALSTEL:INE749A01030",
        "change:E03:ADD:PIIND:INE603J01030",
        "change:E03:ADD:SAIL:INE114A01011",
    )
    DUMMY_KEYS = (
        "change:E09:ADD:DUMMYREL:INE758E01017",
        "change:E15:ADD:DUMMYITC:INE379A01028",
        "change:E18:ADD:DUMMYSIEMS:INE1NPP01017",
        "change:E21:ADD:DUMMYTATAM:INE1TAE01010",
        "change:E23:ADD:DUMMYHDLVR:INE2KCE01013",
    )

    @classmethod
    def setUpClass(cls):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.folder = os.path.join(root, "nse", "data", "universe")
        cls.baseline = os.path.join(cls.folder, "nifty100_baseline.csv")
        cls.changes = os.path.join(cls.folder, "nifty100_changes.csv")
        cls.exceptions = os.path.join(cls.folder, "nifty100_count_exceptions.csv")
        cls.review_path = os.path.join(cls.folder, "nifty100_review.csv")
        cls.backup = os.path.join(cls.folder, "nifty100_review.before-approval-schema-2026-11-11.csv")
        cls.records = os.path.join(cls.folder, "instrument_records.csv")
        missing = [path for path in (
            cls.baseline, cls.changes, cls.exceptions, cls.review_path, cls.backup, cls.records) if not os.path.isfile(path)]
        if missing:
            raise AssertionError("canonical membership file missing: %s" % missing)
        with open(cls.review_path, newline="", encoding="utf-8") as fh:
            cls.rows = list(csv.DictReader(fh))
        cls.by_key = {r["row_key"]: r for r in cls.rows}
        cls.conv = ms.convert(
            cls.baseline, cls.changes, count_exceptions_path=cls.exceptions,
            review_path=cls.review_path, instrument_records=ins.load(cls.records))

    def test_ledger_shape_and_unchanged_row_identity(self):
        self.assertEqual(len(self.rows), 271)
        self.assertEqual(len(self.by_key), 271)
        template = {t["row_key"]: t["row_sha256"] for t in ms.review_template(
            self.baseline, self.changes, self.exceptions)}
        self.assertEqual(set(template), set(self.by_key))
        for key, sha in template.items():
            self.assertEqual(self.by_key[key]["row_sha256"], sha, key)
        with open(self.backup, newline="", encoding="utf-8") as fh:
            backup = list(csv.DictReader(fh))
        self.assertEqual([r["row_key"] for r in backup], [r["row_key"] for r in self.rows])
        for old, new in zip(backup, self.rows):
            self.assertEqual(old["row_sha256"], new["row_sha256"])
            self.assertEqual(old["decision"], "")
        counts = {}
        with open(self.exceptions, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                counts[int(row["members"])] = counts.get(int(row["members"]), 0) + 1
        self.assertEqual(counts, {101: 20, 100: 5})

    def test_only_the_thirty_five_owner_rows_carry_reviewer_and_date(self):
        count_keys = [r["row_key"] for r in self.rows if r["count_approval"] == ms.APPROVED]
        map_keys = [r["row_key"] for r in self.rows if r["mapping_approval"] == ms.APPROVED]
        self.assertEqual(len(count_keys), 25)
        self.assertEqual(sorted(map_keys), sorted(self.E03))
        self.assertTrue(all(k.startswith("exception:") for k in count_keys))
        touched = set(count_keys) | set(map_keys)
        self.assertEqual(len(touched), 35)
        for row in self.rows:
            self.assertEqual(row["decision"], "")
            if row["row_key"] in touched:
                self.assertEqual(row["reviewer"], self.REVIEWER)
                self.assertEqual(row["reviewed_on"], self.ON)
                self.assertTrue(row["notes"])
            else:
                self.assertEqual(row["reviewer"], "")
                self.assertEqual(row["reviewed_on"], "")
                self.assertEqual(row["notes"], "")
                self.assertEqual(row["count_approval"], "")
                self.assertEqual(row["mapping_approval"], "")
        for key in self.DUMMY_KEYS:
            row = self.by_key[key]
            self.assertEqual(row["decision"], "")
            self.assertEqual(row["mapping_approval"], "")
            self.assertEqual(row["count_approval"], "")
            self.assertNotIn(key, touched)

    def test_count_and_mapping_approval_verify_no_period(self):
        review = self.conv.report["review"]
        self.assertEqual(review["problems"], [])
        self.assertEqual(review["accepted"], 0)
        self.assertEqual(review["rejected"], [])
        self.assertEqual(review["stale_hash"], [])
        self.assertTrue(review["count_exceptions_accepted"])
        self.assertEqual(review["status"], "INCOMPLETE")
        # Count and mapping approvals are not membership decisions, so every reviewed
        # transcription row stays undecided.
        self.assertEqual(review["undecided"], review["rows"])
        self.assertEqual(review["accepted"], 0)
        # The report lists the exceptions the conversion actually uses. Every one of
        # those is among the 25 arithmetic approvals, and none is a membership decision.
        self.assertGreaterEqual(len(review["count_approvals"]), 1)
        self.assertTrue(all(k.startswith("exception:") for k in review["count_approvals"]))
        self.assertEqual(len(review["count_approvals"]), len(self.conv.report["count_exceptions_used"]))
        self.assertEqual(sorted(review["mapping_approvals"]), sorted(self.E03))
        self.assertEqual(self.conv.report["unverified_periods"], self.conv.report["periods"])
        self.assertTrue(all(r["source_sha256"] == "" for r in self.conv.rows))
        by_symbol = {}
        for row in self.conv.rows:
            by_symbol.setdefault(row["symbol"], []).append(row)
        for symbol in ("BANKBARODA", "CHOLAFIN"):
            period = next(r for r in by_symbol[symbol] if r["effective_from"] == "2021-09-30")
            self.assertEqual(period["effective_to"], "")
            self.assertEqual(period["source_sha256"], "")
        for symbol in ("DUMMYREL", "DUMMYITC", "DUMMYSIEMS", "DUMMYTATAM", "DUMMYHDLVR"):
            self.assertTrue(by_symbol[symbol])
            self.assertTrue(all(r["source_sha256"] == "" for r in by_symbol[symbol]))
            self.assertTrue(all("UNVERIFIED" in r["notes"] for r in by_symbol[symbol]))

    def test_one_membership_decision_does_not_spread(self):
        # A membership-period decision is a separate field. Filling it on BANKBARODA
        # alone must not certify CHOLAFIN, and clearing every decision is already the
        # canonical file above.
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        path = os.path.join(tmp, "review.csv")
        fields = list(ms.REVIEW_COLUMNS)
        rows = []
        for row in self.rows:
            copied = {column: row.get(column, "") for column in fields}
            if copied["row_key"] == "change:E03:ADD:BANKBARODA:INE028A01039":
                copied["decision"] = ms.ACCEPTED
            rows.append(copied)
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        conv = ms.convert(
            self.baseline, self.changes, count_exceptions_path=self.exceptions,
            review_path=path, instrument_records=ins.load(self.records))
        got = {r["symbol"]: r["source_sha256"] for r in conv.rows if r["effective_from"] == "2021-09-30"
               and r["symbol"] in ("BANKBARODA", "CHOLAFIN")}
        self.assertNotEqual(got["BANKBARODA"], "")
        self.assertEqual(got["CHOLAFIN"], "")
        self.assertEqual(conv.report["review"]["accepted"], 1)
        self.assertLess(conv.report["unverified_periods"], conv.report["periods"])
        self.assertGreater(conv.report["unverified_periods"], 0)
