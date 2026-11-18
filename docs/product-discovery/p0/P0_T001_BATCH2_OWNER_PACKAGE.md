# T-001 batch 2: owner evidence cards

**Status 2026-11-13: approved and applied (D65).** The owner accepted all five cards: G-E04 (10 rows), G-E05 (4 rows), and the JUBLFOOD, TATASTEEL and BAJAJFINSV ISIN changes (1 row each). Exactly those 17 rows of `nse/data/universe/nifty100_review.csv` now carry `decision` `ACCEPTED`, reviewer `Yash Jain`, `reviewed_on` `2026-11-13` and a "T-001 batch 2" note. No other row changed. The ledger SHA-256 went from `292b0e20ce25ccd06c02f4e4653ddb1bb466d10d218fa46b65984f1c993f926e` to `9b0fcba06cc57761a4adbf0a938e004fb6adf808ba7724842248977391ec1f39`.

The conversion then verified exactly the 14 periods predicted below (85 of 185). The certified count stays 0, because every member-date still fails the corporate-action gate (OD-CA-1).

The cards below are the evidence as presented before the decision. Their "consequence" lines were dry-run predictions; the actual result matched them.

Prepared 2026-11-13 against HEAD `69858d0` plus the working tree. Batch 1 (123 rows) is in the working tree and is not committed.

## How each card was checked (all performed this session)

- **Release:** the PDF was re-hashed against `nse/data/universe/evidence/sources.csv`, and the NIFTY 100 section was read on the stated page.
- **Daily files:** each boundary archive was loaded with the project's loader against `nse/data/eod/manifest.csv`. The archive SHA-256 is listed. Only the EQ row is evidence: a BL (block-deal) row printed on the same day is listed for completeness and never read as EQ.
- **Row hash:** `row_sha256` in the review file equals the recommendation file and the packet.
- **Consequence:** the converter was run on a scratch copy of `nse/data/universe/` with exactly these 17 rows set `ACCEPTED`. Result: 85 verified periods instead of 71. 14 periods are newly verified and none is lost (listed per card). The certified count would stay 0: every member-date still fails the corporate-action gate (OD-CA-1).

The date rule (`membership.py`): an ADD is a member from `effective_date`. A REMOVE is a member through the calendar day before `effective_date`.

---

## Card 1: G-E04, semi-annual review effective 2022-03-31 (10 rows)

| Field | Value |
|---|---|
| Release | NSE Indices press release "Revision in criteria and replacements in indices", Mumbai, February 24, 2022 |
| File | `nse/data/universe/evidence/releases/ind_prs24022022_1.pdf` |
| SHA-256 | `3091cf1c10b57bbae3b81645f5d91916a1af2bb7284902060f4640f7fb9fcd56` (recomputed, matches `sources.csv`) |
| Wording, page 1 | "These changes shall become effective from March 31, 2022 (close of March 30, 2022)." |
| Section read, page 5 | "4) NIFTY 100": 5 excluded, 5 included, as below. The earlier extraction's `HINDP` is printed in full as HINDPETRO |
| Effective date | 2022-03-31. Removed names are members through 2022-03-30 |
| Last session before | `cm30MAR2022bhav.csv.zip`, SHA-256 `ac777e3f4574593e3a3ffcc46c3980e5eff9df4f39dc3f83c8c378a4ec1c2f88` |
| First session after | `cm31MAR2022bhav.csv.zip`, SHA-256 `68cf87ac7f8b8823893a474b38844cf72922c2e5daacf8568dfdff177fab2c4e` |
| Conflicting evidence | None found |

| Canonical row key | Action | Company (as printed) | ISIN | EQ row 2022-03-30 | EQ row 2022-03-31 |
|---|---|---|---|---|---|
| `change:E04:REMOVE:AUROPHARMA:INE406A01037` | REMOVE | Aurobindo Pharma Ltd. | INE406A01037 | INE406A01037, close 675.6 | INE406A01037, close 668.55 |
| `change:E04:REMOVE:HINDPETRO:INE094A01015` | REMOVE | Hindustan Petroleum Corporation Ltd. | INE094A01015 | INE094A01015, close 264.45 | INE094A01015, close 269.35 |
| `change:E04:REMOVE:IGL:INE203G01027` | REMOVE | Indraprastha Gas Ltd. | INE203G01027 | INE203G01027, close 373.25 | INE203G01027, close 373.15 |
| `change:E04:REMOVE:JINDALSTEL:INE749A01030` | REMOVE | Jindal Steel & Power Ltd. | INE749A01030 | INE749A01030, close 519.85 | INE749A01030, close 532.85 |
| `change:E04:REMOVE:YESBANK:INE528G01035` | REMOVE | Yes Bank Ltd. | INE528G01035 | INE528G01035, close 12.25 | INE528G01035, close 12.3 |
| `change:E04:ADD:NYKAA:INE388Y01029` | ADD | FSN E-Commerce Ventures Ltd. | INE388Y01029 | INE388Y01029, close 1700.9 | INE388Y01029, close 1689.55 |
| `change:E04:ADD:MINDTREE:INE018I01017` | ADD | MindTree Ltd. | INE018I01017 | INE018I01017, close 4407.8 | INE018I01017, close 4302.9 |
| `change:E04:ADD:PAYTM:INE982J01020` | ADD | One 97 Communications Ltd. | INE982J01020 | INE982J01020, close 541.3 | INE982J01020, close 528.45 |
| `change:E04:ADD:SRF:INE647A01010` | ADD | SRF Ltd. | INE647A01010 | INE647A01010, close 2705.85 | INE647A01010, close 2679.35 |
| `change:E04:ADD:ZOMATO:INE758T01015` | ADD | Zomato Ltd. | INE758T01015 | INE758T01015, close 85.05 | INE758T01015, close 82.3 |

- **Consequence if all 10 are accepted.** Five periods become verified: AUROPHARMA, HINDPETRO and IGL from 2020-12-31 to 2022-03-30; JINDALSTEL from 2021-09-30 to 2022-03-30; YESBANK from 2021-03-31 to 2022-03-30. The five ADD periods stay unverified until their closing rows are decided (NYKAA 2023-09-28, MINDTREE 2022-09-29, PAYTM 2023-03-30, SRF 2024-09-29, ZOMATO 2025-04-08, the last being the rename to ETERNAL).
- **Note.** YESBANK's ISIN rests on NSE/CML/43833 (OD-ID-3, new ISIN from 2020-03-16).
- **Technical recommendation:** accept all 10.

## Card 2: G-E05, ad-hoc replacements effective 2022-08-08 (4 rows)

| Field | Value |
|---|---|
| Release | NSE Indices press release "Replacements in indices", Mumbai, July 11, 2022 |
| File | `nse/data/universe/evidence/releases/ind_prs11072022.pdf` |
| SHA-256 | `dd1021f2123de0facdce17c6dd3cd0e21dc30f1665f346c2798c93f700982e1f` (recomputed, matches) |
| Wording, page 1 | "These changes shall become effective from August 08, 2022 (close of August 05, 2022)." Reasons A and B: the NMDC and Piramal Enterprises demerger schemes |
| Section read, page 2 | "2) Nifty 100": excluded NMDC and PEL; included LICI and TATAPOWER |
| Effective date | 2022-08-08. Removed names are members through 2022-08-07 (last session 2022-08-05) |
| Last session before | `cm05AUG2022bhav.csv.zip`, SHA-256 `2d0def0a27f95de37b9e11d1c0a290c6235e8c30589633c2e704061c8f2fab67` |
| First session after | `cm08AUG2022bhav.csv.zip`, SHA-256 `0b3c3ca294a2e6d2ef55da81f04a7a8ece637f4734601b7e5e3e67c34368185a` |
| Conflicting evidence | None found |

| Canonical row key | Action | Company (as printed) | ISIN | EQ row 2022-08-05 | EQ row 2022-08-08 |
|---|---|---|---|---|---|
| `change:E05:REMOVE:NMDC:INE584A01023` | REMOVE | NMDC Ltd. | INE584A01023 | INE584A01023, close 110.9 | INE584A01023, close 113.1 |
| `change:E05:REMOVE:PEL:INE140A01024` | REMOVE | Piramal Enterprises Ltd. | INE140A01024 | INE140A01024, close 1726.1 | INE140A01024, close 1789.6 (a BL row is also printed; not used) |
| `change:E05:ADD:LICI:INE0J1Y01017` | ADD | Life Insurance Corporation of India | INE0J1Y01017 | INE0J1Y01017, close 687.35 | INE0J1Y01017, close 680 |
| `change:E05:ADD:TATAPOWER:INE245A01021` | ADD | Tata Power Co. Ltd. | INE245A01021 | INE245A01021, close 232.1 | INE245A01021, close 228.25 (a BL row is also printed; not used) |

- **Consequence if all 4 are accepted.** Four periods become verified: NMDC and PEL from 2020-12-31 to 2022-08-07; LICI and TATAPOWER from 2022-08-08 onward (open).
- **Technical recommendation:** accept all 4.

## Card 3: JUBLFOOD ISIN change (G-I-2022-04-20-JUBLFOOD, 1 row)

| Field | Value |
|---|---|
| Canonical row key | `change:I-2022-04-20-JUBLFOOD:ISIN_CHANGE:JUBLFOOD:INE797F01020` |
| Old ISIN, new ISIN | `INE797F01012`, `INE797F01020` |
| Effective date | 2022-04-20 (first session on the new ISIN). The seat is unchanged; this is not an ADD |
| Cause | Face-value split, ex-date 2022-04-19, in `nse/data/corporate_actions/raw/ca_JUBLFOOD_2016_2025.json` (hash matches `coverage.csv`). There is no NSE Indices release: the seat continues |
| Last session on the old ISIN | `cm19APR2022bhav.csv.zip`, SHA-256 `72dfe3fa45f215174d43bcc58884688bc0832454f09e35169008a7d498d4eaa9`: EQ, INE797F01012, close 546.2, PREVCLOSE 2844.7 (the unadjusted pre-split close) |
| First session on the new ISIN | `cm20APR2022bhav.csv.zip`, SHA-256 `6c976aafbcca67fec7c9a9282927f6d806dbfe5d72be7d67ce46fcd28a0f2619`: EQ, INE797F01020, close 551.7, PREVCLOSE 546.2 |
| Identity | One old ISIN, one new ISIN, one change session, same symbol. The instrument records resolve both sides |
| Conflicting evidence | None found. The API body's `isin` field is not used (it prints stale ISINs elsewhere; tracker F-2) |

- **Consequence if accepted.** One period becomes verified: JUBLFOOD on INE797F01012 from 2021-03-31 to 2022-04-19. The period on INE797F01020 (2022-04-20 to 2022-09-29) stays unverified until G-E06's REMOVE is decided.
- **Technical recommendation:** accept.

## Card 4: TATASTEEL ISIN change (G-I-2022-07-29-TATASTEEL, 1 row)

| Field | Value |
|---|---|
| Canonical row key | `change:I-2022-07-29-TATASTEEL:ISIN_CHANGE:TATASTEEL:INE081A01020` |
| Old ISIN, new ISIN | `INE081A01012`, `INE081A01020` |
| Effective date | 2022-07-29 |
| Cause | Face-value split Rs 10 to Re 1, ex-date 2022-07-28, in `ca_TATASTEEL_2016_2025.json` (hash matches `coverage.csv`) |
| Last session on the old ISIN | `cm28JUL2022bhav.csv.zip`, SHA-256 `6efdacccfe775d2b21201eeb0e4531c0355de4d81b7eccdc170415bfd0dc36fe`: EQ, INE081A01012, PREVCLOSE 959.4, open 98.1, close 100.35 |
| First session on the new ISIN | `cm29JUL2022bhav.csv.zip`, SHA-256 `7f00f0d28da46e6d0a9bf9c708b0360d1d5af5685879b815bb3f3066a235cd52`: EQ, INE081A01020, close 107.6, PREVCLOSE 100.35 |
| Conflicting evidence | None found |

- **Consequence if accepted.** Two periods become verified: TATASTEEL on INE081A01012 from 2020-12-31 to 2022-07-28, and on INE081A01020 from 2022-07-29 onward.
- **Technical recommendation:** accept.

## Card 5: BAJAJFINSV ISIN change (G-I-2022-09-14-BAJAJFINSV, 1 row)

| Field | Value |
|---|---|
| Canonical row key | `change:I-2022-09-14-BAJAJFINSV:ISIN_CHANGE:BAJAJFINSV:INE918I01026` |
| Old ISIN, new ISIN | `INE918I01018`, `INE918I01026` |
| Effective date | 2022-09-14 |
| Cause | Bonus 1:1 and face-value split Rs 5 to Re 1, ex-date 2022-09-13, in `ca_BAJAJFINSV_2016_2025.json` (hash matches `coverage.csv`) |
| Last session on the old ISIN | `cm13SEP2022bhav.csv.zip`, SHA-256 `a1273ce4304e06b642423b3bc8351329a7cfac25afa89337a05269fb80e810c4`: EQ, INE918I01018, close 1784.75, PREVCLOSE 17138.05 |
| First session on the new ISIN | `cm14SEP2022bhav.csv.zip`, SHA-256 `5ec8914e9588313af12f6a7b036cc77b7e7ef83238a2b2f3f196ccfc252a51dd`: EQ, INE918I01026, close 1805.35, PREVCLOSE 1784.75 |
| Conflicting evidence | None found |

- **Consequence if accepted.** Two periods become verified: BAJAJFINSV on INE918I01018 from 2020-12-31 to 2022-09-13, and on INE918I01026 from 2022-09-14 onward.
- **Technical recommendation:** accept.

---

## How to answer

Reply with one line per card, for example `G-E04 ACCEPT all 10 rows`, or `G-E05 ACCEPT change:E05:ADD:LICI:INE0J1Y01017 only`. `REJECT` and `DEFER` are also valid. Agents then write `decision`, `reviewer`, `reviewed_on` and one notes line on exactly the rows you name, and re-run the conversion and the certification build. A group-level answer covers every row listed on that card only when you say so.

## Not in this batch

- GRASIM `INE047A01021` and BAJFINANCE `INE296A01024` baseline rows: open identity conflicts (OD-ID-1, OD-ID-2).
- Seven `INSUFFICIENT_EVIDENCE` groups: five dummy seats, VBL 2024-09-12 and BAJFINANCE 2025-06-16.
- 25 count groups: D60 approved the arithmetic only.
- 31 further acceptance-recommended groups: later batches.
