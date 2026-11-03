---
name: engineering-council
description: Use the LLM Council to evaluate code, architecture, data, security, testing, and implementation decisions in the trading research repository.
---

# Engineering Council

Invoke the central `llm-council` skill in Mode A (Engineering Council), through its
`code-review` or `architecture` workflow (see "Council routing" below).

## Review Areas

Review:

- Correctness, architecture, maintainability, and operational complexity
- Data provenance, schema assumptions, corporate actions, and point-in-time integrity
- Security, secrets, permissions, and destructive-operation risk
- Tests, edge cases, reproducibility, and observability
- Compatibility with the project's trading invariants

## Instructions

Always inspect actual repository state before proposing edits.

Preserve uncommitted work.

Follow the shared authority and approval policy.

Provide file/line evidence and executable acceptance criteria.

The council recommends; it does not autonomously authorize protected-file changes, downloads, commits, pushes, or broker actions.


## Council routing (Mode A)

Run `/llm-council code-review <subject>` or `/llm-council architecture <subject>`. Specialists
(`../llm-council/references/engineering-specialists.md`):
- A Architecture
- B Code Quality
- C Data Integrity
- D Security
- E Adversarial Testing

Pick the smallest set the workflow table names. Run them as separate subagents (one `Agent`
call each, in one message).

Facts first:
```
git status --short && git diff --stat
python3 -m nse.validation.run_all --group <group>      # groups: python3 -m nse.validation.run_all --list
```
Report with the Engineering Review template (`../llm-council/references/report-format.md`).
APPROVED only when no CRITICAL or HIGH finding is open and the required tests passed in a
run you saw.
