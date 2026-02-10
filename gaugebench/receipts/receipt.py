"""
Intelexta Content-Addressable Receipt (CAR) v0.3 generation and verification.

Produces receipts compatible with car-v0.3.schema.json and verify.intelexta.com.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

def canonicalize(data: dict) -> bytes:
    """Deterministic JSON bytes: sorted keys, compact separators, UTF-8."""
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def hash_sha256(data: bytes) -> str:
    """Return hex SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def hash_file(path: Path) -> str:
    """Read a file and return its SHA-256 hex digest."""
    return hash_sha256(path.read_bytes())


def _iso_now() -> str:
    """UTC ISO-8601 timestamp with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# CAR v0.3 Builder
# ---------------------------------------------------------------------------

def create_car(
    output_dir: Path,
    manifest: dict,
    provenance: dict,
    results: dict,
    engine: str,
    backend: str,
) -> dict:
    """
    Assemble a CAR v0.3 receipt, write it to *output_dir*/receipt.json,
    and return the full CAR dict.

    The receipt covers three artifacts already on disk:
      manifest.json, results.json, provenance.json
    """
    run_id = str(uuid.uuid4())
    created_at = _iso_now()

    # Hash the three artifact files (canonical bytes)
    manifest_hash = hash_sha256(canonicalize(manifest))
    results_hash = hash_sha256(canonicalize(results))
    provenance_hash = hash_sha256(canonicalize(provenance))

    # Hash the policy file (at repo root)
    policy_path = Path(__file__).resolve().parents[2] / "POLICY.md"
    if policy_path.exists():
        policy_hash = hash_file(policy_path)
    else:
        policy_hash = hash_sha256(b"")

    # Build the CAR body (everything except id and signatures)
    car_body = {
        "run_id": run_id,
        "created_at": created_at,
        "run": {
            "kind": "exact",
            "name": f"gaugebench:{engine}:{backend}",
            "model": "gaugebench-v0.1",
            "version": "0.1.0",
            "seed": 0,
            "steps": [
                {
                    "id": "step-0",
                    "runId": run_id,
                    "orderIndex": 0,
                    "checkpointType": "benchmark",
                    "stepType": "benchmark",
                    "tokenBudget": 0,
                    "proofMode": "exact",
                    "configJson": json.dumps(
                        manifest, sort_keys=True, separators=(",", ":")
                    ),
                }
            ],
        },
        "proof": {
            "match_kind": "exact",
        },
        "policy_ref": {
            "hash": f"sha256:{policy_hash}",
            "egress": False,
            "estimator": "gaugebench.walltime.v0",
        },
        "budgets": {
            "usd": 0.0,
            "tokens": 0,
            "nature_cost": 0.0,
        },
        "provenance": [
            {"claim_type": "manifest", "sha256": f"sha256:{manifest_hash}"},
            {"claim_type": "results", "sha256": f"sha256:{results_hash}"},
            {"claim_type": "git_context", "sha256": f"sha256:{provenance_hash}"},
        ],
        "checkpoints": ["ckpt:init"],
        "sgrade": {
            "score": 100,
            "components": {
                "provenance": 1.0,
                "energy": 1.0,
                "replay": 1.0,
                "consent": 1.0,
                "incidents": 0.0,
            },
        },
        "signer_public_key": "AA==",
        "signatures": ["unsigned:placeholder"],
    }

    # Content-addressable ID = SHA-256 of canonical body (without id/signatures)
    body_for_hash = {k: v for k, v in car_body.items() if k != "signatures"}
    car_id = f"car:{hash_sha256(canonicalize(body_for_hash))}"

    car = {"id": car_id, **car_body}

    # Write receipt
    receipt_path = output_dir / "receipt.json"
    receipt_path.write_text(
        json.dumps(car, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return car


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_car(receipt_dir: Path) -> bool:
    """
    Verify a CAR receipt against the artifacts on disk.

    Checks:
      1. Each provenance claim hash matches the corresponding file.
      2. The car id matches the re-derived content-addressable hash.

    Returns True if everything checks out, False otherwise.
    """
    receipt_path = receipt_dir / "receipt.json"
    car = json.loads(receipt_path.read_text(encoding="utf-8"))

    # --- 1. Verify provenance hashes ---
    claim_file_map = {
        "manifest": receipt_dir / "manifest.json",
        "results": receipt_dir / "results.json",
        "git_context": receipt_dir / "provenance.json",
    }

    for claim in car.get("provenance", []):
        claim_type = claim["claim_type"]
        expected = claim["sha256"]  # "sha256:<hex>"

        artifact_path = claim_file_map.get(claim_type)
        if artifact_path is None or not artifact_path.exists():
            print(f"  Missing artifact for claim '{claim_type}': {artifact_path}")
            return False

        artifact_data = json.loads(artifact_path.read_text(encoding="utf-8"))
        actual_hash = f"sha256:{hash_sha256(canonicalize(artifact_data))}"

        if actual_hash != expected:
            print(f"  Hash mismatch for '{claim_type}':")
            print(f"    expected {expected}")
            print(f"    got      {actual_hash}")
            return False

    # --- 2. Verify content-addressable ID ---
    body = {k: v for k, v in car.items() if k not in ("id", "signatures")}
    expected_id = f"car:{hash_sha256(canonicalize(body))}"

    if car["id"] != expected_id:
        print(f"  CAR ID mismatch:")
        print(f"    expected {expected_id}")
        print(f"    got      {car['id']}")
        return False

    return True
