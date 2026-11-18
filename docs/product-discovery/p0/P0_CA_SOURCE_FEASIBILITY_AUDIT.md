# P0 Batch 7 - Corporate-action source feasibility audit

**Date:** 2026-11-15
**Batch status:** COMPLETE_WITH_ISSUES (feasibility established for event evidence; window-completeness not yet demonstrated by any provider; stops at the acquisition authorization boundary)
**Governs:** D66 (`USER_APPROVED`), ED-56, D62. Builder `nse/research/p0_certification.py` `BUILD_VERSION = "1.6.0"`.
**Supersedes nothing.** Extends `P0_CA_PROVIDER_COMPARISON.md`, whose provider descriptions were general ("often", "may"). This audit records what was actually checked.

**Acquisition:** none. No file was placed in `nse/` or in any evidence folder. Public pages were read to check that access points exist. Two PDFs were cached automatically by the web reader in the session tool-results folder **outside the repository**. They were read for format only, are **not** custody evidence, and must be re-acquired under authorization if used (see section 7).

---

## 1. Baseline verified before this batch

| Item | Verified value | How |
|---|---|---|
| HEAD | `69858d07ccb016b74bc1d518b66b9948656ad6cf` | `git rev-parse HEAD` |
| Staged files | 0 | `git diff --cached --name-only` |
| Dirty paths | 213 (prompt reported ~196) | `git status --porcelain \| wc -l` (difference not investigated path by path; all treated as owner work) |
| Builder | 1.6.0 | `p0_certification.py:82` |
| Production summary | 1.5.0, `certified_symbol_dates` 0 of 123,778 | `P0_CERTIFICATION_SUMMARY.json` |
| D66 | `USER_APPROVED` 2026-11-15; does **not** authorize acquisition | `DECISION_LOG.md` |
| ED-56 | implemented: dual hash, reconciliation schema `gtf.ca_reconciliation.v1`, API refusal | `corporate_actions.py:320-575` |
| `completeness.csv` | absent | `find nse/data -name completeness.csv` |
| `Completeness window accepted` markers | 0 | `grep -c` on `DECISION_LOG.md` |
| Saved NSE CA API bodies | 202 files in `nse/data/corporate_actions/raw/` | `find` |

## 2. What the code enforces versus what D66 requires

Fact (code read): `sources_independent()` (`corporate_actions.py:437`) returns true when the two hashes are distinct and 64-hex, neither file is a saved API response (name `ca_*.json`, `/raw/` path, hash match against held API bodies, or API-shaped JSON), the files are not the same file, and the bytes differ and match their hashes.

Finding F-1 (engineering, not a defect in the D66 sense): **byte distinctness is necessary, not sufficient.** The function cannot detect two files that come from the same upstream record. Examples that would pass the code check but would not be independent under D66:

- a CSV exported from NSE's corporate-actions web page (it is backed by the same `api/corporates-corporateActions` service whose JSON is refused) paired with anything else from NSE's CA service;
- a broker or aggregator reprint of NSE data;
- two PDFs of the same NSE circular (different bytes after re-saving).

Control: provenance independence must be argued per source in the source ledger and in the owner approval request (who issued it, from what upstream record). Code cannot carry that. The owner's dual-hash marker is the control point. **Recommendation (not done):** add a `provider` and `upstream_chain` column to the future source ledger and refuse, in review, any pair whose upstream chains share a publisher. No code change is proposed in this batch.

## 3. Provider findings

Legend: **V** = verified directly in this batch (document or page read); **D** = documented by the provider but not tested against data; **U** = unverified/assumption.

### 3.1 NSE - Futures & Options adjustment circulars (NSE/FAOP) and NSE Clearing (NCL/CMPT)

| Question | Finding | Grade |
|---|---|---|
| Access point | `https://nsearchives.nseindia.com/content/circulars/FAOP<n>.pdf` and `.../CMPT<n>.pdf`; also `archives.nseindia.com` | V (FAOP53548 retrieved, read) |
| Content | NSE/FAOP/53548, 5 Sep 2022, circular ref 101/2022, BAJAJFINSV: "Stock split ratio 5:1", "Bonus issue ratio 1:1", record date 14 Sep 2022, ex-date 13 Sep 2022, adjustment factor 5 x 2 = 10 | V |
| Agreement with held data | `actions.csv` has BAJAJFINSV 2022-09-13 SPLIT 1:5 and BONUS 1:2 (API), record date 14-Sep-2022: consistent | V |
| Event types | SEBI F&O adjustment covers bonus, split, consolidation, rights, mergers/demergers and certain extraordinary dividends | D (stated "In pursuance of SEBI guidelines for adjustments to futures and options contracts"); event list not verified this batch |
| Symbol coverage | Only symbols in the F&O segment at the time | U for each Nifty 100 symbol: F&O tenure is not held locally |
| Historical availability | Archive URLs serve 2022 PDFs; search results show circulars to 2025 | V for 2022; U for 2016-2021 |
| Format | PDF (text-extractable for FAOP53548) | V |
| Event-centric or window-complete | Event-centric. **Possible window-completeness route:** circulars carry a department-wise annual sequence (`101/2022`). If the sequence is gap-free and every F&O adjustment is issued as an FAOP circular, then holding the entire year's FAOP series proves which adjustments were announced for F&O symbols in that year | U (hypothesis; requires the pilot) |
| Empty-window proof | Only through the sequence argument above, only for F&O tenure | U |
| Preservation | Original PDF bytes downloadable; SHA-256 possible | V |
| Independence | Same institution as the refused NSE CA API (exchange), different channel (regulated circular, F&O department). Independent of depositories | Analysis |
| Restrictions / cost / auth | None observed for the archive host; `www.nseindia.com` front end timed out to the web reader (bot protection) | V (archive) / V (front-end timeout) |
| Known gaps | Non-F&O symbols; events NSE does not adjust for (for example, small dividends, which R-12 does not treat as price-scale anyway) | Analysis |

### 3.2 NSE - Capital-market circulars and corporate-announcement attachments

| Question | Finding | Grade |
|---|---|---|
| Access point | Circular search on `www.nseindia.com/resources/exchange-communication-circulars`; corporate filings page `www.nseindia.com/companies-listing/corporate-filings-actions` | U (both timed out to the web reader) |
| Format | Corporate-actions page: listing plus a CSV export, backed by the API already refused | Inference from the held API URL in `coverage.csv`; export not tested |
| Independence | **The web CSV export is not independent of the saved API JSON** (same service). It must not be used as Source A or B | Analysis (F-1) |
| Use | Issuer attachments (scheme documents, board outcomes) can supply **terms** for unparsed events (CGPOWER, VBL) but are issuer documents, not completeness sources | Analysis |

### 3.3 CDSL - "DETAILS OF CORPORATE ACTIONS" DP communiques

| Question | Finding | Grade |
|---|---|---|
| Access point | Communique listing `https://www.cdslindia.com/eservices/Publications/Communique` (filters: year 2022-2026, month, Active/Archive, DP/RTA, department, date range, keyword); historical index PDF `https://www.cdslindia.com/Publications/DP-COMMUNIQUES-INDEX.aspx` | V |
| Series existence | The index (PDF, 804.4 KB, SHA-256 `0afee345d70ed15efa3ec2f2b42a2ba71a5a592bbfc43fe2f70919e4c3a71c22`, read from cache, not held) lists communiques titled "DETAILS OF CORPORATE ACTIONS" every year from 2010 to 2026: 2016 49, 2017 41, 2018 36, 2019 30, 2020 24, 2021 53, 2022 72, 2023 67, 2024 83, 2025 79, 2026 66 (to DP2026-800, 13-Nov-2026) | V (count by title match; a title variant could be missed) |
| Content | **Not verified.** The direct download `DownloadFile?eventID=DP2026-800&method=communique` returned HTTP 404 to the web reader. CDSL operating instructions describe CA setup by parent ISIN, benefit ISIN, ratio and record date | U (content) / D (fields) |
| Event-centric or window-complete | Event-centric list; whether every equity corporate action appears is **unknown** | U |
| Symbol/ISIN | ISIN-keyed (documented); mapping to NSE symbol via `instrument_records.csv` | D |
| Independence | Different institution from NSE. **Risk:** depositories set up actions from issuer/RTA instructions that cite the exchange's record-date confirmation (NSDL lists "copy of the letter / circular of the stock exchange confirming / notifying the record date" as a required document; CDSL's equivalent not checked). The record date is therefore partly exchange-derived; the depository's own contribution is execution (benefit ISIN, ratio credited) | V (NSDL wording, via search result of `issuer.nsdl.com/ca.html`); analysis |
| Restrictions / cost / auth | Listing and index public; per-file download failed to the web reader (may need a browser session) | V (404) |

### 3.4 NSDL

| Question | Finding | Grade |
|---|---|---|
| Access point | `nsdl.co.in/services/corporate.php`, `issuer.nsdl.com/ca.html`, `nsdl.co.in/business/circular.php` | Pages exist (search results); direct fetches failed with `ECONNRESET` |
| Public per-ISIN CA list | **Not found.** Public pages describe process (issuer/RTA uploads benefit details; NSDL informs DPs of dates) and issuer document checklists | V (by absence in search and the process wording); U whether a participant-only feed exists |
| Format | Unknown | U |
| Restrictions | Likely participant/issuer access for executed-action data | U |
| Conclusion | No verifiable public NSDL artefact today. Not proposed for the pilot | - |

### 3.5 BSE (added; the prompt's provider list is not exhaustive)

| Question | Finding | Grade |
|---|---|---|
| Access point | `www.bseindia.com/corporates/corporate_act.aspx` (web listing) | HTTP 403 to the web reader; not checked |
| Paid historical product | BSE market-data-products page, as quoted by search: "historical corporate data (Results, Shareholding pattern and Corporate actions) are available for period since 2006"; EOD corporate-actions subscription | D (search excerpt; page itself 403) |
| Independence | A different exchange; issuers intimate BSE separately under listing regulations. Strongest institutional independence from NSE among the candidates | Analysis |
| Window-completeness | A vendor dataset with a stated coverage period ("since 2006") is the only candidate seen that **claims** window coverage. The claim must be in the delivered product's documentation to count | U |
| Cost | Paid subscription: **requires separate owner authorization** (CLAUDE.md 21.17) | D |
| Symbol mapping | BSE scrip codes; map via ISIN | Analysis |

## 4. D66 independence matrix (analysis)

| Pair | Institutions | Shared upstream | Assessment |
|---|---|---|---|
| NSE FAOP circular + CDSL communique | Exchange + depository | Issuer announcement; depository record date may cite exchange confirmation | **Candidate.** Independent execution records (contract adjustment vs ISIN credit). Shared record-date origin must be disclosed in each approval request |
| NSE FAOP circular + BSE CA record | Exchange + exchange | Issuer announcement only (separate intimations) | **Candidate, strongest independence**; BSE access/cost unresolved |
| CDSL + NSDL | Depository + depository | Issuer/RTA instruction | Not feasible now (no public NSDL artefact) |
| NSE web CSV export + any | - | Same NSE CA service as refused API | **Fails** (F-1) |
| NSE FAOP circular + NSE CMPT circular | Exchange + its clearing corporation | The FAOP circular itself (CMPT implements it) | **Fails**: derivative of one decision; usable only as corroboration |
| Any + saved API JSON | - | - | **Fails** (ED-56) |

## 5. Empty-window feasibility

No provider was shown to prove an empty window. Two routes deserve a pilot:

1. **Sequence-completeness (NSE FAOP):** if the annual FAOP circular number series has no gaps and the adjustment obligation is shown to cover all price-scale events, absence from a complete year proves "no adjustment announced" for a symbol that was in F&O for the whole window. Requires: the full series for the year, evidence of F&O tenure, and evidence of the adjustment obligation's scope.
2. **Coverage-stated dataset (BSE paid):** the delivered product must state its coverage; a stated period plus an empty result is a candidate source, but it is paid.

The CDSL series has continuous numbering of all DP communiques (not just CA ones). Whether every equity action is announced in "DETAILS OF CORPORATE ACTIONS" is unknown, so CDSL cannot prove an empty window on current evidence.

An empty API `[]` remains non-evidence (D66, ED-56).

## 6. Held unparsed events rechecked

| Symbol | Ex-date | Saved API subject (bytes in `raw/ca_<SYM>_2016_2025.json`) | Parser result | Status |
|---|---|---|---|---|
| CGPOWER | 2016-03-15 | " Scheme Of Arrangement" (record date 16-Mar-2016, ISIN INE067A01029) | `_subject_rows` -> None (no terms) | Fail-closed. Needs scheme terms (issuer/NCLT document or exchange circular). Pre-D59 window; affects only pre-2020-12-31 continuity |
| VBL | 2024-09-12 | "Face Value Split (Sub-Division) - From Rs 5/- Per Share To Rs 2/- Per Share" (record date 12-Sep-2024) | `_subject_rows` -> None | Fail-closed. Terms present but ratio 5:2 (factor 2.5) is not representable as the parser's integer (1, n) form. Engineering note: a fractional split is a parser limitation, not missing evidence. Not changed in this batch |

## 7. Restrictions observed

- `www.nseindia.com` and `www.bseindia.com` front ends refused or timed out to an automated reader. Any authorized acquisition must be host-side with a normal browser session; `nse/` stays offline.
- Cached PDFs in the session tool-results folder (CDSL index `0afee345...`, NSE/FAOP/53548, NSE Data_details_CM.pdf) are outside the repository and not custody. They are not cited as evidence anywhere except as "read for format".

## 8. Conclusions

Facts:
- NSE FAOP circulars are publicly retrievable, carry exact ratios and ex-dates, and agree with held API data for BAJAJFINSV 2022.
- CDSL publishes a continuous "DETAILS OF CORPORATE ACTIONS" series 2010-2026; contents unverified.
- No public NSDL per-ISIN artefact was found.
- BSE states a historical corporate-action product since 2006 (paid; not verified directly).

Assessment:
- **Event-level reconciliation is feasible** for F&O symbols using NSE FAOP + CDSL, subject to CDSL content verification.
- **Window completeness is not yet feasible** with any verified source. Without it, no window can be approved even when both sources agree on the events found, because D66 requires "insufficient coverage ... fails closed".

Recommendation: the smallest pilot that tests both open questions is in `P0_CA_PILOT_RECOMMENDATION.md`.

Unknowns (carried to the pilot): CDSL communique contents; FAOP numbering gap-freeness; F&O tenure for each symbol; BSE product terms and price.

## 9. Sources read (public pages; nothing held)

- NSE/FAOP/53548: https://archives.nseindia.com/content/circulars/FAOP53548.pdf
- CDSL communiques: https://www.cdslindia.com/eservices/Publications/Communique
- CDSL DP communique index: https://www.cdslindia.com/Publications/DP-COMMUNIQUES-INDEX.aspx
- CDSL RTA operating instructions (June 2024): https://www.cdslindia.com/Downloads/RTA/RTA-Operating-Instructions-as-on-JUNE-30-2024.pdf (search excerpt only)
- NSDL issuer CA documents: https://issuer.nsdl.com/ca.html (search excerpt only; direct fetch failed)
- BSE market data products: https://www.bseindia.com/market_data_products.html?flag=eod (search excerpt only; direct fetch 403)
