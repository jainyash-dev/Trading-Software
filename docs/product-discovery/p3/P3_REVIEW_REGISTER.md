# GTF P3 - Review register

| Finding ID | Batch | Reviewer | Severity | File / location | Finding | Evidence | Remediation | Retest | Disposition |
|---|---|---|---|---|---|---|---|---|---|
| P3-IR-01 | 9 | independent-reviewer | MEDIUM | `opportunity/lifecycle.py` | SHORTLISTED allowed while canonical BLOCKED/REJECTED/DATA_INSUFFICIENT | Transition map allowed UNDER_REVIEW→SHORTLISTED regardless of status | Refuse SHORTLISTED for non-qualifying canonical; strip from allowed_transitions | Opportunity unit + API tests OK | FIXED |
| P3-IR-02 | 9 | independent-reviewer | MEDIUM | `test_opportunity.py` | Watchlist delete did not assert opportunity survival | Delete only cleared watchlist tables | Assert opportunities and canonical_status unchanged after delete | `test_filters_and_watchlist_delete` OK | FIXED |
| P3-IR-03 | 9 | independent-reviewer | MEDIUM | `opportunities.test.tsx` | Analysis deep-link untested | Only disconnected copy checked | Vitest asserts `navigate("analysis", {scan,symbol,as_of,dataset_id,timeframe,zone})` | 48 web tests OK | FIXED |
| P3-IR-04 | 9 | independent-reviewer | MEDIUM | `docs/product-discovery/p3/*` | Tracker/matrix/certification incomplete | Docs still PENDING | Updated tracker, matrix, certification report | Docs package present | FIXED |
| P3-IR-05 | 9 | independent-reviewer | LOW | Opportunities detail panel | `source_snapshot` not shown in UI/types | API returns snapshot; UI omitted | Types + manual-checks note in detail panel | Build OK | FIXED |
| P3-IR-06 | 9 | independent-reviewer | LOW | Identity `(scan_key,symbol,zone_id)` | Null zone_id collapses multiple candidate-less rows | Unique index design | Accepted: one workflow row per symbol without zone is intentional for desk org | Documented | ACCEPTED |
| P3-IR-07 | 9 | independent-reviewer | LOW | Opportunities filters | No watchlist≠eligibility note on filter panel | Watchlists page had copy; Opportunities filter lacked it | Added filter disclaimer | Vitest asserts copy | FIXED |
| P3-IR-08 | 9 | independent-reviewer | INFO | opportunity package | Core invariants held | No second engine; authorises_order false; CERTIFIED refused | Keep as certification evidence | Platform 52 OK | CLOSED |
