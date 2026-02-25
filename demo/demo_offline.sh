#!/bin/sh
# demo/demo_offline.sh
# 2-minute offline demo: verify a pre-committed signed bundle, then show tamper detection.
# No cloud credentials. No pip install required beyond the base gaugebench install.
set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUNDLE="$SCRIPT_DIR/bundles/demo_qic_aer_signed"

# Work on a temp copy so the committed bundle is never modified.
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT
cp -r "$BUNDLE/." "$TMP_DIR/"

echo "============================================================"
echo "  GaugeBench Offline Demo"
echo "  Bundle: demo_qic_aer_signed (pre-committed, Ed25519 signed)"
echo "============================================================"
echo ""

# ------------------------------------------------------------------
echo "Step 1/3 — Verify the untouched bundle"
echo "  [TALK] 'This receipt was produced offline — no IBM, no D-Wave.'"
echo "         'GaugeBench re-derives every hash and checks the chain.'"
echo ""
gaugebench verify "$TMP_DIR"
echo ""

# ------------------------------------------------------------------
echo "Step 2/3 — Tamper: change fidelity in results.json"
echo "  [TALK] 'Imagine someone edits the results to look better.'"
echo ""
python3 -c "
import json, pathlib
p = pathlib.Path('$TMP_DIR/results.json')
d = json.loads(p.read_text())
original = d.get('fidelity', d)
d['fidelity'] = 0.9999
p.write_text(json.dumps(d, indent=2) + '\n')
print('  results.json: fidelity changed to 0.9999')
"
echo ""

# ------------------------------------------------------------------
echo "Step 3/3 — Re-verify (expect TAMPERED)"
echo "  [TALK] 'GaugeBench catches the manipulation immediately.'"
echo ""
gaugebench verify "$TMP_DIR" || true
echo ""
echo "============================================================"
echo "  Demo complete."
echo "============================================================"
