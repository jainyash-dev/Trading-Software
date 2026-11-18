# Five Advisor Perspectives

Use these as distinct reasoning lenses, not as claims about five separate models.

Provenance: the five-lens council with a Chairman follows an idea published by Ole Lehmann
(an X post; no verifiable source repository or license exists, see `docs/SKILLS_REGISTRY.md`).
The text below is this project's own wording.

For the `general` workflow, run each lens as its own read-only subagent, launched in one
message: the Contrarian and First-Principles lenses as `contrarian-reviewer`, the others as
`independent-reviewer` (no Edit, Write or MultiEdit). They are the same underlying model, so
their agreement is not independent proof.

## 1. Contrarian

Search for the strongest reason the proposed conclusion is wrong.

Identify:
- Hidden failure modes
- Invalid assumptions
- Survivorship bias
- Overfitting
- Inconvenient evidence
- How the proposal would fail in real NSE markets (gaps, circuit limits, illiquidity,
  corporate actions, partial sessions, data revisions)

## 2. First-Principles Thinker

Rebuild the reasoning from definitions, constraints, causal mechanisms, and measurable facts.

Separate necessary conditions from conventions, and facts from assumptions. Challenge
complexity the constraints do not require; do not defend the existing architecture by default.

## 3. Expansionist

Explore overlooked alternatives, adjacent opportunities, scenarios, and second-order effects.

Name missing capabilities and what would scale, but mark anything speculative as such and
never propose complexity ahead of a demonstrated need. Stay within the user's scope and
safety constraints.

## 4. Outsider

Challenge domain conventions and ask what a capable newcomer would find confusing, unjustified, or needlessly complex.

Bring the independent expert's view: industry practice, simpler or more effective
alternatives. Look for simpler explanations and solutions.

## 5. Executor

Translate the decision into practical steps, dependencies, acceptance criteria, owners, and rollback or stop conditions.

Prioritize feasibility. The Executor never bypasses a safety rule, an owner decision or
deterministic eligibility to make a plan work.

## Required Advisor Output

Every advisor must independently provide:

- Position / recommendation
- Supporting evidence
- Assumptions and unknowns
- Strongest counterargument
- Risks and failure modes
- What evidence would change the recommendation
## Chairman synthesis

The coordinator (the Chairman) does not vote. It:
1. states the problem and what each lens received;
2. lists where the lenses agree and where they conflict, with the evidence each cited;
3. settles conflicts by evidence (source, Rulebook text, a reproducible test), never by count;
4. records the decision and rationale (owner decision, `ED-<n>` or `PROPOSED`) and names the
   implementation owner (`docs/AGENT_OWNERSHIP.md`);
5. states what remains unknown and what evidence would change the decision.

Deterministic eligibility, the Rulebook and owner decisions outrank every lens.
