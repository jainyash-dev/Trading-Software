# T-001 membership decision package

**Recommendations in the tables below are the 2026-11-11 advisory record.** They are not themselves decisions.

On 2026-11-12 Yash Jain recorded T-001 batch 1 in `nse/data/universe/nifty100_review.csv`: `decision` `ACCEPTED` on 123 rows, reviewer `Yash Jain`, `reviewed_on` `2026-11-12`. The rows are the 98 identity-clear baseline names, all 12 E01 rows, both E02 rows, all 10 E03 rows, and the CADILAHC to ZYDUSLIFE rename. `baseline:GRASIM:INE047A01021` and `baseline:BAJFINANCE:INE296A01024` were left blank. The converter then reports 71 periods with a source hash and 114 without. That is not full-index certification and not a certified research universe.

Reviewed against HEAD `56434ea` inputs on 2026-11-11. This run matched row hashes and cited-file hashes. It did not re-read every PDF page.

## Reconciled inputs

| Check | Result |
|---|---|
| Review rows | 271 |
| Packet rows | 271, same keys |
| Queue rows | 271, same keys |
| Template hashes | 271, no mismatch against the review file, the packet, or the queue |
| Canonical `decision` | 123 `ACCEPTED` on 2026-11-12; 148 still blank, including GRASIM and BAJFINANCE |
| Reviewer `Yash Jain` | 35 rows (25 `count_approval`, 10 `mapping_approval`) |
| No reviewer | 236 |
| Baseline source file | `indices_dataDec2020.zip`, hash matched on all 100 rows |
| Change source files | 146 rows, 43 documents, 0 missing, 0 hash mismatches |

No discrepancy was repaired.

## How to use the two sheets

`P0_MEMBERSHIP_GROUP_REVIEW.csv` is the owner sheet. One row is one evidence event, the 2020-12-31 baseline, or one count date. Fill `owner_decision` and `owner_notes` there. Leave `recommendation` as it is.

`P0_MEMBERSHIP_ROW_RECOMMENDATIONS.csv` is the row trace. `canonical_decision` is a copy of the blank ledger field. `owner_decision` is blank. Accepting a group means accepting the row keys in that `group_id`, not the count row that shares the date.

`NOT_A_MEMBERSHIP_PERIOD` means do not fill `decision` on that count row. The arithmetic is already stored as `count_approval`.

## Recommendation counts

| Recommendation | Rows | Meaning |
|---|---|---|
| `ACCEPT_RECOMMENDED` | 239 | Cited file hash matches and the advisory packet says `VERIFIED`, or the row is one of the ten E03 mappings the owner already confirmed as a mapping. This run did not re-read the page. |
| `INSUFFICIENT_EVIDENCE` | 7 | The row as written needs an ISIN or a term the cited file does not establish. |
| `NOT_A_MEMBERSHIP_PERIOD` | 25 | Count rows. Already `count_approval` `APPROVED`. |

There is no `REJECT_RECOMMENDED` row. No cited file contradicted its transcription in the checks this run could make. That is not a page-by-page re-read.

### The seven insufficient rows

| Row | What is supported | What is missing |
|---|---|---|
| `DUMMYREL` added 2023-07-20 | The release adds a spun-off Reliance entity to Nifty 100 | The Nifty 100 release does not print `DUMMYREL`. The symbol is from the Nifty 50 list of 31 July 2023. The ISIN is inferred from later `JIOFIN` |
| `DUMMYITC` added 2025-01-06 | The release prints `DUMMYITC` and the effective date | No document assigns `INE379A01028` to the dummy symbol |
| `DUMMYSIEMS` added 2025-04-07 | The release prints `DUMMYSIEMS` and the effective date | No document assigns `INE1NPP01017` to the dummy symbol |
| `DUMMYTATAM` added 2025-10-14 | The release prints `DUMMYTATAM` and the effective date | No document assigns `INE1TAE01010` to the dummy symbol |
| `DUMMYHDLVR` added 2025-12-05 | The release prints `DUMMYHDLVR` and the effective date | No document assigns `INE2KCE01013` to the dummy symbol |
| `VBL` ISIN change 2024-09-12 | Bhavcopies show `INE200M01021` then `INE200M01039` | The cited response does not name `INE200M01039`. Its ISIN field is the older `INE200M01013`. The 5-to-2 subject is unparsed |
| `BAJFINANCE` ISIN change 2025-06-16 | Bhavcopies show `INE296A01024` then `INE296A01032`. The subject text has a 4:1 bonus and a 2-to-1 split | The cited response names stale ISIN `INE296A01016` and does not name `INE296A01032` |

E03 (30 September 2021, `ind_prs23082021.pdf`, page 5 section 3, effective date from page 1) is `ACCEPT_RECOMMENDED` as a membership transcription. `mapping_approval` is already recorded and is not a period approval. The owner still has to put `decision` on those ten rows before the periods can verify.

## What the recommendations would do to the 185 periods

Dry run, in memory only. `decision` was set to `ACCEPTED` on the 239 recommended rows inside a temporary file. Count rows and the seven insufficient rows stayed blank. The canonical ledger was not written. Reviewer text on the temporary file was `DRY RUN`, not an owner signature.

| Result | Count |
|---|---|
| Periods that would carry a source hash | 175 |
| Periods that would stay unverified | 10 |
| Member-dates in 2020-12-31 .. 2025-12-31 | 123,778 |
| Of those, membership gate would pass | 120,559 |
| Of those, membership gate would still fail | 3,219 |

The 10 unverified periods are:

| Symbol | Periods | Why a recommended acceptance still does not verify them |
|---|---|---|
| GRASIM | 1 | Baseline row is recommended. Two ISINs stay listed (`INE047A01013` and `INE047A01021`) because the MSEI circular states both 6 October 2016 and 7 October 2016 |
| BAJFINANCE | 2 | The 2016 ISIN break is the same kind of two-date conflict. The 2025-06-16 ISIN-change row is `INSUFFICIENT_EVIDENCE` |
| VBL | 2 | The 2024-09-12 ISIN-change row is `INSUFFICIENT_EVIDENCE` |
| DUMMYREL, DUMMYITC, DUMMYSIEMS, DUMMYTATAM, DUMMYHDLVR | 1 each | The add row is `INSUFFICIENT_EVIDENCE` |

Count exceptions do not become period approvals in this simulation. The count gate was already open from `count_approval`.

A period is not certifiable only because its event rows are `ACCEPT_RECOMMENDED`. GRASIM shows that: the recommendation can be to accept the transcription, and the period still fails identity.

## Other gates that still exclude the 120,559

Even where the membership gate would pass:

- Corporate-action completeness is not proved. An empty `[]` is not coverage. A non-empty response is not a guarantee that every event was returned.
- Price continuity is not signed off for each symbol-date. Unparsed subjects, including the VBL 5-to-2 split and the CGPOWER 2016-03-15 scheme, stay unresolved. Raw OHLC is unchanged.
- GTF zone eligibility was not run for these dates.
- Full Nifty 100 certification stays false while any member-date on that session is unverified.

Certified research symbol-dates remain **0**. The dry run is not a certification.

## Owner action

Batch 1 is recorded in the ledger, as the opening paragraph says. The remaining acceptance-recommended groups, the seven insufficient groups, and the 25 count groups are still open. A later group is copied into `nifty100_review.csv` `decision` only after an explicit decision on that group. Count rows stay out of `decision`. A recommendation is not an approval.
