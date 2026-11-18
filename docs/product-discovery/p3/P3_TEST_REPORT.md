# GTF P3 - Test report

## Commands and results

| Suite | Command | Result |
|---|---|---|
| Opportunity tests | `PYTHONPATH=platform python3 -m unittest discover -s platform/tests -p 'test_opportunity.py' -q` | 8 passed |
| Platform tests | `PYTHONPATH=platform python3 -m unittest discover -s platform/tests -q` | 52 passed |
| Web vitest | `npx vitest run --pool=forks --maxWorkers=2` (in `platform/web`) | 48 passed |
| Web build | `npm run build` (in `platform/web`) | PASS (`tsc` + vite) |
| Architecture group | `python3 -m nse.validation.run_all --no-data --group architecture` | PASS (28 ran) |
| Repository group | `python3 -m nse.validation.run_all --no-data --group repository` | PASS (15 ran) |
| Em-dash check | `pytest tests/test_repo.py::Repo::test_no_em_dashes_and_no_personal_email` | PASS |

## Skipped

| Check | Why |
|---|---|
| Full `run_all` with local_data | Not required for P3 platform scope; P0 data workstream independent |
| Automated visual screenshot matrix | Not implemented (same limitation as P2) |
| Live production scanner over certified universe | P0_BLOCKED (0 certified symbol-dates) |

## Notes

Software tests are not external validation and are not evidence of trading profitability.
