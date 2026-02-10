"""Runner for the Hierarchy (Plastic Chain / D-Wave Annealing) engine."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..git_utils import get_git_hash
from ..receipts.receipt import create_car


def run(sampler: str, out_dir: Path, N: int = 8, K: int = 4) -> dict:
    """Execute a mock Hierarchy benchmark run and produce a CAR receipt."""
    out_dir.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[2]

    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 1. Manifest
    manifest = {
        "run_id": run_id,
        "engine": "hierarchy",
        "sampler": sampler,
        "N": N,
        "K": K,
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

    # 3. Results (mock annealing data)
    results = {
        "engine": "hierarchy",
        "sampler": sampler,
        "N": N,
        "K": K,
        "energy_gap": 1.2047,
        "ground_state_probability": 0.8731,
        "chain_break_fraction": 0.0023,
        "num_reads": 1000,
    }
    (out_dir / "results.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )

    # 4. Generate CAR receipt
    car = create_car(out_dir, manifest, provenance, results, "hierarchy", sampler)
    return car
