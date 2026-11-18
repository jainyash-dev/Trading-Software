# P0 owner decision pack V2 (Batches 7-8)

**Date:** 2026-11-15
**Programme status:** P0_CERTIFICATION_BLOCKED. Certified member-dates: **0 of 123,778**. Nothing in this pack changes that by itself.
**Previous pack:** `P0_OWNER_DECISION_PACK.md` (kept). V2 replaces its corporate-action section with a verified, pilot-sized request and adds an identity option.

Each decision below is independent. Answer any subset. A blank answer keeps the fail-closed default.

## Decision 1: corporate-action acquisition pilot (blocks all certification)

Detail: `P0_CA_ACQUISITION_AUTHORIZATION_REQUEST.md`.

- Provider A: NSE/FAOP F&O adjustment circulars (verified: NSE/FAOP/53548 states BAJAJFINSV split 5:1, bonus 1:1, ex 2022-09-13, factor 10).
- Provider B: CDSL "DETAILS OF CORPORATE ACTIONS" communiques (verified series 2010-2026; contents unverified).
- Scope: TORNTPHARM, GAIL, HDFCBANK, 2022 only; free public sources; content check first.
- Why only a pilot: no provider has been shown to prove window completeness. D66 fails closed on insufficient coverage.

**Answer:** AUTHORIZE / DECLINE / AUTHORIZE WITH CHANGES. Optionally: authorize an *enquiry* (not a purchase) into BSE's paid historical corporate-action product.

## Decision 2: membership rows (91 evidence-sufficient; 7 more optional)

Detail: `P0_MEMBERSHIP_DECISION_SUMMARY_V2.md`, which lists each row key, evidence file and hash.

- Verified 2026-11-15: 91 rows in 24 groups; all 131 backlog source hashes match their files; all 131 rows are still blank in the ledger; ledger 140 ACCEPTED / 131 blank.
- Engineering recommendation on file: ACCEPT for all 91. This is not a decision.
- Optional: 7 rows (JIOFIN, ITCHOTELS x2, ENRIN x2, TMCV x2) have sufficient membership evidence but unresolved identity and BE-only trading. You may decide membership now; they stay excluded on identity and EQ either way.

**Answer:** per row or per group: ACCEPTED / REJECTED.

## Decision 3: OD-ID-1 BAJFINANCE and OD-ID-2 GRASIM

Detail: `P0_IDENTITY_BLOCKER_DECISIONS_V2.md`.

- Verified cause: the pre-2016 ISIN's listing record never ends, so two ISINs claim the symbol on every research-window date (1,098 + 1,234 member-dates).
- Options: (1) keep unjoined (default); (2) name one effective session with a held document; (3) **new:** record that the old ISIN is not listed after the later stated date (9 Sep 2016; 7 Oct 2016), without a price join.

**Answer per symbol:** 1 / 2 (date + document) / 3.

## Decision 4: optional items

Detail: `P0_OPTIONAL_OWNER_DECISIONS.md`: OD-PX-4 (700 member-dates), OD-PX-3, OD-PX-2 evidence, OD-MEM-2/3 (123 member-dates), TV-1, B11-P, R-5.

## What agents will do next without any answer

- Batch 11-12 independent analysis that needs no new evidence (EQ-series validation table, exception register V2).
- Batch 13 engineering readiness: inspect and run the full test and validation commands; record exact results.
- No downloads, no ledger decisions, no completeness markers, no production rebuild, no P5.
