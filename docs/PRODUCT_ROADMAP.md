# Product roadmap

> The owner ran a foundation milestone (repository Master Prompt 0) and then the data
> milestone (Master Prompt 1/8). On 2026-11-09 the owner issued a separate fourteen-prompt
> series for the desktop product. That series is specified in
> [docs/product/MASTER_PROMPT_ROADMAP.md](product/MASTER_PROMPT_ROADMAP.md). The candidate
> table below remains a PROPOSED blocker order for data and research evidence. It is not
> a second product plan.
> Status per milestone: `docs/MILESTONE_STATUS.md`. Evidence blockers:
> `nse/docs/IMPLEMENTATION_BLOCKERS.md`.

## Product objective

A dependable NSE research and decision-support platform for the owner's GTF
demand-and-supply methodology: point-in-time data, deterministic zone eligibility, G0-G8
qualification, explainable candidates, reproducible research and honest validation.
The owner trades manually (B12: Kite / GTT); the platform never places orders.

## Milestones

| # | Milestone | Defined by | Objective | Exit evidence |
|---|---|---|---|---|
| MP0 | Repository foundation, codebase restructuring and engineering excellence | owner (Master Prompt 0) | enforceable architecture, reproducible environment, agent operating system, quality gates, documentation | `docs/MILESTONE_STATUS.md` MP0 checklist |
| MP1 | Real NSE data readiness | owner (title of Master Prompt 1/8) | to be specified by the owner's prompt | to be specified |
| MP2-MP8 | not yet named as repository milestones | owner (pending) | - | - |

The owner issued a separate fourteen-prompt product series on 2026-11-09 (Product Prompt
00 through 14). That series is the desktop-product plan. It does not rename MP0 or MP1.
Prompt 01 is this MP1 workstream. The catalogue, dependencies, and release gates are in
[docs/product/MASTER_PROMPT_ROADMAP.md](product/MASTER_PROMPT_ROADMAP.md).

## Candidate scope for MP1 onwards (PROPOSED, from the evidence blockers)

These follow the dependency order already recorded in `nse/docs/release/NEXT_PHASE_ROADMAP.md`
and the open blockers. They are inputs for the owner's milestone prompts, not commitments.

| Order | Candidate | Unblocks | Blocker ids | Owner action needed |
|---|---|---|---|---|
| 1 | Real EOD history for MIT, 2021-2025 (legacy bhavcopies) and one UDiFF sample | G0 history depth; all real-data scans | B18, D31 | download the files the plan lists (`python3 -m nse.research.cli acquire-plan ...`); the platform only ingests |
| 2 | Point-in-time Nifty 100 membership and instrument identity history | survivorship-free universe | B11 | supply constituent history |
| 3 | Corporate actions and an adjustment convention | trustworthy prices across splits / bonuses | B7 | supply records; decide the convention |
| 4 | Targeted TradingView reference validation (3-5 symbols) | external validation of OHLC, SMA-50, zones | B8, B10, B17 | record references |
| 5 | Backtest execution model and walk-forward evaluation | historical evaluation (not profitability claims) | B9, B12 | confirm model parameters |
| 6 | Paper-trading loop on the journal | prospective evidence | - | approve the loop |
| 7 | Dashboard and watchlist quality (design skills in `docs/SKILLS_REGISTRY.md`) | daily usability | - | design priorities |
| 8 | WIT (75 / 125-minute) | intraday trade type | M4b, B6, B15 | intraday source and session design |

Not on the roadmap without an explicit owner decision: broker integration or order
placement (D10, D17), paid data, external alert delivery, sector rules (D6), news or
fundamentals sources.

## How a milestone runs

1. The owner issues the milestone prompt; the governance chair (`gtf-autonomous-project-lead`) records its title and exit criteria
   here and in `docs/MILESTONE_STATUS.md`.
2. That chair runs the work. `autonomous-gtf-project-council` staffs the agents. It is not a second chair. GTF phase Pn is not Product Prompt n. The crosswalk is in the master skill, section 7.1.
3. Exit is evidence-based: `python3 -m nse.validation.run_all` results, the readiness
   table, open blockers, and the milestone's own acceptance criteria. Readiness vocabularies stay distinct: `readiness.py` states, the ten production gates, and product gates R1–R5.
