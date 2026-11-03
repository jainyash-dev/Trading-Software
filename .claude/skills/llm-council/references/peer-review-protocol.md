# Peer Review Protocol

1. Remove advisor names and perspective labels from the drafts before peer review where practical.

2. Have each reviewer assess the other drafts against the same rubric:

   - Factual accuracy and traceability
   - Compliance with project rules
   - Reasoning quality and missing cases
   - Feasibility and testability
   - Uncertainty calibration

3. Each reviewer must identify at least one weakness or explicitly state why no material weakness was found.

4. Record material disagreements and evidence needed to resolve them.

5. Do not use majority vote as proof. A single well-supported objection can invalidate a recommendation.

6. The chair checks whether peer review introduced new evidence or merely repeated opinions.

7. If real independent reviewers were not available, label this stage as an internal self-critique, not independent peer review.

## Specialist Cross-Examination (Engineering and Trading Product councils)

8. Specialist drafts are collected before anyone sees another's. The coordinator then lists
   every contradiction: the same fact read two ways, or a claim one specialist refutes with
   evidence.
9. For each contradiction, ask the two specialists (by `SendMessage` to the same subagent,
   or by a new subagent given both claims and the cited evidence) for the evidence that
   settles it. The coordinator decides on evidence, never by count.
10. A contradiction that evidence cannot settle stays in the report as UNRESOLVED, with what
    would settle it. It is escalated if it blocks a verdict or an approval.
11. The Devil's Advocate's objections are answered point by point. An objection is
    "answered" only by evidence, not by another opinion.

## Chair Verification of Material Facts

12. A claim is **material** if the recommendation, a finding's severity, a verdict or an
    approval depends on it. The chair verifies, personally and against primary evidence, every
    material claim that is:
    - disputed by any reviewer;
    - marked "verified" or "confirmed" by reviewers; agreement is checked, not trusted;
    - the basis of the recommendation, even if nobody disputed it.
13. **Primary evidence** means the source code, the tests and their output, the data files,
    and authoritative project documents: the Rulebook, `nse/docs/DECISION_LOG.md` and the
    specification. Another advisor's report, a summary or a reviewer's "verified" is not
    primary evidence. The chair reads the cited lines (`sed -n '<a>,<b>p' <file>`) or runs the
    test; where a line number is wrong, the chair records the correct one.
14. The chair records one of three verdicts per checked claim: **VERIFIED**, **REFUTED** or
    **UNVERIFIABLE**. Each comes with the exact file:line, command or test.
15. **Majority agreement is never proof.** A claim refuted by primary evidence is corrected
    in the report even when every reviewer agreed with it. The report names the correction and
    any recommendation that changes because of it.
16. An UNVERIFIABLE material claim is reported as an assumption. It cannot support an
    APPROVED status or a verdict above the deterministic cap.
17. Record the checks in the report's "Chair Verification" table (`report-format.md`). A
    report with material claims and no Chair Verification table is incomplete.
