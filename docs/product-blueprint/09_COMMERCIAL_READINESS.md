# 09  -  Commercial Readiness

Documentation of requirements only. **Do not contact providers, purchase services, or enter commitments** from this blueprint.

## 1. Customer registration and accounts

- Self-serve registration, email verification, login, logout, session revocation.
- Profile: name, email, password/IdP, timezone Asia/Kolkata default for NSE workflows.
- Workspace = tenant for individual plan.
- Support diagnostics: tenant id, dataset versions, job ids  -  no raw session secrets.

## 2. Subscription and entitlement model (proposed; OD-BP-005)

| Element | Proposal for owner review |
|---|---|
| Plans | Free/trial (limited), Research, Pro (names TBD) |
| Entitlements | Scan quota, backtest quota, history depth, AI calls, seats |
| Enforcement | Server-side only |
| Grace | Read-only on lapse (proposal) |

## 3. Payment integration requirements

- PCI: use hosted PSP fields / checkout; no PAN storage in GTF.
- Webhooks signed and idempotent.
- Invoice/receipt storage references only.
- Indian payment method support to be reviewed with counsel/PSP (UPI/cards/netbanking).
- Taxes/GST treatment = OD-BP-013.

## 4. Data licensing and redistribution

- NSE / index / CA / corporate data redistribution rights must be reviewed before commercial hosting of shared market data (OD-BP-014).
- Do not assume local research fair use equals SaaS redistribution rights.
- Provider contracts out of scope until owner authorises enquiries/purchases (D68 already limits BSE to enquiry-only).

## 5. Privacy and data protection

- Indian DPDP Act readiness review required (OD-BP-006).
- Privacy policy, terms of service, cookie notice for SaaS.
- Lawful basis / consent for account and telemetry.
- Cross-border transfer assessment if region ≠ India.

## 6. Security and incident response

- See `08_CLOUD_SECURITY_AND_TENANCY.md`.
- Vulnerability disclosure contact.
- Backup encryption and access control.

## 7. Onboarding

- Guided first run: capital/risk stage, universe explanation, data freshness, disclaimer (not advice, not broker).
- Sample fixture mode explicitly labelled if used for demos  -  never as certified.

## 8. Support and diagnostics

- In-app support bundle export (redacted).
- Status page for shared market ingest lag.
- Operator tools with audit.

## 9. Availability and reliability

- Targets OD-BP-007.
- Maintenance windows communicated.
- Job SLAs separate from HTTP availability.

## 10. Export and deletion

- Customer export within entitlement.
- Deletion / account closure workflow with confirmation and cooling-off proposal.

## 11. Indian regulatory and commercial compliance review

Required external/legal review topics (not legal advice from this blueprint):

- Securities research vs investment advisory boundaries
- Marketing claims (no guaranteed returns)
- Data vendor redistribution
- Consumer terms, refunds
- GST invoicing
- DPDP compliance

**OD-BP-015:** Engage qualified counsel before public commercial launch.

## 12. Readiness verdict

**NOT COMMERCIALLY READY.** Engineering research product exists locally; SaaS commercial controls are unspecified/unimplemented pending owner decisions and legal review.
