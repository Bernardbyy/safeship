---
name: bugfix
description: Guided bug-fix workflow from ticket to PR. The AI drives an 8-step checklist (intake, diagnose, before evidence, branch + fix, verify, commit message, push, PR text), asks the developer for input at each checkpoint and keeps progress in a file so it survives compaction. Use when the user runs /bugfix, says "new bug", "fix this ticket", hands over a ticket to fix, asks for a small customisation, or says "continue the bug".
---

# Bugfix: ticket to PR, one checkpoint at a time

You drive. The developer gives context and makes the calls. At each **checkpoint** stop, say what you need in
one or two lines, and wait. Never run ahead into the next step on your own.

The developer may not know the codebase. Explain in plain words, name files with `path:line`, no jargon walls.

## Before step 1: config and resume

1. Read `~/.safeship/config.md` (plain `key: value` lines). Keys this skill uses:
   - `evidence_dir`: where bug evidence goes, may use `{client}` and `{branch}`
   - `clients`: `repoFolderName=ClientLabel, ...` (e.g. `Dynamiq_360_dashboard=SDC`)
   - `commit_message`: `short`, `long` or `ask`
   If the file or a key you need is missing, ask **once** when you first need it (offer a sensible default) and
   append the answer to the file. Don't ask for anything you don't need yet.
   When creating the file, start from `templates/config.example.md` so the other keys (`allow_main_commits`,
   `never_stage`) are there with their explanations, and tell the user in one line that the file exists and
   where.
2. If the user says "continue" or a `progress.md` with unchecked steps exists for the current branch under
   `evidence_dir`, read it, say where you are in one line, and pick up from there.

## The steps

### 1. Intake (checkpoint)
Ask for everything at once: ticket text, screenshots, conversations, sample data, and which client/repo if it's
not obvious from the working directory or `clients`. Wait.

### 2. Diagnose (checkpoint, loop until the user is clear)
Read the code and connect the dots. Report:
- **What's wrong**: what the user sees, and the cause in the code
- **What's expected**
- **How big the change is**: one line / one file / several
- **Files involved**: `path:line`
Reproduce it when you can (run the API, query the data, read the computed value) and say what you confirmed vs.
what you're inferring. If it turns out not to be a bug (wrong data, stale cache), say so plainly.
Answer the user's questions until they say it's clear. No code changes in this step.

### 3. Before evidence (checkpoint)
- Propose a branch name: `fix/camelCaseName` (customisation: `feat/camelCaseName`), no dashes, no numbers.
- Create `<evidence_dir>/Screenshots` and `<evidence_dir>/TestData`, and write `progress.md` there from
  `templates/progress.md` (fill in steps 1-2 with the diagnosis summary).
- Tell the user exactly what to capture: page, filters, date range, what should be visible in the shot, and
  a suggested filename (`Before_<What>.png`). For data proof, give a ready-to-run query or API URL.
- Wait for "done". Glance at what landed in the folder and point out anything missing.
- If the user wants to skip, note `before evidence: skipped` in `progress.md` and move on.

### 4. Branch + fix (checkpoint)
- Check `git status`. If there are unrelated uncommitted changes, ask before carrying them onto the branch.
- `git switch main && git pull` (or `master`), then `git switch -c <branch>`. The guard blocks anything else.
- Make the smallest fix that solves the cause from step 2, staying in scope. Explain the diff in a few lines.
- Wait for "looks good" or changes.

### 5. Verify (checkpoint)
Suggest how to prove **this** fix: the same page and filters as the before shot, the API value, or a DB query
(remind the user to stop the backend first if the DB only allows one process). Suggest `After_<What>.png`
names that pair with the before shots. Wait for "verified". Record in `progress.md` how it was verified.

### 6. Commit message (checkpoint)
Draft from `git diff --staged` in Conventional Commits form (use the `yy-draft-git-commit-msg` skill if it
exists). Per `commit_message`: show the short and long versions and let the user pick (`ask`), or use the
preferred one. Every claim in the body must match the diff and the measured numbers, with no mixed date windows.
**Never** add a Claude co-author or a "Generated with Claude Code" line.

### 7. Push
Stage only this change's files **by name** (never `git add .`), commit, `git push -u origin <branch>`.
The guard enforces the never-stage list and main protection; if it blocks, fix the cause and retry.

### 8. PR text (checkpoint)
Fill in `templates/pr.md`: Before, Why this is wrong / Example, After, with each screenshot's filename where
it belongs (the user uploads the images on the website). Give the PR link: the URL from the push output, or
`<origin web url>/compare/main...<branch>`. Remind the user about anything left over, like the tracker row and
PR link. If `clients` lists more than one client, ask whether the other codebase needs the same fix
(a fresh `/bugfix` there, reusing this diagnosis).
Tick the step in `progress.md`. Done.

## Rules

- Tick each step in `progress.md` as it completes and note decisions there, so the work survives compaction
  and can be resumed tomorrow. Anything worth remembering goes in that file, not just the chat.
- If the user skips ahead ("just fix it"), remind them **once** which step is being skipped, then follow them
  and note the skip in `progress.md`.
- One bug per run. If a second issue shows up, note it in `progress.md` under "Found along the way" and
  suggest a separate `/bugfix` later.
