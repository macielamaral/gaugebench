#!/bin/sh
# demo/demo_live_mock.sh
# Live demo: generate a new local run, verify, then show tamper detection.
# Uses --backend aer (local simulator — no cloud credentials required).
set -e

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT
OUT="$TMP_DIR/run_qic_aer"

echo "============================================================"
echo "  GaugeBench Live Mock Demo (aer simulator)"
echo "============================================================"
echo ""

# ------------------------------------------------------------------
echo "Step 1/3 — Run a fresh QIC benchmark (aer backend)"
echo "  [TALK] 'We generate a benchmark locally — no hardware needed.'"
echo "         'GaugeBench produces a signed receipt in seconds.'"
echo ""
gaugebench --quiet run qic --backend aer --out "$OUT"
echo ""

# ------------------------------------------------------------------
echo "Step 2/3 — Verify the fresh receipt"
echo "  [TALK] 'Verification re-hashes every artifact and checks the chain.'"
echo ""
gaugebench verify "$OUT"
echo ""

# ------------------------------------------------------------------
echo "Step 3/3 — Tamper: inject a false gate_error_rate, then re-verify"
echo "  [TALK] 'Now watch what happens when we alter the results...'"
echo ""
python3 -c "
import json, pathlib
p = pathlib.Path('$OUT/results.json')
d = json.loads(p.read_text())
d['gate_error_rate'] = 0.0001
p.write_text(json.dumps(d, indent=2) + '\n')
print('  results.json: gate_error_rate set to 0.0001')
"
echo ""
gaugebench verify "$OUT" || true
echo ""
echo "============================================================"
echo "  Demo complete."
echo "============================================================"
