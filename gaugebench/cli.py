"""GaugeBench CLI — Verifiable Quantum Benchmarking."""

import argparse
import sys
from pathlib import Path


def _warn_submodules() -> None:
    """Emit a warning if the external submodules appear empty."""
    root = Path(__file__).resolve().parents[1]
    for name in ("qic", "hierarchy"):
        sub = root / "external" / name
        if not sub.exists() or not any(sub.iterdir()):
            print(
                f"WARNING: external/{name} submodule is empty. "
                f"Run: git submodule update --init --recursive",
                file=sys.stderr,
            )


def cmd_run_qic(args: argparse.Namespace) -> None:
    from .runners.qic import run

    _warn_submodules()
    out = Path(args.out)
    car = run(backend=args.backend, out_dir=out, shots=args.shots)
    print(f"Run complete. Receipt ID: {car['id']}")


def cmd_run_hierarchy(args: argparse.Namespace) -> None:
    from .runners.hierarchy import run

    _warn_submodules()
    out = Path(args.out)
    car = run(sampler=args.sampler, out_dir=out, N=args.N, K=args.K)
    print(f"Run complete. Receipt ID: {car['id']}")


def cmd_verify(args: argparse.Namespace) -> None:
    from .receipts.receipt import verify_car

    receipt_dir = Path(args.dir)
    receipt_path = receipt_dir / "receipt.json"
    if not receipt_path.exists():
        print(f"No receipt.json found in {receipt_dir}", file=sys.stderr)
        sys.exit(1)

    ok = verify_car(receipt_dir)
    if ok:
        print("\033[32mVERIFIED\033[0m")
    else:
        print("\033[31mTAMPERED\033[0m")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="gaugebench",
        description="GaugeBench — Verifiable Quantum Benchmarking",
    )
    sub = parser.add_subparsers(dest="command")

    # --- run ---
    run_parser = sub.add_parser("run", help="Execute a benchmark run")
    run_sub = run_parser.add_subparsers(dest="engine")

    # run qic
    qic = run_sub.add_parser("qic", help="Gate-based (QIC) benchmark")
    qic.add_argument("--backend", required=True, help="Backend name (e.g. ibm_brisbane)")
    qic.add_argument("--out", required=True, help="Output directory")
    qic.add_argument("--shots", type=int, default=1024, help="Number of shots")
    qic.set_defaults(func=cmd_run_qic)

    # run hierarchy
    hier = run_sub.add_parser("hierarchy", help="Annealing (Hierarchy) benchmark")
    hier.add_argument("--sampler", required=True, help="Sampler name (e.g. dwave_advantage)")
    hier.add_argument("--out", required=True, help="Output directory")
    hier.add_argument("--N", type=int, default=8, help="System size N")
    hier.add_argument("--K", type=int, default=4, help="Hierarchy depth K")
    hier.set_defaults(func=cmd_run_hierarchy)

    # --- verify ---
    verify_parser = sub.add_parser("verify", help="Verify a run directory")
    verify_parser.add_argument("dir", help="Directory containing receipt.json")
    verify_parser.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
