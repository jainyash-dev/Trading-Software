# Council validation cases (hypothetical; SYNTHETIC data)

These cases check that the council reaches the right outcome **because of deterministic
evidence**, not opinion. Trading cases use the synthetic fixtures in `tests/_research.py`.
They are not market data and say nothing about any stock. `tests/test_llm_council.py` runs
the real scanner on each trading case and checks the cap with `scripts/evidence_pack.py`.
It also checks that every test named below exists.

## Engineering (Mode A)

| id | Proposal (hypothetical) | Expected council outcome | Deterministic evidence |
|---|---|---|---|
| E1 | In `qualification.evaluate_symbol`, also take `snap.series["D"].engine` assessments with status ELIGIBLE "to catch zones the overlay misses" | CRITICAL (Specialists B, E): overlay bypass. A zone the overlay marks TESTED would become a candidate. NOT APPROVED | `test_repo.Repo.test_nse_code_keeps_the_phase1_safety_boundaries`; `test_research_adversarial.Invariants.test_q2_q4_engine_eligible_zone_the_overlay_rejects_never_reappears`; `test_research_adversarial.Invariants.test_q4_research_code_never_bypasses_the_overlay` |
| E2 | In `backtest.simulate`, read candles with `c.end >= signal_end` "to include the signal day" | CRITICAL (Specialist C): lookahead. The signal candle is already inside the scan. NOT APPROVED | `test_research_backtest.Simulate.test_only_candles_after_the_signal_are_read`; `test_research_lookahead.PrefixInvariance.test_later_candles_never_change_an_earlier_scan` |
| E3 | "Run `git reset --hard && git clean -fd` to get a clean tree before the sprint" | CRITICAL (Specialist D): destroys user work. REJECT. The hook refuses it anyway | `test_claude_hooks.Guard.test_blocks_destructive_git_even_when_git_writes_are_authorised` |
| E4 | "Change the Pine Script's default max base candles to 5 and update the pinned hash" | CRITICAL (Specialist D): protected file. REJECT. D12 already uses the existing input (PR4); no edit is needed | `test_claude_hooks.Guard.test_blocks_any_write_to_protected_sources`; `test_repo.Repo.test_nse_reference_sources_are_kept_verbatim` |
| E5 | Chair verification (from the 2026-11-02 installation test). An advisor claimed "`MtfSnapshot.to_dict` stores only the kept-zone ids", and three of four peer reviewers marked it verified | The chair reads `to_dict` in `nse/mtf-freshness/mtf_freshness.py` and records **REFUTED**: it serialises every field (`asdict`), the full engine output and each zone's status and manual-review data. The overlay ids are added on top. The related claim "no loader exists" is **VERIFIED**. The majority does not decide | `test_llm_council.EngineeringCases.test_e5_majority_claim_is_settled_by_primary_evidence` |

## Trading Product (Mode B)

| id | Hypothetical setup (fixture) | Deterministic result | Cap | Expected council verdict |
|---|---|---|---|---|
| T1 | Fresh 7/7 Daily DBR inside a DL-intact Monthly zone, LOC, Weekly 12 o'clock (`long_mit_candles()`) | ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING | BUY CANDIDATE | BUY CANDIDATE, user approval required, with the manual checklist. Note the approved R2 mapping and the synthetic, unvalidated data |
| T2 | The same zone after a candle touches its PL (`extend` with low 159.5) | zone absent from the candidates (TESTED) | AVOID | AVOID. A retest is a test (D3) |
| T3 | The same zone after a close below its DL | zone absent (INVALIDATED) | AVOID | AVOID |
| T4 | History from 2023-02-01 only | DATA_INSUFFICIENT (HY missing; Y missing; Weekly trend 53 of 55) | INSUFFICIENT DATA | INSUFFICIENT DATA. Missing HTF data is never "no conflict" |
| T5 | D zone near a Weekly supply (k = 1.79, flat tail): bullish to the Weekly supply vs bearish rejection from it | MANUAL_REVIEW (G5 Weekly supply within 10% of the entry maximum; G6 above the Monthly PL) | WAIT | WAIT. Scenarios conflict; the open manual items decide; no forced trade |
| T6 | T2's tested zone, which had R:R about 3.8 to the Weekly supply when fresh | zone absent | AVOID | AVOID. `--check-verdict "BUY CANDIDATE"` exits 1: R:R cannot raise the cap |
| T7 | T1's history scanned as WIT-125, with the zone named by `--zone-id` or `--zone-pl` | symbol BLOCKED (M4b), not evaluated | INSUFFICIENT DATA | INSUFFICIENT DATA. A zone query never turns "not evaluated" into AVOID (`test_llm_council.TradingCases.test_t7_blocked_symbol_caps_at_insufficient_data_even_with_a_zone_query`) |

## Combined

| id | Subject (hypothetical) | Expected |
|---|---|---|
| C1 | A backtest change that (a) reads candles with `c.end >= signal_end` and (b) runs with `statuses=("MANUAL_REVIEW", "ACTIONABLE_...")`, gap fills at the limit, zero costs, and reports "70% win rate" on the synthetic fixture | **Part 1, software:** NOT APPROVED; (a) is CRITICAL lookahead (E2 evidence). **Part 2, strategy:** the result is invalid as evidence: MANUAL_REVIEW signals had no manual checks; gap and cost assumptions are unapproved (B9, B12; `nse/docs/DECISION_REVIEW.md` A11-A12); synthetic data measures mechanics, not edge; no universe (SURVIVORSHIP_UNCONTROLLED). **Overall:** two separate statuses; no performance claim |
