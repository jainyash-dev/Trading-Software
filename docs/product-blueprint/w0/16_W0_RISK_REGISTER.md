# 16 - W0 Risk Register

| ID | Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|---|
| W0-R01 | Spec mistaken for build authorisation | High | Medium | Explicit NOT_AUTHORIZED banners; gates H |
| W0-R02 | Cross-tenant leakage once built | High | Medium | RLS + tests + threat model |
| W0-R03 | Data licence blocks hosted market data | High | High | OD-BP-014 before spend |
| W0-R04 | Dual production editions (local vs SaaS drift) | Medium | Medium | Single codebase flags; local = baseline only |
| W0-R05 | Engine duplication during migration | High | Medium | research_bridge only; adversarial tests |
| W0-R06 | Dual-write inconsistency | High | Medium | Default off; reconciliation required |
| W0-R07 | Auth provider lock-in / residency | Medium | Medium | Evaluate alternatives in W0-01 |
| W0-R08 | Cost overrun from backtests | Medium | High | Quotas + separate queue |
| W0-R09 | Weak RPO/RTO without drills | Medium | Medium | W0-10 monthly restore |
| W0-R10 | P0/D66 confusion with SaaS launch | High | Medium | CERTIFIED claims remain blocked |
| W0-R11 | Premature PSP integration | Medium | Medium | OD-BP-005 gate |
| W0-R12 | Log PII leakage | Medium | Medium | Redaction tests |
| W0-R13 | Regulatory advisory boundary | High | Medium | OD-BP-015 counsel |
| W0-R14 | Migration corrupts journal caps | High | Low | Reconcile ledger hashes; keep SQLite freeze |
