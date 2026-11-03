# Council workflows

Invoke the central skill as `/llm-council <workflow> <subject>`. The existing entry skills
route here: `/engineering-council`, `/trading-council`, `/nse-code-review`, `/trade-analysis`,
`/position-review`, `/strategy-review`, `/backtest-review`.

**Modes** (the only mode names; use them everywhere):
- **Mode A**: Engineering Council (`engineering-specialists.md`, specialists A-E).
- **Mode B**: Trading Product Council (`trading-specialists.md`, specialists A-F).
- **Combined**: Mode A + Mode B, reported as separate statuses.
- The `general` workflow uses neither roster: it uses the five lenses.

The workflow is the first argument and must be a name in the first column below. Modes are
not workflows: never pass `engineering`, `trading`, `A` or `B` as the first argument.

| Workflow | Mode | Specialists | Required evidence first | Output template |
|---|---|---|---|---|
| `general` | inferred | the five lenses in `advisor-perspectives.md`, each as an `independent-reviewer` subagent | the files the question names | report-format: Council Report |
| `code-review` | A | B always; D if it touches git, files, subprocess or the network; E if it touches eligibility, gates, overlay or reports; C if it touches data, time or the backtest | `git status --short`, `git diff`, the group tests | Engineering Review |
| `architecture` | A | A, B; D if boundaries touch I/O | module map (`nse/docs/RESEARCH_PIPELINE.md` section 1), imports | Engineering Review |
| `trade` | B | A, B, C, D in parallel; then E; then F | evidence pack from a scan at the stated as_of | Trade Analysis |
| `position` | B | A, C, D in parallel; then E; then F (position rules) | evidence pack, plus the user's position details with price source and time | Position Review |
| `scenario` | B | D, with A and B; F only if a verdict is asked for | evidence pack | Trade Analysis (scenario section; verdict optional) |
| `strategy` | B (+A for tests) | B, E, F; engineering E for test impact | `nse/docs/DECISION_REVIEW.md` entry, the cited RB lines | Strategy Review |
| `backtest` | combined | engineering B, C, E; trading C, E, F | the backtest code or diff, model JSON, data coverage (`cli inventory`), results file if any | Combined Review |
| `combined` | A + B | chosen from both rosters by the subject | as each specialist requires | Combined Review |

Release readiness stays with `/release-readiness`. The council may be asked to review that report.

## Steps common to every workflow

1. **Frame:** the exact question, the scope (files, symbol, as_of, direction), and what
   counts as done.
2. **Facts first:** run the deterministic evidence before any opinion.
   - **Engineering:** the validation group tests, `git` state, protected hashes.
   - **Trading:** a scan, then the evidence pack. Trading facts come only from local files
     (bhavcopies, user CSVs with source and time) or the user's own stated values, labelled
     as such. The council never fetches or invents prices.

   ```
   python3 -m nse.research.cli scan --as-of <date> --symbols <S> --bhavcopy-dir nse/data/eod/raw \
       --manifest nse/data/eod/manifest.csv --calendar nse/data/calendar --out nse/output/council-<S>-<date>
   python3 .claude/skills/llm-council/scripts/evidence_pack.py --scan nse/output/council-<S>-<date>/scan.json --symbol <S>
   ```

   If no data exists for the symbol and date, the trading verdict is INSUFFICIENT DATA.
   Stop there, unless the user asked for a scenario study on stated hypothetical values.
3. **Select specialists** by the table: the smallest set that covers the scope.
4. **Run them independently.** In one message, launch one `Agent` call per parallel
   specialist, using the agent type from the brief. Each prompt contains:
   - the question;
   - the scope;
   - the evidence pack path;
   - "read `.claude/skills/llm-council/references/<briefs file>` section <X> and follow its
     output contract" (for `general`: "read `advisor-perspectives.md` section <N>");
   - "read `.claude/skills/<skill>/SKILL.md`" for each skill in the brief's "Reads skill
     file" column. Subagents cannot invoke skills, so naming the skill is not enough;
   - "do not edit files";
   - "label assumptions".

   It never contains another specialist's conclusions. Devil's Advocate and Strategist run
   after.
5. **Cross-examine** per `peer-review-protocol.md`, including the chair's verification of
   every disputed or majority-"verified" material claim against primary evidence.
6. **Synthesize.** The coordinator writes one report. Trading verdicts are checked with
   `evidence_pack.py --check-verdict`. Engineering approval is APPROVED only when no
   CRITICAL or HIGH finding is open and the required tests pass in a run the coordinator
   saw.
7. **Escalate:** each unresolved decision goes to the user with the alternatives (link
   `DECISION_REVIEW.md` where it applies).

## Light mode

For a small question, the coordinator may apply the briefs itself in one context. The
report must say "single-context review: specialists not independent" at the top. A light
review never approves a release or a strategy change.
