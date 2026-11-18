# Per-symbol eligibility architecture proposal

**Dated 2026-11-11. Proposal only. No eligibility code was changed.**

Branch `main`. HEAD `9e302df1a81c2b13696d8fab61f05d377481be2e`.

## What the code does now

Two different mechanisms are already separate.

1. Full-index label. `universe.limitations` returns `UNIVERSE_UNVERIFIED` when any member that day is unverified. `scanner.scan` puts that label on the scan. `reports.candidate_rows` copies it onto every candidate row so a CSV cannot hide it. It does not change another symbol's gate outcomes.

2. Per-symbol identity. `scan_symbol` returns `DATA_INSUFFICIENT` only when that symbol's own findings include an error, such as `ISIN_CHANGED_WITHOUT_RECORD`. GRASIM's unresolved ISIN does not put that error on INFY.

3. Per-period hash. `membership.convert` withholds a period's `source_sha256` when that period's own rows are not accepted, or when that period has an identity finding. A separate global rule also withholds every period while any used count exception is not accepted.

So an unresolved GRASIM identity blocks GRASIM's period and blocks full-index certification. It does not, by itself, make another constituent `DATA_INSUFFICIENT`. The eligibility matrix marked every member-date `EXCLUDED_MEMBERSHIP` because every review decision is blank, not because of GRASIM alone.

## Proposed distinction

Do not weaken a check. Add a reader. Do not change `qualification.evaluate_symbol`.

| Question | Rule |
|---|---|
| Is the full Nifty 100 certified that day? | No, if any member is unverified, a dummy seat is unresolved, or a count exception is unaccepted. Scan limitation stays `UNIVERSE_UNVERIFIED`. |
| Is this symbol's membership evidence accepted? | Only that symbol's in-force period, from its own start and end rows. |
| Is this symbol's identity resolved? | Only that symbol's `ISIN_CHANGED_WITHOUT_RECORD` or missing instrument record. |
| Can this symbol's price be researched? | Own EOD row, own corporate-action window, own price-scale breaks. Empty coverage stays manual. |

A reduced set of symbols that pass their own checks is an owner-named sample. It is not survivorship-controlled Nifty 100 research. The scan limitation must remain visible.

## Tests to add before any behaviour change

1. A universe with INFY verified and GRASIM unverified: the scan limitation contains `UNIVERSE_UNVERIFIED`, and INFY's symbol status is not `DATA_INSUFFICIENT` solely because GRASIM failed.
2. GRASIM's own input with `ISIN_CHANGED_WITHOUT_RECORD` is `DATA_INSUFFICIENT`.
3. One unaccepted count exception still withholds every period hash.
4. A helper that reports per-symbol membership does not clear the scan-level limitation.
5. No test may expect a reduced sample to be labelled survivorship-controlled.

No code change follows until this proposal is accepted.
