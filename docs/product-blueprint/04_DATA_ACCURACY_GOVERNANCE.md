# 04  -  Data Accuracy Governance

## 1. Purpose

Define a verifiable data-to-result chain for GTF SaaS and preserve D66. No profitability or predictive guarantees.

## 2. Canonical chain

```
Source
  → Ingestion (offline / authorised adapter into inbox)
  → Raw Archive (immutable object + SHA-256)
  → Normalization (parsers; no silent repair of conflicts)
  → Validation (findings; quarantine on failure)
  → Certification (P0 gates; D66 for CA completeness windows)
  → Canonical Data (versioned dataset identity)
  → Calculation (candles, zones, MTF overlay)
  → Research Rules (G0-G8 qualification)
  → Results (scan envelopes, plans inputs, backtest outputs)
```

Every customer-visible research result must be able to cite dataset identity (hash / version), code revision, methodology version, and as-of / known_at.

## 3. Shared vs private

| Class | Examples | Accuracy owner |
|---|---|---|
| Shared market | EOD, calendar, membership, CA events, certification windows | Platform data engineering |
| Private customer | Plans, drawings, journal, settings, attachments | Customer + platform integrity controls |
| Derived shared | Zone caches, shared scan artefacts (if authorised) | Must recompute from canonical inputs |

## 4. D66 (binding)

Corporate-action completeness for a symbol-date window requires:

- Two independent official sources
- Verified SHA-256 for both
- Provenance and independence established
- Event-by-event reconciliation (missing / additional / conflicting / differently represented)
- Owner approval naming symbol, window, both hashes, reconciliation record

Fail closed on unresolved discrepancy. A single source never establishes completeness. This blueprint does not change D66.

## 5. Data state machine

| State | May enter research? | May claim CERTIFIED? | Notes |
|---|---|---|---|
| MISSING | No for dependents | No | |
| STALE | Yes with STALE label | No | EOD valuation policy exists in P5 docs |
| PROVISIONAL | Exploratory / labelled | No | D59 / D62 weaker tiers |
| FIXTURE | Dev/test only | No | Never default production customer mode |
| INCOMPLETE | Labelled partial | No | |
| FAILED | No | No | Quarantine |
| CERTIFIED | Yes | Yes | All applicable gates including D66 windows |

## 6. Verification domains

| Domain | Verification approach |
|---|---|
| OHLCV / candles | Parser tests; OHLC consistency; calendar alignment; replay against reference when available |
| Indicators | Deterministic unit tests; no lookahead |
| Zones | Zone engine tests; adversarial cases; never UI-side recompute |
| Scanner qualification | Gate tests; MTF eligibility path tests; prefix invariance |
| Risk calculations | Risk stage bands; sizing floor rules; refuse invalid geometry |
| Portfolio accounting | Journal authority; concurrency races for caps; planned vs actual |
| Backtest / performance | Manifest required; costs from configured policy; descriptive vs validated labels |

TradingView parity remains pending (Q12). Do not claim parity without exports.

## 7. Customer communication rules

- Never display invented zeros for missing charges or missing index levels.
- Never rename `ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING` to Buy/Approved.
- Fixture banners required whenever fixture datasets are used.
- Backtest metrics labelled with execution model and dataset identity.

## 8. Retention and correction

- Raw archives are immutable; corrections = new object + new manifest row.
- Customer export/delete follows commercial policy (OD-BP-006).
- Audit logs retained per OD-BP-011.

## 9. Acceptance

- Chain implemented with trace IDs in APIs.
- Negative tests for fixture→certified promotion.
- D66 tooling remains fail-closed.
