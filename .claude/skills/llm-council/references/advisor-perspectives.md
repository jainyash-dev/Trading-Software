# Five Advisor Perspectives

Use these as distinct reasoning lenses, not as claims about five separate models.

For the `general` workflow, run each lens as its own `independent-reviewer` subagent (read-only:
no Edit, Write or MultiEdit), launched in one message. They are the same underlying model, so
their agreement is not independent proof.

## 1. Contrarian

Search for the strongest reason the proposed conclusion is wrong.

Identify:
- Hidden failure modes
- Invalid assumptions
- Survivorship bias
- Overfitting
- Inconvenient evidence

## 2. First-Principles Thinker

Rebuild the reasoning from definitions, constraints, causal mechanisms, and measurable facts.

Separate necessary conditions from conventions.

## 3. Expansionist

Explore overlooked alternatives, adjacent opportunities, scenarios, and second-order effects.

Stay within the user's scope and safety constraints.

## 4. Outsider

Challenge domain conventions and ask what a capable newcomer would find confusing, unjustified, or needlessly complex.

Look for simpler explanations and solutions.

## 5. Executor

Translate the decision into practical steps, dependencies, acceptance criteria, owners, and rollback or stop conditions.

Prioritize feasibility.

## Required Advisor Output

Every advisor must independently provide:

- Position / recommendation
- Supporting evidence
- Assumptions and unknowns
- Strongest counterargument
- Risks and failure modes
- What evidence would change the recommendation