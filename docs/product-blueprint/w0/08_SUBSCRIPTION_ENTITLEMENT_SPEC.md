# W0-08 - Subscription and Entitlement Architecture Specification

**Status:** Specification only. OD-BP-005/013 open. No PSP selection or integration authorised.

## 1. Purpose

Gate commercial features and quotas server-side.

## 2. Proposed plan dimensions (names TBD by owner)

| Dimension | Examples |
|---|---|
| Features | scanner, plans, journal, backtest, AI, export |
| Quotas | scans/day, backtests/month, storage MB, seats |
| History depth | as_of lookback days |
| Support tier | email only vs priority |

Illustrative tiers for discussion only: Trial / Research / Pro. **Not approved.**

## 3. Subscription lifecycle

`none -> trial? -> active -> past_due -> suspended -> cancelled -> reactivated`

Events from PSP webhooks drive transitions after signature verification.

## 4. Billing provider evaluation (no selection)

| Option | Pros | Cons |
|---|---|---|
| Stripe | Mature subscriptions/webhooks | India payment-method fit needs check |
| Razorpay | India-native methods | Feature parity evaluation needed |
| Manual invoicing | Simple early | Not self-serve |
| Paddle/LemonSqueezy | MoR tax help | Fees; control tradeoffs |

Owner picks via OD-BP-005 after India methods + GST review (OD-BP-013). **Do not contact providers from this task.**

## 5. Entitlement enforcement

- Compute `entitlement_snapshot` for tenant.
- Middleware/route guards return `ENTITLEMENT_DENIED` / `QUOTA_EXCEEDED`.
- UI hiding is not enforcement.
- Workers re-check entitlements before heavy jobs.

## 6. Payment operations

| Topic | Spec |
|---|---|
| Webhooks | Verify signature; idempotent `psp_event_id` |
| Invoices/receipts | Store PSP references; no PAN |
| Failed payment | Grace then suspend (durations OD) |
| Cancel | End of period vs immediate (OD) |
| Refunds/disputes | Manual ops runbook; audit |

## 7. Acceptance tests

Quota exceed; lapsed suspend; webhook replay; cross-tenant billing mutation denied; no card data in DB.
