# 11  -  Existing Pending Work Reconciliation

## 1. Numbering systems (do not conflate)

| System | Meaning |
|---|---|
| GTF phases P0-P11 | Data/engineering programme in gtf-autonomous-project-lead |
| Product Prompts 00-14 | Desktop/local product programme docs |
| Modules P01-P28 | Research capability inventory in PRODUCT_MASTER_STATUS |
| Assignment 00 MS-001-018 | This SaaS blueprint module catalogue |

## 2. Phase reconciliation

| Phase | Documented software state | Data/cert state | SaaS blueprint impact |
|---|---|---|---|
| P0 | Certification builder advanced | **Not certified** (0 member-dates; D66) | MS-001-004 trust claims blocked |
| P1-P4 | COMPLETE_WITH_EXPLICIT_LIMITATIONS | Refuse CERTIFIED modes while P0=0 | Port to SaaS W3-W4 |
| P5 | ACCEPTANCE_READY (not owner ACCEPTED) | N/A | MS-011 |
| P6 | ACCEPTANCE_READY (not owner ACCEPTED) | N/A | MS-012 |
| P7 | Infra partial |  -  | Expands into MS-018 SaaS |
| P8 | Quantitative validation incomplete | R4 open | MS-013 |
| P9 | Assistant not LLM | OQ-2 | MS-014 |
| P10 | UI ACCEPTANCE_READY on fixtures | Not cert | Frontend shell reuse |
| P11 | Release not closed | R1-R5 open | Commercial launch ≠ P11 |

## 3. Engineering-first roadmap vs Assignment 00

`GTF_ENGINEERING_FIRST_ROADMAP.md` parks P0 certification priority behind software completion without weakening D66. Assignment 00 adds a **commercial SaaS architecture track**. Tracks can proceed in parallel only if:

- Certification claims remain blocked until D66 windows exist.
- Cloud spend still waits for separate purchase/deploy approvals (OD-BP-001 does not authorise spend).
- Local product invariants remain tested during migration.

## 4. Pending work buckets

### Bucket A  -  Preserve and port

Platform workflows: overview, scanner, charts, plans, portfolio, journal, settings, jobs subset.

### Bucket B  -  Data blockers (unchanged)

D66 dual sources; remaining membership blanks; identity unjoined BAJFINANCE/GRASIM; TradingView Q12; price exceptions OD-PX-4 declined.

### Bucket C  -  New SaaS foundation

MS-016, MS-017, MS-018, Postgres migration, Redis, object storage, tenancy tests.

### Bucket D  -  Deferred product

Fundamentals (MS-008), sector sources (MS-009), LLM assistant, paper book, live quotes (OQ-1), WIT.

### Bucket E  -  Governance conflicts

OD-BP-001 closed packaging conflict (D57 superseded for commercial production). Remaining: UX-018 wording cleanup in older docs; R-5 precedence wording (Q13); commercial ODs OD-BP-004+.

## 5. Requirement ID preservation

All FR-* and capability IDs remain valid references. SaaS adds SFR-* without renumbering historical evidence packs.

## 6. What not to reopen

Rulebook text; Pine; `authorises_order=false`; MTF eligibility path; D66 Option A; dummy seat Option A (D68); OD-PX-4 decline.
