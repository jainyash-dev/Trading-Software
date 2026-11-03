# Methodology traceability (summary)

The full rule-to-code-to-test matrix is `nse/docs/TRACEABILITY.md` (rows 1-50 and the gate
summary). This page is the release-level view.

## Sources and precedence

1. Trading Rulebook (protected Markdown, cited as `RB n`). The root PDF is a different
   revision (RB-VERSION-1): it lacks RB 1784 and RB 1786-1803. No MIT gate cites those lines
   (audit confirmed); only WIT G1 recency does, and WIT is BLOCKED.
2. Owner-approved decisions: D1-D39, R1-R6 (`DECISION_LOG.md`, `DECISION_REGISTER.md`).
3. Pine Script where the Rulebook is silent (D12).
4. Engineering readings: D41 (PROPOSED), P-* items; every one restricts or is labelled.

No GTF fallback rule (`INFERRED_GTF`) was introduced: every case reviewed this session was
covered by the Rulebook, an approved decision, or a MANUAL / owner-decision state.

## Approved M1 decisions

| ID | Implementation | Tests |
|---|---|---|
| R1 CMP-only curve | `qualification._g3`, `structure.positions` | G3, e2e |
| R2 Extreme Up -> STRONG_UP, label kept | `trend.READINGS` | trend, report |
| R3 Coinciding = actual range overlap | `structure.coinciding`, `_g6` | G6 overlap / boundary |
| R4 DL close invalidates; SL hit separate | Zone Engine, overlay, backtest, journal | invalidation, backtest, store |
| R5 HOC outcomes | `matrix_long`, `_g3`, `_g8` | matrix, scenario `mit_hoc_strong_up_rejected` |
| R6 Known absence = Standard | `_g6` | G6, G3 |

## Gates G0-G8

Implemented in `nse/research/qualification.py`; status precedence in `models.derive_status`.
Each gate returns PASS, FAIL, MANUAL, DATA_INSUFFICIENT, BLOCKED or NOT_EVALUATED with
reasons, evidence and sources. Coverage per gate: `TRACEABILITY.md` gate summary.

## Added this session

- Risk (RB 37-99, 2135-2214, 2388-2408): `risk.py`; the stage-band FAIL is a labelled
  reading (P-RISK-1, owner decision).
- X/14 display (RB 846-1033; spec 5.1, 5.3): `confluence.py`, information only.
- Backtest portfolio rules (RB 2392-2415): owner options, recorded limitations (B12-CAP).
- Journal constraints (RB 2139, 2140, 2380, 2385, 2392; R4): `store.py`.

## Known gaps in methodology coverage

| Rule | State |
|---|---|
| Sector support (RB 484-499, 851-895) | Not evaluated (D6); always MANUAL where it matters |
| RSI / Stochastic (RB 574-583, 965-987) | Not evaluated pre-entry (spec 5.1) |
| Aggressive entry conditions (RB 1843-1847, 1854-1855) | G6 MANUAL |
| Confirmation Entry, 6/7 override, RF3 override, LOTL, ATA | Not automated (spec 2 item 11) |
| Wick-to-Wick marking; drop timeframe in a 6+ base mess | Not implemented (TRACEABILITY 35) |
| Weekly trailing stop | Reference only (D9) |
| WIT rules | BLOCKED (M4b) |
