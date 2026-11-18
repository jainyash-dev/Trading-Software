# P0 corporate-action acquisition authorization request (Batch 8)

**Date:** 2026-11-15
**Status:** AWAITING OWNER. Nothing is authorized. D66 sets the standard and explicitly does not authorize acquisition.
**Inputs:** `P0_CA_SOURCE_ACQUISITION_PROPOSAL.md`, `P0_CA_PROVIDER_COMPARISON.md`, `P0_CA_SOURCE_FEASIBILITY_AUDIT.md`, `P0_CA_PILOT_RECOMMENDATION.md`, `P0_CA_PROVIDER_ACCESS_MATRIX.csv`.

## 1. What changed since the Batch 3 proposal

The Batch 3 proposal asked for authority over 85-164 symbols and 2016-2025 without a verified provider. Batch 7 verified the providers. The result: event evidence is feasible; **no provider is yet shown to prove window completeness**. Requesting a full tranche now would acquire files that cannot pass D66. This request is therefore a **pilot** only.

## 2. Request A: feasibility pilot (recommended)

| Field | Requested scope |
|---|---|
| Provider A | NSE, Futures & Options department adjustment circulars (`NSE/FAOP/<n>`), from `nsearchives.nseindia.com/content/circulars/` |
| Provider B | CDSL, DP communiques titled "DETAILS OF CORPORATE ACTIONS", from `www.cdslindia.com/eservices/Publications/Communique` |
| Independence evidence | Different institutions (exchange vs depository); different records (contract adjustment vs ISIN credit). **Disclosed limit:** depository record dates may derive from the exchange's confirmation (NSDL's checklist requires it; CDSL not checked). NSE/CMPT circulars are corroboration only (they implement the FAOP circular) |
| Symbols | TORNTPHARM, GAIL, HDFCBANK |
| Window | 2022-01-01 .. 2022-12-31 |
| Files | Step 0: 2-3 CDSL communiques around 2022-07-08 and 2022-09-06 (content check). Then, only if step 0 passes: all 2022 NSE/FAOP circulars (~150-200) and all 72 CDSL 2022 "DETAILS OF CORPORATE ACTIONS" communiques; F&O-membership evidence for the three symbols in 2022 |
| Event types | split, subdivision, consolidation, bonus, rights with terms, demerger, schemes with price effect; dividends recorded, not price-scale (R-12) |
| Retrieval | Host-side, normal browser session, outside `nse/`; no scripts inside `nse/`; no credentials stored |
| Formats | PDF as published; original bytes, never re-saved |
| Storage | `nse/data/corporate_actions/evidence/nse_faop/2022/`, `.../cdsl_dp/2022/`, `.../fo_tenure/` (new folders) |
| Provenance | Per file: URL, circular/communique number, retrieval date, method, byte size, SHA-256, coverage claim proved from the document; ledger `P0_CA_SOURCE_LEDGER.csv` |
| Cost | Free public pages only |
| Stop conditions | Login or payment requested; terms of use forbid download; step 0 fails |
| Expected limitations | Pilot proves at most 3 symbol-years; empty-window proof depends on the unverified FAOP sequence hypothesis; record-date independence is partial |

**Owner answer needed:** AUTHORIZE / DECLINE / AUTHORIZE WITH CHANGES (name the changes).

## 3. Request B: paid source (information only; not recommended yet)

BSE states a historical corporate-actions data product "since 2006" (search excerpt; page returned 403 to the reader). It is the only candidate seen that claims window coverage, and BSE is institutionally independent of NSE. It is paid (subscription). Under CLAUDE.md section 21.17, a paid service needs explicit owner authorization. **Owner answer needed (optional):** whether to obtain BSE's product terms, price and coverage documentation (an enquiry only, not a purchase).

## 4. Not requested

- NSDL: no public per-ISIN artefact found.
- NSE web CSV export of corporate actions: not independent of the refused API.
- Any 2016-2021 or 2023-2025 window, or any other symbol, until the pilot reports.

## 5. After authorization (what agents will and will not do)

Will: acquire exactly the authorized files, hash and ledger them, reconcile, write `gtf.ca_reconciliation.v1` records, prepare one approval request per qualifying window in `P0_CA_OWNER_APPROVAL_QUEUE.md`.
Will not: write `completeness.csv` rows that claim approval, write any `Completeness window accepted` marker, rebuild production outputs, or widen scope.
