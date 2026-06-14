"""Git interaction helpers — diff, status, staging, committing."""

import os
import subprocess
import sys

from local_commit.colors import err, ok

# ─── Helpers ──────────────────────────────────────────────────────────────────


def git(args: list[str], capture: bool = True, check: bool = True) -> str:
    """Run a git command. Always uses UTF-8 to avoid Windows CP1252 errors.

    Returns stdout (stripped), or an empty string on failure.
    Never returns None.
    """
    result = subprocess.run(  # noqa: S603, S607
        ["git"] + args,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if check and result.returncode != 0:
        err(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
        sys.exit(1)
    if not capture:
        return ""
    return (result.stdout or "").strip()


# ─── Repository ───────────────────────────────────────────────────────────────


def ensure_git_repo() -> None:
    """Exit with error if CWD is not inside a git repository."""
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],  # noqa: S607
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        err("Not inside a git repository. Run `git init` first.")
        sys.exit(1)


# ─── File queries ─────────────────────────────────────────────────────────────


def get_changed_files() -> dict[str, list]:
    """Return dict: {"staged": [(status, path), ...],
                     "unstaged": [(status, path), ...],
                     "untracked": [path, ...]}"""
    staged_out = git(["diff", "--cached", "--name-status"])
    unstaged_out = git(["diff", "--name-status"])
    untracked_out = git(["ls-files", "--others", "--exclude-standard"])

    changes: dict[str, list] = {"staged": [], "unstaged": [], "untracked": []}

    for line in staged_out.splitlines():
        if line.strip():
            parts = line.split("\t", 1)
            if len(parts) == 2:
                changes["staged"].append((parts[0][0], parts[1]))

    for line in unstaged_out.splitlines():
        if line.strip():
            parts = line.split("\t", 1)
            if len(parts) == 2:
                changes["unstaged"].append((parts[0][0], parts[1]))

    for line in untracked_out.splitlines():
        if line.strip():
            changes["untracked"].append(line.strip())

    return changes


def get_diff(max_chars: int = 3000) -> tuple[str, str]:
    """Get a trimmed diff of staged changes (falls back to unstaged).

    Returns (diff_stat, diff_content).
    """
    diff = git(["diff", "--cached", "--stat"]) or ""
    if not diff:
        diff = git(["diff", "--stat"]) or ""

    full_diff = git(["diff", "--cached"]) or ""
    if not full_diff:
        full_diff = git(["diff"]) or ""

    if len(full_diff) > max_chars:
        full_diff = full_diff[:max_chars] + "\n... [truncated]"

    return diff, full_diff


# ─── Write operations ────────────────────────────────────────────────────────


def stage_files(files: list[str]) -> None:
    """Stage a list of file paths."""
    for f in files:
        subprocess.run(  # noqa: S603
            ["git", "add", "--", f],  # noqa: S607
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )


def do_commit(message: str) -> None:
    """Run git commit with the given message."""
    result = subprocess.run(  # noqa: S603
        ["git", "commit", "-m", message],  # noqa: S607
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        ok(f"Committed: {message.splitlines()[0]}")
    else:
        err(f"Commit failed:\n{result.stderr.strip()}")
