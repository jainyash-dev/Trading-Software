# P0 pending board

**Updated 2026-11-11. Branch `main`.** Research certification is not achieved. Certified symbol-dates: 0. Excluded member-dates: 123,778.

| ID | Status | What is unresolved | Evidence still required | Owner action | Blocks research certification? |
|---|---|---|---|---|---|
| OD-MEM-1 | Open | All 271 `decision` cells are blank. 35 rows have a scoped approval. 236 have no reviewer | The owner writes `decision` `ACCEPTED` or `REJECTED` per row, or per source group in `P0_MEMBERSHIP_OWNER_QUEUE.csv` | Period decisions only. Do not treat D60 or D61 as period approval | Yes. Every member-date stays excluded |
| D60 | Recorded | 25 count calculations are `count_approval` `APPROVED` | None for the arithmetic | None for the arithmetic. The periods stay open | The arithmetic no longer blocks the count gate. Periods still do |
| D61 | Recorded | Ten E03 mappings are `mapping_approval` `APPROVED` | None for those ten directions | None for the mapping. BANKBARODA and CHOLAFIN periods stay open | Does not certify those periods |
| OD-MEM-2 / OD-MEM-3 | Open | Five dummy seats are not tradable. Four packet rows are `INFERENCE`. DUMMYREL is not printed on the Nifty 100 release | A rule for a non-tradable seat, if one is wanted | Leave them non-tradable. Do not invent ISINs | Those seats, and any full-index claim that includes them |
| OD-ID-1 | Open | BAJFINANCE `INE296A01016` to `INE296A01024` | One notice with one effective session. MSEI/LIST/4496/2016 states 8 September 2016 and 9 September 2016 | Do not join until one date is chosen or a single-date notice exists | BAJFINANCE, and full-index certification |
| OD-ID-2 | Open | GRASIM `INE047A01013` to `INE047A01021` | One notice with one effective session. MSEI/LIST/4581/2016 states 6 October 2016 and 7 October 2016 | Do not join | GRASIM, and full-index certification. Other symbols keep their own results |
| OD-ID-3 | Recorded for the new ISIN | NSE/CML/43833 names `INE528G01035` from 2020-03-16. The circular does not print the old ISIN | None for that new-ISIN date | None for the identity row. The membership period is still undecided | YESBANK member-dates stay excluded by the blank membership decision |
| B11-P | Open | No constituent baseline before 2020-12-31 | An official dated constituent list with symbols or ISINs | D59 keeps the window at 2020-12-31. `IndexInclExcl.xls` is a name-only change log through 2020-07-31 | Dates before 2020-12-31 |
| B7 / R-10 | Open | 57 saved bodies are `[]`, including SRTRANSFIN. Ten price subjects are unparsed | A source that proves coverage, and ratios for the unparsed subjects | Do not treat `[]` as no events. Do not invent ratios | Unknown coverage and unparsed events fail closed |
| OD-PX-1 | Open, rechecked 2026-11-11 | ADANIPOWER 2021-06-11..2021-09-20 has 67 BE sessions, ISIN `INE814H01011`, and the previous-close chain does not break. CGPOWER 2021-09-15..2022-01-04 has 75 BE sessions, ISIN `INE067A01029`, and the previous-close chain does not break. The endpoint sessions are EQ. BE/BZ policy is not approved | None new. The series filter is EQ | Leave EQ-only. Do not backfill BE into EQ | Those EQ gaps stay gaps |
| OD-PX-2 | Open | CGPOWER 2016-03-15 scheme ratio is unparsed. VBL 5-to-2 is not an integer ratio the parser accepts | Official terms that the parser can represent without rounding | Do not invent a factor | Continuity across those ex-dates |
| TV-1 | Open | TradingView parity is `PENDING_EXTERNAL_EVIDENCE` | Chart exports for INFY D/W/M/Q/HY/Y, SMA-50, zones, freshness, and TATASTEEL adjustment on and off | Supply the exports. Do not close T-005 | External parity only |
| OD-CAL-1 | Disclosed | 2024-01-20 hours are inferred from NSE/CMTR/41180 | None unless the inferred 09:15–15:30 should be replaced | Leave the inference visible | No |

No blocker is closed by a synthetic test. Passing the test suite is not strategy validation.
