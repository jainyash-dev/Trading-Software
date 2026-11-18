# P0 identity blocker decisions V2: OD-ID-1 (BAJFINANCE), OD-ID-2 (GRASIM)

**Date:** 2026-11-15 (Batch 8)
**Extends:** `P0_IDENTITY_BLOCKER_DECISIONS.md` (kept unchanged). V2 adds the verified mechanism by which the 2016 ambiguity reaches the research window, and a third option for the owner.
**Rule kept:** agents do not choose an effective session and do not join ISIN histories. Nothing in this file has been implemented.

## 1. Verified facts

| Item | BAJFINANCE (OD-ID-1) | GRASIM (OD-ID-2) |
|---|---|---|
| Old ISIN -> new ISIN | `INE296A01016` -> `INE296A01024` | `INE047A01013` -> `INE047A01021` |
| Held notice | `nse/data/universe/evidence/identity/isin_notices/msei_bajfinance_4496_2016.pdf`, SHA-256 `11b2a619b064c270d04a3fedc14633317d0a87959a212f98dad5349ad14babc5` (re-hashed 2026-11-15, matches) | `.../msei_grasim_4581_2016.pdf`, SHA-256 `974296c5ad548d0f69e686af4cdb36d04e2472c7dc486a6ea68144d50ea2511d` (re-hashed, matches) |
| Notice wording (text extracted in Batch 11) | "ISIN code ... shall be changed w.e.f. September 9, 2016"; "The New ISIN shall be effective for trades done on and from the Ex-date i.e. September 8, 2016"; record-date column September 10, 2016 (a Saturday) | "shall be changed w.e.f. October 7, 2016"; "effective for trades done on and from the Ex-date i.e. October 6, 2016"; record-date column October 6, 2016 (the NSE API says 08-Oct-2016, a Saturday) |
| Batch 11 correction | The two dates have different stated meanings (code change vs trades from ex-date). NSE's own "Change in ISIN" circulars use the same pairing (NSE/CML/35870). The remaining ambiguity is that the notice is MSEI's and the record dates are inconsistent; see `P0_BATCH11_MEMBERSHIP_IDENTITY_REPORT.md` section 5 | same |
| Bhavcopy observation | New ISIN first held session 2016-09-09 (`cm09SEP2016bhav.csv.zip`, SHA-256 `fba772ec...`) | New ISIN first held session 2016-10-07 (`cm07OCT2016bhav.csv.zip`, SHA-256 `c58f9537...`) |
| Instrument records | Two `LISTING` rows: old ISIN from 2016-01-01 with **no end**, new ISIN from 2016-09-09. Later `ISIN_CHANGE` to `INE296A01032` on 2025-06-16 (ED-37) | Two `LISTING` rows: old ISIN from 2016-01-01 with **no end**, new ISIN from 2016-10-07 |
| `instruments.resolve` result (run 2026-11-15) | 2016-06-01 RESOLVED (old ISIN); 2021-06-01 **UNKNOWN_INSTRUMENT**: "two or more ISINs are listed as BAJFINANCE on 2021-06-01: INE296A01016, INE296A01024"; 2025-07-01 RESOLVED (`INE296A01032`) | 2021-06-01 **UNKNOWN_INSTRUMENT**: "two or more ISINs are listed as GRASIM ... INE047A01013, INE047A01021" |
| Eligibility matrix (isolated 1.6.0, `P0_RESEARCH_ELIGIBILITY_MATRIX.csv`) | 1,234 member-dates: 1,098 on `INE296A01024`, 136 on `INE296A01032`; identity UNRESOLVED; membership UNVERIFIED; all EXCLUDED_MEMBERSHIP | 1,234 member-dates on `INE047A01021`; identity UNRESOLVED; membership UNVERIFIED |
| Ledger | `baseline:BAJFINANCE:INE296A01024` blank; `change:I-2025-06-16-BAJFINANCE:...:INE296A01032` blank | `baseline:GRASIM:INE047A01021` blank |

## 2. Why a 2016 ambiguity blocks 2021-2025 dates (verified mechanism)

The research window starts 2020-12-31 (D59). Both candidate effective dates for each change are more than four years earlier. Inside the window each symbol trades on one ISIN only. The block arises because the old ISIN's LISTING record is open-ended, so the record set contradicts itself on every date after the change. `resolve` fails closed on a contradiction. That is the correct behaviour; the cause is the missing end of the old listing, not the choice between the two dates.

Inference (not a decision): any treatment that ends the old ISIN **no later than** the later of the two stated dates (9 Sep 2016; 7 Oct 2016) gives the same identity for every date from 2016-10-07 onward, whichever of the two dates is legally correct. The ambiguity is material only to sessions on or between the two dates and to price joins across them.

## 3. Missing evidence

One official document (NSE CM circular, depository corporate-action record, or a clarifying MSEI/NSE notice) stating a single effective session. The CDSL "DETAILS OF CORPORATE ACTIONS" series exists for 2016 (49 communiques; see `P0_CA_SOURCE_FEASIBILITY_AUDIT.md`), but whether it covers these changes is unverified, and acquiring it needs authorization.

## 4. Owner decision required (one per symbol)

| Option | What the owner records | Effect | Risk |
|---|---|---|---|
| **1. Keep unjoined, unchanged** (default) | Nothing | 1,098 BAJFINANCE and 1,234 GRASIM member-dates stay identity UNRESOLVED | None; maximum exclusion |
| **2. Name one effective session** | The date and the authoritative document, which must be held locally with its hash | Engineering adds a verified `ISIN_CHANGE` record citing that document; history may be joined | Needs evidence not held today |
| **3. Bounded end without a join** (new in V2) | "The old ISIN is not listed after <later stated date>; no price join across the change", citing the held MSEI notice and the first-session bhavcopy | Engineering would record an end for the old listing; identity on dates after the later date resolves to the new ISIN; pre-change and post-change price histories stay separate | Records something the notice supports only as an upper bound. The owner must judge whether an upper bound is acceptable identity evidence. Not a Rulebook question; it is an identity-evidence standard question |

Option 3 is an engineering observation offered for decision. It does not choose between the two stated dates and does not join prices. Agents will not implement it without an explicit owner instruction naming the symbol and the bound.

**Separate decisions (unchanged by any option):** membership acceptance of each baseline row; `change:I-2025-06-16-BAJFINANCE` membership (its identity on 2025-06-13 is also UNKNOWN for the same reason); D66 corporate-action completeness for every window.

## 5. Related

- YESBANK OD-ID-3: recorded via NSE/CML/43833; not part of this request.
- Dummy seats OD-MEM-2/3: separate (`P0_OPTIONAL_OWNER_DECISIONS.md`).
- The backlog text for these two baseline rows is cross-copied (`P0_MEMBERSHIP_DECISION_SUMMARY_V2.md` section 4); this file has the correct per-symbol facts.
