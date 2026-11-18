# P0 corporate-action provider comparison

**Date:** 2026-11-15  
**Basis:** `P0_CA_SOURCE_ACQUISITION_PROPOSAL.md` + D66/ED-56 rules  
**Downloads:** none (inspection and documentation only)

Owner has **not** authorized acquisition. This comparison does not approve any provider pair.

Independence rule (binding): two sources must have distinct SHA-256 hashes, distinct non-identical files, and neither may be a saved NSE corporate-actions API response or API-shaped JSON.

---

## Comparison table

| Dimension | NSE exchange circulars / CM notices | NSDL corporate-action records | CDSL corporate-action records |
|---|---|---|---|
| What it is | Official NSE capital-market circulars and notices (CML / CMTR / related) that announce or schedule corporate actions, ex-dates, schemes, listing changes | Depository participant / issuer CA communications and NSDL-published CA information keyed primarily by ISIN | Parallel depository CA information from CDSL, also ISIN-centric |
| Typical formats | PDF (sometimes ZIP of PDF + annex) | PDF notices; possible portal extracts/CSV depending on product (formats not held locally today) | Same class as NSDL (formats not held locally today) |
| Strength for D66 | Primary exchange voice for NSE-listed cash equity; circular number + hash fit existing provenance pattern used for calendar/membership | Strong for ISIN-level identity of events; useful when ticker renamed; independent institution from the exchange | Same institutional class as NSDL but a **different** depository - can form a pair with NSDL *if* bytes/content are independent |
| Coverage limitations | Event-centric: one circular may cover one event or a short list; **proving a full symbol window is empty** needs a coverage claim the document itself supports (or many circulars). Not a single bulk "all CA for INFY 2020-2025" unless such an extract exists | May lag or differ in presentation from exchange notices; retail/portal views may not prove window completeness; access often account-gated | Same limitations as NSDL; may disagree with NSDL on timing/wording for the same ISIN |
| Independence vs NSE API archives | Distinct from API JSON when the artefact is a real circular PDF/extract (not a renamed `ca_*.json`) | Independent of NSE API by institution | Independent of NSE API by institution |
| Independence vs each other | N/A | NSDL vs CDSL: usually independent **if** files are not copies of each other; same economic event may still need EQUIVALENT reconciliation | Same |
| Independence vs NSE circulars | - | Exchange circular + NSDL notice is a strong candidate Source A/B pair (different issuers) | Exchange circular + CDSL notice likewise |
| Acquisition constraints | Public NSE archives/circular pages historically used elsewhere in this repo; still needs **owner authorization** for new CA scope; host-side fetch then local custody; no credentials in repo | Often requires depository portal access / membership; may be paid or account-bound; **owner authorization + access method** required; no credentials in repo | Same as NSDL |
| Fit for empty-window proof | Weak unless a document asserts full-period coverage with no events | Weak for the same reason unless a dated extract claims completeness | Weak for the same reason |
| Fit for event reconciliation | Good when ratio/ex-date/symbol printed | Good for ISIN + event type; map to research ticker via identity records | Same |
| Known local holdings for CA completeness | **None** as dual-source completeness artefacts. Held items are membership/calendar circulars and NSE **API** CA JSON (API refused as completeness source) | **None** held for this programme | **None** held for this programme |

---

## Practical pairing options (recommendations only)

| Pair | Independence outlook | Main risk |
|---|---|---|
| NSE circular(s) + NSDL record(s) | High, if distinct bytes and proved coverage | Circular set may be incomplete for a long window |
| NSE circular(s) + CDSL record(s) | High, same caveats | Same |
| NSDL + CDSL | High if not mirrors | Both may omit exchange-only nuances; still need parseable ratios |
| Any provider + NSE API JSON | **Fails** ED-56 / R-3 | API never qualifies |

---

## Acquisition constraints (all three)

1. No download until owner authorizes provider class, symbol tranche, and windows.
2. `nse/` code path has no network access; custody is local after host-side acquisition.
3. Every file needs URL/circular id, retrieval date, size, SHA-256, and a coverage claim proved from the document.
4. Cost/access unknown until owner chooses providers; paid services need explicit approval.
5. Empty API responses already on disk are **not** empty-window proof under D66.

---

## Owner decision still required

Authorize (or decline) acquisition and name which two provider classes may serve as Source A and Source B for a first tranche. See `P0_CA_SOURCE_ACQUISITION_PROPOSAL.md` section 4.
