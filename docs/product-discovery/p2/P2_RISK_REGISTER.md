# P2 Risk Register

| ID | Risk | Severity | Mitigation / disposition |
|---|---|---|---|
| R-P2-1 | Exploratory data mistaken for certified | High | `data_quality.certified=false`; research_use labels; UI banner |
| R-P2-2 | Missing volume drawn as zero | High | Fixed: null volume; prepareSeries accepts null |
| R-P2-3 | Frontend invents zone freshness | Critical | Candidates/blocked: unknown→UNKNOWN. fresh_zones: D3 list contract may imply FRESH (documented) |
| R-P2-11 | last_scan as_of/dataset fallback desync | Medium | Closed: resolve missing as_of/dataset from the URL scan envelope only (P2-IR-2) |
| R-P2-4 | Direct nse.eod import from candles | High | Fixed: use `nse.research.deps` |
| R-P2-5 | Standalone chart without scan | Medium | OD-P2-1 deferred; FR-4.5 scan-linked kept |
| R-P2-6 | W/M volume misleading | Medium | Explicit `VOLUME_NOT_AGGREGATED_FOR_HTF`; volumes null |
| R-P2-7 | Dirty concurrent working tree | Medium | P2 edits limited to platform + p2 docs; no commit |
| R-P2-8 | Drag edit race / failed PATCH | Low | Error surfaced; local state still updates |
| R-P2-9 | Docs-health P1 broken transcript link | Low | Pre-existing; not a P2 blocker |
| R-P2-10 | Full visual screenshot suite not automated | Low | Accepted limitation for Batch 7 |
