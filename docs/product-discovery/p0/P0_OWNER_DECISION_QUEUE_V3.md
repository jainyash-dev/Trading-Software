# P0 owner decision queue V3

**Date:** 2026-11-15 (after Batches 11-13)
**Supersedes for ordering:** `P0_OWNER_DECISION_PACK_V2.md` (kept). V3 adds what Batches 11-13 found and puts decisions in the order that unblocks the most.
**Default for any unanswered item:** unchanged and fail-closed. Engineering recommendations here are not decisions.

## Priority 1: unblocks everything

### Q1. Corporate-action acquisition pilot (OD-CA-1)
- Scope: TORNTPHARM, GAIL, HDFCBANK; 2022; NSE/FAOP circulars + CDSL "Details of Corporate Actions" communiques; free public pages; CDSL content check first. Detail: `P0_CA_ACQUISITION_AUTHORIZATION_REQUEST.md`.
- New since V2: NSE Listing "Change in ISIN" circulars (`NSE/CML`) exist and give ex-date and code-change dates, but only for ISIN-changing events. They are the same institution as FAOP, so they cannot pair with FAOP as independent sources.
- **Answer:** AUTHORIZE / DECLINE / AUTHORIZE WITH CHANGES.

### Q2. Optional: BSE paid-data enquiry
- An enquiry only (product terms, price, coverage documentation). No purchase.
- **Answer:** YES / NO.

## Priority 2: membership (no certification effect until Q1 clears)

### Q3. 91 evidence-sufficient rows
- Verified in Batch 11: 271/271 ledger row hashes current; 91/91 blank; evidence hashes match. List: `P0_MEMBERSHIP_DECISION_SUMMARY_V2.md` section 2.
- **Answer:** ACCEPTED / REJECTED per row or per group.

### Q4. 7 optional rows (JIOFIN, ITCHOTELS x2, ENRIN x2, TMCV x2)
- Batch 11 read each source document; membership evidence is sufficient on its own. Identity and EQ stay unresolved either way.
- **Answer:** decide now / defer.

## Priority 3: identity (2,332 member-dates)

### Q5. OD-ID-1 BAJFINANCE and Q6. OD-ID-2 GRASIM
Batch 11 facts: the notices' two dates have different stated meanings (code change w.e.f. 9 Sep / 7 Oct; trades from ex-date 8 Sep / 6 Oct), which is NSE's own standard wording (NSE/CML/35870). NSE bhavcopies agree: price step on the ex-date under the old ISIN; new ISIN from the next session; old ISIN never seen again. Residual doubt: the notices are MSEI's, and record dates are inconsistent (Saturdays; GRASIM 6 Oct vs 8 Oct).

Options per symbol:
1. Keep unjoined (default).
2. Join with one effective session, citing a document you accept.
3. End the old ISIN's listing (BAJFINANCE 2016-09-08, GRASIM 2016-10-06) with no price join, citing a document you accept.

Sub-question for 2 or 3: **which evidence do you accept?** (a) the held MSEI notices plus held NSE bhavcopies; or (b) only an NSE/CML Change-in-ISIN circular, which would need **authorization to retrieve** two specific PDFs from NSE's public archive.

**Answer per symbol:** 1 / 2 / 3, and (a) or (b).

## Priority 4: rules and classifications

| Q | Item | Count | Answer |
|---|---|---|---|
| Q7 | OD-PX-4: pass the session after a held Muhurat/shortened session when the PREVCLOSE chain is intact | 700 | ADOPT / DECLINE |
| Q8 | OWN-1: treat a scheme distributing non-equity securities (BRITANNIA 2021-05-25 debentures; TVSMOTOR 2025-08-25 NCRPS) as non-price-scale like a dividend, or keep unparsed | 2 events | NON-PRICE-SCALE / KEEP UNPARSED |
| Q9 | OD-PX-3: create a reviewed market-move exception (ADANIENSOL 2024-11-21, 20% band) | 1 | CREATE / NO |
| Q10 | OD-MEM-2/3: dummy-seat accounting rule | 123 | RULE / LEAVE EXCLUDED |
| Q11 | CGPOWER 2016 scheme terms: authorize retrieval of terms | pre-window | YES / NO |
| Q12 | TV-1 exports | external | SUPPLY / LEAVE PENDING |
| Q13 | R-5 precedence wording | governance | CONFIRM ORDER |

## Engineering items that need no owner decision (will be scheduled as ED entries)

ENG-1 (VBL fractional split parsing; changes a regression expectation, so it gets an ED entry and review), ENG-2 (backlog text), ENG-3 (CA ledger provenance fields), ENG-4 (CONFLICT-event regression test), ENG-5 (`run_all --acceptance` before any final claim). None changes the certified count.
