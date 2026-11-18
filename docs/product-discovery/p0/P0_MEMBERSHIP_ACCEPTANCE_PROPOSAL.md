# P0 membership acceptance proposal: 91 evidence-sufficient rows

**Date:** 2026-11-15
**Authority:** owner Q3, "APPROVE PREPARATION OF ACCEPTANCE PROPOSAL ONLY".
**This is a proposal, not a decision.** Nothing was written to `nse/data/universe/nifty100_review.csv`. The ledger SHA-256 is unchanged (`9b0fcba06cc5...`). Preparing this proposal does not approve any row.

Files:
- Row-level evidence and results: `P0_MEMBERSHIP_ACCEPTANCE_PROPOSAL.csv` (91 rows, 26 columns).
- Proposed owner decision file for explicit review: `P0_MEMBERSHIP_OWNER_DECISION_FILE_PROPOSED.csv`. It has `row_key`, the current ledger `row_sha256`, `proposed_decision`, and blank `owner_decision`, `reviewer` and `reviewed_on` columns. It is not read by any code.

Out of scope and unchanged: the 7 optional rows (Q4 pending), the 8 other deferred rows, and the 25 NOT_APPLICABLE rows.

## 1. Checks performed on every row

| Check | Method | Result |
|---|---|---|
| Ledger row present | key in `nifty100_review.csv` | 91 / 91 |
| Ledger row hash current | recomputed with `membership.review_template(baseline, changes, count_exceptions)` | 91 / 91 current |
| Ledger decision blank | ledger `decision` column | 91 / 91 blank |
| Evidence file full SHA-256 | re-hashed on disk; compared with the backlog | 91 / 91 match (full 64-hex values in the CSV) |
| Document supports symbol and direction | Release: the symbol is in the NIFTY 100 section's "being excluded" (REMOVE) or "being included" (ADD) list and not in the opposite list. Rename: `symbolchange.csv` line old->new. ISIN change: an NSE corporate-action record whose ex-date or record date equals the effective date | 91 / 91 (87 automated text checks, 4 manual reads) |
| Document states the effective date | Release: "effective from <date>" (spacing-normalised). Rename: date column. ISIN change: ex/record date | 91 / 91 |
| ISIN | Releases print no ISIN, so the held bhavcopy EQ row at the boundary is used. ISIN change: first new-ISIN EQ session differs from the old ISIN | 91 / 91 |
| Group-level | Each release group's NIFTY 100 lists were counted against the group's rows | All 10 release groups match exactly (table below) |

Manual reads (layout differs from the standard release):

| Row | What the document says |
|---|---|
| `change:E08:REMOVE:HDFC:INE001A01036` | "2) Nifty 1 00 ... being excluded: ... Housing Development Finance Corporation Ltd. HDFC"; effective July 13, 2023 (amalgamation with HDFC Bank) |
| `change:E08:ADD:JINDALSTEL:INE749A01030` | Same section: "being included: 1 Jindal Steel & Power Ltd. JINDALSTEL" |
| `change:E10:REMOVE:JIOFIN:INE758E01017` | JIOFIN excluded from listed indices including "2 Nifty 100", effective September 7, 2023 |
| `change:E13:REMOVE:TATAMTRDVR:IN9155A01020` | Tata Motors DVR excluded from "1 Nifty 100", effective August 30, 2024 |

## 2. Group-level reconciliation

| Group | Source document (held, hash-verified) | Effective | Document lists (removed / added) | Rows in group |
|---|---|---|---|---|
| G-E06 | `ind_prs01092022.pdf` | 2022-09-30 | 6 / 6 | 12 |
| G-E07 | `ind_prs17022023_1.pdf` | 2023-03-31 | 5 / 5 | 10 |
| G-E08 | `ind_prs04072023.pdf` | 2023-07-13 | 1 / 1 | 2 |
| G-E10 | `ind_prs05092023.pdf` | 2023-09-07 | 1 / 0 | 1 |
| G-E11 | `ind_prs17082023.pdf` | 2023-09-29 | 5 / 6 | 11 |
| G-E12 | `ind_prs28022024.pdf` | 2024-03-28 | 5 / 5 | 10 |
| G-E13 | `ind_prs23082024_1.pdf` | 2024-08-30 | 1 / 0 | 1 |
| G-E14 | `ind_prs23082024.pdf` | 2024-09-30 | 5 / 5 | 10 |
| G-E17 | `ind_prs21022025.pdf` | 2025-03-28 | 5 / 5 | 10 |
| G-E20 | `ind_prs22082025.pdf` | 2025-09-30 | 5 / 5 | 10 |
| 9 ISIN-change groups | saved NSE CA API body per symbol + held bhavcopies | each date | one face-value split record on the effective date each | 9 |
| 5 rename groups | `evidence/identity/symbolchange.csv` | each date | LTI->LTIM, ADANITRANS->ADANIENSOL, MCDOWELL-N->UNITDSPR, ZOMATO->ETERNAL, TATAMOTORS->TMPV, each with the exact date | 5 |

## 3. Proposed decision

**Proposed: `ACCEPTED` for all 91 rows** (row list and hashes in the proposed decision file). No row is proposed for rejection, and no row is left without a proposal.

## 4. Exceptions, limitations and open questions

No row failed verification. Limitations the owner should weigh:

1. **ISIN is not printed in index press releases.** For 77 release rows the ISIN comes from NSE bhavcopies at the boundary session. Membership is by company and symbol; identity is a separate gate.
2. **ISIN-change rows (9) rest on saved NSE corporate-action API bodies** (ED-37 identity basis). This is the same basis as the three ISIN-change rows the owner accepted under D65. It is identity/event evidence, **not** corporate-action completeness evidence. An NSE "Change in ISIN" Listing circular would be stronger, independent-channel evidence. Such circulars exist (Batch 12/13), but they are not held for these nine and were not authorized for retrieval.
3. **Rename rows (5) rest on NSE `symbolchange.csv`**, a single NSE file (hash `6937337d...`).
4. **VBL 2024-09-12** (row 55): membership is supported; the same date's split is UNPARSED (OD-PX-2 / ENG-1). Independent issue.
5. **Release text extraction:** four releases needed a manual read, and the automated check depends on the release layout. All 91 conclusions were cross-checked against the group counts above.

Open question for the owner: accept all 91 as proposed, or accept by group, or reject or defer named rows.

## 5. Effect if the owner accepts all 91

Periods verified would rise from 85 toward the number those rows complete. The exact figure depends on the isolated rebuild and is not claimed here. **Certified member-dates stay 0**, because D66 corporate-action completeness is unproved for every window.
