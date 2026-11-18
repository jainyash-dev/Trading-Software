# GTF P4  -  Dependency matrix

**Date:** 2026-11-15  
**Categories:** `INDEPENDENT` | `INTERFACE_DEPENDENT` | `P0_BLOCKED` | `P7_BLOCKED`

| Req ID | Description | Category | Upstream | Impl | Validation | Release restriction |
|---|---|---|---|---|---|---|
| P4-R01 | Extend `trade_plan` + audit/notes tables | INDEPENDENT | Platform SQLite `003`/`004` | COMPLETE | Migration + unit | Never mutate `candidate_status` |
| P4-R02 | Plan lifecycle DRAFT→AWAITING_OWNER→APPROVED/REJECTED/CANCELLED | INDEPENDENT | DOMAIN_MODEL | COMPLETE | Transition tests | Workflow ≠ eligibility |
| P4-R03 | Plan list / filter / overview API | INDEPENDENT | `trade_plan` | COMPLETE | API tests | Status labels honest |
| P4-R04 | Rationale / notes / audit history | INDEPENDENT | Plan id | COMPLETE | API tests | Notes ≠ methodology |
| P4-R05 | Reject / cancel with reason | INDEPENDENT | Lifecycle | COMPLETE | API tests | Cancel before journal only on platform |
| P4-R06 | Plans UI overview + filters | INDEPENDENT | Plan APIs | COMPLETE | Vitest + build | No success chrome for FIXTURE |
| P4-R07 | Manual-execution prep disclosure | INDEPENDENT | UX copy | COMPLETE | UI assertion | `authorises_order` false |
| P4-R08 | Create draft from stored candidate | INTERFACE_DEPENDENT | `scan_result` envelope | COMPLETE | Product flow | Refuse BLOCKED/REJECTED/DATA_INSUFFICIENT |
| P4-R09 | Buffer combinations + geometry | INTERFACE_DEPENDENT | `risk.plan_trade`, G7 target | COMPLETE | Risk + desk tests | Never invent targets |
| P4-R10 | Checklist + owner approval | INTERFACE_DEPENDENT | `models.CHECKLIST`, `journal_add` | COMPLETE | Checklist refuse tests | Approval ≠ order |
| P4-R11 | Portfolio checks on preview | INTERFACE_DEPENDENT | `portfolio_at` + `portfolio_checks` | COMPLETE | Cap display tests | Advisory until TRIGGERED |
| P4-R12 | Position sizing transparency | INTERFACE_DEPENDENT | Settings capital/`rpt_pct`/`risk_stage` | COMPLETE | Risk tests | No invented RPT % |
| P4-R13 | ED-3 / 10/10 hard enforcement | INTERFACE_DEPENDENT | `nse.research.store` | EXISTS (P1) | Store + product flow | Do not duplicate engine |
| P4-R14 | Opportunity provenance link | INTERFACE_DEPENDENT | P3 `opportunity_id` | COMPLETE | Optional field | Does not change status |
| P4-R15 | Planned vs actual after fills | INTERFACE_DEPENDENT | Journal executions | COMPLETE | Fill comparison tests | No fabricated fills |
| P4-R16 | Source quality on plan | INTERFACE_DEPENDENT | Scan fixture / dataset | COMPLETE | Quality tests | Never promote to CERTIFIED |
| P4-R17 | Certified historical plan-generation claims | P0_BLOCKED | P0 certified member-dates | DEFERRED |  -  | Refuse CERTIFIED while P0=0 |
| P4-R18 | Certified opportunity statistics on plans | P0_BLOCKED | P0 certification | DEFERRED |  -  | Show exploratory/unavailable |
| P4-R19 | Performance-optimised sizing / target picks | P7_BLOCKED | Quantitative validation | DEFERRED |  -  | Absent |
| P4-R20 | Success-rate / expectancy claims | P7_BLOCKED | P7 acceptance | DEFERRED |  -  | Absent |
| P4-R21 | Broker / automated execution | Disallowed |  -  | N/A | Architecture | `authorises_order` always false |

## Notes

- Hard monthly and open-position refusals remain at journal TRIGGERED / first ENTRY print (P1). Plan preview checks are advisory and must use the same constants.
- Cancelling a platform DRAFT/AWAITING_OWNER plan that never reached `journal_add` does not touch zone allowance (no journal row yet). Post-approval cancellation is a journal `CANCELLED` event under ED-3 rules.
- Plan `candidate_status` is a frozen copy of the stored scanner status at draft creation.
