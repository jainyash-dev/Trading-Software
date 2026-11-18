# GTF P4 - Review register

**Date:** 2026-11-15  
**Independent reviewer:** independent-reviewer agent  
**Quant reviewer:** quant-researcher agent  
**Initial verdict:** accept-with-limitations  
**Post-remediation:** Critical/High unresolved = none

| Finding ID | Severity | File / function | Evidence | Consequence | Remediation | Retest | Disposition |
|---|---|---|---|---|---|---|---|
| P4-IR-01 | Medium | `planning/service._geometry_summary` | TESTED overlay could still report Geometry VALID | Misleading endorsement of tested zone | Force BLOCKED when overlay != FRESH or test_count > 0 | `test_geometry_blocks_tested_overlay` PASS | Fixed |
| P4-IR-02 | Medium | `WorkflowPages.PlansPage` | UI substituted default reject/cancel reasons | Audit trail lost owner intent | Require explicit non-empty reason in UI | Manual path + backend still requires reason | Fixed |
| P4-IR-03 | Medium | P4 tracker / plan docs | Tracker lagged shipped work; plan said `state` key | Wrong readiness / deep-link | Align docs; query key is `plan_state` | Docs updated | Fixed |
| P4-IR-04 | Medium | `cancel_plan` vs journal cancel | Platform APPROVED stays after journal CANCELLED | UI desync; not silent ED-3 release | 2026-11-17 (owner Decision 4): journal-authoritative mirror of journal CANCELLED/EXPIRED onto the plan on journal write, plan read, and startup (`desk.sync_plans_from_journal`, `planning.mirror_journal_terminal`); platform cancel of an approved plan with a live entry still 409 | 9 `test_ir04_*` PASS (`platform/tests/test_trade_planning.py`) | Remediated; see `docs/implementation/P4_IMPLEMENTATION_STATUS.md` |
| P4-IR-05 | Low | capacity fallback | Literal 10 when book unavailable | Display drift if constants change | Use `OWNER_*` constants | Code uses models constants | Fixed |
| P4-IR-06 | Low | `states.EXPIRED` | Edge exists; no producer | Dead state | Deferred until D42 expiry sync. 2026-11-17: plan mirrors an owner-recorded journal EXPIRED event only; no automatic producer (owner Decision 5) | `test_ir04_journal_expired_event_is_mirrored_not_auto_produced` | Automatic expiry deferred |
| P4-IR-07 | Low | `test_trade_planning.py` | Coverage holes | Missed regressions | Added geometry test; more refuse cases remain optional | 6 tests PASS | Partially addressed |
| P4-QR-01 | Info | RiskConfig trades_this_month | Not fed into combo MONTHLY check | Dual path (advisory portfolio_checks) | Intentional; hard refuse stays journal | Quant accept | Accepted |
| P4-SEC-01 | High (build) | planning package | nse.research / journal_event substring outside adapter | Architecture boundary fail | Move journal/cap reads to desk; clean docs | platform 58 PASS | Fixed |

## Quant summary

Quantity remains `floor(RPT/(entry-stop))` via `risk.plan_trade`. No invented RPT default.
Caps remain advisory on preview and hard at journal TRIGGERED / first ENTRY.
Closing does not restore monthly allowance. No performance claims.
