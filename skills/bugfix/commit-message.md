# Writing the commit message (step 6)

Conventional Commits. Draft only: show it to the user, the commit itself happens in step 7.

## Shape

```
<type>(<optional scope>): <short description>

<optional body: what and why>

<optional footer: Closes #42, BREAKING CHANGE: ...>
```

Only the subject is required. The blank lines between blocks are not optional; without them git treats it all
as one paragraph.

## Type

| type | use |
|---|---|
| `fix` | patches an existing bug (the usual one here) |
| `feat` | adds something new (customisations, branch `feat/...`) |
| `refactor` | rewrites code without changing behaviour |
| `perf` | a refactor that only improves speed |
| `docs` | documentation only |
| `style` | formatting, white-space |
| `test` | adds or fixes tests |
| `build` / `ci` | tooling, dependencies, pipeline |
| `chore` | housekeeping, `.gitignore` |

Pick it from what the change does, not which file it touches. One type per commit: if the diff needs two,
it wants two commits; say so instead of picking the bigger one.

## Subject

- Imperative: "keep", not "keeps" or "kept". It completes "If applied, this commit will ___".
- Lowercase after the colon, no full stop, aim for 50 characters, stop at 72.
- Scope names the area (`slots`, `patrons`, `ui`), not the file. Leave it out rather than invent one.

## Body

What and why, never how (the diff shows how). Wrap at 72. Put in a number when one was measured: "Champion card
now 1,370, matching the export" beats "fixes the count".

## Rules

1. Read `git diff --staged` first. Describe what is staged, not what was discussed.
2. Every claim must match the diff and the numbers measured in steps 2 and 5, all from the same date window.
3. Follow `commit_message` in `~/.safeship/config.md`: `short` (subject only), `long` (subject + body), or
   `ask` (show both and let the user pick).
4. Never add Claude as co-author or a "Generated with Claude Code" line. The guard blocks it anyway.

## Example

```
fix(slots): keep machine health tables inside their cards

Table cells don't wrap, so at 150% zoom the six Machine Health tables
grew wider than their cards and the whole page scrolled sideways. Each
table now scrolls inside its card, the same way patrons/Overview does.
```
