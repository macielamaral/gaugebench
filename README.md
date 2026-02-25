# GaugeBench

Verifiable Quantum Benchmarking with Content-Addressable Receipts (CARs).

GaugeBench wraps two physics engines — **QIC** (gate-based / IBM) and **Hierarchy** (annealing / D-Wave) — and produces cryptographically verifiable receipts for every benchmark run. Receipts conform to the Intelexta CAR v0.3 schema.

## Setup

```bash
git clone --recurse-submodules <repo-url>
cd gaugebench
pip install -e .
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

### Optional: Enable Ed25519 signing

```bash
pip install -e ".[sign]"
```

This installs `pynacl` and enables real Ed25519 signatures on receipts. On first run, a keypair is generated at `~/.gaugebench/identity.key`. Without this extra, receipts are still generated but marked `unsigned:placeholder`.

## Usage

### Run a gate-based benchmark

```bash
gaugebench run qic --backend ibm_brisbane --out runs/qic_01
```

### Run an annealing benchmark

```bash
gaugebench run hierarchy --sampler dwave_advantage --out runs/hier_01
```

### Verify a run

```bash
gaugebench verify runs/qic_01
```

A successful verification prints **VERIFIED**. If any artifact has been modified, it prints **TAMPERED**.

Verification checks:
- Provenance claim hashes match artifact files on disk
- Content-addressable ID re-derives correctly
- Process checkpoint chain integrity
- Ed25519 signature (when pynacl is installed and receipt is signed)

### Wrap third-party results

Prove claims about an existing result folder without modifying the original data:

```bash
gaugebench wrap \
    --in  path/to/constellation_export/ \
    --out runs/wrapped_01 \
    --engine constellation \
    --backend quantum_elements

gaugebench verify runs/wrapped_01
```

Every file under `--in` is copied to `runs/wrapped_01/inputs/` and receives its own
`sha256` claim in the receipt. Tamper any input file and verification prints **TAMPERED**
with the exact file and hash mismatch.

### Using as a Python module

```bash
python3 -m gaugebench run qic --backend ibm_brisbane --out runs/test_01
python3 -m gaugebench verify runs/test_01
```

### Global options

```
gaugebench --quiet <subcommand>   # suppress [WARN] messages
```

## Demo

See [demo/README.md](demo/README.md) for a 2-minute walkthrough.

```bash
make demo-offline    # uses a pre-committed signed bundle — fastest
make demo-live       # generates a fresh local run (aer, no credentials)
make demo-signed     # fresh signed run with Ed25519
make demo-wrap       # wraps a Constellation export folder
```

## How It Works

Each run produces four files in the output directory:

| File | Description |
|---|---|
| `manifest.json` | Run configuration (args, timestamp, UUID) |
| `provenance.json` | Git commit hashes of root repo and submodules |
| `results.json` | Benchmark metrics (mock data in this bootstrap version) |
| `receipt.json` | CAR v0.3 receipt binding all artifacts together |

The receipt uses **process-mode proofs**: a checkpoint links `inputs_sha256` (manifest) to `outputs_sha256` (results) via a hash chain. The receipt ID (`car:<sha256>`) is derived from the canonical JSON hash of the receipt body. Verification re-hashes every artifact, re-derives the chain, and re-derives the ID — no central server required.

For wrapped runs (`gaugebench wrap`), every input file also gets an `input:<path>` provenance claim whose hash is computed over raw bytes.
