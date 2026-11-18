# P0 final blocker register

## D68 update (2026-11-15)

**Status unchanged: P0_CERTIFICATION_BLOCKED, certified 0 of 123,778.**

- D66: CDSL corroborates all 15 known in-window splits (event level). The BSE enquiry is drafted but not sent. No window qualifies, so all 123,778 member-dates remain blocked.
- Q7 declined: the 700 shortened-session member-dates stay excluded (no rule pending).
- Q10 Option A: the 123 dummy-seat member-dates stay excluded at security level. Index counts are reported separately in `P0_INDEX_COUNTS_DUMMY_SEATS.csv`: 123 sessions carry one dummy seat; security-level members are 100 on 979 sessions and 101 on 255.
- Q8 and Q9: the BRITANNIA, TVSMOTOR and ADANIENSOL steps stay excluded by owner decision. CGPOWER representation is deferred (pre-window).

## V3 update (2026-11-15, after D67 and ED-57)

**Programme status: P0_CERTIFICATION_BLOCKED. Certified 0 of 123,778.** Live counts are from isolated builds F and G (byte-identical).

| Blocker | Member-dates | Evidence missing | Next action |
|---|---|---|---|
| D66: no qualified independent source pair; no window proved | **123,778 (all)** | Independent official source with provable window coverage (BSE paid product unverified; CDSL covers ISIN-changing events only) | Owner: queue V4 #1 |
| Membership unverified (12 periods) | 2,622 | Owner decisions (OD-ID-1/2 Option 1; dummy seats; 7 deferred rows) | Queue V4 #3; Q4 when wanted |
| Identity UNKNOWN_INSTRUMENT | 2,455 | None: kept unjoined by owner choice (D67); dummy rule | Queue V4 #3 |
| Price continuity exceptions | 1,132 | Q7 (700), Q9 (1), Q8 (2), more evidence (2), non-EQ (387), recorded-event steps (40) | Queue V4 #2, #6, #7 |
| EQ: BE-only / no row | 383 | None (rule: EQ only) | none |

Resolved this cycle: 91 membership rows accepted (verified member-dates 79,151 -> 121,156; periods 85 -> 173); VBL 2024-09-12 split classified exactly (ED-57); CGPOWER entitlement terms retrieved (1:1, demerger, no price factor); NSE Change-in-ISIN circulars held for BAJFINANCE and GRASIM (decision unchanged).

---

## Earlier register (after Batch 13; kept unchanged below)

**Date:** 2026-11-15
**Programme status:** **P0_CERTIFICATION_BLOCKED**. Certified member-dates **0 of 123,778** (fresh isolated 1.6.0 build, deterministic, identical data to `nse/output/p0_isolated_2026-11-15/`).
**Why blocked:** evidence and owner decisions. The software gates are implemented, tested (1,475 passing tests, full local-data run) and deterministic. Software readiness is not data certification.

## 1. Blocking every member-date

| ID | Blocker | Gate | Member-dates affected | Type | What clears it | Next action |
|---|---|---|---|---|---|---|
| **OD-CA-1 / D66** | No proved corporate-action completeness window | Corporate action | **123,778 (all)** | Evidence + owner | Two independent official sources per window, reconciled, owner dual-hash marker per window | Owner: authorize the pilot (`P0_CA_ACQUISITION_AUTHORIZATION_REQUEST.md`) |
| CA-SRC | No provider shown to prove window completeness; CDSL content unverified; NSE FAOP/CML are event-centric and partial (F&O only / ISIN-changing events only) | Corporate action | all | Evidence | Pilot answers Q1-Q3 | Pilot |

## 2. Blocking subsets (would matter once D66 clears)

| ID | Blocker | Gate | Member-dates | Type | Clears with |
|---|---|---|---|---|---|
| MEM-91 | 91 evidence-sufficient rows undecided | Membership | part of 44,627 UNVERIFIED | Owner | ACCEPTED/REJECTED per row |
| MEM-7 | 7 optional rows (JIOFIN, ITCHOTELS, ENRIN, TMCV) | Membership (+ identity, EQ) | small (BE-only stretches) | Owner + evidence | Membership decision; identity/EQ stay excluded |
| MEM-INS | 8 deferred rows (5 dummy adds, BAJFINANCE/GRASIM baselines, BAJFINANCE 2025 ISIN change) | Membership | included above | Evidence / OD-ID | OD-ID-1/2; dummy rule |
| OD-ID-1 | BAJFINANCE old-ISIN listing never ends | Identity | 1,098 (+136 on the 2025 ISIN via its membership row) | Owner + evidence | Option 2 or 3 with accepted document. Best evidence: NSE/CML Change-in-ISIN circular (Sep 2016), not held |
| OD-ID-2 | GRASIM same | Identity | 1,234 | Owner + evidence | same (Oct 2016) |
| OD-MEM-2/3 | Five dummy seats | Identity, EOD, CA | 123 | Owner | Accounting rule; never an invented ISIN |
| BE-ONLY | Members trading only in BE | EOD | 260 | Fact (not a defect) | None: stays excluded |
| OD-PX-4 | Session after Muhurat/shortened session | Price continuity | 700 | Owner | Adopt/decline rule |
| OD-PX-3 | ADANIENSOL 2024-11-21 band move | Price continuity | 1 | Owner | Exception mechanism, if wanted |
| OD-PX-2 / ENG-1 | VBL 2024-09-12 fractional split unparsed | Corporate action / price | VBL around the step | Engineering | ENG-1 (ED entry + test review) |
| OWN-1 | BRITANNIA 2021-05-25, TVSMOTOR 2025-08-25 non-equity distributions unparsed | Corporate action / price | those steps | Owner | Classification rule |
| OD-PX-2 (CGPOWER) | 2016 scheme terms absent | Pre-window only | 0 in window | Evidence | Scheme terms (authorized acquisition) |
| Identity reconciliation | UNKNOWN_INSTRUMENT 2,455 = 1,098 + 1,234 + 123 | Identity | 2,455 | - | Items above |

## 3. Not blocking P0 data certification

| ID | Item | Status |
|---|---|---|
| TV-1 | TradingView parity, 34/34 worksheet rows blank | PENDING_EXTERNAL_EVIDENCE; external parity only |
| B11-P | No symbol/ISIN baseline before 2020-12-31 | D59 window kept |
| R-5 | Precedence wording | Governance; CLAUDE.md follows D12 |
| ENG-2..5 | Backlog text, ledger provenance fields, CONFLICT regression test, acceptance-mode run | Engineering backlog |

## 4. Final-status test

| Permitted status | Justified? |
|---|---|
| P0_CERTIFICATION_COMPLETE_WITH_EXPLICIT_LIMITATIONS | **No**: 0 certified member-dates; D66 unmet for every window |
| P0_CERTIFICATION_PARTIALLY_COMPLETE | **No**: no record qualifies |
| **P0_CERTIFICATION_BLOCKED** | **Yes** |

Batches 9, 10, 14, 15 (with real certified rows) and 16 cannot start until OD-CA-1 clears. The contrarian reviewer's earlier verdict (reject any certification claim) still stands; nothing in Batches 7-13 changes it.
