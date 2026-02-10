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

### Using as a Python module

```bash
python -m gaugebench.cli run qic --backend ibm_brisbane --out runs/test_01
python -m gaugebench.cli verify runs/test_01
```

## How It Works

Each run produces four files in the output directory:

| File | Description |
|---|---|
| `manifest.json` | Run configuration (args, timestamp, UUID) |
| `provenance.json` | Git commit hashes of root repo and submodules |
| `results.json` | Benchmark metrics (mock data in this bootstrap version) |
| `receipt.json` | CAR v0.3 receipt binding all artifacts together |

The receipt ID (`car:<sha256>`) is derived from the canonical JSON hash of the receipt body. Verification re-hashes every artifact and re-derives the ID — no central server required.
