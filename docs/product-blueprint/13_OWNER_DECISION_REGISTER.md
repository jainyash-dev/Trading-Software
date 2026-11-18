# 13 - Owner Decision Register (Blueprint)

Owner decisions for the SaaS blueprint programme. Level A requires `USER_APPROVED` (or binding `USER_STATED` within scope) in `nse/docs/DECISION_LOG.md`.

## Resolved

| ID | Topic | Status | Effect |
|---|---|---|---|
| OD-BP-001 | Commercial production packaging | `USER_APPROVED` 2026-11-18 | Cloud multi-tenant browser SaaS is the commercial production architecture; supersedes D57 for production. See `ADR_OD-BP-001.md`. Implementation / spend / deploy **not** authorised. W0 specs authorised for specification only. |
| OD-BP-002 | Local mode retention | `RESOLVED_BY_OD-BP-001` | Local-first loopback may be retained as development, testing, migration or engineering baseline; not commercial production. |

## Open (still require owner decisions)

| ID | Topic | Question | Blocks | Notes |
|---|---|---|---|---|
| OD-BP-003 | Seats | Individual-only tenants at launch, or multi-seat orgs? | MS-016 schema | Assignment / OD-BP-001 say individual traders initially; confirm seats |
| OD-BP-004 | Auth/MFA | Auth method (password/OIDC) and MFA requirement at launch? | MS-016 | |
| OD-BP-005 | Billing PSP + plans | Which PSP and which plan entitlements? | MS-017 | No purchase from blueprint |
| OD-BP-006 | Privacy deletion | DPDP policies, retention, deletion cooling-off, legal hold? | Export/delete | Legal review |
| OD-BP-007 | SLO/RPO/RTO | Availability and recovery targets? | MS-018 | |
| OD-BP-008 | DB isolation | Shared DB+RLS vs schema-per-tenant vs DB-per-tenant? | MS-016/018 | Blueprint recommends RLS |
| OD-BP-009 | Shared scans | Compute shared post-close scan once for all tenants vs per-tenant? | Cost/isolation | |
| OD-BP-010 | Region | Cloud region / data residency preference? | Hosting | Propose India |
| OD-BP-011 | Audit retention | How long to retain audit logs? | Compliance | |
| OD-BP-012 | Incident comms | Customer notification thresholds? | Ops | |
| OD-BP-013 | Tax/GST | Invoicing and tax treatment? | Billing | Counsel |
| OD-BP-014 | Data redistribution | Licence to host/redisplay NSE/index/CA data in SaaS? | MS-001 commercial | Critical external blocker |
| OD-BP-015 | Legal launch review | Authorise counsel for advisory vs research positioning? | Go-to-market | |
| OD-BP-016 | Cap policy | Keep D42 10/10 caps for all SaaS customers or make configurable? | MS-011 | D42 is USER_STATED |
| OD-BP-017 | AI provider | Enable paid LLM assistant provider? | MS-014 | Prior OQ-2 |
| OD-BP-018 | Live quotes | Allow paid quote provider later? | MS-005/015 | Prior OQ-1 |
| Q12 | TradingView | Provide zone reference exports? | Parity claims | Pending in D68 |
| Q13 | R-5 | Resolve precedence wording conflict? | Governance docs | Pending |

## Already binding (do not reopen casually)

OD-BP-001 (commercial production SaaS), D57 (historical; superseded for commercial production only), D66, D50, D53, D58, D59, D62-D68 items as recorded, no-broker rule, WIT blocked, Rulebook precedence for methodology.

## Authorisation summary (2026-11-18)

| Item | Status |
|---|---|
| OD-BP-001 decision | USER_APPROVED |
| Commercial cloud implementation | NOT_AUTHORIZED |
| Cloud spend / provider commitments | NOT_AUTHORIZED |
| DB / API / schema changes | NOT_AUTHORIZED |
| W0 foundation specification programme | AUTHORIZED FOR SPECIFICATION ONLY |
