# CDSL coverage test: 15 known in-window splits (D68 Decision 2)

**Date:** 2026-11-15. **Authority:** D68: a free coverage test, "not to be treated as proof of complete corporate-action coverage". Row-level results: `P0_CDSL_SPLIT_COVERAGE_TEST.csv`. Files: `nse/data/corporate_actions/evidence/cdsl_coverage_test/` (15 matching notices + the communique index), with ledger rows in `P0_CA_SOURCE_LEDGER.csv`.

## Method

1. Downloaded the CDSL DP communique index (SHA-256 `cb924e6d...`, 2026-11-15T15:37:27Z). It lists 810 communiques titled "DETAILS OF CORPORATE ACTION(S)".
2. For each of the 15 splits in `P0_CA_EVENT_REGISTER_V3.csv`, took the old and new ISIN from `instrument_records.csv`. Then selected every "Details of Corporate Action(s)" communique dated from 14 days before the NSE record date to 1 day after it.
3. Downloaded those communiques (63 notices in total) and searched each one's text for the old and new ISIN.
4. Read the matching table row and compared it with NSE's record: type, record date, ratio, old ISIN, new ISIN.

## Results

| Measure | Result |
|---|---|
| Splits with a CDSL notice found | **15 of 15** |
| Agreement on type (SUB-DIVISION), record date, ratio, old and new ISIN | **15 of 15** |
| Lead time | Notices dated 0-4 days before the record date; the CDSL "effective date" is record date + 1 |
| VBL 2024-09-12 | CDSL prints "RATIO [OLD ISIN : NEW ISIN] 2 : 5", the same old:new representation as ED-57 |
| Not found | none |

## Findings and limitations (owner instruction: record them)

- **Event types covered:** sub-divisions with an ISIN change (and, in other notices, consolidations). The series never covers bonuses (pilot Q1), and it covers no rights or demergers in any notice read.
- **ISIN-change requirement:** the series appears to list events that create a new ISIN. A split that kept its ISIN would presumably not appear (none is known in the window).
- **Historical availability:** the index lists the series from 2010; the earliest notice used here is 2021-10-27.
- **Direction of the test:** it checked that CDSL contains the 15 events NSE recorded. It did **not** test whether CDSL lists in-window ISIN-changing events for member symbols that NSE's data lacks. That would mean reading all relevant notices (outside this authorization).
- **Document quirks:** three PDFs contain stale embedded objects from older communiques (2017, 2022, 2024 headers); each match was confirmed on the correct table. MAZDOCK's index ID (DP2024-775) differs from its document number (CAIPO/2024/774). SHRIRAMFIN's old ISIN came from the notice (INE721A01013) because the instrument records hold it under the SRTRANSFIN rename.
- **Independence:** CDSL is a different institution. Its record dates agree exactly with NSE's, which is consistent with both deriving from the issuer's announced record date. Upstream independence of the record date is still not established.

## What this does and does not establish

- **Does:** for ISIN-changing splits, CDSL is an official, retrievable, event-level second record that agreed with NSE on 15 of 15 known events, including the fractional VBL ratio.
- **Does not:** prove window completeness. A D66 window needs every event class in the window covered and the absence of events proven. CDSL cannot show the absence of bonuses, rights or demergers. **No D66 window qualifies as a result of this test.** No reconciliation record or approval marker was created.
