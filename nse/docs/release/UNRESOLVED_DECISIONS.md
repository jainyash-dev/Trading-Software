# Unresolved decisions and their safe handling (2026-11-02)

> Dated snapshot (2026-11-02). Current status: `docs/MILESTONE_STATUS.md`, `nse/docs/DECISION_LOG.md` (section 1F, 2026-11-08 approvals) and `docs/ARCHITECTURE.md`.

Exact texts and alternatives: `nse/docs/DECISION_REGISTER.md`. Nothing here is approved by
being listed. Each item's current behaviour only restricts or is labelled.

## Owner decisions (trading methodology)

| ID | Question | Current safe behaviour | Affects |
|---|---|---|---|
| RB-VERSION-1 | Which Rulebook revision (PDF or Markdown) is authoritative? | Code cites the Markdown; both hash-pinned | WIT G1 recency source only |
| P-LOC-2 | Price inside a tested HTF demand: VLOC, or redraw? | G3 MANUAL | G3 |
| P-RISK-1 | RPT above the stage band (or > 2% undeclared): FAIL or MANUAL? | FAIL in the risk plan (never a gate) | Risk plan |
| B12-CAP | Backtest cap: count at placement or fill? Allow caps above 10? | Fill; > 10 allowed and labelled | Backtest |
| D41 (rest) | Research-pipeline readings other than R1-R6 | PROPOSED; each restricts | Several gates |
| Aggressive criteria | When an Aggressive setup qualifies (RB 1843-1847) | G6 MANUAL | G6 |
| Sector rules | Whether and how to evaluate sector support (D6) | MANUAL wherever needed | G4 matrix rows, HOC |
| M4b | 75/125-minute session and gap design | WIT BLOCKED | WIT |

## Owner decisions (engineering / execution)

| ID | Question | Current safe behaviour |
|---|---|---|
| B9 | Buffer choice within printed tiers for backtests | Ranges; backtest needs an explicit choice |
| B12 | Fill, same-bar, expiry, cost, slippage model | Backtest refuses to run without every field |
| D40 | Accept the inferred 20 Jan 2024 session hours? | Calendar uses it; PROPOSED |
| Instruments | Confirm record semantics (inclusive dates, ISIN_CHANGE carries the new ISIN, merger is not a rename) | Documented in `instruments.py` |

## Evidence needed (external)

| ID | Evidence | Unblocks |
|---|---|---|
| EOD range | Missing legacy sessions; UDiFF sample (B18) | Real-data G3-G7, history sufficiency |
| B7 | Corporate-action records | Removing CORPORATE_ACTIONS_UNVERIFIED |
| B11 | Nifty 100 constituent history | Point-in-time universe; survivorship control |
| B8, B10, B17 | TradingView references for HTF candles, zones, calendar | Reference and external validation |
| B6, B15 | Intraday source and depth | WIT |

## Engineering limitations recorded (no decision needed to proceed)

- Backtest: a trade open at the end of data can be counted as excluded by a later
  price-scale event, and incomplete bars after a signal are skipped silently (counts only).
- Alerts: ids include as_of but not configuration; two configurations at one as_of share ids.
- Dashboard charts draw the last 180 completed candles per timeframe.
