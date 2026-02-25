# GaugeBench Demo Pack

Two-minute demo guide for showing verifiable quantum benchmarking to Ari.

## Prerequisites

```bash
cd gaugebench/
python3 -m venv .venv && source .venv/bin/activate
pip install -e .                   # base (no signing)
pip install -e ".[sign]"           # + Ed25519 signing (optional but recommended)
```

No IBM / D-Wave credentials needed for any of these demos.

---

## Quick Start

```bash
make demo-offline    # fastest — uses pre-committed signed bundle
make demo-live       # generates a fresh local run
make demo-signed     # fresh run with explicit Ed25519 signing
make demo-wrap       # wraps a third-party (Constellation) export folder
```

Or run the scripts directly:

```bash
sh demo/demo_offline.sh
sh demo/demo_live_mock.sh
sh demo/demo_live_signed.sh
sh demo/demo_wrap.sh
```

---

## Scripts

### `demo_offline.sh` — The Simplest Demo

Uses a **pre-committed signed bundle** (`bundles/demo_qic_aer_signed/`). No live run.

| Step | Action | Talk track |
|---|---|---|
| 1/3 | `gaugebench verify <bundle>` | "This receipt was produced offline — no IBM, no D-Wave." |
| 2/3 | Mutate `results.json` | "Imagine someone edits the results to look better." |
| 3/3 | `gaugebench verify <bundle>` | "GaugeBench catches the manipulation immediately." |

**Expected output:**

```
Step 1/3 — Verify the untouched bundle
VERIFIED

Step 2/3 — Tamper: change fidelity in results.json
  results.json: fidelity changed to 0.9999

Step 3/3 — Re-verify (expect TAMPERED)
  Hash mismatch for 'results':
    expected sha256:...
    got      sha256:...
TAMPERED
```

---

### `demo_live_mock.sh` — Fresh Local Run

Generates a brand-new QIC run using the local `aer` (simulator) backend.

| Step | Action | Talk track |
|---|---|---|
| 1/3 | `gaugebench run qic --backend aer` | "We generate a benchmark locally — no hardware needed." |
| 2/3 | `gaugebench verify <run>` | "Verification re-hashes every artifact and checks the chain." |
| 3/3 | Mutate `results.json`, re-verify | "Watch what happens when we alter the results…" |

---

### `demo_live_signed.sh` — Ed25519 Signing

Same as live mock, but installs `pynacl` if needed and prints the signer public key.

| Step | Action | Talk track |
|---|---|---|
| 1/3 | Check / install pynacl | "Signing is a pip extra — one command to enable it." |
| 2/3 | Fresh signed run, show key + sig excerpt | "The receipt carries a real Ed25519 signature. Anyone can verify it." |
| 3/3 | Mutate `manifest.json`, re-verify | "Both the hash chain and signature catch the change." |

---

### `demo_wrap.sh` — Third-Party Export Wrapping

Wraps `bundles/demo_wrapped_constellation_in/` (a fake Constellation export) into a
verifiable CAR bundle. **No access to Quantum Elements required.**

| Step | Action | Talk track |
|---|---|---|
| 1/3 | `gaugebench wrap --in ... --out ...` | "We prove claims about existing results — zero changes to the original export." |
| 2/3 | `gaugebench verify <wrapped>` | "Every input file has its own sha256 claim in the receipt." |
| 3/3 | Mutate `inputs/metrics.json`, re-verify | "Change one metric in the third-party file…" |

---

## Pre-Committed Bundles

| Bundle | Signing | Description |
|---|---|---|
| `bundles/demo_qic_aer/` | unsigned | QIC / aer — `signatures: ["unsigned:placeholder"]` |
| `bundles/demo_qic_aer_signed/` | Ed25519 | QIC / aer — `signatures: ["ed25519:<b64>"]` |
| `bundles/demo_wrapped_constellation_in/` | — | Fake Constellation export (input only) |
| `bundles/demo_wrapped_constellation_out/` | Ed25519 | Wrapped output — verifiable CAR bundle |

To regenerate the signed bundle:

```bash
make demo-signed
```

---

## What We Can Demo Without Cloud Credentials

- Full install from scratch (`pip install -e .` or `pip install -e ".[sign]"`)
- `gaugebench run qic --backend aer` → generates a real signed receipt in < 1 s
- `gaugebench verify <dir>` → **VERIFIED** (green)
- Tamper any artifact → **TAMPERED** (red) with exact hash mismatch
- `gaugebench wrap` → proves third-party claims without touching the original stack
- Receipt inspection: `cat <dir>/receipt.json` shows CAR id, process-mode checkpoints,
  Ed25519 signature, embedded public key

## What Requires External Credentials

- `--backend ibm_brisbane` (or any real IBM backend) → needs Qiskit Runtime credentials
- `gaugebench run hierarchy --sampler dwave_advantage` → needs D-Wave API token
- Submodule content (`external/qic`, `external/hierarchy`) → run `git submodule update --init --recursive`
