# Architecture Decision Record - OD-BP-001

## Title

Supersede D57 Local-First Production Architecture with Browser-Based Cloud SaaS

## Status

USER_APPROVED

## Decision date

2026-11-18

## Decision owner

Product owner

## Context

D57 previously established a USER_APPROVED local-first, loopback architecture.

The product direction has subsequently been defined as a commercially distributable, browser-based cloud SaaS for individual NSE cash-equity traders.

These two deployment models have materially different production architecture requirements.

The commercial product requires:

- Browser-based customer access.
- Cloud-hosted frontend and backend.
- Multi-customer support.
- Secure tenant isolation.
- Centralized managed data services.
- Independently operated background workers.
- Customer identity and access management.
- Subscription and entitlement management.
- Cloud monitoring, backups and recovery.

Continuing to treat local-first loopback as the commercial production architecture would conflict with the approved SaaS product direction.

## Owner decision

The owner explicitly approves superseding D57 for the GTF commercial production architecture.

The commercial GTF product shall be a browser-based, cloud-hosted, multi-tenant SaaS web application.

Customers access GTF through supported web browsers. A desktop application or mandatory desktop installation is not part of the commercial product scope.

Local-first execution may be retained as a development, testing, migration or engineering baseline where useful. It is not the target commercial production deployment model.

## Confirmed product boundaries

- Market: NSE cash equities.
- Initial research universe: Nifty 100.
- Customer: Individual traders.
- Trading approach: Positional and swing trading.
- Deployment: Cloud-hosted browser-based SaaS.
- Execution: Manual through external broker platforms.
- Customer data: Tenant-isolated.
- Broker order routing: Not authorized.
- Desktop shells: Excluded from the commercial product.

## Architectural implications

The target architecture must provide for:

- Browser-based React/TypeScript frontend.
- Cloud-hosted backend APIs and application services.
- Multi-tenant identity and authorization.
- Tenant-isolated customer data.
- Shared market reference data where legally permitted.
- Managed production database.
- Background worker infrastructure.
- Secure object storage.
- Cloud networking, TLS and edge protection.
- Centralized monitoring and observability.
- Backup, recovery and deployment processes.
- Subscription and entitlement enforcement.

Specific technologies and providers remain subject to architecture review and separate approval.

## Preserved decisions and constraints

This decision does not:

- Delete or rewrite the historical D57 decision record.
- Authorize cloud infrastructure purchases.
- Authorize deployment or migration.
- Authorize a database migration.
- Authorize API or schema changes.
- Authorize external provider commitments.
- Authorize broker integration or order execution.
- Remove existing local development/testing capabilities.
- Modify D66 or historical data certification requirements.
- Change existing Rulebook or research-engine decisions.

## Implementation authorization

No implementation is authorized by this decision alone.

The W0 foundation specifications must be completed, reviewed and approved before implementation.

Cloud spending, external provider selection and production deployment require the relevant approvals.

## Supersession rule

D57 remains preserved as a historical USER_APPROVED decision.

For commercial production architecture, OD-BP-001 is the newer controlling owner decision and explicitly supersedes D57.

Any remaining local-first requirements must be classified as development/testing compatibility requirements rather than commercial production architecture requirements.

## Acceptance evidence

- Explicit owner approval recorded on 2026-11-18.
- Master product blueprint updated to reflect cloud SaaS.
- Owner decision register updated.
- Technology decision register updated.
- D57 historical record preserved with supersession reference.
- Canonical log entry: `nse/docs/DECISION_LOG.md` (OD-BP-001).
- Register index: `nse/docs/DECISION_REGISTER.md`.

## Final status

OD-BP-001: USER_APPROVED

Commercial cloud architecture implementation: NOT_AUTHORIZED

W0 specification programme: AUTHORIZED FOR SPECIFICATION ONLY
