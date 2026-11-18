# W0-10 - Backup and Disaster Recovery Specification

**Status:** Specification only. Numeric RPO/RTO are **proposals** until OD-BP-007.

## 1. Targets (proposed for owner review)

| Metric | Proposed production | Notes |
|---|---|---|
| RPO | <= 15 minutes (DB PITR) | Proposal |
| RTO | <= 4 hours for core API+DB | Proposal |
| Object market raw | Versioning + cross-region copy optional | Licence permitting |

## 2. Backup design

| Asset | Method | Frequency | Encryption | Retention |
|---|---|---|---|---|
| PostgreSQL | Continuous PITR + daily snapshot | continuous | provider CMEK/managed | OD-BP-011 / 30-35 days proposed |
| Redis | ephemeral; rebuild from DB | n/a | - | sessions lost acceptable if re-login |
| Object storage | Versioning + lifecycle | continuous | SSE | raw indefinite if licensed |
| Secrets | provider versioning | on change | native | per policy |

## 3. Disaster scenarios

1. Single AZ failure -> multi-AZ failover.
2. DB corruption -> PITR to timestamp.
3. Bad migration -> rollback + restore.
4. Region impairment -> cold standby plan (OD whether active multi-region).
5. Ransomware/object delete -> version restore.
6. Tenant accidental delete -> restore selected tenant rows from PITR + objects (runbook).

## 4. Restore verification

- Monthly automated restore to isolated staging.
- Checksums: table counts, journal ledger hash sample, object inventory sample.
- Record drill evidence.

## 5. Measurable acceptance tests

1. Restore Postgres backup to empty instance; app readiness green.
2. PITR recovers row deleted 10 minutes prior.
3. Object version restore recovers overwritten market raw object.
4. Drill completes within proposed RTO or documents miss.
5. Encryption enabled flags verified in config evidence.

## 6. Open

OD-BP-007 final RPO/RTO; cross-region requirement; retention lengths.
