# Remaining defects

Originally observed during Priority 02 / early platform hardening. Superseded items are closed by GTF P1 evidence in `docs/product-discovery/p1/`.

## Closed by GTF P1 (do not reopen without a new failure)

1. **Architecture check.** `python3 -m nse.validation.architecture` passes (54 modules, 0 violations) as of 2026-11-13.
2. **Symbol status badge.** `NO_FRESH_EXECUTION_ZONE` is labelled "No fresh execution zone" with a non-ok tone (`status.ts` / `status.test.ts`). Unknown codes stay unknown; they are never mapped to PASS.
3. **Fee column.** Itemised charges exist via `journal_charges` and `nse/research/charges.py`. Absent charges stay `ABSENT`. No built-in brokerage tariff is invented.
4. **Partial fills.** `journal_executions` stores each print. Position quantity is the sum. Unfilled quantity is not a monthly fill.
5. **In-memory session.** Restart still drops the cookie by design (D57). Journal survives. UI clears portfolio/journal when the session is not authenticated. Recovery is a new bootstrap, not a persisted token.
6. **Portfolio zone after close.** Closed zones show `counts_as_open === false` and "Not an open position. Zone allowance stays held." Open count is separate from monthly allowance.
7. **Plan page query parameters.** Hash query changes refresh plan fields (`plans-navigation.test.tsx`).
8. **Backup / restore.** `backup_to` + `restore_copy` with integrity and row-count checks; interrupted restore leaves live files untouched.

## Still open (not P1 blockers)

1. **Frontend bundle size.** Production build remains large; Vite chunk warning only. Deferred to P10 visual/perf work unless it becomes a reliability gate.
2. **DATA_READY.** Still false while P0 certification is open. P1 must not claim certified historical performance.
3. **NO_BACKUP_SCHEDULE.** No automated backup cron. Documented limitation.
4. **Official charge rates.** Not stored in the repository; owner supplies a dated schedule.

## Out of scope

Live position monitoring, paper trading, an LLM assistant, WIT scanning, broker login, live quotes, and automated order placement. `authorises_order` stays false.
