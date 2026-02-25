"""Git helper utilities for provenance tracking."""

import subprocess
from pathlib import Path


def get_git_hash(repo_path: Path) -> str:
    """Return the HEAD commit hash for a git repo, or 'unknown' on failure.

    Returns 'unknown' when *repo_path* does not contain an initialised git
    repo (e.g. an empty submodule directory), preventing the parent repo's
    HEAD from being silently recorded for an uninitialised submodule.
    """
    # An initialised git repo (or submodule) always has a .git entry.
    if not (repo_path / ".git").exists():
        return "unknown"
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return "unknown"
