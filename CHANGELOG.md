# Changelog

What changed in each version, in plain words. Newest first.
To get the latest: `claude plugin marketplace update safeship`, then `claude plugin update safeship`, then restart.

## 0.2.0 (2026-11-21)

- **Bugfix, step 7 (Push): catches up with `main` before pushing.** If someone else merged into `main` while
  you were fixing, the AI rebases your branch onto the latest `main` first. If those new commits touched the
  same files as your fix, it asks you to check the fix again before pushing. The rebase is noted in the bug's
  `progress.md`.
- **Bugfix, step 6 (Commit message): same rules for everyone.** The commit-message rules now ship inside the
  plugin (`skills/bugfix/commit-message.md`) instead of depending on a personal skill only one developer had.

## 0.1.0 (2026-11-14)

First version.

- **`/safeship:bugfix`**: takes one bug from ticket to PR in 8 steps (intake, diagnose, before evidence,
  branch + fix, verify, commit message, push, PR text). It stops at each step for your input and keeps its
  place in a `progress.md` in the bug's evidence folder, so you can pick up the next day.
- **Guard**: checks every git command the AI runs and blocks: committing or pushing to `main`, force-pushing
  `main`, branches not cut from freshly pulled `main`, staging `CLAUDE.md` or other never-stage files, and
  Claude attribution in commit messages. It only sees commands the AI runs, not ones you type yourself.
- **Personal settings** in `~/.safeship/config.md` (evidence folder, client names, commit message length).
