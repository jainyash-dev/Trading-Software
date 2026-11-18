# P0 - Alternative corporate-action source discovery report

**Date:** 2026-11-16  
**Phase:** GTF P0 (Product Prompt 01 / MP1)  
**Authority:** D66; D62; ED-56; D67/D68 enquiry limits; task instruction that BSE paid Datafeed Products are unavailable under current individual eligibility.  
**Result: D66 remains blocked. Certified member-dates remain 0 / 123,778. No candidate is D66-qualified.**

**Deliverables**

| File | Role |
|---|---|
| `P0_CA_ALTERNATIVE_SOURCE_REGISTER.csv` | Candidate register with evaluation fields and classification |
| `P0_CA_SOURCE_INDEPENDENCE_ASSESSMENT.md` | Independence / upstream-chain analysis |
| `P0_CA_COVERAGE_GAP_MATRIX.csv` | Population needs × candidate coverage |
| This report | Findings, PRIME enquiry draft, recommendations |

**Restrictions observed:** D66 not weakened; no completeness markers; no price/identity/production changes; no purchase; protected source hashes untouched; existing repository work preserved.

---

## 1. Objective and population

Find and qualify a genuinely independent second corporate-action source capable of satisfying D66.

From prior V3 discovery (`P0_D66_SOURCE_DISCOVERY_REPORT.md`), the blocked population is unchanged:

| Need | Count | Member-dates |
|---|---|---|
| Symbols with ≥1 non-dividend event (dual-source per event + inter-event coverage) | 49 symbols / 60 events | 41,006 |
| Symbols with no recorded non-dividend event (dual-source zero-event proof) | 115 symbols | 82,772 |
| **Total blocked by D66** | 164 | **123,778** |

BSE paid Datafeed Products are treated as unavailable under the owner's current individual eligibility (task constraint). The existing BSE enquiry draft remains unsent unless the owner sends it for information only.

---

## 2. Classification summary

No candidate may be marked D66-qualified until all D66 requirements are demonstrated **and** owner approval is obtained.

| source_id | Candidate | Classification | One-line basis |
|---|---|---|---|
| ALT-PRIME-CA | PRIMEINFOBASE Corporate Actions Database | **QUALIFIED_FOR_FURTHER_TESTING** | Only public claim of all NSE companies from 1 Apr 2009; independence/provenance/licensing unproven; enquiry next; no purchase |
| ALT-NSDL-OFFICIAL | NSDL CA records / DP circulars / CA Exports | **COMMERCIAL_ACCESS_REQUIRED** | Official institution; public archive not usable; participant/issuer path |
| ALT-NSDL-THIRDPARTY | NoticeBlue-class NSDL reprints | **REJECTED** | Not the official publisher; same underlying circulars |
| ALT-CDSL-EXPANDED | Expanded CDSL CA communique archives | **INSUFFICIENT_COVERAGE** | Strong for ISIN-changing splits only; no bonus/rights/demerger/zero-event |
| ALT-ISSUER-FILINGS | Issuer / MCA / scheme documents | **INSUFFICIENT_COVERAGE** | Event terms only; cannot prove windows |
| ALT-BSE-DATAFEED | BSE Corporate Action data products | **COMMERCIAL_ACCESS_REQUIRED** | Separate exchange; individual Datafeed eligibility unavailable; paid |
| ALT-CMIE-PROWESS | CMIE Prowess / Prowess dx | **COMMERCIAL_ACCESS_REQUIRED** | Also independence not established (exchange-sourced components) |
| ALT-ACE-EQUITY | ACE Equity | **COMMERCIAL_ACCESS_REQUIRED** | Vendor; provenance not established |
| ALT-CAPITALINE | Capitaline | **COMMERCIAL_ACCESS_REQUIRED** | Vendor; provenance not established |
| ALT-BLOOMBERG-CA | Bloomberg Corporate Actions | **COMMERCIAL_ACCESS_REQUIRED** | Enterprise vendor; India upstream undisclosed |
| ALT-NSE-INTERNAL | NSE FAOP/CML/API/CSV as Source B | **REJECTED** | Same institution / refused API chain |

Secondary labels that also apply (recorded in the register/independence note, not as the primary class): PRIME → provenance and independence not established until PRIME answers; CMIE/ACE/Capitaline/Bloomberg → independence not established.

---

## 3. Candidate findings

### 3.1 PRIMEINFOBASE (priority enquiry)

**Legal publisher:** Praxis Consulting & Information Services Pvt. Ltd. (copyright on Terms page).  
**Public product page** (`https://primeinfobase.com/single-product5.aspx`, read 2026-11-16):

- 25,889 corporate actions "as on 13-NOV-2026".
- Coverage table: **All companies listed on NSE - 1st April 2009 onwards**; BSE-only companies with mcap > INR 1,000 crore - 1st April 2019 onwards.
- Search parameters include Company/NSE Symbol, Subject, Ex-Date, Record Date, BC Start Date, Dividend Payment Date.
- Contact: Tel +91-11-4100-8346/7/8; Email `info@primeinfobase.com`.
- One-time data: "send an email to info@primeinfobase.com".
- Purchase form: `buynow.aspx` (quote path; no public price list).

**Terms & Conditions (read 2026-11-16):**

- Site described as an **information intermediary**.
- Explicit disclaimer of accuracy/completeness; "number of sources" with delays/omissions possible.
- Publisher may edit, index, group and regroup data for its search methodology.
- Default use: personal / non-commercial view/print; redistribution restricted without prior written consent.
- **No** public methodology naming exchange feeds, depositories, or issuer filings as upstream.

**Verification status of the 2009 NSE claim**

| Check | Result |
|---|---|
| Claim present on PRIME's own product page | Yes |
| Claim repeated by an institutional library summary (IIMB) | Yes |
| Claim verified by PRIME in writing to this programme | **No - enquiry not yet sent** |
| Sample export held locally | No |
| Completeness / zero-event methodology disclosed | No |
| Independence from NSE established | No |

**Assessment:** Highest-leverage **further-testing** candidate because it is the only source found that *states* a full NSE window from a date before the D59 research window. That statement alone does **not** satisfy D66. Matching events after purchase would also be insufficient without provenance independence.

### 3.2 NSDL

- Issuer-services page describes monetary and non-monetary CA handling and lists document packages for bonus, rights, sub-division, demerger, amalgamation, etc. (read 2026-11-16).
- `nsdl.com/participant/circulars` returned no usable public circular listing in this session (empty/gated behaviour).
- Participant CA Export standardised format exists (NSDL/POLICY/2023/0006) - operational DP feed, not a public research archive.
- Secondary aggregators list "Corporate Action details" circular titles; those reprints are **REJECTED** as D66 sources (not official publisher).
- Prior Batch 7: public per-ISIN CA list not found; pages previously failed with ECONNRESET.

**Assessment:** Institutionally independent of NSE; research-usable archive **not established**. Classification: **COMMERCIAL_ACCESS_REQUIRED** (participant/authorised access).

### 3.3 Expanded CDSL archives

- Public communique listing remains active; "DETAILS OF CORPORATE ACTIONS" continues into 2026 (e.g. DP2026-800).
- DP communique index held from D68 (SHA-256 `cb924e6d...`).
- D68 free coverage test: **15/15** known in-window ISIN-changing splits found and matched.
- Still absent: bonuses, rights, demergers; zero-event proof; reverse-direction completeness; proved independence of record date from exchange confirmation.

**Assessment:** Further expansion of the same series does not create new event classes. **INSUFFICIENT_COVERAGE** for D66 second-source role.

### 3.4 Official issuer filings and scheme documents

- Primary for event **terms** (held example: CGCEL Information Memorandum).
- SEBI LODR announcements are typically retrieved via exchange corporate-filings portals; MCA holds scheme/public documents.
- One document per event; silence elsewhere is not a proved empty window.

**Assessment:** **INSUFFICIENT_COVERAGE** for completeness; keep for unparsed-event terms only.

### 3.5 Other institutional providers

| Provider | What was checked | Why not D66-ready |
|---|---|---|
| BSE Datafeed CA products | Tariff held; enquiry draft exists; owner eligibility constraint | Paid + individual eligibility unavailable |
| CMIE Prowess / Prowess dx | Product pages + licence; CA included; dx for academia/non-profits | Paid; exchange+MCA sourcing → independence open |
| ACE Equity | User-guide / library listings; 100+ event heads claimed | Paid; provenance open |
| Capitaline | Library descriptions; corporate announcements claimed | Paid; provenance open |
| Bloomberg CA | Public fact sheet; global history from 2007 | Enterprise cost; India upstream undisclosed |

All five: primary class **COMMERCIAL_ACCESS_REQUIRED**. None inspected via sample export in this session. None purchased.

### 3.6 NSE internal channels

Rejected as independent Source B (same publisher / ED-56 API refusal / owner corroboration-only rule).

---

## 4. Evaluation against D66 criteria (cross-candidate)

| Criterion | Best current answer |
|---|---|
| Legal publisher / data origin | Clear for CDSL, NSDL, BSE, issuers; **uncleared for PRIME and commercial vendors** |
| Historical coverage start/end | PRIME claims 2009-04-01→; CDSL CA series ~2010→; BSE "since 2006" unverified; others unknown |
| Population / universe | Only PRIME and BSE *claim* exchange-wide windows; CDSL/NSDL are event/ISIN feeds |
| Event classes (bonus/split/rights/merger/demerger) | CDSL proved for ISIN-changing splits only; others unverified or terms-only |
| Zero-event windows | **None proved** |
| Original notices | CDSL PDFs yes; issuer PDFs yes; PRIME/vendors unknown |
| Event-level reconciliation | Feasible where artefacts exist (CDSL splits); not done for PRIME |
| Retrieval reproducibility | CDSL/NSE archives yes; NSDL public no; vendors subscription-dependent |
| SHA-256 preservation | Feasible whenever original bytes are obtained into custody |
| Licensing | PRIME/CMIE/ACE/Capitaline/Bloomberg/BSE paid or restricted; CDSL public communiques free |
| Genuine independence | Only institutional separation is clear for CDSL/NSDL/BSE/issuer; **PRIME independence not established** |

---

## 5. PRIME written enquiry (NOT SENT)

This session has no authorised outbound mail channel. Send as written, or edit. **No purchase, subscription, payment or commitment** is made or implied.

**To:** info@primeinfobase.com  
**Subject:** Research enquiry - Corporate Actions Database coverage, methodology and sample (no purchase at this stage)

---

Dear PRIMEINFOBASE team,

We are evaluating historical corporate-action data for internal research on NSE-listed equities. This is an information request only; we are not placing an order and we are not authorising any purchase.

Your public Corporate Actions Database page states coverage of all companies listed on NSE from 1 April 2009 onwards (and of qualifying BSE-only companies from 1 April 2019). Could you please provide:

1. **Product documentation** for the Corporate Actions Database (schema, field definitions, update frequency, delivery/export formats).
2. **Source methodology:** how records are compiled; which primary sources are used (issuer filings, stock-exchange intimations, depository records, other); and whether any fields are derived from NSE corporate-action feeds or NSE circulars.
3. **Historical sample export** for internal evaluation only, if possible for calendar year 2022 for: TORNTPHARM, GAIL, HDFCBANK (or a documented schema sample if company-level samples are not available).
4. **Event-class coverage:** confirmation whether the database includes bonus issues, stock splits/sub-divisions (with ratios and old/new ISIN where applicable), rights issues (with terms), mergers/amalgamations, demergers/schemes of arrangement, consolidations, and other capital events - and which classes are excluded.
5. **Original documents:** whether original notices, exchange circulars or issuer PDFs are available or referenced for each event.
6. **Completeness and zero-event methodology:** whether the database is intended to contain every corporate action for every NSE-listed company in the stated period; how completeness is assured; and whether a company-period with no row can be taken as proof that no corporate action of the covered types occurred.
7. **Pricing and licensing** for internal research use only (no redistribution), including subscription and any one-time historical extract options, and conditions on local storage and SHA-256 preservation of delivered files.

Please treat this as a written enquiry only. We will not purchase or subscribe without a separate explicit authorisation.

Thank you.

Regards,  
[Owner name and organisation]

---

When a reply arrives: answers to items 2 and 6 decide whether PRIME can even be a D66 candidate; item 3 enables reconciliation testing; item 7 needs a separate owner purchase decision. **Matching the sample to NSE events alone must not be treated as independence.**

---

## 6. Recommendations (not owner decisions)

1. **Send the PRIME enquiry** (section 5). Highest information value per unit effort; still free.
2. **Do not purchase** PRIME, BSE, CMIE, ACE, Capitaline or Bloomberg on the strength of public marketing claims.
3. **Optional parallel:** if the owner has or can obtain NSDL participant/research access, request official CA circular/export samples for the same 2022 symbols - never NoticeBlue reprints.
4. **Keep CDSL** as ISIN-changing split corroboration only; do not invent bonus/zero-event coverage from it.
5. **Keep issuer/MCA filings** for event terms (including unparsed events); never as window completeness.
6. **Leave BSE Datafeed** parked while individual eligibility is unavailable; the unsent enquiry draft remains available if eligibility changes.
7. **Do not weaken D66**; do not create completeness markers; do not certify any member-date from this discovery.

---

## 7. What this cycle did not do

- No outbound email was sent.
- No paid product was purchased or trial-subscribed.
- No `completeness.csv` row or "Completeness window accepted" marker was created.
- No prices, identity records or production certification outputs were changed.
- No claim was made that any candidate is D66-qualified.

---

## 8. Status line

**P0 remains `P0_CERTIFICATION_BLOCKED` at 0 / 123,778.**  
Engineering cannot clear D66 without an independent second source that proves both events and empty windows. PRIMEINFOBASE is the only newly prioritised candidate for **further testing via written enquiry**; it is not yet qualified.
