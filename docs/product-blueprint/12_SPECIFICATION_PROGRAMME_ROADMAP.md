# 12 - Specification Programme Roadmap

## 1. Objective

Move from Assignment 00 blueprint to implementable module specifications, then to separately authorised build waves.

**Authorisation (2026-11-18):**

| Item | Status |
|---|---|
| OD-BP-001 | USER_APPROVED |
| W0 foundation specification (MS-016, MS-017, MS-018 + foundation annexes) | AUTHORIZED FOR SPECIFICATION ONLY |
| Commercial cloud implementation | NOT_AUTHORIZED |
| Cloud spend / provider selection / production deploy | NOT_AUTHORIZED |

## 2. Stages

| Stage | Deliverable | Exit criteria | Status |
|---|---|---|---|
| S0 | Blueprint package | Owner review started | Done |
| S1 | Resolve OD-BP-001 | Decision in DECISION_LOG | **Done** (2026-11-18) |
| S1b | Resolve remaining critical commercial ODs | OD-BP-004/005/008/010/014 as needed for W0 depth | Open |
| S2 | W0 foundation specification package (`docs/product-blueprint/w0/`) | Specs reviewable; open decisions listed; no build auth | **Drafted 2026-11-18** (spec only; Gate H open) |
| S3 | Deepen MS-001-004 for cloud data plane + D66 ops | Ingest/cert workers specified | Pending |
| S4 | Adapt MS-005-007/010-012 from platform OpenAPI to tenant APIs | Contract diffs reviewed | Pending |
| S5 | MS-013/015 heavy jobs | Quotas + isolation tests specified | Pending |
| S6 | MS-008/009/014 after source/provider ODs | Or explicitly defer | Pending |
| S7 | Implementation waves W0-W6 | Separate owner **build** authorisation | NOT_AUTHORIZED |

## 3. Parallel tracks

| Track | Work | Constraint |
|---|---|---|
| T-SaaS-Spec | W0 and later module specifications | Spec only until build authorisation |
| T-Local | Continue local product hardening | Do not break loopback research baseline |
| T-P0 | D66 source path / membership | No certification theatre |
| T-Quant | Backtest integrity | No profitability claims |

## 4. Specification quality bar (each MS)

Must include: API list with authz; tables with tenant_id; workers; failure modes; acceptance tests; open questions. Unresolved rules stay questions.

## 5. Suggested calendar (planning only)

Not commitments: deepen W0 specs next; build only after written implementation authorisation and required commercial ODs.
