# P0 identity blocker decisions - OD-ID-1 / OD-ID-2

**Date:** 2026-11-15  
**Rule:** Do not join ISIN histories when two authentic official dates remain. Agents do not invent an effective session.  
**Notices held (not newly downloaded):**

| File | SHA-256 |
|---|---|
| `nse/data/universe/evidence/identity/isin_notices/msei_bajfinance_4496_2016.pdf` | `11b2a619b064c270d04a3fedc14633317d0a87959a212f98dad5349ad14babc5` |
| `nse/data/universe/evidence/identity/isin_notices/msei_grasim_4581_2016.pdf` | `974296c5ad548d0f69e686af4cdb36d04e2472c7dc486a6ea68144d50ea2511d` |

---

## OD-ID-1 - BAJFINANCE

### Problem (verified)

- Change: `INE296A01016` -> `INE296A01024`.
- Held MSEI circular MSEI/LIST/4496/2016 states **both** 8 and 9 September 2016 as effective wording (two dates).
- Instrument records keep the history **unjoined**; `identity_report.json` lists this change under `isin_changes_unevidenced`.
- Bhavcopy observation: last old / first new around 2016-09-08 / 2016-09-09 (report metadata), which does **not** choose the legal effective session for a join.

### Affected periods (research window)

| Item | Value |
|---|---|
| Universe periods | `2020-12-31..2025-06-15` ISIN `INE296A01024` (UNVERIFIED membership); `2025-06-16..open` ISIN `INE296A01032` (UNVERIFIED; backlog G-I-2025-06-16 deferred) |
| Isolated matrix (1.6.0) | **1234** BAJFINANCE member-dates; identity `UNKNOWN_INSTRUMENT` **1098**, `RESOLVED` **136**; all `EXCLUDED_MEMBERSHIP` |
| Prior board estimate | ~1098 member-dates blocked by unresolved join through 2025-06-15 |
| Baseline ledger row | `baseline:BAJFINANCE:INE296A01024` still blank (batch 1 left GRASIM/BAJFINANCE blank) |

### Missing evidence

One official notice (NSE CM, depository CA, or clarifying MSEI/NSE text) that states **a single effective session** for the 2016 ISIN change.

### Exact owner decision required

Choose one:

1. **Keep unjoined** (default fail-closed; no agent join) - continue UNKNOWN_INSTRUMENT on ambiguous dates; or  
2. Name **one** effective session date and the authoritative document that supports it (then engineering can add a verified ISIN_CHANGE record citing that document - still requires that evidence on disk).

Membership acceptance of the baseline row is a **separate** decision and does not resolve OD-ID-1.

---

## OD-ID-2 - GRASIM

### Problem (verified)

- Change: `INE047A01013` -> `INE047A01021`.
- Held MSEI circular MSEI/LIST/4581/2016 states **both** 6 and 7 October 2016.
- Unjoined in instrument records; listed in `isin_changes_unevidenced`.
- Observation metadata: last old / first new around 2016-10-06 / 2016-10-07 - not a join decision.

### Affected periods (research window)

| Item | Value |
|---|---|
| Universe periods | Single period `2020-12-31..open` ISIN `INE047A01021` (UNVERIFIED membership / source hash withheld) |
| Isolated matrix (1.6.0) | **1234** GRASIM member-dates; identity `UNKNOWN_INSTRUMENT` **1234**; all `EXCLUDED_MEMBERSHIP` |
| Prior board estimate | ~1234 member-dates |
| Baseline ledger row | `baseline:GRASIM:INE047A01021` still blank |

### Missing evidence

One official notice with **a single effective session** for the October 2016 ISIN change.

### Exact owner decision required

Same shape as OD-ID-1: keep unjoined, or name one effective session backed by a document to hold locally.

---

## Related (not OD-ID-1/2)

| Item | Status |
|---|---|
| YESBANK `INE528G01027` -> `INE528G01035` | OD-ID-3 recorded via NSE/CML/43833; not part of this decision request |
| Dummy seats | OD-MEM-2/3 - non-tradable; separate from ISIN join |

---

## Stop

No joins were performed. No ledger identity decisions were written.
