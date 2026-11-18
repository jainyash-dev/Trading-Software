# Priority-02 executive report

Date: 2026-11-10. Branch `main`. HEAD `9e302df1a81c2b13696d8fab61f05d377481be2e`. Nothing was staged or committed.

Priority-02 makes the existing desktop workflows usable against the research engine. It does not change eligibility, the Rulebook, or the data decisions assigned to Priority-01.

## Result

The isolated lab at `http://127.0.0.1:5173` (API `http://127.0.0.1:8765`, databases under `/tmp/gtf-p02`) completed the manual research path:

`fixture scan → stored scan and manifest → labelled candles → draft plan → journal approval → typed Kite submission → fill → portfolio → close → export → backup and restore-check`

`DATA_READY` stayed false. `authorises_order` stayed false. The owner's research journal was not opened. The lab journal is `/tmp/gtf-p02/research.sqlite`.

## What already existed

Stock Analysis, trade plans, the journal, portfolio, report export, backup, explanations, and the scheduler setting were already wired to `nse/`. Eligibility remains `pipeline.run → scanner.scan → scan_symbol → qualification.evaluate_symbol`. The platform does not score a candidate.

## What changed in this pass

- Stock Analysis clears the previous symbol before a new request, and an empty candle series shows an empty state instead of a leftover chart.
- A fixture scan can be planned only when the page was opened with `fixtures=1`. The client cannot mark a candidate eligible.
- A browser timestamp with a timezone offset is converted to naive IST before it reaches the research journal. Scan times in this system are naive exchange-local IST, and the journal refuses to compare the two forms.
- Portfolio reads `portfolio_at` on that same clock. Valuation, sector, and drawdown stay `UNAVAILABLE`.
- The journal screen can record a manual close. Closing freed the open slot and left the monthly count at 1.
- Settings can copy both SQLite files and restore them under `restore-checks/`. Live files are not replaced.

## Tests

- `PYTHONPATH=platform python3 -m pytest platform/tests -q -p no:cacheprovider`: 37 passed.
- `npx tsc -p tsconfig.json --noEmit`, `npx vitest run` (40 passed), and `npx vite build`: passed. The build warns that the JavaScript bundle is over 500 kB.
- `.venv/bin/ruff check` on `platform/gtf_platform/integration/desk.py` and `platform/tests/test_product_flow.py`: passed.
- Expiry tests `test_fill_after_ten_verified_sessions_is_refused_and_expired_still_records` and `test_two_connections_cannot_both_commit_an_eleventh_trigger`: passed. `nse/research/store.py` was not edited.
- `python3 -m nse.validation.architecture`: FAIL. `nse/research/backtest.py` imports `nse.research.run_manifest`. That import was already in the working tree. This pass did not edit `backtest.py`.

## Release gates

| Gate | Assessment |
|---|---|
| R1 Data ready | Open. Overview reported `data_ready` false, with universe, corporate-action, and identity warnings. |
| R2 Research ready | Open. Not reassessed. No research rule was changed. |
| R3 Application ready | Improved, not closed. The lab path works. Fees have no journal column. A cold API restart drops the in-memory session. The architecture check still fails on the existing backtest import. |
| R4 Strategy validated | Open. No performance claim was produced. |
| R5 Operationally ready | Improved, not closed. Backup and restore-check work on an isolated pair of databases. The owner's live files were not part of the drill. The scheduler does not download. |

## Left running, then stopped

The lab API and the Vite server used for the journeys were stopped after the evidence was recorded. `/tmp/gtf-p02` was left in place. It is not the owner's journal.
