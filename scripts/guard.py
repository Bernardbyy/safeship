#!/usr/bin/env python3
"""SafeShip guard: PreToolUse hook for the Bash and PowerShell tools.

Blocks a command (exit 2; the reason on stderr goes back to the AI, which self-corrects) when it would:
  1. commit on main/master                       (unless the repo is in allow_main_commits)
  2. push to main/master                         (same allowlist)
  3. force-push to main/master                   (always)
  4. create a branch that doesn't start from freshly fetched origin/main|master
                                                 (bypass: SAFESHIP_OVERRIDE=1 in the command, only when the user said so)
  5. stage or commit a never_stage file          (CLAUDE.md always)
  6. put Claude attribution in a commit message

Personal config: ~/.safeship/config.md, plain `key: value` lines (SAFESHIP_CONFIG env var overrides the path).
Commands are simulated left to right, so `git switch main && git pull && git switch -c fix/x` passes.
"""
import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

MAIN = {"main", "master"}
CONFIG = Path(os.environ.get("SAFESHIP_CONFIG") or Path.home() / ".safeship" / "config.md")
ATTRIBUTION = re.compile(r"co-authored-by:[^\n]*(claude|anthropic)|generated with \[?claude code", re.I)
PUNCT = "();<>|&\n"
NOT_CREATE = {"-d", "-D", "--delete", "-m", "-M", "--move", "-c", "-C", "--copy", "-l", "--list", "-a", "--all",
              "-r", "--remotes", "--show-current", "-v", "-vv", "--verbose", "--contains", "--no-contains", "--merged",
              "--no-merged", "-u", "--set-upstream-to", "--unset-upstream", "--edit-description", "--points-at"}


def load_config():
    cfg = {}
    if CONFIG.exists():
        for line in CONFIG.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*([a-z_]+)\s*:\s*(.*)$", line)
            if m:
                cfg[m.group(1)] = m.group(2).strip()
    items = lambda k: [x.strip() for x in cfg.get(k, "").split(",") if x.strip()]
    return {"allow_main": items("allow_main_commits"), "never_stage": ["CLAUDE.md"] + items("never_stage")}


def git(cwd, *args, timeout=10):
    try:
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def native(path):  # Git Bash style /c/Users/... -> C:/Users/...
    m = re.match(r"^/([a-zA-Z])(/.*)?$", path) if os.name == "nt" else None
    return f"{m.group(1)}:{m.group(2) or '/'}" if m else path


def segments(cmd):
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=PUNCT)
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    try:
        tokens = list(lex)
    except ValueError:  # unbalanced quotes etc.; a rough split is good enough
        tokens = cmd.split()
    seg = []
    for t in tokens:
        if t and set(t) <= set(PUNCT):
            if seg:
                yield seg
            seg = []
        else:
            seg.append(t)
    if seg:
        yield seg


def parse_git(seg):
    """-> (path given with -C, subcommand, args) or None."""
    i = 0
    while i < len(seg) and re.match(r"^\$?(env:)?[A-Za-z_]\w*=", seg[i]):
        i += 1
    if i >= len(seg) or os.path.basename(seg[i]).lower() not in ("git", "git.exe"):
        return None
    i, cpath = i + 1, None
    while i < len(seg) and seg[i].startswith("-"):
        if seg[i] == "-C" and i + 1 < len(seg):
            cpath, i = seg[i + 1], i + 2
        elif seg[i] in ("-c", "--git-dir", "--work-tree") and i + 1 < len(seg):
            i += 2
        else:
            i += 1
    return (cpath, seg[i], seg[i + 1:]) if i < len(seg) else None


def blocked_paths(paths, patterns):
    return sorted({p for p in paths for pat in patterns
                   if fnmatch.fnmatch(p, pat) or fnmatch.fnmatch(os.path.basename(p), pat)})


def changed_paths(top):
    out = git(top, "status", "--porcelain", "--untracked-files=all") or ""
    return [line[3:].split(" -> ")[-1].strip('"') for line in out.splitlines() if len(line) > 3]


def new_branch_error(top, st, start, override):
    if override or (start is None and st["fresh"]):
        return None
    if not git(top, "remote"):
        return None  # local-only repo, nothing to be fresh against
    fetched = git(top, "fetch", "--quiet", "origin", timeout=30) is not None
    default = next((b for b in ("main", "master")
                    if git(top, "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{b}")), None)
    if not default:
        return None
    if not fetched:
        return (f"Couldn't fetch origin to confirm the branch starts from the latest {default} (offline?). "
                f"Pull {default} first, or prefix the command with SAFESHIP_OVERRIDE=1 if the user approves.")
    start_sha = git(top, "rev-parse", "--verify", "--quiet", f"{start or st['branch']}^{{commit}}")
    if start_sha and start_sha == git(top, "rev-parse", f"origin/{default}"):
        return None
    return (f"New branches must start from the latest {default}. Run `git switch {default} && git pull` first, "
            f"then create the branch (uncommitted changes carry over). If the user explicitly asked to branch from "
            f"somewhere else, prefix the command with SAFESHIP_OVERRIDE=1.")


def check(cmd, cwd, cfg):
    errors, state = [], {}
    override = "SAFESHIP_OVERRIDE=1" in cmd.replace('"', "").replace("'", "").replace(" ", "")
    for seg in segments(cmd):
        if seg[0].lower() in ("cd", "set-location", "sl", "pushd") and len(seg) > 1:
            cwd = os.path.join(cwd, native(seg[-1]))
            continue
        parsed = parse_git(seg)
        if not parsed:
            continue
        cpath, sub, args = parsed
        top = git(os.path.join(cwd, native(cpath)) if cpath else cwd, "rev-parse", "--show-toplevel")
        if not top:
            continue
        st = state.setdefault(top, {"branch": git(top, "rev-parse", "--abbrev-ref", "HEAD"), "fresh": False})
        allowed_on_main = Path(top).name in cfg["allow_main"]
        flags = [a for a in args if a.startswith("-")]
        pos = [a for a in args if not a.startswith("-")]

        if sub in ("checkout", "switch"):
            create = {"-b", "-B"} if sub == "checkout" else {"-c", "-C", "--create", "--force-create"}
            idx = next((i for i, a in enumerate(args) if a in create), None)
            if idx is not None and idx + 1 < len(args):
                rest = [a for a in args[idx + 2:] if not a.startswith("-")]
                err = new_branch_error(top, st, rest[0] if rest else None, override)
                if err:
                    errors.append(err)
                st.update(branch=args[idx + 1], fresh=False)
            elif pos and "--" not in args[:1]:
                st.update(branch=pos[0], fresh=False)

        elif sub == "branch" and pos and not set(flags) & NOT_CREATE:
            err = new_branch_error(top, st, pos[1] if len(pos) > 1 else None, override)
            if err:
                errors.append(err)

        elif sub == "pull":
            st["fresh"] = st["branch"] in MAIN

        elif sub == "add":
            broad = {"-A", "--all", "-u", "--update"} & set(flags) or {".", "*", ":/"} & set(pos)
            bad = blocked_paths(changed_paths(top) if broad else pos, cfg["never_stage"])
            if bad:
                errors.append(f"Never stage {', '.join(bad)}. Stage only this change's files by name "
                              f"(git add <file> ...).")

        elif sub == "commit":
            if st["branch"] in MAIN and not allowed_on_main:
                errors.append(f"Don't commit on {st['branch']}. Create a branch from the latest {st['branch']} "
                              f"first (e.g. git switch -c fix/camelCaseName); uncommitted changes carry over.")
            staged = (git(top, "diff", "--cached", "--name-only") or "").splitlines()
            if "--all" in flags or any(f[1:2] != "-" and "a" in f for f in flags):
                staged += (git(top, "diff", "--name-only") or "").splitlines()
            bad = blocked_paths(staged, cfg["never_stage"])
            if bad:
                errors.append(f"{', '.join(bad)} is staged and must never be committed. "
                              f"Unstage it (git restore --staged <file>) and commit again.")
            text = cmd
            for i, a in enumerate(args):
                if a in ("-F", "--file") and i + 1 < len(args):
                    try:
                        text += Path(cwd, native(args[i + 1])).read_text(encoding="utf-8")
                    except OSError:
                        pass
            if ATTRIBUTION.search(text):
                errors.append("Remove the Claude co-author / 'Generated with Claude Code' line from the commit "
                              "message; this user never wants AI attribution.")

        elif sub == "push":
            force = any(f in ("-f", "--force") or f.startswith("--force-with-lease")
                        or (f[1:2] != "-" and "f" in f) for f in flags)
            if {"--all", "--mirror"} & set(flags):
                targets = set(MAIN)
            elif len(pos) > 1:
                targets = set()
                for ref in pos[1:]:
                    force |= ref.startswith("+")
                    dst = ref.lstrip("+").split(":", 1)[-1].removeprefix("refs/heads/")
                    targets.add(st["branch"] if dst == "HEAD" else dst)
            else:
                targets = {st["branch"]}
            hits = sorted(targets & MAIN)
            if hits and force:
                errors.append(f"Never force-push to {', '.join(hits)}.")
            elif hits and not allowed_on_main:
                errors.append(f"Don't push to {', '.join(hits)}. Push the feature branch instead "
                              f"(git push -u origin <branch>) and open a PR.")
    return errors


def main():
    data = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if "git" not in cmd:
        return 0
    errors = check(cmd, data.get("cwd") or os.getcwd(), load_config())
    if errors:
        print("SafeShip guard blocked this command:\n- " + "\n- ".join(errors), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # ponytail: fail open so a guard bug never bricks the shell; the error is shown
        print(f"SafeShip guard error (command allowed): {e!r}", file=sys.stderr)
        sys.exit(1)
