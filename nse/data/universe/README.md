# Historical NIFTY 100 membership and instrument identity (B11; D49, D51, D53, D56)

**Status: UNVERIFIED until a human reviews every row (D49, D53).** Every scan that uses
`nifty100_universe.csv` carries `UNIVERSE_UNVERIFIED` and is never presented as
research-ready until then. Agents verify and prepare; only a human accepts.

## Files

| File | What | Built from |
|---|---|---|
| `nifty100_baseline.csv` | The 100 members on 31 Dec 2020, with ISIN | NSE Indices "Constituents of NIFTY 100 \| December 31, 2020" (`evidence/baseline/indices_dataDec2020.zip`); ISINs from the 2021-01-01 bhavcopy |
| `nifty100_changes.csv` | 146 rows, 2021-03-31 to 2025-12-05: ADD / REMOVE rows of the reconstitution and ad-hoc events, `RENAME` rows (including `DUMMYREL` to `JIOFIN` on 2023-08-21) and 13 `ISIN_CHANGE` rows | NSE Indices press releases (`evidence/releases/`), NSE circulars (`evidence/circulars/`), NSE `symbolchange.csv`, NSE corporate-action records (`../corporate_actions/raw/`) |
| `nifty100_count_exceptions.csv` | 25 dated official counts other than 100 (101 during spin-off, DVR and dummy windows) | the release on each row |
| `nifty100_review.csv` | **The human review: one row per baseline row, change row and count exception (271).** `decision` is still blank on every row. On 2026-11-11 Yash Jain approved the 25 count calculations (`count_approval` `APPROVED`) and the ten E03 mappings (`mapping_approval` `APPROVED`). Neither column verifies a membership period | the reviewer (below) |
| `nifty100_review_packet.csv` | The independent verifier's verdict and evidence per row (advisory; never a decision) | D53 verifier agents |
| `nifty100_universe.csv` | Output of `membership.convert`, read by `universe.load` / `--universe` (185 periods) | the files above |
| `nifty100_conversion_report.json` | Members per date, exceptions used, review status, identity findings | `membership.convert` |
| `instrument_records.csv` | LISTING, SYMBOL_CHANGE and ISIN_CHANGE records for member instruments, read by `--instruments` (219, all source-verified; rebuilt by `.claude/skills/nse-data-engineering/scripts/identity_collect_obs.py` then `identity_build_records.py`) | see "Identity" below |
| `identity_report.json` | How each identity record was evidenced; what is unevidenced | the identity build |
| `build_report.json` | Every inference made while formatting the transcription | the build |
| `evidence/` | Official PDFs, archives and lists, each in `evidence/sources.csv` with URL, SHA-256 and size | niftyindices.com and nsearchives.nseindia.com, 2026-11-09 |

Archives and PDFs are git-ignored; the CSVs are not.

## How the transcription was checked

- **Two independent transcriptions** of the releases agreed on 122 of 123 ADD / REMOVE rows. The difference was the Jio Financial inclusion on 2023-07-20, where the release prints no symbol.
- **Jio Financial (D53).** The entity enters as `DUMMYREL`, the symbol in NSE Indices' official "Constituents of NIFTY 50 \| July 31, 2023" ("Dummy - Jio Financial Services Ltd."). It is renamed `JIOFIN` on 2023-08-21, the listing date in NSE circular CML58021. Both rest on official documents, not inference. No NIFTY 100 list for July 2023 exists, so `DUMMYREL` in NIFTY 100 rests on the same release adding it to both indices.
- **Checkpoints.** Rolled forward, the universe equals the official lists for Mar 2021, Sep 2021 and Mar 2022 (100 of 100 each).
- **Row-level verification (D53).** An independent agent checked every row against its cited evidence; verdicts are in `nifty100_review_packet.csv`. The rows added or corrected after that pass (ISIN changes, DUMMYREL, the JIOFIN rename, BE series, re-derived count exceptions) were checked by a second independent agent (2026-11-09). Four dummy ISINs remain inferences and are labelled `INFERENCE`.
- **Periods of 101 members are kept** wherever the official counts say so (D49: never force 100).

## How to review (D53): one decision per row

1. Open `nifty100_review.csv` next to `nifty100_review_packet.csv` (same `row_key` and `row_sha256`).
2. For each row, check the transcription row against its evidence (the packet names it), then fill:
   - `decision`: `ACCEPTED` or `REJECTED` when the whole membership row is approved or refused;
   - `count_approval`: `APPROVED` or `REJECTED` on an `exception:` row only, when the derived count is approved and the constituents are not;
   - `mapping_approval`: `APPROVED` or `REJECTED` on a `change:` row only, when the symbol and the add or remove direction are approved and the period is not;
   - `reviewer`: your name;
   - `reviewed_on`: the date (`YYYY-MM-DD`);
   - `notes`: optional.
3. Do not change `row_key` or `row_sha256`. Editing a transcription row changes its hash and voids only that row's acceptance (`stale_hash`).

A period is verified only when its start row and its end row (if any) have `decision` `ACCEPTED` with matching hashes, every count exception it relies on passes the count gate, and its identity check is clear. `count_approval` passes only the count gate. `mapping_approval` does not verify a period. A blank scope does not change an older `ACCEPTED` row. A blank `decision` fails closed.

Recorded on 2026-11-11 by Yash Jain, and only on those rows:

- 25 `exception:` rows: `count_approval` `APPROVED`. This accepts the derived count arithmetic. It does not approve constituents, dummy seats, inferred ISINs, or a membership period.
- 10 `change:E03:` rows (ABBOTINDIA, ALKEM, MRF, PETRONET, UBL out; BANKBARODA, CHOLAFIN, JINDALSTEL, PIIND, SAIL in): `mapping_approval` `APPROVED`. This accepts the symbol and the direction in `ind_prs23082021.pdf` page 5 section 3, effective 2021-09-30 from page 1. It does not approve the membership period. BANKBARODA and CHOLAFIN stay open and unverified.

The other 246 rows have an empty decision, reviewer, date and both scope columns. Agents do not write `decision` `ACCEPTED`. The stored scope value is `APPROVED`, not `ACCEPTED`, so it cannot be read as a membership-period decision.

Re-run the conversion afterwards:

```
python3 -c "import sys; sys.path.insert(0,'.'); from nse.research import membership as ms, instruments as i; \
U='nse/data/universe'; c=ms.convert(U+'/nifty100_baseline.csv', U+'/nifty100_changes.csv', \
count_exceptions_path=U+'/nifty100_count_exceptions.csv', review_path=U+'/nifty100_review.csv', \
instrument_records=i.load(U+'/instrument_records.csv')); ms.write(c.rows, U+'/nifty100_universe.csv'); print(c.report['review'])"
```

## Identity (D51, D56; ED-37)

`instrument_records.csv` holds LISTING, SYMBOL_CHANGE and ISIN_CHANGE records built from three sources:
- NSE `EQUITY_L.csv` and `symbolchange.csv` (`evidence/identity/`).
- The held official bhavcopies 2016-2025, which give the first held session and the ISIN traded at a rename.
- NSE corporate-action records, which evidence ISIN changes.

What the records cover:
- **ISIN changes.** 30 ISIN changes of member symbols appear in the 2016-2025 bhavcopies; 27 are evidenced by an official split or bonus record whose ex-date or record date is the first session under the new ISIN. Each evidenced change is an `ISIN_CHANGE` record citing the saved NSE response.
- **Three unevidenced changes:** BAJFINANCE 2016-09-09 and GRASIM 2016-10-07 (their splits' printed record dates are the Saturdays after the change, so a match would be an inference) and YESBANK 2020-03-16 (no official price event held). Their histories are never joined across those dates (`ISIN_CHANGED_WITHOUT_RECORD`, DATA_INSUFFICIENT across them).
- **ISINs missing from EQUITY_L.** Member ISINs absent from EQUITY_L.csv (HDFC, MINDTREE, PEL, TATAMTRDVR, the pre-2026 KOTAKBANK ISIN) are listed from their first held session. Their end is not recorded without an official document.
- **Joins.** Renames are joined only through verified ISIN continuity (ED-29). ISIN changes and mergers are never joined, and names and reused tickers never link two instruments.

Every 2016-2025 observation of every member symbol was checked against the records. The only findings left are those three unevidenced changes.
