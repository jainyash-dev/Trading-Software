# Historical universe validation

**Dated 2026-11-11. Branch `main`. HEAD `9e302df1a81c2b13696d8fab61f05d377481be2e`.**

This addendum checks the current files. It does not replace the 2026-11-10 membership review.
No review row was marked ACCEPTED or REJECTED. No identity was joined. No price was adjusted.

## Classification of the 271 ledger rows

Recounted from `docs/product-discovery/phase-01/T001_nifty100_owner_worksheet.csv` and
`nse/data/universe/nifty100_review.csv`.

| Class | Rows |
|---|---|
| Baseline | 100 |
| Membership changes | 146 |
| Count exceptions | 25 |
| Total | 271 |

These are not 271 membership changes plus 25 exceptions. The 25 exceptions are inside the 271.
The row ids and SHA-256 values match the canonical review file. Non-empty `decision` fields: 0.

`nifty100_universe.csv` still has 185 periods and 0 source hashes.

## Review state

| State | Rows | Meaning |
|---|---|---|
| SUPPORTED, still OWNER_DECISION_REQUIRED | 257 | Packet says the cited file hash matched and the proposed action is ACCEPT_RECOMMENDED. That is not owner approval |
| PARTIALLY_SUPPORTED | 10 | E03 rows for `ind_prs23082021.pdf`. The file is the cited original. Page 5 is images. This pass did not read the names off the page |
| OWNER_DECISION_REQUIRED | 4 | Dummy ISIN inferences: DUMMYITC, DUMMYSIEMS, DUMMYTATAM, DUMMYHDLVR |
| UNSUPPORTED | 0 cited files missing | Every worksheet `source_file` resolved on disk in the earlier package build |
| CONFLICT | 0 | No hash mismatch was found in that package build |

DUMMYREL is in the 257. The packet calls the row verified because the symbol is taken from a Nifty 50 list, not because the Nifty 100 release prints `DUMMYREL`. The period still has no instrument record. Accepting the row would not verify the period.

## Count exceptions

All 25 dates match the owner's recommendation list. The recommendation is recorded as
`ACCEPT_RECOMMENDED` in `P0_COUNT_EXCEPTION_PROPOSED_DECISIONS.csv`, with column
`derived_member_count`. The canonical review file was not updated. Owner approval status
on that artifact is `OWNER_DECISION_REQUIRED`.

The converter default is 100. A derived count of 101 is kept where a dummy seat or an
unmatched inclusion is the recorded basis. Renames and ISIN changes do not change the
count. One blank exception withholds all 185 periods.

## Period verification

No period is verified. GRASIM's unevidenced 2016-10-07 ISIN change is still on the open
membership period from 2020-12-31. The gate marks a date unverified if any member that
day is unverified. No full Nifty 100 date is certified. D59 is only the provisional start.
It is not a certified research period.

A reduced sample that drops GRASIM, BAJFINANCE, YESBANK and the dummy seats would be an
owner-defined sample. It would not be the Nifty 100 and it would not be survivorship-controlled
index research. That sample was not created.

## Dummy seats

| Symbol | Effective period | Tradable instrument |
|---|---|---|
| DUMMYREL | 2023-07-20 .. 2023-08-20 | No. Placeholder. ISIN not printed on the Nifty 100 release |
| DUMMYITC | 2025-01-06 .. 2025-01-28 | No. Symbol printed. ISIN inferred |
| DUMMYSIEMS | 2025-04-07 .. 2025-06-18 | No. Symbol printed. ISIN inferred |
| DUMMYTATAM | 2025-10-14 .. 2025-11-11 | No. Symbol printed. ISIN inferred |
| DUMMYHDLVR | 2025-12-05 .. open | No. Symbol printed. ISIN inferred |

They can count in the index arithmetic. They are not eligible instruments.

## Baseline before 2020-12-31

The dated constituent file is `evidence/baseline/indices_dataDec2020.zip`.
`evidence/baseline/IndexInclExcl.xls` remains labelled NOT PARSED. No membership baseline
before 2020-12-31 was established.
