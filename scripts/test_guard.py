"""Self-check for guard.py: builds a throwaway remote + clone and feeds the hook real commands.
Run: python scripts/test_guard.py"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

GUARD = Path(__file__).with_name("guard.py")


def sh(cwd, *cmd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


def guard(cmd, cwd, config):
    r = subprocess.run([sys.executable, str(GUARD)], input=json.dumps({"tool_input": {"command": cmd}, "cwd": str(cwd)}),
                       capture_output=True, text=True, env={**os.environ, "SAFESHIP_CONFIG": str(config)})
    return r.returncode


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    ident = ["-c", "user.name=t", "-c", "user.email=t@t"]
    sh(tmp, "git", "init", "--bare", "-b", "main", "remote.git")
    for name in ("repo", "other"):
        sh(tmp, "git", "clone", "-q", str(tmp / "remote.git"), name)
    repo, other = tmp / "repo", tmp / "other"
    (repo / "a.txt").write_text("a")
    sh(repo, "git", "add", "a.txt")
    sh(repo, "git", *ident, "commit", "-qm", "init")
    sh(repo, "git", "push", "-q", "origin", "main")
    sh(other, "git", "pull", "-q", "origin", "main")
    config = tmp / "config.md"
    config.write_text("never_stage: secret/*.txt\n")
    allow = tmp / "allow.md"
    allow.write_text("allow_main_commits: repo\n")

    cases = [  # (command, expected exit code, config)
        ("ls -la", 0, config),
        ("git status", 0, config),
        ('git commit -m "x"', 2, config),
        ("git push origin main", 2, config),
        ("git push", 2, config),
        ("git push origin main", 0, allow),
        ("git push --force origin main", 2, allow),
        ("git switch -c fix/fresh", 0, config),
        ("git switch -c fix/a && git commit -m x", 0, config),
        ("git push origin fix/a:main", 2, config),
        ("git push -u origin fix/a", 0, config),
        ("git push origin +fix/a:main", 2, allow),
        ('git commit -m "x\n\nCo-Authored-By: Claude Opus <noreply@anthropic.com>"', 2, allow),
        ("git add CLAUDE.md", 2, config),
        ("git add secret/key.txt", 2, config),
        ("git add a.txt", 0, config),
    ]
    results = [(c, e, guard(c, repo, cfg)) for c, e, cfg in cases]

    # broad add with CLAUDE.md lying around
    (repo / "CLAUDE.md").write_text("x")
    results.append(("git add . [CLAUDE.md untracked]", 2, guard("git add .", repo, config)))
    results.append(("git add -A [CLAUDE.md untracked]", 2, guard("git add -A", repo, config)))
    (repo / "CLAUDE.md").unlink()

    # someone else moves main forward: local main is now stale
    (other / "b.txt").write_text("b")
    sh(other, "git", "add", "b.txt")
    sh(other, "git", *ident, "commit", "-qm", "b")
    sh(other, "git", "push", "-q", "origin", "main")
    for c, e in [("git switch -c fix/stale", 2),
                 ("git checkout -b fix/stale", 2),
                 ("git branch fix/stale", 2),
                 ("git switch main && git pull && git switch -c fix/ok", 0),
                 ("git switch -c fix/ok origin/main", 0),
                 ("SAFESHIP_OVERRIDE=1 git switch -c fix/override", 0),
                 ("git branch -d fix/old", 0)]:
        results.append((c, e, guard(c, repo, config)))

    failed = [(c, e, got) for c, e, got in results if e != got]
    for c, e, got in results:
        print(("ok  " if e == got else "FAIL"), got, "(want", e, ")", c.replace("\n", " "))
    sys.exit(1 if failed else 0)
