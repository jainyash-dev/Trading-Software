# P0 D66 source discovery and qualification report (V3)

**Date:** 2026-11-15
**Result: D66 remains BLOCKED. No qualified independent source pair exists for any event class or window.** D66 is unchanged. No completeness window, `completeness.csv` row or approval marker was created.
**Files:** `P0_D66_SOURCE_QUALIFICATION_MATRIX.csv` (13 rows: source x event class), `P0_D66_REMAINING_GAPS.csv`, `P0_CA_EVENT_REGISTER_V3.csv`, `P0_CA_RECONCILIATION_V3.csv`, `P0_D66_WINDOW_APPROVAL_QUEUE.csv`, `P0_CA_SOURCE_LEDGER.csv` (13 held documents with provenance).

## 1. What the population needs

From NSE's own records (`actions.csv`; not completeness evidence) for the 164 member symbols in 2020-12-31..2025-12-31:

| Need | Count | Member-dates |
|---|---|---|
| Symbols with at least one non-dividend event: each event needs two independent official records, reconciled | 49 symbols, 60 events (29 bonus, 15 split, 8 demerger, 6 rights, 2 unparsed) | 41,006 |
| Symbols with no recorded event: each window needs two independent sources that **prove** no event | 115 symbols | 82,772 |
| **Total blocked by D66** | 164 | **123,778** |

## 2. Sources examined this cycle

| Source | What was checked | Result |
|---|---|---|
| **BSE** (Q2, enquiry only) | Public product pages: `www.bseindia.com/market_data_products.html` and `corporates/corporate_act.aspx` return one identical 16,912-byte JavaScript shell to a plain request (client-rendered; no content). BSE's internal APIs were not probed. Official **tariff sheet** retrieved (SHA-256 `874a58e5...`, Last-Modified 2025-11-11): corporate actions are sold as "Corporate Action via Internet" INR 6,00,000/yr (continuous) or 5,00,000/yr (EOD), and "via SWIFT" INR 12,00,000/yr, excluding taxes. A "historical data" repository is described without coverage terms | **Paid**. No statement of window completeness, zero-event proof, provenance or upstream sources was found in public material. An enquiry needs a channel: no BSE contact address was found in the material read, and no outbound message was sent (no authorised mail channel in this session). **Status UNKNOWN / purchase required -> owner** |
| **CDSL** | Communique index re-analysed: 586 "Details of Corporate Action(s)" communiques since 2016 and **no** bonus or allotment series. Pilot (3 notices): ISIN-changing sub-divisions only | **NOT_QUALIFIED for bonuses.** For ISIN-changing splits, CDSL is a candidate (different institution; old/new ISIN, ratio, record and effective dates), but coverage of every ISIN change is untested. Testing it needs notices for other symbols, which is outside the pilot authorization |
| **NSE CML / FAOP** | Change-in-ISIN, Face Value Split, Listing of further issues, F&O adjustment circulars | Same institution as the NSE data. Never an independent pair (owner Q1). Corroboration only |
| **Issuer documents** | CGCEL Information Memorandum (2016-05-06, NSE-hosted) | Gives event terms (entitlement 1:1). One document per event; never proves a window |
| **NSDL** | Batch 7 | Inaccessible; no public per-ISIN record |

## 3. Pair qualification

| Proposed pair | Publisher independence | Upstream independence | Event overlap | Zero-event support | Result |
|---|---|---|---|---|---|
| NSE (any) + NSE (any) | No | No | - | - | NOT_QUALIFIED |
| NSE CML (Change in ISIN) + CDSL DP | Yes | Not established (issuer intimation to both; depository record dates may derive from exchange confirmations) | ISIN-changing splits only | No | **UNKNOWN** for splits; NOT_QUALIFIED for bonus, rights, demerger, zero-event windows |
| NSE + BSE product | Yes (separate exchanges) | Not established (both receive issuer intimations) | Presumed all classes (unverified) | Unknown | UNKNOWN (paid, not inspected) |
| NSE + issuer document | Partly | Issuer is the upstream of both | Per event | No | Event terms only; cannot prove windows |

## 4. Conclusion

- Different hashes do not establish independence, and no pair here demonstrates independence and completeness.
- The smallest additional evidence that could move any class:
  1. **Splits:** an owner-authorised CDSL coverage test on the 15 known in-window splits (free; retrieval of about 15-30 specific notices).
  2. **All classes and zero-event windows:** a BSE product, only if its documentation proves window coverage. Paid, so it needs owner authorisation. Even then, issuer-upstream dependence must be judged by the owner under D66.
- Without one of these, D66 stays blocked for all 123,778 member-dates. Engineering cannot clear this.
