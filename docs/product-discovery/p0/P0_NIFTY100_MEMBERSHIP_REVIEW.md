# P0 Nifty 100 membership review

**Dated 2026-11-10. Status: `OWNER_DECISION_REQUIRED`. No period is certified.**

This is the current-status record for T-001. The Phase 01 worksheet and review notes stay
as they were written. No review row was filled. No constituent, ISIN, or effective date
was invented. An in-memory simulation is labelled as a simulation.

Investigation: Nifty 100 membership, agent id f936ac8f-4cd7-4397-85b0-6d254e3aa2f8 (read-only).
This pass re-counted the review file, the universe file, the baseline, the exceptions,
and the instrument records. Those counts match the investigation.

## 1. Conclusion

Every Nifty 100 membership period is unverified. All 271 review decisions are blank, so
the review gate withholds a source hash from all 185 periods. A scan that uses
`nse/data/universe/nifty100_universe.csv` carries `UNIVERSE_UNVERIFIED`. A backtest on
that file carries `SURVIVORSHIP_UNCONTROLLED`.

There is no point-in-time membership before 2020-12-31. Bhavcopies for 2016-2020 do not
create a universe.

Accepting every row would still leave 8 periods unverified. GRASIM's open period starts
on 2020-12-31, so those 8 findings would keep every later date unverified as well.
`DATA_READY` is not claimed.

## 2. Counts verified on the current files

| Item | Count |
|---|---|
| Review rows | 271 |
| Non-empty `decision`, `reviewer`, `reviewed_on`, or `notes` | 0 |
| Baseline rows | 100, all `as_of_date` 2020-12-31, series EQ |
| Change rows | 146 (ADD 62, REMOVE 61, RENAME 10, ISIN_CHANGE 13) |
| Count-exception rows | 25, all used by conversion (20 at 101 members, 5 returning to 100) |
| Universe periods | 185 (84 closed, 101 open) |
| Periods with a source hash | 0 |
| Symbols / ISINs in the universe file | 164 / 166 |
| Same-symbol or same-ISIN overlaps | 0 |
| Instrument records | 219 |
| `build_report.json` `counts.instrument_records` | 189 |

The 189 figure is a stale count inside the build report. The live conversion report and
the universe file agree with each other. The build report was not rewritten.

Review, packet, and worksheet share the same 271 row keys. Cited transcription files
that fail their recorded hash: 0, as reported by the investigation (38 evidence-registry
files, 38 matches). `IndexInclExcl.xls` is on disk and labelled NOT PARSED. It was not
parsed into constituents.

File hashes at the investigation:

| File | SHA-256 |
|---|---|
| `nifty100_review.csv` | `a9289cbe4a1efcbc04497770e23739b36d920d0fee49139cf03800dcd6938886` |
| `nifty100_universe.csv` | `1ce5442ab251ea85b3ee7126458ae3c2ba68487a1ad8290e6f0359c2c9af5ebb` |
| `nifty100_baseline.csv` | `d82af7f7d45f209d77268a3e82dc1ed8a3d317db7077d5e39d712c390e926b9c` |
| `nifty100_changes.csv` | `ddd4302e31a5ce7c1508c5a64b5a2b75cbab824b30a73c2e34bed3e483e0da65` |
| `nifty100_count_exceptions.csv` | `f92b7a18725700cc11e6931eafee2ffe7222dbf32c3fe2844263800e783cfd63` |
| `T001_nifty100_owner_worksheet.csv` | `4dbf88ce830f7d5c96df3ef7c3cd1ff052d6e2d433f825a26f11ebc01196a87f` |

Date span: first `effective_from` is 2020-12-31. Latest period start is 2025-12-05
(`DUMMYHDLVR`, open). A membership load before 2020-12-31 returns no members.

## 3. How a period becomes verified

`membership.py` verifies a period only when the start row, and the end row when the
period is closed, have a human `ACCEPTED` decision whose hash matches the current row,
and every count-exception row the conversion uses is likewise accepted. An identity
finding clears the source hash even when the review rows are accepted. One undecided
exception withholds verification from every period. A blank decision is skipped.
Worksheet recommendations are not decisions (`D49`, `D53`).

## 4. Row classification

The decision column is empty on every row. The groups below are the worksheet's evidence
class and proposed action. They are not owner approvals.

| Rows | Priority | Evidence class | Proposed action | Identity finding |
|---|---|---|---|---|
| 222 | P3 | `EVIDENCE_CONFIRMED` | `ACCEPT_RECOMMENDED` | none |
| 6 | P3 | `EVIDENCE_CONFIRMED_LIVE_LIST` | `ACCEPT_RECOMMENDED` | none |
| 4 | P3 | `EVIDENCE_CONFIRMED` | `ACCEPT_RECOMMENDED` | yes (section 6) |
| 10 | P2 | `EVIDENCE_CONFIRMED_VISUAL_READ` | `ACCEPT_AFTER_VISUAL_CHECK` | none |
| 4 | P2 | `EVIDENCE_INCOMPLETE` | `OWNER_JUDGEMENT_REQUIRED` | yes |
| 25 | P1 | `EVIDENCE_CONFIRMED` | `ACCEPT_RECOMMENDED` | none; each gates all periods |

`EVIDENCE_CONFLICTING`: 0. `EVIDENCE_ABSENT`: 0. Every worksheet source-file hash check
is `MATCH`.

The 222-row group is one disposition: the packet says `VERIFIED` against the cited file,
the hash matches, and the decision is empty. Accepting that group still does not verify
a period until the period's start row, end row, and all 25 exceptions are accepted, and
the period has no identity finding.

Intervals below are inclusive universe dates. A removal stays a member through the day
before the removal's effective date.

### Six same-ISIN renames

Evidence is the local NSE `symbolchange.csv` copy. The worksheet calls it an official
list and also says the copy is not a dated document. Decision: empty. Proposed action:
`ACCEPT_RECOMMENDED`.

| Row | Symbol opened | Inclusive period opened | Closes |
|---|---|---|---|
| `change:R-2022-03-07-ZYDUSLIFE:RENAME:ZYDUSLIFE:INE010B01027` | ZYDUSLIFE | 2022-03-07 .. 2022-09-29 | CADILAHC through 2022-03-06 |
| `change:R-2022-12-05-LTIM:RENAME:LTIM:INE214T01019` | LTIM | 2022-12-05 .. open | LTI through 2022-12-04 |
| `change:R-2023-08-24-ADANIENSOL:RENAME:ADANIENSOL:INE931S01010` | ADANIENSOL | 2023-08-24 .. open | ADANITRANS through 2023-08-23 |
| `change:R-2024-06-07-UNITDSPR:RENAME:UNITDSPR:INE854D01024` | UNITDSPR | 2024-06-07 .. open | MCDOWELL-N through 2024-06-06 |
| `change:R-2025-04-09-ETERNAL:RENAME:ETERNAL:INE758T01015` | ETERNAL | 2025-04-09 .. open | ZOMATO through 2025-04-08 |
| `change:R-2025-10-24-TMPV:RENAME:TMPV:INE155A01022` | TMPV | 2025-10-24 .. open | TATAMOTORS through 2025-10-23 |

### Ten image-only rows (E03)

Source: `ind_prs23082021.pdf`. The registry says the body is images and is not
transcribed. The packet verdict is `VERIFIED` from a visual read. This campaign did not
re-read page 5. Decision: empty. Proposed action: `ACCEPT_AFTER_VISUAL_CHECK`.

| Row | Action | Symbol | Inclusive period touched |
|---|---|---|---|
| `change:E03:REMOVE:ABBOTINDIA:INE358A01014` | REMOVE | ABBOTINDIA | closes 2020-12-31 .. 2021-09-29 |
| `change:E03:REMOVE:ALKEM:INE540L01014` | REMOVE | ALKEM | closes 2020-12-31 .. 2021-09-29 |
| `change:E03:REMOVE:MRF:INE883A01011` | REMOVE | MRF | closes 2021-03-31 .. 2021-09-29 |
| `change:E03:REMOVE:PETRONET:INE347G01014` | REMOVE | PETRONET | closes 2020-12-31 .. 2021-09-29 |
| `change:E03:REMOVE:UBL:INE686F01025` | REMOVE | UBL | closes 2020-12-31 .. 2021-09-29 |
| `change:E03:ADD:BANKBARODA:INE028A01039` | ADD | BANKBARODA | opens 2021-09-30 .. open |
| `change:E03:ADD:CHOLAFIN:INE121A01024` | ADD | CHOLAFIN | opens 2021-09-30 .. open |
| `change:E03:ADD:JINDALSTEL:INE749A01030` | ADD | JINDALSTEL | opens 2021-09-30 .. 2022-03-30 |
| `change:E03:ADD:PIIND:INE603J01030` | ADD | PIIND | opens 2021-09-30 .. 2024-03-27 |
| `change:E03:ADD:SAIL:INE114A01011` | ADD | SAIL | opens 2021-09-30 .. 2022-09-29 |

### Twenty-five count exceptions

Each decision is empty, so `count_exceptions_accepted` is false and every period is
unverified. One rejection or skip keeps all 185 periods unverified. Proposed action:
`ACCEPT_RECOMMENDED`.

| Row | Count | Cited document |
|---|---|---|
| `exception:2023-07-20` | 101 | ind_prs17072023.pdf |
| `exception:2023-08-21` | 101 | ind_prs17072023.pdf |
| `exception:2023-08-24` | 101 | ind_prs17072023.pdf |
| `exception:2023-09-07` | 100 | ind_prs05092023.pdf |
| `exception:2023-09-29` | 101 | ind_prs17082023.pdf |
| `exception:2024-01-05` | 101 | ind_prs17082023.pdf |
| `exception:2024-03-28` | 101 | ind_prs17082023.pdf |
| `exception:2024-05-15` | 101 | ind_prs17082023.pdf |
| `exception:2024-06-07` | 101 | ind_prs17082023.pdf |
| `exception:2024-08-30` | 100 | ind_prs23082024_1.pdf |
| `exception:2025-01-06` | 101 | ind_prs30122024.pdf |
| `exception:2025-01-10` | 101 | ind_prs30122024.pdf |
| `exception:2025-01-29` | 101 | ind_prs30122024.pdf |
| `exception:2025-02-10` | 100 | ind_prs06022025_1.pdf |
| `exception:2025-04-07` | 101 | ind_prs02042025.pdf |
| `exception:2025-04-09` | 101 | ind_prs02042025.pdf |
| `exception:2025-05-07` | 101 | ind_prs02042025.pdf |
| `exception:2025-06-16` | 101 | ind_prs02042025.pdf |
| `exception:2025-06-19` | 101 | ind_prs02042025.pdf |
| `exception:2025-06-27` | 100 | ind_prs25062025_2.pdf |
| `exception:2025-10-14` | 101 | ind_prs07102025.pdf |
| `exception:2025-10-24` | 101 | ind_prs07102025.pdf |
| `exception:2025-11-12` | 101 | ind_prs07102025.pdf |
| `exception:2025-11-17` | 100 | ind_prs13112025.pdf |
| `exception:2025-12-05` | 101 | ind_prs28112025.pdf |

## 5. Five dummy spin-off seats

None has an instrument record under the dummy symbol. All five ISINs are inferences in
`build_report.json`, taken from `EQUITY_L` of the later name, with no bhavcopy row on
the add date. The packet marks four `INFERENCE`. DUMMYREL is `VERIFIED` in the packet
because the symbol is taken from the Nifty 50 list of 31 July 2023. The Nifty 100
release does not print that symbol, and `D53` does not treat an inference as fact. This
review does not settle that disagreement.

| Symbol | Inclusive interval | ISIN | Later seat |
|---|---|---|---|
| DUMMYREL | 2023-07-20 .. 2023-08-20 | INE758E01017 | JIOFIN, separate period |
| DUMMYITC | 2025-01-06 .. 2025-01-28 | INE379A01028 | ITCHOTELS |
| DUMMYSIEMS | 2025-04-07 .. 2025-06-18 | INE1NPP01017 | ENRIN |
| DUMMYTATAM | 2025-10-14 .. 2025-11-11 | INE1TAE01010 | TMCV |
| DUMMYHDLVR | 2025-12-05 .. open | INE2KCE01013 | still the open seat; KWIL is outside this file |

Accepting a dummy row accepts the inferred ISIN. The dummy period stays unverified
either way, because the dummy symbol has no identity record.

## 6. Eight periods a full acceptance would still leave unverified

The investigation replaced `read_review` in memory with `ACCEPTED` for all 271 keys,
reviewer `SIMULATION-NOT-A-DECISION`, date 2026-11-10. It did not write the review file.
After the run the file on disk still had 271 empty decisions. This pass confirmed that
the decision column is still empty.

Simulation result, as reported: review status would be `COMPLETE`, 177 periods would
carry a source hash, 8 would not. Those 8 are the identity findings. The simulation is
not an owner decision and certifies nothing.

| Symbol | Inclusive interval | Why it stays unverified |
|---|---|---|
| BAJFINANCE | 2020-12-31 .. 2025-06-15 | INE296A01016 and INE296A01024 both listed as BAJFINANCE on the start date. The 2016-09-09 link is refused (`ED-37`) |
| GRASIM | 2020-12-31 .. open | INE047A01013 and INE047A01021 both listed as GRASIM. The 2016-10-07 link is refused. No `ISIN_CHANGE` record exists |
| YESBANK | 2021-03-31 .. 2022-03-30 | INE528G01027 and INE528G01035 both listed as YESBANK on the start date. The 2020-03-16 price-scale record is absent. The earlier 2017-09-22 change is a different, evidenced event |
| DUMMYREL | 2023-07-20 .. 2023-08-20 | No record for DUMMYREL |
| DUMMYITC | 2025-01-06 .. 2025-01-28 | No record for DUMMYITC |
| DUMMYSIEMS | 2025-04-07 .. 2025-06-18 | No record for DUMMYSIEMS |
| DUMMYTATAM | 2025-10-14 .. 2025-11-11 | No record for DUMMYTATAM |
| DUMMYHDLVR | 2025-12-05 .. open | No record for DUMMYHDLVR |

The later BAJFINANCE period, INE296A01032 from 2025-06-16, is among the 177 in that
simulation. It is a separate period and is not joined to the earlier price history.

Because GRASIM's unverified period is open from the baseline, the simulated file would
still return `UNIVERSE_UNVERIFIED` on every event date from 2020-12-31 forward. GRASIM
is a member on every one of those dates.

## 7. Missing history before 2020-12-31

The only baseline date is 2020-12-31. No universe `effective_from` is earlier. The
evidence registry's earliest `doc_date` is 2021-02-23. Dated lists on disk cover
December 2020, March 2021, September 2021, and March 2022, plus two Nifty 50 lists that
are not Nifty 100 baselines. `IndexInclExcl.xls` remains NOT PARSED.

Using a later constituent list for 2016-2020 would be survivorship bias. Removed names
are present only from 2020-12-31 forward. Their absence before the baseline is a missing
universe, not evidence that they were out of the index.

Inside the transcribed window the converter rolls forward at 100, or a declared 101, on
each event date. The README's claim that this matches the March 2021, September 2021,
and March 2022 official lists was not re-extracted from those PDFs in this pass.

## 8. Owner decisions

| ID | Decision | Current state | Recommendation | If deferred |
|---|---|---|---|---|
| OD-MEM-1 | `ACCEPTED` or `REJECTED` on each of the 271 rows, written by the owner into `nifty100_review.csv`, with reviewer and date. The 25 exceptions gate every period. The 10 E03 rows need a look at page 5 of `ind_prs23082021.pdf` | All blank | Follow the worksheet priority: exceptions, then E03, then the four inferred dummy ISINs, then the rest | Every period stays unverified |
| OD-MEM-2 | Whether DUMMYREL's ISIN `INE758E01017` is accepted as an inference | Packet says verified; build report says inferred | Leave the period unverified until an official Nifty 100 assignment exists | The 2023-07-20 .. 2023-08-20 seat stays unverified |
| OD-MEM-3 | How a dummy seat with no candles is represented | Five seats, no identity record | Keep them unverified and out of candidate generation. Do not invent a listing | Those dates stay `UNIVERSE_UNVERIFIED` while the seat is in the file |
| OD-MEM-4 | Official records for BAJFINANCE 2016-09-09, GRASIM 2016-10-07, YESBANK 2020-03-16 | Refused by `ED-37`. Histories stay unjoined | Do not join the ISINs | GRASIM alone keeps every in-window date unverified after a full acceptance |
| OD-MEM-5 | Research window: from 2020-12-31 only, or an earlier official baseline transcribed under `D49` | No baseline before 2020-12-31 | Limit membership-based research to 2020-12-31 onward until a baseline is supplied | 2016-2020 cannot support a survivorship-controlled study |

## 9. What was not done

- No `ACCEPTED` value was written. `D53` reserves that act for the owner.
- `nifty100_universe.csv` was not regenerated with hashes.
- `IndexInclExcl.xls` was not parsed into constituents.
- The three ISIN histories were not joined.
- No scan was run, and no performance figure was computed.
- `build_report.json` was left with its historical `instrument_records: 189` count. The current identity file has 219 records.

## 10. Blockers

| Blocker | State |
|---|---|
| B11-R | Open. 271 rows undecided. 185 periods unverified |
| B11-P / B11-R2 | Open. No membership before 2020-12-31 |
| Five dummy seats | Open. Review acceptance does not verify them |
| ED-37 | Open. Three unevidenced ISIN changes. GRASIM blocks every later date by itself |
| DATA_READY | Not claimed |

Part 10 of `IMPLEMENTATION_BLOCKERS.md` still speaks of 171 periods and 13 unresolved
ISINs. The live file is 185 periods, 3 unevidenced ISIN changes, and 5 dummy identity
gaps. That older paragraph was not rewritten.
