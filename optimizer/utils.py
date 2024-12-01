"""Utility functions."""

import subprocess


def get_git_commit_info() -> tuple[str] | tuple[None]:
    """Return current git commit hash and timestamp."""
    try:
        commit_info = (
            subprocess.check_output(
                ["git", "show", "-s", "--format=%H %cI"],
            )
            .strip()
            .decode("utf-8")
        )
        commit_hash, commit_date = commit_info.split(" ")
        return commit_hash, commit_date
    except subprocess.CalledProcessError:
        return None, None
