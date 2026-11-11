# Corporate-action responses are not treated as complete

Dated 2026-11-11. Raw files under `nse/data/corporate_actions/raw/` were not overwritten.

`corporate_actions.load_coverage` counts a window only when the saved file matches its SHA-256 and the body is not an empty JSON list. A body of `[]` stays on disk and does not make a date covered. The API has no completeness guarantee, so a non-empty response is also not proof that every event was returned.

Held files, counted from the directory:

- 57 saved bodies are exactly `[]`, including `ca_SRTRANSFIN_2016_2025.json`.
- None of those 57 files is a row in `coverage.csv`. `SRTRANSFIN` is not a coverage symbol.
- A coverage row that pointed at a hash-matched `[]` would still not cover a date. `tests/test_research_corporate_actions.py` checks that.

`conversion_report.json` has 10 unparsed price subjects. No ratio was invented for them:

| Symbol | Ex-date | Subject |
|---|---|---|
| ADANIENT | 2018-04-05 | Scheme Of Arrangement |
| ADANIENT | 2018-09-06 | Scheme Of Arrangement |
| BRITANNIA | 2019-08-22 | Scheme Of Arangement - bonus debenture |
| BRITANNIA | 2021-05-25 | Scheme Of Arangement - bonus debenture |
| CGPOWER | 2016-03-15 | Scheme Of Arrangement |
| GRASIM | 2017-07-19 | Scheme Of Arrangement |
| ICICIBANK | 2017-06-20 | AGM / dividend / bonus text the parser does not accept as a ratio |
| TATASTEEL | 2018-01-31 | Rights text the parser does not accept as a ratio |
| TVSMOTOR | 2025-08-25 | Scheme Of Arrangement - bonus NCRPS |
| VBL | 2024-09-12 | Face-value split from Rs 5 to Rs 2; 5/2 is not an integer ratio the parser accepts |

Each unparsed subject blocks price-scale use across that ex-date. It does not adjust OHLC. CGPOWER's 2016-03-15 row is the event previously discussed as CROMPGREAV. No factor was applied.
