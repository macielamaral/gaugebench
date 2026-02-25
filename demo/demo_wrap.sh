#!/bin/sh
# demo/demo_wrap.sh
# Demonstrates wrapping a third-party (Constellation) export folder into a
# verifiable CAR bundle — without touching the original data stack.
set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
IN_DIR="$SCRIPT_DIR/bundles/demo_wrapped_constellation_in"

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT
OUT="$TMP_DIR/wrapped_out"

echo "============================================================"
echo "  GaugeBench Wrap Demo (Constellation export)"
echo "============================================================"
echo ""

# ------------------------------------------------------------------
echo "Step 1/3 — Wrap the Constellation export folder"
echo "  [TALK] 'We prove claims about existing results — zero changes'"
echo "         'to the original export. No access to Quantum Elements needed.'"
echo ""
echo "  Input files:"
ls -1 "$IN_DIR"
echo ""
gaugebench wrap \
    --in  "$IN_DIR" \
    --out "$OUT" \
    --engine constellation \
    --backend quantum_elements
echo ""

# ------------------------------------------------------------------
echo "Step 2/3 — Verify the wrapped bundle"
echo "  [TALK] 'Every input file has its own sha256 claim in the receipt.'"
echo "         'The CAR ID is derived from all of them together.'"
echo ""
gaugebench verify "$OUT"
echo ""

# ------------------------------------------------------------------
echo "Step 3/3 — Tamper: alter metrics.json, then re-verify"
echo "  [TALK] 'Change one metric in the third-party file...'"
echo ""
python3 -c "
import json, pathlib
p = pathlib.Path('$OUT/inputs/metrics.json')
d = json.loads(p.read_text())
d['randomized_benchmarking']['epg'] = 0.00001
p.write_text(json.dumps(d, indent=2) + '\n')
print('  inputs/metrics.json: EPG changed to 0.00001')
"
echo ""
gaugebench verify "$OUT" || true
echo ""
echo "============================================================"
echo "  Demo complete."
echo "============================================================"
