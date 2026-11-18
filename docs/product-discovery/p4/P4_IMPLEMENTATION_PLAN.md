# GTF P4  -  Implementation plan

**Date:** 2026-11-15  
**Phase:** GTF P4  -  Trade Planning (maps to Product Prompt 07 / TP-001…TP-012; not Product Prompt 04)  
**Governance chair:** `gtf-autonomous-project-lead`  
**Status after Batch 0:** Ready for independent and interface-dependent batches

## 1. Discovery verdict

Trade planning is **not greenfield**. P1 already certified journal caps, ED-3, partial fills, checklist fail-closed behaviour, and the desk path:

`POST /api/v1/plans` → draft → buffer combinations via `risk.plan_trade` → checklist → `POST .../approve` → `store.journal_add` → journal / portfolio.

P3 deep-links into `#/plans?scan&symbol&zone` and does not create plans itself.

P4 therefore **extends and hardens** the existing desk, models and UI. It does not invent a second eligibility engine, a second cap engine, or broker integration.

## 2. Reuse map

| Concern | Authority | Location |
|---|---|---|
| Eligibility / qualification | `nse/` scanner + qualification | Stored candidate snapshot only |
| Position sizing / R:R / stage | Rulebook via `nse.research.risk` | `plan_trade`, `RiskConfig` |
| Cap constants | Owner limits | `OWNER_MAX_OPEN_POSITIONS`, `OWNER_MONTHLY_TRADE_CAP` in `models.py` |
| Hard refuse on trigger | Research journal | `store._refuse_new_trigger`, `journal_execution` |
| ED-3 zone allowance | Research journal | `store._zone_allowance` / `_holds_zone` |
| Advisory portfolio checks | Pipeline | `pipeline.portfolio_checks` |
| Plan table | Platform SQLite | `trade_plan` (migration `003`) |
| Checklist codes | Rulebook companion | `models.CHECKLIST` |

## 3. Gap list addressed by P4

1. Richer plan lifecycle on the platform row (`AWAITING_OWNER`, `REJECTED`, `CANCELLED`) with audit history.
2. Optional `opportunity_id` provenance from P3 without mutating `candidate_status`.
3. Plan list / filter API and overview UI.
4. Wire `portfolio_checks` into plan preview (TP-008).
5. Explicit geometry / sizing explanation on preview (TP-002…TP-007).
6. Reject / cancel / submit-for-review workflow (TP-009).
7. Planned-versus-actual comparison after fills (TP-012).
8. Manual-execution preparation copy: plan is not an order; `authorises_order` always false.
9. Source-quality labelling on plans (FIXTURE / EXPLORATORY / UNKNOWN); never promote to CERTIFIED while P0=0.
10. Dedicated P4 documentation and certification.

## 4. Explicit non-goals

- No broker / Kite API.
- No automated order placement or paper-trading engine.
- No change to Rulebook, ED-3 semantics, or 10/10 caps.
- No second qualification field.
- No P0-certified historical planning claims.
- No P7 performance-based sizing or success-rate claims.
- No commits or pushes in this session.

## 5. Batch sequence

| Batch | Focus |
|---|---|
| 0 | Discovery (this document + dependency matrix) |
| 1 | Contract / migration / immutable status / audit tables |
| 2 | Create / submit / approve / reject / draft reopen |
| 3 | Geometry validation surface (reuse `risk.plan_trade`) |
| 4 | Transparent sizing fields on preview |
| 5 | Portfolio checks on preview (journal-backed) |
| 6 | Lifecycle + manual execution prep |
| 7 | Planned vs actual + journal linkage |
| 8 | Dashboard / UX |
| 9 | Tests / architecture / security |
| 10 | Independent review + certification |

## 6. P4-owned files

- `docs/product-discovery/p4/*`
- `platform/gtf_platform/planning/*` (new)
- `platform/gtf_platform/db.py` (migration `005` only)
- `platform/gtf_platform/routes.py` (plan routes only)
- `platform/gtf_platform/integration/desk.py` (plan helpers; preserve journal/cap paths)
- `platform/web/src/features/workflow/WorkflowPages.tsx` (Plans / Journal planned-vs-actual)
- `platform/web/src/navigation/query.ts` (optional `plan` / `state` allowlist keys)
- `platform/tests/test_trade_planning.py` (new)
- Updates to existing plan tests only when behaviour contracts change

Shared files touched only with minimal diffs: `desk.py`, `routes.py`, `db.py`, `WorkflowPages.tsx`.
