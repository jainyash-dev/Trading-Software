# P0 certifiable-window assessment

**Dated 2026-11-10. Assessment only. No code, price, review decision, or identity join was changed.**

Repository: branch `main`, HEAD `9e302df1a81c2b13696d8fab61f05d377481be2e`, nothing staged,
80 modified and 38 untracked paths. `DATA_READY` is not claimed. P0 is not complete.

Confidence words: **VERIFIED** means checked against the current files or code in this
pass. **PARTIALLY VERIFIED** means a prior read-only investigation plus a current file
check, without repeating every raw-row extraction. **UNVERIFIED** means the evidence
needed to certify it is absent.

## A. Executive conclusion

No date can be certified today as a point-in-time Nifty 100 research universe.
**VERIFIED.**

The membership file has 185 periods and 0 source hashes. All 271 review decisions are
blank. The conversion withholds every period until every count-exception row it uses is
`ACCEPTED`, and it also withholds any period with an identity finding. A scan date is
`UNIVERSE_UNVERIFIED` unless every member that day is verified. GRASIM is a member on
every sampled date from 2020-12-31 through 2025-12-31, and its identity finding is
unresolved. There is no sub-window of this file in which the full index is free of that
finding.

The largest period that could become a defensible sample, after owner decisions and
explicit exclusions, starts on **2020-12-31** and can run through **2025-12-31** only as
a named sample that is not the Nifty 100. The longest stretch in which the official
member count is 100 and no dummy seat is present is **2020-12-31 through 2023-07-19**.
That stretch still includes GRASIM and BAJFINANCE on every day, and YESBANK from
2021-03-31 through 2022-03-30. Dropping those names, and every member whose
corporate-action response is an empty list, is an owner-defined sample. It is not
survivorship-controlled index research.

2016-01-01 through 2020-12-30 cannot be certified. There is no point-in-time membership.
D59 already forbids using a later constituent list to fill that gap.

## B. Earliest potentially certifiable date

**2020-12-31.** **VERIFIED** as the first baseline date in `nifty100_baseline.csv` and as
the D59 window start.

It is not certifiable now. It becomes a candidate start only after the owner accepts the
review rows that open the retained periods, accepts all 25 count exceptions, and
authorises an explicit exclusion list for unresolved identities. Without those acts the
current gate certifies nothing on that date.

No earlier date is a candidate. **VERIFIED:** a membership load before 2020-12-31 has no
members.

## C. Latest potentially certifiable date

**2025-12-31** is the latest archive date and the latest date a reduced sample could
reach. **PARTIALLY VERIFIED:** the calendar and manifest still show an equity session
that day, from the prior reconciliation. This pass did not rehash the archives.

It is not a certified end date. From 2025-12-05 the official count is 101 because
DUMMYHDLVR is an open seat with no identity record. A sample that continues through
2025-12-31 must exclude that seat and say it is not the official index.

The latest date on which the file's own count is 100 and no dummy symbol is a member is
**2023-07-19**. **VERIFIED** from the universe rows: 100 members that day, exclusions
required are BAJFINANCE and GRASIM, 98 names remain before corporate-action exclusions.
2023-07-20 adds DUMMYREL and the count becomes 101.

## D. Potentially certifiable universe

Method, applied to `nifty100_universe.csv` in memory. Nothing was written.

1. A date is inside the D59 window only on or after 2020-12-31.
2. The current code certifies a date only when every member that day has a verified
   period. One unverified member withholds the date.
3. Identity findings and dummy symbols were read from the period notes. They are
   BAJFINANCE, GRASIM, YESBANK, DUMMYREL, DUMMYITC, DUMMYSIEMS, DUMMYTATAM, DUMMYHDLVR.
4. Empty corporate-action responses were intersected with membership. They are not
   treated as "no events."
5. A name is retained on a date only if it is a member, its review rows would have to be
   owner-accepted, and it is not in the exclusion list for that date.

Illustrative size after removing only the identity and dummy names, before
corporate-action exclusions:

| Date | Members in the file | Removed | Remaining |
|---|---|---|---|
| 2020-12-31 | 100 | BAJFINANCE, GRASIM | 98 |
| 2021-03-31 through 2022-03-30 | 100 | those two, plus YESBANK | 97 |
| 2023-07-19 | 100 | BAJFINANCE, GRASIM | 98 |
| 2023-07-20 | 101 | those two, plus DUMMYREL | 98 |
| 2025-12-31 | 101 | BAJFINANCE, GRASIM, DUMMYHDLVR | 98 |

**VERIFIED** as a count of rows. It is not a certified universe. The current code will
not treat those 97 or 98 names as verified while the removed names are still members in
the file.

Corporate-action exclusions shrink it further. On 2020-12-31 the empty-response members
include ADANITRANS, CADILAHC, ICICIPRULI, LTI, MCDOWELL-N, MOTHERSUMI and TATAMOTORS, in
addition to GRASIM and BAJFINANCE. That is 11 names removed and 89 remaining, before any
unparsed price event inside a loaded history is considered. **VERIFIED** as membership
overlap with the empty-response list. Whether each of those scans is G0 `MANUAL` follows
from the existing gate and was not re-executed symbol by symbol in this pass.
**PARTIALLY VERIFIED.**

This sample is defensible only under a name that is not "the Nifty 100." The omitted
names were in the index. Removing them because evidence is missing avoids treating
unknown evidence as valid. It also means index-level results are not survivorship-controlled.

## E. Securities and periods that must be excluded

Excluded from any claim that the full index is certified. They can stay in the file.
The scan then stays `UNIVERSE_UNVERIFIED`. They can be removed only by an owner decision
that defines a smaller sample.

| Symbol or seat | Period that blocks a full-index date | Why |
|---|---|---|
| GRASIM | 2020-12-31 onward, open | Unevidenced ISIN change on 2016-10-07. Member on every sampled date |
| BAJFINANCE | 2020-12-31 through 2025-06-15, and the symbol remains `DATA_INSUFFICIENT` after the later evidenced change | Unevidenced change on 2016-09-09. The 2025 change does not clear that finding. **PARTIALLY VERIFIED** from the prior identity read and the current universe note |
| YESBANK | 2021-03-31 through 2022-03-30 | Unevidenced change on 2020-03-16. The 2017 split is a separate, evidenced event and still does not join prices |
| DUMMYREL | 2023-07-20 through 2023-08-20 | No identity record. ISIN inferred |
| DUMMYITC | 2025-01-06 through 2025-01-28 | Same class |
| DUMMYSIEMS | 2025-04-07 through 2025-06-18 | Same class |
| DUMMYTATAM | 2025-10-14 through 2025-11-11 | Same class |
| DUMMYHDLVR | 2025-12-05 onward, open | Same class |

Empty corporate-action responses that overlap membership, so those member-dates cannot be
treated as corporate-action-covered: ADANITRANS, BAJAJHFL, CADILAHC, ENRIN, ETERNAL,
ICICIPRULI, ITCHOTELS, LTI, LTIM, MCDOWELL-N, MOTHERSUMI, PAYTM, SWIGGY, TATAMOTORS,
TMCV, ZOMATO. `SRTRANSFIN` is also an empty 2016-2025 response. It is not a current
member symbol; `SHRIRAMFIN` holds the parsed events and those rows do not cover
`SRTRANSFIN`. **VERIFIED** for the overlap list and for the saved `SRTRANSFIN` body.

Price-continuity exclusions, if a continuous unadjusted series is required:

| Case | Effect |
|---|---|
| EQ-only loader | ADANIPOWER and CGPOWER have sessions that exist only as BE or BZ. An EQ series has holes there. The prices were not missing. **PARTIALLY VERIFIED** from the prior raw-row investigation. This pass did not re-read the zips |
| ADANIPOWER 2021-06-11 to 2021-09-20, and the other BE stretches listed in the price-gap report | Exclude those dates from an EQ continuous series, or leave the missing-EQ markers. Do not fill them with BE prices unless the owner changes the series rule |
| CGPOWER 2021-09-15 to 2022-01-04, and the other BE/BZ stretches | Same |
| ADANIPOWER 2025-09-22 | Recorded 1:5 split and ISIN change. Do not treat prices across the two ISINs as one scale |
| CROMPGREAV 2016-03-15 | Unparsed scheme, ratio 0,0. The date is before the D59 window. Any CGPOWER history that starts before that date and is treated as one series includes an unknown factor |

## F. Unresolved owner decisions

None of these were taken in this pass.

1. Accept or reject each of the 271 review rows. The 25 count exceptions gate every period. Ten E03 rows still need a look at page 5 of `ind_prs23082021.pdf`, which has no extractable text for those names. Four dummy-ISIN rows are inferences.
2. Authorise, or refuse, a research sample that drops unresolved identities and dummy seats. Refusal leaves no certifiable full-index date.
3. Keep or change the EQ-only rule for BE and BZ sessions.
4. Supply a ratio for the CROMPGREAV scheme, or keep continuity across 2016-03-15 excluded.
5. Decide whether an adjusted price series is wanted. D50 still forbids applying an unverified ratio.
6. Confirm or replace the inferred 09:15-15:30 hours on 2024-01-20.
7. Supply the 34 TradingView observations if external parity is part of the claim being certified. It is not required to describe a fail-closed data sample, and it is required before any external validation claim.

## G. External evidence still required

| Evidence | Why the files on disk are not enough |
|---|---|
| Owner review decisions | Hash-matched citations are not acceptance |
| A document naming `INE296A01024` on 2016-09-09 | The held split's ex-date is the previous session and the record date is a Saturday |
| A document naming `INE047A01021` on 2016-10-07 | The saved response never prints that ISIN |
| A document naming `INE528G01035` on 2020-03-16 | The saved response has no March 2020 event |
| Official ISINs for the five dummy symbols, if those seats are to be verified | Current ISINs are inferred from the later listings |
| A pre-2020-12-31 Nifty 100 baseline, only if the window should start earlier | `IndexInclExcl.xls` is still not parsed. Parsing it was not authorised |
| A second corporate-action source | 47 empty lists and 10 unparsed price events. An empty list is not completeness |
| Ratios for the unparsed events that fall inside loaded history | Includes VBL 2024-09-12 and TVSMOTOR 2025-08-25, which are inside the D59 window |
| The 34 TradingView observations | None are in the repository |

## H. Minimum remaining tasks before any P0 certification

1. Owner completes the review worksheet, including all 25 count exceptions.
2. Owner states whether unresolved identities and dummy seats are removed from the research sample or whether certification waits until documents exist. The second choice certifies no full-index date with the evidence now held.
3. Re-run conversion only after those decisions are written by the owner. Do not write `ACCEPTED` before that.
4. Keep empty corporate-action responses out of coverage. Symbols that remain in the sample with an empty response stay G0 `MANUAL`.
5. Keep raw prices unadjusted. Exclude continuity across the ADANIPOWER split and the CROMPGREAV scheme.
6. Leave T-005 open unless the TradingView observations are supplied and compared.
7. Only then restate readiness. `DATA_READY` stays false until that statement matches the gates.

## I. Why a proposed window is or is not defensible

| Proposed window | Verdict | Reason |
|---|---|---|
| 2016-01-01 through 2025-12-31 as the Nifty 100 | Not defensible | No membership before 2020-12-31. Using today's or 2020's constituents for 2016-2020 would be survivorship bias. D59 forbids it |
| 2020-12-31 through 2025-12-31 as the full Nifty 100, now | Not defensible | 0 verified periods. GRASIM blocks every date even after a hypothetical acceptance of all 271 rows |
| 2020-12-31 through 2023-07-19 as the full index, now | Not defensible | Official count is 100 and there is no dummy seat. GRASIM and BAJFINANCE are still members on every day, and the review is blank |
| 2020-12-31 through 2023-07-19, full index, after the owner accepts every evidence-confirmed row and every count exception, without new identity documents | Not defensible as the index | The identity findings remain. The code withholds any date that still contains GRASIM |
| 2020-12-31 through 2025-12-31 as a named sample that drops unresolved identities, dummy seats, and empty-coverage member-dates, after owner acceptance of the retained rows and of that exclusion rule | Potentially defensible as a sample. Not defensible as the Nifty 100 | Unknown evidence stays excluded. The omitted names were index members, so index performance and survivorship control are not claimed. Corporate-action completeness inside covered, dividend-only windows is still not proved |
| Any window plus a TradingView parity claim | Not defensible | No TradingView observation exists |

## J. Confidence by conclusion

| Conclusion | Confidence |
|---|---|
| 271 decisions are blank and 185 periods have no source hash | VERIFIED |
| All 25 count exceptions must be accepted before any period verifies | VERIFIED, from `membership.convert` |
| A date is unverified if any member that day is unverified | VERIFIED, from `universe.limitations` |
| GRASIM is a member on every sampled date from 2020-12-31 through 2025-12-31 | VERIFIED |
| No full-index date is certifiable with the evidence now held | VERIFIED |
| The eight identity and dummy periods are the ones a full acceptance would still leave unverified | PARTIALLY VERIFIED. The in-memory simulation was run in the earlier investigation. This pass confirmed those symbols are still the ones marked `UNKNOWN_INSTRUMENT` or `DUMMY*` |
| BAJFINANCE stays `DATA_INSUFFICIENT` after 2025-06-16 | PARTIALLY VERIFIED. Prior identity run. Not re-executed today |
| Empty responses are 47 and are not coverage | VERIFIED for the saved `SRTRANSFIN` body and the coverage row count of 145. The other 46 were counted in the prior coverage pass |
| BE/BZ gaps and the two price-scale events | PARTIALLY VERIFIED. Classifications stand. Zips were not re-read today |
| Calendar and EOD counts of 2,466 and 12 | PARTIALLY VERIFIED. Reproduced earlier in this campaign. Not rehashed today |
| TradingView parity | UNVERIFIED. No observations |
| A reduced sample after owner approval could start on 2020-12-31 | VERIFIED as a boundary. UNVERIFIED as a certification, because the approvals do not exist |

## What is already verified, what is only potential, what is blocked

Already verified: the fail-closed gates, the blank review, the D59 start date, the
identity and dummy names still present in the universe file, the empty corporate-action
list including `SRTRANSFIN`, and the absence of TradingView observations.

Potentially certifiable after owner approval: a sample from 2020-12-31 onward that
excludes unresolved identities, dummy seats, and empty-coverage member-dates, and that
is not called the Nifty 100.

Currently blocked: every full-index date, every pre-2020 membership claim, T-005, and
`DATA_READY`.

Cannot be certified with available evidence: the full Nifty 100 on any date, continuity
across the three unevidenced ISIN changes, continuity across the CROMPGREAV scheme, and
external zone or SMA parity.
