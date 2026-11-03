# Release readiness (2026-11-02)

Per-capability states come from `python3 -m nse.research.cli readiness` (29 capabilities);
none claims reference or external validation it does not have.

## Separate readiness dimensions

| Dimension | State | Evidence |
|---|---|---|
| Implementation completeness (planned MIT software) | High: every MIT module in the product plan exists except news, fundamentals, sector evaluation, external alert delivery, UDiFF parsing and a paper-trading loop | `IMPLEMENTATION_REPORT.md` |
| Automated tests | 992 pass, 0 fail, 0 skipped (normal and acceptance runs) | `TESTING_REPORT.md` |
| Data completeness | Low: 62 of 494 sessions for 2022-2023; nothing for 2016-2021 or 2024-2026; no constituents, corporate actions or UDiFF | `DATA_ACQUISITION_REPORT.md` |
| Methodology compliance | R1-R6 implemented; rulebook audit found no false-positive path; several rules stay MANUAL by design | `METHODOLOGY_TRACEABILITY.md` |
| External chart validation | None | B8, B10 |
| Backtest validation | None: no run on real history; needs B9, B11, B12 and data | - |
| Operational readiness | Local CLI usable end to end on real files; no scheduler installed; no external alerting | real-data run 2022-03-31 |

## Acceptance criteria (prompt Part 17)

| Criterion | State |
|---|---|
| Rulebook mapped to deterministic rules | PARTIAL (gaps listed in METHODOLOGY_TRACEABILITY) |
| R1-R6 implemented and tested | COMPLETE |
| Freshness / invalidation enforced | COMPLETE (synthetic evidence) |
| MTF calculations verified | PARTIAL (synthetic only; B8) |
| Coinciding / Aggressive | COMPLETE / PARTIAL (Aggressive MANUAL) |
| Trend and curve | COMPLETE (synthetic) |
| Qualification matrix | COMPLETE for long rows; unlisted cells MANUAL |
| Critical red flags | PARTIAL (RF1-3, 6-8 automated; RF4, 5, 9, 10 checklist) |
| Risk and position sizing; 2:1 | COMPLETE |
| Rejection reasons explainable | COMPLETE (explain, reports, dashboard) |
| Ten-year EOD acquisition architecture | COMPLETE (offline); data BLOCKED on owner downloads |
| Verified format adapters | PARTIAL (legacy only; UDiFF BLOCKED, B18) |
| Resumable backfill; validation; daily updates | COMPLETE |
| Historical membership | PARTIAL (loader; data BLOCKED, B11) |
| Corporate actions; raw/adjusted separation | PARTIAL (records interface, detection; no adjustment, B7) |
| Data-quality reporting | COMPLETE |
| Full-universe scanner | COMPLETE (needs constituent file to be verified) |
| Historical replay; decision replay | COMPLETE |
| Scenario library | COMPLETE (19 synthetic) |
| Backtest engine; out-of-sample; walk-forward; metrics | COMPLETE (software); not run on real data |
| Reproducible reports | COMPLETE |
| Dashboard; stock pages; scanner results; explanations | COMPLETE (static HTML) |
| Watchlists; alert infrastructure | COMPLETE (local delivery only) |
| CLI and API | CLI COMPLETE; no HTTP API |
| Existing work preserved; no unauthorised git changes; protected files unchanged | COMPLETE (see AGENT_EXECUTION_REPORT git comparison) |
| Database migrations verified | COMPLETE (SQLite store) |
| Security reviewed | COMPLETE (internal review; no external audit) |

## Final classification

**Integrated research platform.** Not historical-data-ready (data coverage), not
backtest-validated, not paper-trading-ready, not live-trading-ready.
