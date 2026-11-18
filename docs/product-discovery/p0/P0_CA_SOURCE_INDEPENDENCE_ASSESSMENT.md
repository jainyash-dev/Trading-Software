# P0 corporate-action source independence assessment

**Date:** 2026-11-16  
**Authority:** D66 (`USER_APPROVED`); ED-56; prior Batch 7 / D68 evidence.  
**Result:** No candidate is D66-qualified. No completeness window, `completeness.csv` row or approval marker was created. D66 is unchanged.

## 1. Binding independence rule

Under D66, completeness for a symbol-window needs **two independent official sources**, each with verified SHA-256, established provenance, and event-by-event reconciliation. A single source never establishes completeness.

Independence is **not**:

- distinct file hashes alone (ED-56 / Batch 7 F-1);
- two publications of the same underlying record;
- agreement on the same events without an upstream-chain argument;
- the same institution publishing through two channels.

Independence **is** an argument that the two artefacts are issued by distinct publishers whose recorded facts are not mere republications of one another. Shared economic origin at the issuer is expected; shared **publication chain** is not.

## 2. Existing chains already in custody

| Chain | Publisher | Role today | Can it be Source B against NSE? |
|---|---|---|---|
| NSE CA API JSON (`raw/ca_*.json`) | NSE | Exploratory (D62); refused as completeness source (ED-56) | No |
| NSE FAOP / CML circulars | NSE | Event corroboration (owner Q1) | No - same institution |
| CDSL DP "DETAILS OF CORPORATE ACTIONS" | CDSL | Event-level match on 15/15 known ISIN-changing splits (D68) | Not for a full window; class coverage insufficient |
| Issuer scheme / IM PDFs | Issuer (sometimes NSE-hosted) | Event terms only | Not for window completeness |
| BSE tariff / enquiry materials | BSE | Catalogue only; no CA dataset held | N/A until product obtained |

## 3. Candidate independence matrix

| Candidate | Distinct legal publisher from NSE? | Upstream origin disclosed? | Risk of being an NSE republisher | Pairing outlook vs held NSE artefacts | Assessment |
|---|---|---|---|---|---|
| **PRIMEINFOBASE** | Yes (Praxis Consulting & Information Services Pvt. Ltd.) | **No** - terms call the site an "information intermediary" drawing from "a number of sources" | **Material** - coverage keyed to "NSE Symbol"; no methodology statement rules out exchange feeds | Unknown until PRIME discloses sources and a sample is reconciled without assuming independence from match alone | **INDEPENDENCE_NOT_ESTABLISHED** (blocks D66 even if commercial access later opens) |
| **NSDL official CA / DP circulars** | Yes (NSDL) | Partially - issuer/RTA setup; non-cash checklists require exchange record-date confirmation | Low as NSE republisher; medium shared-date risk with exchange | Institutional pair with NSE circulars is plausible **if** official bytes are obtained and coverage proved | Independence **institutionally plausible**; access and provenance of a research-usable archive still open |
| **NSDL third-party reprints** | No (aggregator publishes) | No authentic NSDL custody | High - same circulars, non-official bytes | Fails | **REJECTED** |
| **CDSL expanded archives** | Yes (CDSL) | Partially - issuer/RTA; record-date independence from exchange **not** established | Low as NSE republisher | Split-only corroboration already shown; cannot cover bonus/rights/demerger/zero-event | Independence vs NSE institutionally ok for splits; **insufficient** as sole second source for D66 windows |
| **Issuer filings / schemes** | Issuer is primary | Yes (issuer is origin) | N/A | Supplies terms; same upstream as every exchange/depository reprint of that event | Not a window Source B |
| **BSE Datafeed CA products** | Yes (BSE) | Not obtained | Low as NSE republisher if product is BSE intimations only | Strongest exchange-to-exchange pair **if** docs prove coverage and non-NSE upstream | Independence promising; **commercial / eligibility blocked** (owner: individual Datafeed eligibility unavailable) |
| **CMIE Prowess** | Yes (CMIE) | Partial - "MCA and Stock Exchanges" | **Material** - exchange-sourced market data | Match-only qualification forbidden | **INDEPENDENCE_NOT_ESTABLISHED** + commercial |
| **ACE Equity / Capitaline / Bloomberg** | Yes (vendors) | Not established in public materials read | Material until upstream named | Same | **INDEPENDENCE_NOT_ESTABLISHED** + commercial |
| **NSE internal second channel** | No | NSE | Is NSE | Fails | **REJECTED** |

## 4. Pair evaluations (analysis only; none approved)

| Proposed pair | Publisher independence | Upstream independence | Event-class overlap | Zero-event support | Verdict |
|---|---|---|---|---|---|
| NSE circulars + PRIME export | Yes if PRIME ≠ NSE republisher | **Unknown** | Claimed broad; unverified | Claimed by coverage statement; unverified | **Not established** - enquiry required |
| NSE circulars + NSDL official CA | Yes | Shared issuer; exchange record-date letter may feed NSDL | Process supports many classes; archive access missing | No | Blocked on access/provenance |
| NSE CML + CDSL DP (splits) | Yes | Record-date independence unproved | ISIN-changing splits only | No | Event corroboration only (D68); **not** a D66 window |
| NSE + BSE Datafeed | Yes | Likely separate intimations; unproven | Unknown | Unknown | Blocked on eligibility/purchase |
| NSE + issuer scheme | Partial | Issuer is common upstream | Per event | No | Terms only |
| CDSL + NSDL | Yes (two depositories) | Shared issuer/RTA class | Unknown without NSDL artefacts | No | NSDL side inaccessible |
| Any + NSE API JSON | - | - | - | - | **Fails** ED-56 |
| PRIME + CMIE / ACE / Capitaline | Vendor + vendor | Both unknown; possible shared exchange feeds | Unknown | Unknown | Cannot invent independence from two commercial compilations |

## 5. Zero-event windows (115 symbols / 82,772 member-dates)

No candidate today can prove a zero-event window under D66.

- CDSL: event-centric ISIN-change series; silence ≠ no bonus.
- NSDL: no public completeness product.
- Issuer filings: absence of a found PDF ≠ proved absence.
- Commercial vendors: only PRIME's public copy **claims** full NSE coverage from 2009; that claim is unverified and does not disclose how empty results are validated.
- BSE paid products: coverage claim "since 2006" remains unverified and currently unavailable under individual Datafeed eligibility.

## 6. What would move a candidate

For any candidate to become **eligible for owner completeness approval** (still not automatic qualification):

1. Named legal publisher and named upstream chain in writing.
2. Demonstrated non-identity with NSE CA service bytes and with each other.
3. Event-class coverage for bonus, split, rights, merger, demerger (or an explicit, accepted limitation that shrinks the certified population).
4. A documented method that makes an empty result a proved zero-event window.
5. Retrievable original artefacts with SHA-256 custody.
6. Research licensing that permits local preservation.
7. Event-level reconciliation record for the requested symbol-window.
8. Explicit owner approval naming both hashes and the reconciliation (D66).

Until all eight exist, classification stays below D66-qualified.

## 7. Facts vs recommendations

**Facts**

- PRIME publicly claims all NSE-listed companies from 1 April 2009; contact `info@primeinfobase.com`; pricing unpublished.
- NSDL's public DP circulars page did not expose a usable public archive in this session; participant CA Export formats exist.
- CDSL remains free and held for ISIN-changing splits only.
- BSE Datafeed CA products remain paid; owner states individual eligibility is unavailable.
- Certified member-dates remain 0 / 123,778.

**Recommendations** (not owner decisions)

1. Send the PRIME written enquiry (draft in `P0_CA_SOURCE_DISCOVERY_REPORT.md`); do not purchase on the reply alone.
2. Treat NSDL official access as a parallel institutional track if a DP/research channel exists.
3. Do not spend on ACE/Capitaline/Bloomberg/CMIE until an official or PRIME path has disclosed upstream independence.
4. Keep CDSL as split corroboration only.
5. Do not weaken D66.
