#!/bin/bash
# Aurora runner for Xin's doc-120 two-chain gate (wcp-porting-validation
# sbnd/sbnd_xin/scripts/cfg/two_chain_gate.py): compile the LArSoft 1-step chain and
# the local PR job from the SAME toolkit cfg tree and require every shared PR
# component to agree key for key.  Since toolkit 7a85e5c5 (2026-09-21) the operating
# point is pr()'s own defaults and sbnd/pr-operating-point.jsonnet is gone, so this
# gate replaces the old "resync the mirror" step (issues/17) after every toolkit pull.
#
# The gate hard-codes wcgpu1 paths (TK, WCSONNET, DATA, SBND_WD, /home/xqian/tmp); the
# script is copied into $OUT with those five lines repointed and run from there --
# nothing in sbnd_xin is modified.  Run INSIDE SL7 with setup-aurora-ap.sh sourced:
#   SL7_SETUP=$S/setup-aurora-ap.sh $S/in-aurora-sl7.sh $S/two-chain-gate-aurora.sh <outdir>
set -u
OUT=${1:?outdir}; mkdir -p "$OUT"
Y=/lus/flare/projects/neutrinoGPU/yuhw
WCT_SRC=${WCT_SRC:-$Y/wire-cell-toolkit}; WCD=${WCD:-$Y/wire-cell-data}; WCP_SBND=${WCP_SBND:-$Y/wcp-porting-validation/sbnd}
G=$WCP_SBND/sbnd_xin/scripts/cfg/two_chain_gate.py
sed -e "s#^TK = .*#TK = \"$Y\"#" \
    -e "s#^WCSONNET = .*#WCSONNET = \"$(which wcsonnet)\"#" \
    -e "s#^DATA = .*#DATA = \"$WCD\"#" \
    -e "s#^SBND_WD = .*#SBND_WD = \"$WCP_SBND\"#" \
    -e "s#dir=\"/home/xqian/tmp\"#dir=\"$OUT\"#" "$G" > "$OUT/two_chain_gate.py"
echo "two_chain_gate.py: $(md5sum < $G | cut -c1-8) (sbnd_xin) -> $(md5sum < $OUT/two_chain_gate.py | cut -c1-8) (repointed); cfg=$WCT_SRC/cfg ($(cd $WCT_SRC && git rev-parse --short HEAD))"
python3 "$OUT/two_chain_gate.py" --cfg "$WCT_SRC/cfg" --keep "$OUT/compiled" > "$OUT/two_chain_gate.txt" 2>&1
rc=$?
echo "TWO_CHAIN_GATE_RC=$rc"; grep -vE '^$' "$OUT/two_chain_gate.txt" | tail -12
exit $rc
