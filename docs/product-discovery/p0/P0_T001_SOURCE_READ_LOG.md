# T-001 source read log

**2026-11-11. Not an owner decision. Not a certification.**

Canonical `nse/data/universe/nifty100_review.csv` was not modified. All 271 `decision` fields remain blank. All 72 `owner_decision` fields in `P0_MEMBERSHIP_GROUP_REVIEW.csv` remain blank. The 239 `ACCEPT_RECOMMENDED` values are still only the prior hash-and-packet recommendation. They are not approvals, and a file hash is not proof the page was transcribed correctly.

This pass read the text layer of specific press releases and compared the Nifty 100 excluded and included symbol lists with the change ledger.

## Read, and the symbol lists match the ledger

| Source | Ledger event | What was read |
|---|---|---|
| `ind_prs23022021.pdf` | E01, effective 2021-03-31, 6 out and 6 in | Section "4) NIFTY 100". Excluded: BANKBARODA, CONCOR, GICRE, HINDZINC, OFSS, PFC. Included: ADANIENT, APOLLOHOSP, JUBLFOOD, MRF, VEDL, YESBANK. |
| `ind_prs23082021.pdf` | E03, effective 2021-09-30, 5 out and 5 in | Section "3) NIFTY 100". Excluded: ABBOTINDIA, ALKEM, MRF, PETRONET, UBL. Included: BANKBARODA, CHOLAFIN, JINDALSTEL, PIIND, SAIL. The file has a text layer for this table. An older registry note called the PDF image-only. That note is not a description of this table. Mapping approval remains separate from a membership-period decision. |
| `ind_prs01092022.pdf` | E06, 6 out and 6 in | Standard "NIFTY 100 / the following companies are being excluded" list. All 12 ledger symbols sit on the matching side of that list. |
| `ind_prs11072022.pdf` | E05, 2 out and 2 in | Same heading. All 4 ledger symbols match side. |
| `ind_prs17022023_1.pdf` | E07, 5 out and 5 in | Same heading. All 10 ledger symbols match side. |
| `ind_prs24022022_1.pdf` | E04, 5 out and 5 in | Same heading. All 10 ledger symbols match side. |

The effective-date sentence on each of these pages was not re-checked in this pass, except that E01 and E03 were already tied to the printed "effective from" wording in the ledger notes. Symbol match is not, by itself, a period approval.

## Not read as a Nifty 100 membership list in this pass

These release files did not yield that same heading, so their add/remove rows stay unverified by this pass:

`ind_prs02042025.pdf`, `ind_prs04072023.pdf`, `ind_prs05092023.pdf`, `ind_prs06022025_1.pdf`, `ind_prs07102025.pdf`, `ind_prs13112025.pdf`, `ind_prs15062021.pdf`, `ind_prs17072023.pdf`, `ind_prs17082023.pdf`, `ind_prs21022025.pdf`, `ind_prs22082025.pdf`, `ind_prs23082024.pdf`, `ind_prs23082024_1.pdf`, `ind_prs25062025_2.pdf`, `ind_prs28022024.pdf`, `ind_prs28112025.pdf`, `ind_prs30122024.pdf`.

`ind_prs17072023.pdf` does not contain the string `DUMMYREL`. `ind_prs30122024.pdf` does not contain the string `DUMMYITC` in the extracted text. Those two rows stay `INSUFFICIENT_EVIDENCE`.

Renames, ISIN-change rows, the December 2020 constituent zip, and the 25 count rows were not page-read in this pass.

No canonical decision was written.
