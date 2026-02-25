#!/bin/sh
# demo/demo_live_signed.sh
# Live demo with Ed25519 signing explicitly enabled.
# Installs pynacl if missing, generates a signed run, then shows tamper detection.
set -e

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT
OUT="$TMP_DIR/run_qic_aer_signed"

echo "============================================================"
echo "  GaugeBench Live Signed Demo (Ed25519 + aer simulator)"
echo "============================================================"
echo ""

# ------------------------------------------------------------------
echo "Step 1/3 — Ensure Ed25519 signing is available (pynacl)"
echo "  [TALK] 'Signing is a pip extra — one command to enable it.'"
echo ""

if python3 -c "import nacl" 2>/dev/null; then
    echo "  pynacl already installed."
else
    echo "  Installing pynacl..."
    python3 -m pip install -e ".[sign]" --quiet
    echo "  pynacl installed."
fi

# Confirm signing will be active
python3 -c "
import nacl.signing
print('  Ed25519 available: YES')
" || {
    echo ""
    echo "ERROR: pynacl installation failed. Install manually:"
    echo "  pip install -e \".[sign]\""
    exit 1
}
echo ""

# ------------------------------------------------------------------
echo "Step 2/3 — Run a fresh signed QIC benchmark"
echo "  [TALK] 'The receipt now carries a real Ed25519 signature.'"
echo "         'Anyone can verify it using the public key in the receipt.'"
echo ""
gaugebench --quiet run qic --backend aer --out "$OUT"

# Show signature excerpt
python3 -c "
import json
r = json.loads(open('$OUT/receipt.json').read())
sig = r['signatures'][0]
pk  = r['signer_public_key']
print('  signer_public_key:', pk)
print('  signature:        ', sig[:48] + '...')
"
echo ""

# ------------------------------------------------------------------
echo "Step 3/3 — Tamper with manifest.json, then re-verify"
echo "  [TALK] 'The Ed25519 signature and hash chain both catch the change.'"
echo ""
python3 -c "
import json, pathlib
p = pathlib.Path('$OUT/manifest.json')
d = json.loads(p.read_text())
d['shots'] = 9999
p.write_text(json.dumps(d, indent=2) + '\n')
print('  manifest.json: shots changed to 9999')
"
echo ""
gaugebench verify "$OUT" || true
echo ""
echo "============================================================"
echo "  Demo complete."
echo "============================================================"
