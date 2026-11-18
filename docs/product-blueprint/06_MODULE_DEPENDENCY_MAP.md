# 06  -  Module Dependency Map

## 1. Hard dependencies (build / runtime)

```
MS-018 Infra ─────────────────────────────────────────────┐
MS-016 Identity ──► MS-017 Billing                        │
         │                                                │
         ▼                                                ▼
MS-001 Data Centre ──► MS-002 Instruments/Universe
         │                 │
         ▼                 ▼
MS-003 CA & Calendar ──► MS-004 Quality & Certification
         │                        │
         └────────────┬───────────┘
                      ▼
              Shared canonical market data
                      │
      ┌───────────────┼────────────────┐
      ▼               ▼                ▼
   MS-005          MS-006           MS-007
 Overview         Charting          Scanner
      │               │                │
      │               └───────┬────────┘
      │                       ▼
      │                 MS-010 Trade Planning
      │                       │
      │         ┌─────────────┼──────────────┐
      │         ▼             ▼              ▼
      │      MS-011        MS-012         MS-013
      │    Portfolio      Journal        Backtest
      │         │             │              │
      │         └──────┬──────┘              │
      │                ▼                     │
      │         MS-015 Alerts ◄──────────────┘
      │                │
      └──── MS-014 AI ─┘  (reads stored research only)

MS-008 Fundamentals ── depends on MS-002 (+ external sources OD)
MS-009 Sector Intel ── depends on MS-002/005 (+ sector source OD)
```

## 2. Suggested specification / implementation waves

| Wave | Modules | Why |
|---|---|---|
| W0 | MS-018, MS-016 | Cloud foundation + tenancy before customer data |
| W1 | MS-017 | Entitlements before paid features |
| W2 | MS-001-004 | Shared market data plane + certification |
| W3 | MS-005-007, MS-006 | Research terminal core |
| W4 | MS-010-012 | Decision workflow |
| W5 | MS-013, MS-015 | Heavy jobs + automation |
| W6 | MS-014, MS-008, MS-009 | Differentiated research (after sources) |

## 3. Existing local product reuse

W3-W5 can port heavily from `platform/` + `nse/`. W0-W1 are mostly new relative to the repository.

## 4. Blockers that freeze claims (not necessarily UI coding)

- D66 completeness windows (certification claims)
- Membership human acceptance remaining blanks
- TradingView parity (Q12) for zone reference claims
- Separate build/spend authorisation before public SaaS deploy (OD-BP-001 is direction only)
