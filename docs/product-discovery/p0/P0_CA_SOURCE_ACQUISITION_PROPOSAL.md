# P0 Batch 3 - Corporate-action source acquisition proposal

**Status:** STOPPED AT OWNER AUTHORIZATION BOUNDARY  
**Date:** 2026-11-15  
**Governance:** D66 `USER_APPROVED` sets the acceptance standard but does **not** authorize acquiring any source (explicitly). D47/D55/D56 and later decisions must be re-read before any download. `nse/` has no network access by design.

No new sources were downloaded in this programme.

---

## 1. Existing evidence inspected first

| Held artefact | Role under D66 |
|---|---|
| `nse/data/corporate_actions/raw/ca_*.json` (202 files) | Saved NSE corporate-actions **API** bodies. Hash-verified custody for exploratory tier only. **Cannot** be Source A or Source B for completeness (ED-56 / R-3). |
| `coverage.csv` / `collection_log.jsonl` | Provenance of those API pulls |
| `actions.csv` | Parsed events from API subjects (not completeness proof) |
| `completeness.csv` | **Absent** |
| Reconciliation JSON (`gtf.ca_reconciliation.v1`) | **Absent** |
| Decision-log completeness markers | **0** |

Conclusion: new **non-API** official sources are required before any completeness window can be proposed for owner approval.

---

## 2. Proposed acquisition scope (for owner authorization)

### Symbols

Priority order:

1. All symbols with verified membership periods intersecting 2020-12-31..2025-12-31 (largest defensible set first).
2. Remaining Nifty 100 historical members in the same window.
3. Do not expand beyond Nifty 100 cash-equity research symbols without a separate decision.

Exact symbol list to authorize: the 164 symbols in `nifty100_universe.csv` (period union), optionally narrowed to the 85 currently verified-period symbols for a first tranche.

### Date windows

- Primary certification window: **2020-12-31 .. 2025-12-31** (D59).
- Optional warming / pre-history CA context: 2016-01-01 .. 2020-12-30 (does not create membership certification before D59).

Per-symbol windows may be split where listings start/end inside the range.

### Required event types

Price-affecting events the research stack must reconcile:

- Split / subdivision / consolidation
- Bonus
- Rights (with terms)
- Demerger / scheme with price effect
- Other ratio-bearing capital changes the parser can represent

Dividends may appear in sources but are not price-scale events for R-12. Unparsed price subjects on file today (including CGPOWER 2016-03-15, VBL 2024-09-12) need terms that the parser can represent or stay fail-closed.

### Official source providers (candidates; not pre-approved)

Owner must name which pair counts as independent official sources. Candidates to evaluate (not acquired here):

| Provider class | Example artefact | Notes |
|---|---|---|
| Exchange circular / CM notice PDFs | NSE CML / CMTR circulars naming ex-dates and ratios | Primary when they list the event |
| Exchange corporate-action bulk / historical extract (non-API file) | Official downloadable CA dataset if one exists with proved coverage window | Must not be a renamed copy of the saved API JSON |
| Depository (NSDL/CDSL) corporate-action records | ISIN-level CA notices | Useful for identity-linked events |
| Issuer filings (exchange-hosted) | Scheme / bonus / split notices | Terms; do not rewrite bhavcopy OHLC |

**Independence rule (D66/ED-56):** distinct SHA-256 hashes, distinct non-identical files, neither is a saved API response or API-shaped JSON. Two different hashes of the same bytes fail. A pair of API mirrors fails.

### Expected file formats

- PDF circulars / notices with extractable or inspectable tables
- CSV/XLS official extracts with symbol/ISIN, ex-date, event type, ratio
- JSON only if it is a documented non-API official dump (and fails API-shape detection)

### Provenance requirements

For every file:

1. Source URL or circular number
2. Retrieval date and method
3. Byte size
4. SHA-256
5. Coverage claim (symbol + from/to) proved from the document itself
6. Storage under `nse/data/corporate_actions/evidence/<provider>/` (proposed; not created until authorized)
7. Row in a future `completeness.csv` only after reconciliation + owner dual-hash marker

### Hashing procedure

```
shasum -a 256 <file>
```

Record in `sources.csv`-style ledger beside the bytes. Never overwrite an accepted raw file.

### Cost / access constraints

- Unknown until owner chooses providers.
- No paid data services without explicit owner authorization (master prompt section 21.17).
- No credentials in the repository.
- Acquisition must happen outside `nse/` network prohibition (host-side tooling), then files are placed into local custody.

---

## 3. Reconciliation procedure after acquisition (engineering; not approval)

For each candidate window:

1. Identify Source A and Source B
2. Establish independence
3. Preserve originals; hash both
4. Parse supported events
5. Normalize only documented equivalents
6. Event-by-event reconcile -> `gtf.ca_reconciliation.v1` record
7. Unresolved -> fail closed
8. Prepare owner marker line:
   `- **Completeness window accepted:** <sha_a> <sha_b> <recon_sha> <SYMBOL> <from>..<to>`
9. Owner writes the decision; agents do not invent markers

Empty window: both sources prove full-period coverage, both empty of events, recon has `empty_window: true`, hashes distinct, owner approves. Empty API `[]` never qualifies.

---

## 4. Owner decision requested

Please authorize (or decline) explicitly:

1. Whether acquisition may proceed.
2. Which two provider classes are acceptable as Source A / Source B.
3. Symbol tranche (85 verified-period symbols first vs all 164).
4. Date windows (D59 only vs also 2016-2020 context).
5. Storage path confirmation.
6. Any cost/paid-source limit.

Until that authorization exists, this programme will not download CA sources. Other independent work (membership packs, exception register, isolated dry-build with current evidence) continues.
