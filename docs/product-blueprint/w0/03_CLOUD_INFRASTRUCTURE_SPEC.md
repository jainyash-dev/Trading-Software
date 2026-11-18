# W0-03 - Cloud Infrastructure Specification

**Status:** Specification only. Provider/region selection NOT authorised (OD-BP-010). No accounts or purchases.

## 1. Target topology

```
Customers
   |
 CDN (SPA static) + WAF
   |
 API service (N replicas, private subnet)
   |-- Workers (M replicas)
   |-- Managed PostgreSQL (private)
   |-- Managed Redis (private)
   |-- Object storage (private + signed URL egress)
   |-- Secrets manager
   |-- Logs / metrics / traces
```

ASCII diagram only; formal draw.io optional later.

## 2. Provider alternatives (evaluation; no selection)

| Dimension | AWS | GCP | Azure | Other (Fly/Render/Railway) |
|---|---|---|---|---|
| Managed Postgres | RDS/Aurora | Cloud SQL | Flexible Server | Often external |
| Redis | ElastiCache | Memorystore | Azure Cache | Addon |
| Object storage | S3 | GCS | Blob | R2/S3-compat |
| India region | ap-south-1 | asia-south1 | centralindia | Limited |
| WAF/CDN | CloudFront+WAF | Cloud CDN+Armor | Front Door | Cloudflare |
| Ops maturity | High | High | High | Faster start, less control |

**Recommendation for owner review:** Prefer a major cloud with an India region for residency (OD-BP-010). PaaS-only stacks acceptable for early staging if production can meet W0-07/10.

## 3. Component mapping

| Concern | Spec |
|---|---|
| Frontend hosting | Object storage + CDN for `platform/web` build artefacts |
| Backend hosting | Container service / VM ASG running FastAPI |
| Workers | Separate service same image different entrypoint |
| Database | Managed PostgreSQL multi-AZ preferred |
| Object storage | Versioned buckets: market-raw, market-derived, tenant-private |
| Networking | Public only CDN/WAF/ALB; DB/Redis private |
| TLS | Managed certs; HTTPS only; HSTS |
| Secrets | Cloud secret manager; no secrets in images/git |
| Envs | `local` (baseline), `staging`, `production` |

## 4. Availability and scaling (proposals pending OD-BP-007)

| Tier | Proposal |
|---|---|
| API | Horizontal pods; target 99.5% monthly (proposal) |
| Workers | Autoscale on queue depth |
| DB | Vertical + read replica later if needed |
| CDN | Global edge for SPA |

## 5. Cost estimate assumptions (illustrative; not a quote)

Assumptions: 100 active tenants, 20 concurrent API users, 1 post-close scan wave, 50GB market objects, 20GB tenant objects, multi-AZ small Postgres, small Redis, modest logs.

| Scenario | Monthly ballpark (USD) | Notes |
|---|---|---|
| Conservative | 150-400 | Single-AZ staging-like prod (not recommended long-term) |
| Expected | 400-1200 | Multi-AZ DB + WAF + workers |
| Growth (1k tenants) | 2k-8k+ | Dominated by DB, workers, egress, observability |

**These are planning assumptions, not bids.** Validate after OD-BP-010 and capacity model W0-12. No purchase authorised.

## 6. Acceptance for infrastructure spec

- Environments named and separated.
- Public/private network boundary defined.
- Region decision listed as open until OD-BP-010.
- Cost assumptions explicit.
