# W0-06 - Worker Orchestration Specification

**Status:** Specification only.

## 1. Job model

| Field | Notes |
|---|---|
| id | UUID |
| tenant_id | NULL only for platform market jobs |
| type | enum below |
| state | `QUEUED|RUNNING|SUCCEEDED|FAILED|CANCELLED|DEAD` |
| idempotency_key | unique per tenant+type |
| payload | JSON schema per type |
| progress | 0-100 + message |
| attempts | int |
| locked_by | worker id |
| heartbeat_at | for stale detection |
| created_at / started_at / finished_at | timestamps |
| error_code / error_detail_redacted | failures |

## 2. Job types

| Type | Trigger | Tenant? |
|---|---|---|
| `market.ingest` | schedule/admin | No |
| `market.validate` | after ingest | No |
| `market.ca_process` | after CA acquire | No |
| `market.candle_build` | after validate | No |
| `scan.run` | user/schedule | Yes |
| `backtest.run` | user | Yes |
| `notify.deliver` | event | Yes |
| `ops.maintenance` | schedule | No |
| `ops.restore_verify` | schedule/admin | No |
| `tenant.export` | user | Yes |
| `tenant.purge` | schedule after delete | Yes |

## 3. Queue topology

Recommendation: Redis Streams or queue lists + delayed retry ZSET.

| Queue | Contents |
|---|---|
| `q:market` | shared market jobs |
| `q:scan` | tenant scans |
| `q:backtest` | heavy tenant jobs (separate concurrency) |
| `q:notify` | emails/webhooks |
| `q:ops` | maintenance |
| `q:dlq` | dead letters |

## 4. Lifecycle rules

- Exactly-once **effect** via idempotency keys + transactional outbox preferred; at-least-once delivery assumed.
- Retry: exponential backoff with jitter; max attempts per type (scan 3, backtest 2, notify 5 proposed).
- Timeout per type; heartbeat; stale RUNNING -> requeue or FAILED.
- Cancellation: cooperative flag checked by worker.
- Concurrency: global and per-tenant limits (backtest especially).
- DLQ after max attempts; alert SEV-2+.
- Progress reporting polled via `GET /jobs/{id}` (tenant-scoped).

## 5. Tenant context

Worker must:
1. Load job.
2. If tenant_id set, bind tenant + SET LOCAL RLS.
3. Refuse to write other tenants.
4. Include tenant_id in logs (not PII).

## 6. Mapping from current jobs

Replace in-process thread in `jobs.py` for SaaS mode; keep in-process optional for local baseline only.

## 7. Acceptance tests

Idempotent re-delivery; tenant isolation on job status; DLQ path; cancel; heartbeat stale recovery; backtest concurrency cap.
