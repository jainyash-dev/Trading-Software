# Next phase recommendations

Do these before adding anything from Phase D.

1. The owner completes T-001 and T-002, or explicitly keeps both blocked.
2. Run one fixture scan and one real, limitation-labelled scan in the browser: Overview, a symbol chart, a refused non-actionable plan, and a journal fill in an isolated database.
3. Add one platform test that approves a synthetic candidate through `POST /api/v1/plans/{id}/approve` and checks the research journal count.
4. Re-run any stored envelope that predates the corporate-action coverage check before showing it as current.
5. Leave WIT, paper trading, the language-model assistant, live quotes, and the parse cache unbuilt until their own decisions exist.

Do not flip `data_ready` to true to make the overview look finished.
