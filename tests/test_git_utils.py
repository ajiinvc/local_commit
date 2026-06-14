"""Integration tests for git utility functions (require a real git repo)."""

import os
import subprocess
import pytest
from pathlib import Path

from local_commit.git_utils import ensure_git_repo, get_changed_files, get_diff


RUNNING_IN_REPO = (
    subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    ).returncode
    == 0
)


@pytest.mark.skipif(not RUNNING_IN_REPO, reason="Not inside a git repo")
class TestGitUtils:
    def test_ensure_git_repo_ok(self) -> None:
        ensure_git_repo()  # should not raise

    def test_get_changed_files_returns_dict(self) -> None:
        changes = get_changed_files()
        assert isinstance(changes, dict)
        assert "staged" in changes
        assert "unstaged" in changes
        assert "untracked" in changes

    def test_get_diff_returns_strings(self) -> None:
        stat, content = get_diff()
        assert isinstance(stat, str)
        assert isinstance(content, str)
