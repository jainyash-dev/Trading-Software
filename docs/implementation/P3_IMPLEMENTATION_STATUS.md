# P3 Implementation Status - Opportunity Intelligence

**Date:** 2026-11-17 | **HEAD:** `69858d0` (unchanged) | **Verdict:** `P3_ACCEPTANCE_READY` (owner retains `ACCEPTED`)

Row-level detail: `P2_P4_ACCEPTANCE_MATRIX.md` section B (27 rows: 13 INDEPENDENT_REVIEWED, 4 VALIDATED,
5 TESTED, 2 DEFERRED_OWNER, 3 BLOCKED).

## Work done

| Item | Change | Evidence |
|---|---|---|
| P3-D / FR-3.4 / OI-002 "why nothing qualified" | `platform/web/src/features/scanner/model.ts` `scanOutcome` + `ScannerPage.tsx` panel. Distinguishes scanner UNAVAILABLE, stored FAILED, EMPTY, QUALIFIED, NOTHING_QUALIFIED, and lists stored reason classes: PARTIAL_SCAN (not-opened symbols are "unknown, not zero"), STALE_DATASET (scan dataset is not the current local dataset; only claimed when the dataset list loaded), EVIDENCE_MISSING, EVIDENCE_INCOMPLETE, CANDIDATES_REJECTED with deciding gates, NO_FRESH_ZONE, ZONES_BLOCKED, NOT_IN_UNIVERSE, COUNTS_DISAGREE. Every line cites stored statuses or gates; nothing is inferred. Job panel states that a FAILED/INTERRUPTED scan is not a zero-candidate scan. | vitest (9). BR-16 stored scan QUALIFIED; BR-17 real pipeline scan of WALK + missing NOPE: NOTHING_QUALIFIED with `EVIDENCE_MISSING ... NO_INPUT_FILE` and `ZONES_BLOCKED 8`. A scan with as_of beyond the data was refused 422 `DATA_INSUFFICIENT` (not an empty success). |
| **Defect fixed (FR-3.3 / FR-3.5 / OI-001)** | The Scanner page and its vitest fixtures read `symbol_status` / `candidate_status`, which no stored envelope has; the research reports emit `status` (as platform ingest and planning already read). Real scans therefore showed "Unavailable" statuses and the decision-status filter matched nothing. New `symbolStatusOf` / `candidateStatusOf` read `status` first, legacy names as fallback. | Found in browser (first run, BR-16 showed "Unavailable"). vitest canonical-key regression (3). |
| **Defect fixed (P3-R08)** | `opportunity/ingest.py` read `timeframe`; canonical keys are candidate `execution_tf` and zone `tf`, so every real opportunity had a null timeframe. Canonical keys first, old keys as fallback. | Found in browser (BR-18 TF "Unavailable"). `test_ingest_reads_canonical_keys_from_real_scanner_output` uses real `scanner.scan` output. |

## Verified, unchanged

- **Qualification authority (P3-A):** opportunities, scanner and outcome panel read stored envelopes; no
  frontend gate evaluation (reviewer confirmed).
- **Lifecycle (P3-B):** the canonical desk lifecycle is `opportunity/lifecycle.py` (DISCOVERED, UNDER_REVIEW,
  SHORTLISTED, REJECTED, EXPIRED, BLOCKED, ARCHIVED). There is no approved APPROACHING state; none was invented.
  FIXTURE-sourced rows start BLOCKED by design (`initial_workflow`), seen in BR-18. Transitions tested in
  `test_opportunity.py`; not clicked through in the browser.
- **MTF alignment (P3-C):** stored overlay statuses only; covered by `run_all` zone/MTF groups; no change.
- **Watchlists / history (P3-G/H):** BR-19 create + persist after reload, BR-23 rename persists; BR-20 history
  lists both scans; stored envelopes reopen unchanged.
- **Certification honesty (P3-J):** FIXTURE labels everywhere in BR-16..18; no CERTIFIED text; P0 certified
  symbol-dates remain 0.

## Owner-deferred / blocked

- **OI-007 / P3-R15** analogue matcher: `DEFERRED_OWNER` (Decision 3). Not implemented; no substitute.
- **D6 sector filter:** `BLOCKED`. D6 is `USER_APPROVED`: sector not evaluated, no proxy. No sector source.
- **Alerts:** `BLOCKED` beyond the existing research scan-diff alerts; no external delivery or paid provider.
- **Certified discovery (P3-R12/R13):** `BLOCKED` by P0/D66.

## Limitations

- OI-006 comparison is the capability map's "Yes, degraded" CLI `explain` compare; no product screen.
- FR-3.2 scheduler, FR-3.6 search, FR-3.8 scan configs: automated tests only in this programme.
- The browser scan run was submitted through the API from the browser session, not the scan form.
- Stored DATA_INSUFFICIENT reasons can contain local file paths (e.g. `NO_INPUT_FILE`), shown as stored.
