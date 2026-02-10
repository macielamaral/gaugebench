"""Runner for the QIC (Golden Chain / IBM Gate-based) engine."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..git_utils import get_git_hash
from ..receipts.receipt import create_car


def run(backend: str, out_dir: Path, shots: int = 1024) -> dict:
    """Execute a mock QIC benchmark run and produce a CAR receipt."""
    out_dir.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[2]

    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 1. Manifest
    manifest = {
        "run_id": run_id,
        "engine": "qic",
        "backend": backend,
        "shots": shots,
        "created_at": now,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    # 2. Provenance (git hashes)
    provenance = {
        "root": get_git_hash(root),
        "external/qic": get_git_hash(root / "external" / "qic"),
        "external/hierarchy": get_git_hash(root / "external" / "hierarchy"),
    }
    (out_dir / "provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )

    # 3. Results (mock physics data)
    results = {
        "engine": "qic",
        "backend": backend,
        "shots": shots,
        "fidelity": 0.9923,
        "gate_error_rate": 0.0012,
        "depth": 42,
        "two_qubit_gate_count": 87,
    }
    (out_dir / "results.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )

    # 4. Generate CAR receipt
    car = create_car(out_dir, manifest, provenance, results, "qic", backend)
    return car
