"""GaugeBench CLI — Verifiable Quantum Benchmarking."""

import argparse
import sys
from pathlib import Path


def _warn_submodules(quiet: bool = False) -> None:
    """Emit a [WARN] if the external submodules appear empty."""
    if quiet:
        return
    root = Path(__file__).resolve().parents[1]
    for name in ("qic", "hierarchy"):
        sub = root / "external" / name
        if not sub.exists() or not any(sub.iterdir()):
            print(
                f"[WARN] external/{name} submodule is empty. "
                f"Run: git submodule update --init --recursive",
                file=sys.stderr,
            )


def cmd_run_qic(args: argparse.Namespace) -> None:
    from .runners.qic import run

    _warn_submodules(quiet=args.quiet)
    out = Path(args.out)
    car = run(backend=args.backend, out_dir=out, shots=args.shots)
    print(f"Run complete. Receipt ID: {car['id']}")


def cmd_run_hierarchy(args: argparse.Namespace) -> None:
    from .runners.hierarchy import run

    _warn_submodules(quiet=args.quiet)
    out = Path(args.out)
    car = run(sampler=args.sampler, out_dir=out, N=args.N, K=args.K)
    print(f"Run complete. Receipt ID: {car['id']}")


def cmd_wrap(args: argparse.Namespace) -> None:
    from .runners.wrap import run

    try:
        car = run(
            in_dir=Path(args.in_dir),
            out_dir=Path(args.out),
            engine=args.engine,
            backend=args.backend,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)
    print(f"Wrap complete. Receipt ID: {car['id']}")


def cmd_inspect(args: argparse.Namespace) -> None:
    import json

    receipt_dir = Path(args.dir)
    receipt_path = receipt_dir / "receipt.json"
    if not receipt_path.exists():
        print(f"No receipt.json found in {receipt_dir}", file=sys.stderr)
        sys.exit(2)

    car = json.loads(receipt_path.read_text(encoding="utf-8"))

    run_name = car.get("run", {}).get("name", "")
    # "gaugebench:engine:backend" or "engine:backend" or just the name
    parts = run_name.split(":")
    if len(parts) >= 3 and parts[0] == "gaugebench":
        engine, backend = parts[1], parts[2]
    elif len(parts) == 2:
        engine, backend = parts[0], parts[1]
    else:
        engine = backend = run_name

    sigs = car.get("signatures", [])
    signing = "signed" if any(s.startswith("ed25519:") for s in sigs) else "unsigned"

    input_claims = [
        c for c in car.get("provenance", [])
        if c.get("claim_type", "").startswith("input:")
    ]
    n_inputs = len(input_claims)

    egress = car.get("policy_ref", {}).get("egress", False)

    print(f"id         {car['id']}")
    print(f"engine     {engine}  /  {backend}")
    print(f"created    {car.get('created_at', '—')}")
    print(f"signing    {signing}")
    print(f"inputs     {n_inputs} wrapped file{'s' if n_inputs != 1 else ''}")
    print(f"egress     {'yes (real hardware)' if egress else 'no (simulator / offline)'}")


def cmd_verify(args: argparse.Namespace) -> None:
    from .receipts.receipt import verify_car

    receipt_dir = Path(args.dir)
    receipt_path = receipt_dir / "receipt.json"
    if not receipt_path.exists():
        print(f"No receipt.json found in {receipt_dir}", file=sys.stderr)
        sys.exit(2)

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
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        default=False,
        help="Suppress [WARN] messages (e.g. missing submodules)",
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

    # --- wrap ---
    wrap_parser = sub.add_parser(
        "wrap",
        help="Wrap a third-party result folder into a verifiable CAR bundle",
    )
    wrap_parser.add_argument(
        "--in", dest="in_dir", required=True,
        help="Input directory to wrap (e.g. a Constellation export folder)",
    )
    wrap_parser.add_argument("--out", required=True, help="Output directory")
    wrap_parser.add_argument(
        "--engine", default="constellation",
        help="Engine label (default: constellation)",
    )
    wrap_parser.add_argument(
        "--backend", default="quantum_elements",
        help="Backend label (default: quantum_elements)",
    )
    wrap_parser.set_defaults(func=cmd_wrap)

    # --- inspect ---
    inspect_parser = sub.add_parser("inspect", help="Print a summary of a run directory")
    inspect_parser.add_argument("dir", help="Directory containing receipt.json")
    inspect_parser.set_defaults(func=cmd_inspect)

    # --- verify ---
    verify_parser = sub.add_parser("verify", help="Verify a run directory")
    verify_parser.add_argument("dir", help="Directory containing receipt.json")
    verify_parser.set_defaults(func=cmd_verify)

    args = parser.parse_args()

    if not hasattr(args, "func"):
        if args.command == "run":
            run_parser.print_help()
        else:
            parser.print_help()
        sys.exit(2)

    args.func(args)


if __name__ == "__main__":
    main()
