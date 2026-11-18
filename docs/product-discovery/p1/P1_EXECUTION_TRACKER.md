# GTF P1 execution tracker

GTF P1 is application hardening. It is not Product Prompt 01 and it does not certify P0.
Status below is the implementation state after independent audit and gap closure on 2026-11-13.

| Workstream | Owner | Status | Files | Dependencies | Tests | Review | Residual risk |
|---|---|---|---|---|---|---|---|
| P1-A D42 caps | Project lead | COMPLETE | `nse/research/store.py` | ED-46 / ED-54 | `P1JournalIntegrity`, tenth-fill race, open-slot race, IST month | Independent reviewer | Crash after commit is a committed fill |
| P1-B ED-3 zone | Project lead | COMPLETE | `nse/research/store.py` | No unique zone index | `test_ed3_*`, zone race, stop/close | Independent reviewer | Pre-v2 cancelled rows still hold the zone (documented) |
| P1-C Fail closed | Project lead | COMPLETE | `platform/web/src/design/status.ts` | Qualification unchanged | `status.test.ts`; refused-plan API | Independent reviewer | Unknown codes stay unknown, never PASS |
| P1-D Closed trade | Project lead | COMPLETE | `store.portfolio_at`, `WorkflowPages.tsx` | P1-A | portfolio assertions in store + product-flow | Independent reviewer | Closed zone remains visible as held, not open |
| P1-E Navigation | Project lead | COMPLETE | `navigation/query.ts`, `WorkflowPages.tsx` | Hash router | `plans-navigation.test.tsx`, `routes.test.ts` | Independent reviewer | Unknown routes open Overview |
| P1-F Restart | Project lead | COMPLETE | `security.SessionStore`, journal idempotency, WorkflowPages clear | In-memory session (D57) | restart + execution retry; UI clears on disconnect | Independent reviewer | New request_key + new timestamp can still append a different event |
| P1-G Charges | Project lead | COMPLETE_WITH_LIMITATIONS | `nse/research/charges.py`, journal charge tables | Owner schedule | Itemised / absent charge tests | Independent reviewer | Official rates are not in the repository |
| P1-H Partial fills | Project lead | COMPLETE | migration 4 `journal_executions` | RB 2140 one order | `test_partial_prints_*`, API execution retry | Independent reviewer | Bare `TRIGGERED` remains a full planned fill |
| P1-I Backup | Project lead | COMPLETE_WITH_LIMITATIONS | `desk.backup_to`, `desk.restore_copy` | SQLite backup API | backup + interrupted restore product-flow tests | Independent reviewer | No schedule. Raw bhavcopies excluded. Live swap is owner-only |

P0 files, membership decisions and certification outputs were not part of this batch.
No commit was made (awaiting explicit owner authorisation).
