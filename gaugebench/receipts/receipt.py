"""
Intelexta Content-Addressable Receipt (CAR) v0.3 generation and verification.

Produces receipts compatible with car-v0.3.schema.json and verify.intelexta.com.
Supports optional Ed25519 signing when pynacl is installed (pip install gaugebench[sign]).
Set GAUGEBENCH_DISABLE_SIGN=1 to force unsigned receipts even if pynacl is installed.
"""

import base64
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Optional nacl import — signing is available only when pynacl is installed.
# ---------------------------------------------------------------------------
try:
    import nacl.signing
    import nacl.encoding
    _HAS_NACL = True
except ModuleNotFoundError:
    _HAS_NACL = False

_IDENTITY_DIR = Path.home() / ".gaugebench"
_IDENTITY_KEY = _IDENTITY_DIR / "identity.key"

# Backends that imply real hardware (egress = True)
_SIMULATOR_KEYWORDS = {"aer", "simulator", "mock", "fake", "sim", "local"}


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
    """Read a file and return its SHA-256 hex digest (raw bytes)."""
    return hash_sha256(path.read_bytes())


def _iso_now() -> str:
    """UTC ISO-8601 timestamp with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _needs_egress(backend: str) -> bool:
    """Return True if the backend name suggests real hardware (not a simulator)."""
    lower = backend.lower()
    return not any(kw in lower for kw in _SIMULATOR_KEYWORDS)


# ---------------------------------------------------------------------------
# Key management (optional — requires pynacl)
# ---------------------------------------------------------------------------

def _get_signing_key():
    """
    Load or create an Ed25519 signing key from ~/.gaugebench/identity.key.

    Returns the nacl.signing.SigningKey, or None if:
      - pynacl is not installed, OR
      - GAUGEBENCH_DISABLE_SIGN=1 is set in the environment.
    """
    if os.getenv("GAUGEBENCH_DISABLE_SIGN") == "1":
        return None
    if not _HAS_NACL:
        return None

    if _IDENTITY_KEY.exists():
        raw = _IDENTITY_KEY.read_bytes()
        return nacl.signing.SigningKey(raw)

    # Generate a new keypair and persist it
    _IDENTITY_DIR.mkdir(parents=True, exist_ok=True)
    key = nacl.signing.SigningKey.generate()
    _IDENTITY_KEY.write_bytes(bytes(key))
    _IDENTITY_KEY.chmod(0o600)
    return key


def _sign_message(signing_key, message: str) -> str:
    """Sign a message string and return base64-encoded signature."""
    sig = signing_key.sign(message.encode("utf-8")).signature
    return base64.b64encode(sig).decode()


def _public_key_b64(signing_key) -> str:
    """Return the base64-encoded public key."""
    return signing_key.verify_key.encode(
        encoder=nacl.encoding.Base64Encoder
    ).decode()


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
    extra_provenance: list | None = None,
) -> dict:
    """
    Assemble a CAR v0.3 receipt, write it to *output_dir*/receipt.json,
    and return the full CAR dict.

    The receipt covers three standard artifacts already on disk:
      manifest.json, results.json, provenance.json

    *extra_provenance* may be a list of additional provenance claim dicts,
    each with keys ``claim_type`` and ``sha256``.  These are appended after
    the standard three claims (e.g. ``input:inputs/path/to/file`` claims
    produced by the wrap runner).
    """
    # Reuse the run_id from the manifest so the receipt and manifest share the
    # same identifier; fall back to a fresh UUID only if the manifest omits it.
    run_id = manifest.get("run_id") or str(uuid.uuid4())
    created_at = _iso_now()

    # Hash the three standard artifact files (canonical bytes)
    manifest_hash = hash_sha256(canonicalize(manifest))
    results_hash = hash_sha256(canonicalize(results))
    provenance_hash = hash_sha256(canonicalize(provenance))

    # Hash the policy file (at repo root)
    policy_path = Path(__file__).resolve().parents[2] / "POLICY.md"
    if policy_path.exists():
        policy_hash = hash_file(policy_path)
    else:
        policy_hash = hash_sha256(b"")

    # --- Signing key (optional) ---
    signing_key = _get_signing_key()

    # --- Process-mode checkpoint ---
    ckpt_id = f"ckpt:{uuid.uuid4().hex}"
    prev_chain = ""

    checkpoint_body = {
        "run_id": run_id,
        "kind": "Step",
        "timestamp": created_at,
        "inputs_sha256": manifest_hash,
        "outputs_sha256": results_hash,
        "usage_tokens": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
    }
    checkpoint_canonical = canonicalize(checkpoint_body).decode("utf-8")
    curr_chain = hash_sha256((prev_chain + checkpoint_canonical).encode("utf-8"))

    ckpt_signature = ""
    if signing_key is not None:
        ckpt_signature = _sign_message(signing_key, curr_chain)

    checkpoint = {
        "id": ckpt_id,
        "prev_chain": prev_chain,
        "curr_chain": curr_chain,
        "signature": ckpt_signature,
        "run_id": run_id,
        "kind": "Step",
        "timestamp": created_at,
        "inputs_sha256": manifest_hash,
        "outputs_sha256": results_hash,
        "usage_tokens": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
    }

    # --- Provenance claims ---
    provenance_claims = [
        {"claim_type": "manifest", "sha256": f"sha256:{manifest_hash}"},
        {"claim_type": "results", "sha256": f"sha256:{results_hash}"},
        {"claim_type": "git_context", "sha256": f"sha256:{provenance_hash}"},
    ]
    if extra_provenance:
        provenance_claims.extend(extra_provenance)

    # --- Build the CAR body (everything except id and signatures) ---
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
            "match_kind": "process",
            "process": {
                "sequential_checkpoints": [checkpoint],
            },
        },
        "policy_ref": {
            "hash": f"sha256:{policy_hash}",
            "egress": _needs_egress(backend),
            "estimator": "gaugebench.walltime.v0",
        },
        "budgets": {
            "usd": 0.0,
            "tokens": 0,
            "nature_cost": 0.0,
        },
        "provenance": provenance_claims,
        "checkpoints": [ckpt_id],
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
        "signer_public_key": _public_key_b64(signing_key) if signing_key else "AA==",
    }

    # Content-addressable ID = SHA-256 of canonical body
    car_id = f"car:{hash_sha256(canonicalize(car_body))}"

    # --- Signatures ---
    if signing_key is not None:
        sig = _sign_message(signing_key, car_id)
        signatures = [f"ed25519:{sig}"]
    else:
        signatures = ["unsigned:placeholder"]

    car = {"id": car_id, **car_body, "signatures": signatures}

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
         - Standard claims (manifest, results, git_context): JSON-canonicalized hash.
         - input:* claims: raw-bytes SHA-256 of the file at receipt_dir/<path>.
           A missing file is treated as TAMPERED (not a missing-artifact error).
      2. The car id matches the re-derived content-addressable hash.
      3. Process checkpoint chain integrity (curr_chain).
      4. Ed25519 signature on the CAR id (if pynacl is available and receipt is signed).

    Returns True if everything checks out, False otherwise.
    """
    receipt_path = receipt_dir / "receipt.json"
    car = json.loads(receipt_path.read_text(encoding="utf-8"))

    # --- 1. Verify provenance hashes ---
    standard_claim_map = {
        "manifest": receipt_dir / "manifest.json",
        "results": receipt_dir / "results.json",
        "git_context": receipt_dir / "provenance.json",
    }

    for claim in car.get("provenance", []):
        claim_type = claim["claim_type"]
        expected = claim["sha256"]  # "sha256:<hex>"

        if claim_type.startswith("input:"):
            # Raw-bytes hash for wrapped input files.
            # A missing file is a TAMPERED signal, not a setup error.
            rel = claim_type[len("input:"):]
            artifact_path = receipt_dir / rel
            if not artifact_path.exists():
                print(f"  Hash mismatch for '{claim_type}': file missing")
                print(f"    expected {expected}")
                print(f"    got      <missing>")
                return False
            actual_hash = f"sha256:{hash_file(artifact_path)}"
        else:
            artifact_path = standard_claim_map.get(claim_type)
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

    # --- 3. Verify checkpoint chain ---
    proof = car.get("proof", {})
    if proof.get("match_kind") == "process":
        checkpoints = proof.get("process", {}).get("sequential_checkpoints", [])
        prev = ""
        for ckpt in checkpoints:
            ckpt_body = {
                "run_id": ckpt["run_id"],
                "kind": ckpt["kind"],
                "timestamp": ckpt["timestamp"],
                "inputs_sha256": ckpt["inputs_sha256"],
                "outputs_sha256": ckpt["outputs_sha256"],
                "usage_tokens": ckpt["usage_tokens"],
                "prompt_tokens": ckpt["prompt_tokens"],
                "completion_tokens": ckpt["completion_tokens"],
            }
            canonical = canonicalize(ckpt_body).decode("utf-8")
            expected_chain = hash_sha256((prev + canonical).encode("utf-8"))

            if ckpt["curr_chain"] != expected_chain:
                print(f"  Checkpoint chain mismatch for '{ckpt['id']}':")
                print(f"    expected {expected_chain}")
                print(f"    got      {ckpt['curr_chain']}")
                return False
            prev = ckpt["curr_chain"]

    # --- 4. Verify Ed25519 signature (if signed and pynacl available) ---
    signatures = car.get("signatures", [])
    has_real_sig = any(s.startswith("ed25519:") for s in signatures)

    if has_real_sig and _HAS_NACL:
        pub_b64 = car.get("signer_public_key", "")
        if pub_b64 and pub_b64 != "AA==":
            try:
                pub_bytes = base64.b64decode(pub_b64)
                verify_key = nacl.signing.VerifyKey(pub_bytes)
                for sig_entry in signatures:
                    if not sig_entry.startswith("ed25519:"):
                        continue
                    sig_b64 = sig_entry[len("ed25519:"):]
                    sig_bytes = base64.b64decode(sig_b64)
                    verify_key.verify(car["id"].encode("utf-8"), sig_bytes)
            except Exception as exc:
                print(f"  Signature verification failed: {exc}")
                return False

    return True
