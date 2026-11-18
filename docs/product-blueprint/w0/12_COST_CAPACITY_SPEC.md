# W0-12 - Cloud Cost and Capacity Specification

**Status:** Specification only. Figures are assumptions requiring validation.

## 1. Customer tier assumptions (planning)

| Stage | Tenants | Concurrent API users | Scans/day | Backtests/day |
|---|---|---|---|---|
| Launch | 50-100 | 10-30 | 100-300 | 10-40 |
| Expected Y1 | 500-1000 | 50-150 | 1k-3k | 50-200 |
| Growth | 5k | 300-800 | 10k+ | 500+ |

## 2. Market-data volume assumptions

| Item | Assumption |
|---|---|
| Nifty 100 history | ~10y EOD; order 50-200GB with CA/raw/versions (validate) |
| Growth | New daily bhavcopies + CA artefacts << history bulk |
| Tenant private | attachments dominate; quota per plan |

## 3. Compute

| Workload | Notes |
|---|---|
| API | CPU light; scale on RPS |
| Scan workers | CPU bound around engines; burst post 15:45 IST |
| Backtest | Cap concurrency per tenant and global; queue otherwise |
| DB | Start small multi-AZ; watch connections via pooler |

## 4. Per-tenant quotas (proposed defaults; OD-BP-005)

| Quota | Trial | Research | Pro |
|---|---|---|---|
| Scans/day | 5 | 50 | 200 |
| Backtests/month | 2 | 20 | 100 |
| Attachment MB | 100 | 1GB | 5GB |
| Seats | 1 | 1 | 1 (until OD-BP-003) |

## 5. Cost scenarios (illustrative USD/month)

See also W0-03. Conservative 150-400; Expected 400-1200; Growth 2k-8k+. Dominated by DB, workers, observability, egress.

## 6. Cost alerts / scaling thresholds

- Budget alerts at 50/80/100% of monthly envelope (owner sets envelope).
- Autoscale workers when queue age > 5 minutes.
- Page if scan backlog not cleared before next session.

## 7. Assumptions requiring validation

Region pricing; India egress; observability vendor; actual scan CPU seconds; attachment behaviour; data licence fees (OD-BP-014) which may dwarf infra.
