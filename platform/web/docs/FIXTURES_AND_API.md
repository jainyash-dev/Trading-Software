# Fixtures and the API client

Fixtures are deterministic, use non-market labels such as `FIXTURE_NOT_MARKET_DATA`, and set `meta.fixture: true`. The client never switches a failed API call over to fixture JSON. The banner is shown when fixture mode was requested or the API marks the payload as fixture.

The browser calls `/api` with `credentials: "include"` and `X-GTF-Request: 1`. It does not put a session value in `localStorage`, the URL, or source. The cookie is HttpOnly.

Implemented routes include health, session, bootstrap, logout, overview, instruments, universe, calendar, datasets, candles, scans, jobs, symbol bundle/explain, watchlists (including DELETE), opportunities (list/ingest/transition/notes/history), scan-configs, drawings (GET/POST/PATCH/DELETE), settings, plans, journal, portfolio, reports export, backup, and restore-check. They do not place orders. `orders_placed` / `authorises_order` stay false.

Opportunity rows are workflow metadata over stored scan candidates. Ingest never re-qualifies zones. Fixture opportunities are labelled and are not market opportunities. Organizational priority is non-authoritative and does not predict returns.

Candle responses carry `data_quality` with `certified: false`. Successful chart retrieval is not P0 certification.

`GET /api/v1/openapi.json` is not a route. The checked-in document is `platform/gtf_platform/openapi.json`, generated from the app and compared by `platform/tests/test_api_security.py`.

Start the API with `python3 platform/run_api.py`. Tests: `python3 -m unittest discover -s platform/tests -q` with `platform` on `PYTHONPATH`. Web tests: `npm test` in `platform/web`.
