# Authority and Approval Policy

## Authority Hierarchy

1. Explicit user instructions and project safety boundaries.
2. Protected Rulebook and approved decision register.
3. Deterministic, tested program outputs and data-quality gates.
4. Verified external evidence and reproducible research.
5. Council reasoning and model-generated hypotheses.

The council cannot override a higher authority with consensus or persuasive language.
This list does not replace the governance precedence in `gtf-autonomous-project-lead`
sections 3 and 6. The council does not decide eligibility. Risk R-5 remains unresolved.

## Trading Safeguards

- Fresh demand zones only are eligible for long-entry consideration.
- Tested, invalidated, or unknown-freshness zones are not eligible.
- Scanner decisions must use `MtfSnapshot.eligible_after_overlay(timeframe)`.
- Never bypass the overlay using raw `EngineResult.eligible`.
- AI may explain or challenge evidence but cannot override deterministic eligibility.
- Distinguish:
  - BUY CANDIDATE
  - WAIT
  - AVOID
  - EXIT, only with position context and only on the Rulebook exit conditions below
  - INSUFFICIENT DATA
- REDUCE is not an action. It has no Rulebook basis. Do not recommend it.
- Do not invent live prices, volume, corporate actions, probabilities, fills, or performance.
- No broker connection, order placement, or execution.

## Repository Safeguards

- Preserve all uncommitted work.
- Inspect `git status` before edits.
- Do not commit, push, reset, clean, rebase, or discard user changes.
- Do not modify protected files without explicit approval:

  - `nse/sources/Demand&Supply Indicator.pine`
  - `nse/sources/Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md`

- Do not download market data, change data sources, or incur costs without explicit approval.
- Run relevant tests and report exact commands/results.
- Never claim tests passed unless actually run.
## Decision Register

- `nse/docs/DECISION_LOG.md`: `USER_APPROVED` decisions are authoritative within their recorded scope. `USER_STATED` entries are recorded operating constraints within their wording. They are not methodology changes and are not reclassified as `USER_APPROVED`. `PROPOSED` is not a rule. Read the log through its last heading.
- `nse/docs/DECISION_REGISTER.md` and `nse/docs/DECISION_REVIEW.md` list open items.
  D40 and D41 readings not covered by an approval in the register stay unresolved until
  the user approves them, even when the council agrees with a recommendation. R1-R6 are
  `USER_APPROVED` and authoritative; do not describe them as proposed.
- The council may cite a recommended default but must label it "PROPOSED, not approved".

## Deterministic Verdict Cap (Mode B, Trading Product Council)

The scanner's status for the zone caps the council's verdict. The council may weaken it,
never strengthen it. `scripts/evidence_pack.py --check-verdict` enforces this mechanically.

| Deterministic result | Strongest allowed verdict |
|---|---|
| ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING | BUY CANDIDATE (user approval required; manual checklist attached) |
| MANUAL_REVIEW | WAIT (the open manual items are listed) |
| REJECTED | AVOID |
| DATA_INSUFFICIENT, or symbol BLOCKED (e.g. WIT) with or without a zone named | INSUFFICIENT DATA |
| Zone not a candidate (tested, invalidated, below 7/7, never formed) | AVOID |
| No scan for the symbol, or no verified data | INSUFFICIENT DATA |

An attractive R:R, a strong chart impression or unanimous specialists never raise the cap.

## Position rules (EXIT)

These verdicts apply only with position details: symbol, entry date and price, SL, target,
quantity, and a price with its source and timestamp.

- **EXIT:**
  - the SL was touched (RB 2141 "Exit on TOUCH, not on CLOSE");
  - the target was reached;
  - a pre-planned Weekly Demand Trailing stop was touched (RB 2327, 2345).
- **No other early exit is a Rulebook action.** RB 2343: "Once your order executes, the trade
  runs to either the full Target or the full Stop Loss. There is no break-even exit."
- **REDUCE** (a partial exit) has no Rulebook basis. The council does not recommend it; it
  may report that the user would be departing from the plan.
- **SL is locked** after the trigger (RB 2139). The council never suggests moving it. Weekly
  trailing is reference only and not automated (D9).

## Independence and Evidence

- Specialists are separate subagents with separate context. They are the same underlying
  model, so their agreement is not independent confirmation.
- Only cited, reproducible evidence counts: file:line, a command and its output, a
  scan.json field, a Rulebook line.
- "N specialists agree" never upgrades a finding, a verdict or an approval.
- Majority agreement is never proof of a fact. The chair checks every disputed or
  reviewer-"verified" material claim against primary evidence and corrects a refuted claim
  even when most reviewers agreed (`peer-review-protocol.md` 12-17).
- If specialists ran in one context, label the report "single-context review: specialists
  not independent".
