# Test and verification report

| Command | Result | Limitation |
|---|---|---|
| `PYTHONPATH=platform python3 -m pytest platform/tests -q -p no:cacheprovider` | 24 passed after the OpenAPI file was regenerated | Fixture prices. Not a Nifty 100 scan |
| `npx vitest run` in `platform/web` | 40 passed | `fetch` is stubbed. Not a browser session |
| `npx tsc -p tsconfig.json --noEmit` in `platform/web` | Passed | Typecheck only |
| `PYTHONPATH=.:tests python3 -m unittest` journal race, expiry, walk-forward command, sensitivity command | 4 tests, OK | Synthetic candles |
| `.venv/bin/ruff check` on the touched Python files | Passed after the export-route fix | F and E9 only |
| Browser click-through | Not run | The live app was not started in this session |

No test assertion was removed to hide a failure. The overview test that expected an omitted status to render as 0 was changed to expect unavailable, which is the T-007 rule. The shell test that expected Stock Analysis to be unavailable was changed because that screen is now a route.
