"""Git helper utilities for provenance tracking."""

import subprocess
from pathlib import Path


def get_git_hash(repo_path: Path) -> str:
    """Return the HEAD commit hash for a git repo, or 'unknown' on failure."""
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
