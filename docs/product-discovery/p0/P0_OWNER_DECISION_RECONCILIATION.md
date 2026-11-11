# Owner-decision reconciliation

**Dated 2026-11-11. Branch `main`. HEAD `9e302df1a81c2b13696d8fab61f05d377481be2e` before the schema commit.**

P0 is not complete. Eligible symbol-dates remain 0. The three ISIN breaks were not joined. No corporate-action file was edited.

## What the owner approved

- The 25 derived count calculations, limited to the arithmetic.
- The ten E03 symbol mappings and directions in `ind_prs23082021.pdf`, page 5 section 3, effective 30 September 2021 from page 1. Not identity, not a full period.

## Schema

`decision` `ACCEPTED` would have verified the open BANKBARODA and CHOLAFIN periods once the count gate was open. ED-48 adds `count_approval` and `mapping_approval` on the same review file. Those columns do not verify a period. The design is in `P0_APPROVAL_SCHEMA.md`. Tests are `tests/test_research_membership.py`, class `ApprovalScopes`.

## Ledger

`nifty100_review.csv` has the two scope columns. Every original `row_key` and `row_sha256` is unchanged. Every `decision` remains blank.

The owner named the reviewer as `Yash Jain` on 2026-11-11. That string is written only on the 25 exception rows and the ten E03 rows.

- Exception rows: `count_approval` `APPROVED`, reviewer `Yash Jain`, `reviewed_on` `2026-11-11`.
- E03 rows: `mapping_approval` `APPROVED`, reviewer `Yash Jain`, `reviewed_on` `2026-11-11`.
- The other 236 rows: reviewer, date, notes and both scope columns blank. `decision` is blank on all 271 rows.

The six-column file remains `nse/data/universe/nifty100_review.before-approval-schema-2026-11-11.csv`. It was not overwritten.

## Dry run of the recorded ledger

The canonical review, not a temporary copy, is what the converter reads. Every `decision` stays blank.

| Check | Result |
|---|---|
| Count gate | passed |
| `decision` ACCEPTED rows | 0 |
| Count approvals counted | 25 |
| Mapping approvals counted | 10 |
| Periods with a source hash | 0 |
| BANKBARODA from 2021-09-30 | unverified, still open |
| CHOLAFIN from 2021-09-30 | unverified, still open |
| Dummy periods with a source hash | 0 of 5 |
| GRASIM identity finding | `UNKNOWN_INSTRUMENT` on GRASIM only (INE047A01013 and INE047A01021 both listed on 2020-12-31). BAJFINANCE and YESBANK have their own findings. The five dummy symbols have no instrument record. No other symbol carries these findings |
| Review problems | 0 |

Membership conversion was not written to `nifty100_universe.csv`. The counts in the table are the recorded review rows. The converter report lists only the count exceptions the walk uses; `RecordedOwnerApprovals` checks that every used exception is one of these 25 and that no period receives a source hash.

## Still open

Membership-period `decision` values for all 271 rows, including the 35 rows above. D60 and D61 do not fill them.
