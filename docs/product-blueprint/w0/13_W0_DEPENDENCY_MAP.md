# 13 - W0 Dependency Map

## 1. Internal W0 dependencies

```
W0-03 Infra ─────────────────────────────┐
W0-01 Identity ──► W0-02 Tenancy ──► W0-07 Security
         │              │                 │
         ▼              ▼                 ▼
      W0-08 Billing   W0-04 DB/Storage ◄──┘
         │              │
         ▼              ▼
               W0-05 Backend
                      │
                      ├── W0-06 Workers
                      ├── W0-09 Observability
                      ├── W0-10 Backup/DR
                      ├── W0-11 CI/CD
                      └── W0-12 Cost (feeds quotas in W0-08)
```

## 2. W0 -> MS module dependencies

| W0 | Enables MS |
|---|---|
| W0-01/02 | MS-016 |
| W0-08 | MS-017 |
| W0-03/09/10/11/12 | MS-018 |
| W0-04/05/06 | MS-001-015 cloud adaptations |
| W0-07 | All modules |

## 3. Existing repo dependencies

Must keep working during later implementation: `nse/` engines, platform tests, run_all groups, P0/D66 artefacts, journal authority, qualification path.

## 4. External blockers

OD-BP-014 data licensing; OD-BP-010 region/provider; OD-BP-004 identity; OD-BP-005 billing.
