---
name: repository-guardian
description: Protect existing work in this repository before and after any change. Use at the start and end of every task that edits files, before any git operation, and whenever a test failure might come from pre-existing work. Records the baseline, checks protected files, and confirms nothing was discarded, staged or committed without authorisation.
---

# Repository guardian

## Before changes

```
git status --short --branch
git log --oneline -3
git diff --stat
git diff --cached --name-only          # must be empty unless the user staged it
python3 -m nse.validation.run_all --group repository
```
Write down: branch, HEAD, modified files, untracked files. Treat every modified or
untracked file as the user's work. Read an untracked file before overwriting it.

## Hard rules (also enforced by `.claude/hooks/guard.py`)

- Never `git reset --hard`, `git clean`, `git checkout -- <path>`, `git restore`, `git stash`,
  `git rebase`, `git commit --amend`, `git branch -D`.
- Never `git add`, `git commit`, `git push` or `git tag` without explicit authorisation in
  the current conversation. If authorised, stage explicit paths only (never `-A` or `.`),
  end the message with the attribution line from the session instructions, and confirm
  `main` is untouched.
- Never modify `nse/sources/` (Rulebook, Pine Script). Hashes are pinned in
  `nse/validation/protected.py` and `tests/test_repo.py`.
- Raw market data, circulars and screenshots stay out of git (D31, `.gitignore`).

The guard is deliberately conservative: a shell command that mentions a protected file
name together with a write-like token is refused even if the write goes elsewhere. Use
the Write/Edit tools for such files.

## After changes

```
git status --short --branch            # compare with the baseline
git diff --check
git diff --cached --name-only          # still empty
git log --oneline -3                   # HEAD unchanged unless a commit was authorised
python3 -m nse.validation.run_all --group repository
```
Explain every new or modified path. Generated outputs belong in `nse/output/` (ignored).
If a failure comes from pre-existing work, report it with evidence; never revert the work.
