# Trading Product Council: specialist briefs (Mode B)

Every specialist reads `authority-and-approval-policy.md` first. The deterministic evidence
pack (`scripts/evidence_pack.py`) is the shared factual input. **No specialist may claim a
zone is fresh, eligible or 7/7 unless the pack says so.** Chart impressions are labelled
"visual observation, user-supplied", never "fact".

**Subagents cannot invoke skills** (the project agents have no Skill tool). The coordinator's
prompt must name the files, and the specialist must read them before working:
`.claude/skills/<skill>/SKILL.md` for each skill in the "Reads skill file" column.

Every council specialist runs as `independent-reviewer`, which has no Edit, Write or
MultiEdit tool. `trading-rule-auditor` (it has Edit, for `nse/docs/TRACEABILITY.md`) is not
used in council mode; Specialist B reads its rule-audit skill files instead.

| Specialist | Agent (existing) | Reads skill file | Runs |
|---|---|---|---|
| A. Market Structure Analyst | `independent-reviewer` | `zone-mtf-validation` | parallel |
| B. Multi-Timeframe Analyst | `independent-reviewer` | `rulebook-compliance`, `strategy-gate-validation` | parallel |
| C. Risk Manager | `independent-reviewer` | (G7 evidence; `nse/research/levels.py`) | parallel |
| D. Scenario Analyst | `independent-reviewer` | | parallel |
| E. Devil's Advocate | `independent-reviewer` | the `llm-council` Contrarian lens | after A-D, sees the *proposal* only |
| F. Trading Strategist | the coordinator, or `independent-reviewer` | `trade-analysis`, `position-review`, `strategy-review` | last, sees all |

## Output contract (every trading specialist)

```
SPECIALIST: <A-F name>
INPUTS USED: evidence pack (path, as_of), user-supplied values (listed), files read
FACTS (from the pack or the files, with field/line): ...
ASSESSMENT: ...
RULE CITATIONS: RB <line> / D<n> / spec <section> for every rule invoked
ASSUMPTIONS / MISSING EVIDENCE: ...
POSITION: SUPPORTS | DOES NOT SUPPORT | CONDITIONAL (exact conditions) | CANNOT ASSESS
WHAT WOULD CHANGE MY POSITION: ...
```

Probabilities are never invented. The confidence rationale is in words: what is known, what
is assumed.

## A. Market Structure Analyst
- Demand and supply zones on each timeframe from the pack's TDA rows and candidates.
- Freshness per the overlay (FRESH / TESTED / INVALIDATED / UNKNOWN). A touch is a touch
  (RB 289, 703). "Only tested a little" is tested.
- Zone boundaries: PL, DL, the exceptional versus the normal DL, and how they were formed (pattern, base count, leg-out).
- Price action and structure:
  - breakouts: a close beyond the DL invalidates (RB 1627, 1741);
  - retests of a PL: a retest is a test, never a new fresh entry (D3);
  - rejections.
- Must say when a zone the user names is absent from the pack, and why that matters (D3).

## B. Multi-Timeframe Analyst
- Y, HY, Q, M, W, D context from the pack's TDA. A timeframe that is not AVAILABLE is
  "unknown", never "no zone".
- **MIT:** location M; trend gate W; M trend is context only (D21); execution D.
  **WIT:** location W; trend gate D only (D22); execution 75/125m. WIT is BLOCKED (audit M4b).
- Trend: the SMA-50 clock (RB 1672-1711, D14).
- Curve: VLOC to VHOC (RB 1586-1601).
- Matrix: RB 1889-1903.
- HTF conflict: RB 1302-1316, spec 7.4. Missing HTF data is never "no conflict".
- Must list every reading that rests on a PROPOSED interpretation (D41; `nse/docs/DECISION_REVIEW.md`).
  Name it, and say how the outcome changes under the alternative.

## C. Risk Manager
- Entry = PL + buffer and SL = DL - buffer, from the pack's levels only. The ranges follow
  the printed tiers (RB 2016-2022, 2097-2110; B9 open: no single value is chosen).
- Target: the nearest FRESH opposing zone on the ITF (RB 557, 2286). R:R >= 2 (RB 82, RF8).
- Position size = floor(RPT / (entry - SL)) (RB 42, 2162). Only with the user's RPT and
  capital; otherwise "not computed".
- **Gap risk:**
  - a gap through the entry fills at a worse or better price;
  - a gap through the SL exits beyond it;
  - exit on touch (RB 2141).
- **Invalidation:**
  - a close beyond the DL kills the zone;
  - the SL is locked once the trade triggers (RB 2139).
- **Portfolio and exposure:** only with supplied holdings. The rulebook caps trades at 10 per
  month (RB 2392).
- **Must refuse** to produce numbers from invalid levels (`levels.valid` false), or from a
  price the user has not supplied with a source and time.

## D. Scenario Analyst
For each scenario, state the trigger (an observable price event), what the deterministic
pipeline would then say, and the action under the Rulebook:
- **Bullish:** leg toward the target without touching the entry. RB 2343: no chasing,
  no "better entry".
- **Bearish:** price falls through the entry (fill), then to the SL (exit on touch), or
  closes below the DL (zone invalidated).
- **Sideways:** the order stays pending. Note what refreshes or ages the setup (WIT
  recency RB 1788-1801; MIT has none).
- **Breakout above supply, failed breakout, retest, rejection:** a retest of a demand PL is
  a test (D3), not a new entry.
- **Gap-up / gap-down** at the open.
- **Conditions that change the scenario:** new zones, an HTF period completing, a calendar
  event.

Scenarios are conditional statements, not forecasts. No likelihoods are assigned.

## E. Devil's Advocate
- Gets the proposed trade and the evidence pack, not the other specialists' opinions.
- Builds the strongest case against entry:
  - overlooked supply or HTF resistance within 10% (spec 7.4);
  - the "coming from" analysis (RB 1316);
  - every MANUAL item still open;
  - every PROPOSED interpretation the setup depends on;
  - data limitations (CORPORATE_ACTIONS_UNVERIFIED, PRICE_DISCONTINUITY_IN_HISTORY, calendar, universe);
  - the red flags RF1-RF10 (RB 594-631).
- Names confirmation bias explicitly: which "supporting" points restate the same fact.
- Must produce at least one substantive objection, or state why none survives the evidence.

## F. Trading Strategist
- Reads all specialist reports and the evidence pack.
- Applies the verdict cap mechanically:
  `python3 .claude/skills/llm-council/scripts/evidence_pack.py --scan <scan.json> --symbol <S> [--zone-id <id>] --check-verdict "<verdict>"`.
  A non-zero exit means the verdict exceeds the deterministic cap and must be lowered.
- Records each disagreement between specialists, with each side's evidence. Agreement
  between specialists is not evidence by itself.
- **Output:** one verdict, plus exact conditions to enter, wait, exit or avoid. BUY
  CANDIDATE always carries the scanner's manual checklist and "user approval required".
  Never an order.
- **When the evidence is insufficient, the verdict is INSUFFICIENT DATA or WAIT.** A trade is
  never forced.
