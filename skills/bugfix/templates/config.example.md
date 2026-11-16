# SafeShip personal config
# Lives at ~/.safeship/config.md. Plain `key: value` lines; anything else is ignored.
# Every key is optional. Without this file the guard uses strict defaults.

# Where /bugfix puts each bug's evidence. {client} and {branch} are filled in per bug.
evidence_dir: C:\path\to\Docs\BugFixes\{client}\{branch}

# Repo folder name = client label, comma separated. Used for {client} and "does the other client need this fix?"
clients: MyRepoFolder=ClientA, MyOtherRepoFolder=ClientB

# Commit message: short | long | ask (show both and let me pick)
commit_message: ask

# Repo folder names allowed to commit/push straight to main/master. Force-push stays blocked everywhere.
# Default: none.
allow_main_commits:

# Files the guard refuses to stage or commit, comma separated, wildcards ok. CLAUDE.md is always included.
never_stage:
