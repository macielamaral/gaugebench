"""Runner for wrapping third-party result folders into verifiable CAR bundles."""

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..git_utils import get_git_hash
from ..receipts.receipt import create_car, hash_file

# ---------------------------------------------------------------------------
# Exclude patterns
# ---------------------------------------------------------------------------

# Directory names to skip entirely when walking the input tree.
_SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules",
}

# File suffixes to exclude (credentials / key material).
_SKIP_SUFFIXES = {
    ".key",
    ".pem",
    ".p12",
    ".pfx",
    ".crt",
    ".cer",
    ".der",
}


def _should_skip(rel: Path) -> bool:
    """Return True if *rel* (relative path) should be excluded from wrapping."""
    for part in rel.parts:
        # Skip hidden directories and known venv/cache names.
        if part.startswith(".") or part in _SKIP_DIR_NAMES:
            return True
    # Skip secret/key file types and hidden files.
    name = rel.name
    if name.startswith("."):
        return True
    if rel.suffix.lower() in _SKIP_SUFFIXES:
        return True
    return False


def run(in_dir: Path, out_dir: Path, engine: str, backend: str) -> dict:
    """
    Wrap a third-party result folder into a verifiable CAR bundle.

    Copies all non-excluded files from *in_dir* into *out_dir*/inputs/,
    then generates manifest.json, provenance.json, results.json, and a
    CAR v0.3 receipt.json whose provenance claims cover every copied file.

    Raises ValueError if *in_dir* and *out_dir* overlap (recursion guard).
    """
    in_dir = in_dir.resolve()
    out_dir = out_dir.resolve()

    # ------------------------------------------------------------------
    # Recursion / overlap guard
    # ------------------------------------------------------------------
    try:
        in_dir.relative_to(out_dir)
        raise ValueError(
            f"--in directory ({in_dir}) is inside --out directory ({out_dir}). "
            "This would cause infinite recursion. Use non-overlapping paths."
        )
    except ValueError as exc:
        if "inside --out" in str(exc):
            raise

    try:
        out_dir.relative_to(in_dir)
        raise ValueError(
            f"--out directory ({out_dir}) is inside --in directory ({in_dir}). "
            "This would copy the output into itself. Use non-overlapping paths."
        )
    except ValueError as exc:
        if "inside --in" in str(exc):
            raise

    # ------------------------------------------------------------------
    # Collect input files
    # ------------------------------------------------------------------
    input_rels: list[Path] = []
    for path in sorted(in_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(in_dir)
        if _should_skip(rel):
            continue
        input_rels.append(rel)

    # ------------------------------------------------------------------
    # Copy to out_dir/inputs/
    # ------------------------------------------------------------------
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir = out_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)

    for rel in input_rels:
        src = in_dir / rel
        dst = inputs_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # ------------------------------------------------------------------
    # Build metadata
    # ------------------------------------------------------------------
    root = Path(__file__).resolve().parents[2]
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    manifest = {
        "run_id": run_id,
        "engine": engine,
        "backend": backend,
        "input_source": str(in_dir),
        "input_file_count": len(input_rels),
        "created_at": now,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    provenance = {
        "root": get_git_hash(root),
    }
    (out_dir / "provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )

    results = {
        "engine": engine,
        "backend": backend,
        "input_file_count": len(input_rels),
        "input_files": [r.as_posix() for r in input_rels],
        "total_bytes": sum((inputs_dir / r).stat().st_size for r in input_rels),
    }
    (out_dir / "results.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )

    # ------------------------------------------------------------------
    # Extra provenance claims — one per input file (raw-bytes hash)
    # ------------------------------------------------------------------
    extra_provenance = [
        {
            "claim_type": f"input:inputs/{rel.as_posix()}",
            "sha256": f"sha256:{hash_file(inputs_dir / rel)}",
        }
        for rel in input_rels
    ]

    car = create_car(
        out_dir, manifest, provenance, results, engine, backend, extra_provenance
    )
    return car
