# W0-09 - Observability and Operations Specification

**Status:** Specification only.

## 1. Telemetry pillars

| Pillar | Requirement |
|---|---|
| Logs | Structured JSON; request_id; tenant_id; user_id hash optional; **never** passwords/OTPs/tokens/cookies |
| Metrics | RED for API; queue depth; job success/fail; DB connections; ingest lag |
| Traces | Distributed trace across API -> DB -> worker |

## 2. Health surfaces

| Check | Endpoint / signal |
|---|---|
| API liveness | `/api/v1/health` |
| Readiness | DB + Redis + secrets reachable |
| Worker health | heartbeat metric + queue consumer lag |
| Database | connection + replication lag |
| Queue | depth + oldest age |
| Ingestion | last successful market session artefact age |
| Job failures | rate by type |

## 3. Alert severity

| SEV | Example | Response |
|---|---|---|
| 1 | Data breach suspected; total auth outage | Page immediately |
| 2 | DLQ growth; DB down; ingest missed session | Page |
| 3 | Elevated 5xx; single worker crash loop | Ticket same day |
| 4 | Slow queries; quota noise | Backlog |

## 4. Customer-safe diagnostics

Support bundle: tenant id, job ids, dataset versions, redacted recent errors. No session secrets. Customer status page shows shared ingest lag only.

## 5. Acceptance

Log redaction tests; health checks documented; alert runbooks drafted; no PII in example log fixtures.
