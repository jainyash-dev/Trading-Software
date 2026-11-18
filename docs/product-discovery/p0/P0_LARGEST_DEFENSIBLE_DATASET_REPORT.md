# Largest defensible dataset, first pass

**Dated 2026-11-11. Branch `main`. HEAD `9e302df1a81c2b13696d8fab61f05d377481be2e`.**

This is not P0 completion. Canonical membership, identity, corporate-action and price files were not modified. No owner decision was written into `nifty100_review.csv`. No ISIN history was joined. No price was adjusted. Nothing was staged or committed.

Protected hashes are unchanged:

- Pine `14293fa5d3c8e5ba9309b45804a840bb5d8c43d47c193ebb6bca0480bc0a5519`
- Rulebook Markdown `039883be6b97ca39b00e5afe80f219a5d759dae99fa9c4179475f506a275d54b`
- Rulebook PDF `e41cd0e7893513a492a39095c0f771ec67b320f1b51bc356da7c6a2c2946c2fc`

Working tree at the start of this pass: 80 modified, 40 untracked, nothing staged. `authorises_order` remains false.

## 1. Repository safety

The matrices below are new review artifacts. They are not a second membership ledger. The decision file remains blank on all 271 rows.

## 2. Reconciled blocker inventory

| Blocker | State | What this pass established |
|---|---|---|
| 271 review decisions | UNDER_REVIEW | 100 baseline, 146 changes, 25 exceptions. Zero canonical decisions |
| 25 count exceptions | UNDER_REVIEW | ACCEPT_RECOMMENDED only, in the earlier proposed CSV. Not written to the ledger |
| 10 E03 rows | EVIDENCE_FOUND | Page 5, section 3, prints the same five exclusions and five inclusions. Page 1 dates the release 30 September 2021 (close of 29 September 2021). Not approved |
| DUMMYREL | UNDER_REVIEW | Corrected in `P0_MEMBERSHIP_CLOSURE.csv`. The Nifty 100 release does not print that symbol. The seat stays non-tradable |
| Other dummy ISINs | UNDER_REVIEW | Symbol and date are printed. ISINs stay inferred and unapproved |
| BAJFINANCE, GRASIM, YESBANK | UNRESOLVED | Local corporate-action files do not name the new ISIN on the session. No join |
| Before 2020-12-31 | UNRESOLVED | `IndexInclExcl.xls` is on disk and still marked NOT PARSED. It is not a baseline |
| 47 empty corporate-action files | UNRESOLVED | Each current file is the two bytes `[]`. That is not proof of no event |
| CROMPGREAV 2016-03-15 | UNRESOLVED | No ratio in the local file. None was invented |
| TradingView | UNRESOLVED | 34 observations still blank. Parity is not claimed |
| EOD archives | EVIDENCE_FOUND | All 2,478 archive files were rehashed. 0 missing, 0 manifest mismatches |

Eligible symbol-dates in `P0_RESEARCH_ELIGIBILITY_MATRIX.csv`: **0 of 123,778**. Every member-date from 2020-12-31 through 2025-12-31 is `EXCLUDED_MEMBERSHIP` because membership evidence is unverified. Unknown evidence was not marked eligible.

## 3. Official-source acquisition still required

| Need | Why the files on disk are not enough |
|---|---|
| Owner decisions on the 271 rows | Hash matches and a visual symbol list are not `ACCEPTED` |
| Notice naming BAJFINANCE `INE296A01024` on 2016-09-09 | Saved JSON keeps the old ISIN. Record date is the following Saturday |
| Notice naming GRASIM `INE047A01021` on 2016-10-07 | Saved JSON never prints the new ISIN |
| Notice naming YESBANK `INE528G01035` on 2020-03-16 | Saved JSON has no March 2020 event |
| A parsed pre-2020-12-31 constituent list, only if the window should start earlier | The xls is not a transcribed baseline |
| A ratio for the CROMPGREAV scheme | Subject text only |
| The 34 TradingView observations | Separate parity milestone |

No new official file was downloaded into the repository on this pass.

## 4. Proposed owner decisions

These are proposals. They are not approvals.

1. Do not certify any date as the full Nifty 100 until the ledger decisions and the GRASIM notice exist.
2. If the 25 derived counts are approved, write `ACCEPTED` only on those 25 review rows, with a reviewer and a date. Do not treat that as certifying the other 246 rows.
3. Keep all five dummy seats non-tradable. Do not approve inferred ISINs. Treat DUMMYREL as not printed by the Nifty 100 release.
4. Do not join the three ISIN breaks.
5. Do not treat empty corporate-action responses as "no event."
6. Do not invent the 2016 CROMPGREAV factor. Do not backfill BE or BZ into EQ.
7. Leave T-005 pending.

## 5. Exact next execution batch, after review

1. Owner writes the 25 count-exception decisions into `nifty100_review.csv`, or says they stay blank.
2. Owner states whether the ten E03 rows, now visually matched on page 5, are accepted.
3. Only then re-run `membership.convert`. Do not verify periods that still have an identity finding. GRASIM will still block every full-index date.
4. Re-run `python3 -m nse.validation.run_all` after any ledger edit. This pass did not repeat the full suite. The 2026-11-11 suite had one failure, `test_root_matches_the_reel`, caused by a root `.DS_Store`. That file is gone, and the single test passed afterward.

## E03 visual result

Original file: `nse/data/universe/evidence/releases/ind_prs23082021.pdf`, 29 pages.

Page 5, section 3, Nifty 100, excluded: ABBOTINDIA, ALKEM, MRF, PETRONET, UBL.
Included: BANKBARODA, CHOLAFIN, JINDALSTEL, PIIND, SAIL.
Those are the ten worksheet symbols, with the same add or remove direction. The effective date is on page 1, not in the Nifty 100 table itself.

## Files added

- `P0_BLOCKER_CLOSURE_MATRIX.csv`
- `P0_EVIDENCE_REGISTER.csv`
- `P0_MEMBERSHIP_CLOSURE.csv`
- `P0_IDENTITY_CLOSURE.csv`
- `P0_CORPORATE_ACTION_CLOSURE.csv`
- `P0_RESEARCH_ELIGIBILITY_MATRIX.csv`
- `P0_RESEARCH_EXCLUSION_REGISTER.csv`
- this report

The eligibility matrix is a review extract. It is not a certified research dataset.
