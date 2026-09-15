#!/bin/bash
# Polaris port of issues/17-pr-operating-point-drift/scripts/resync-operating-point.sh
# (procedure doc section 3).  Run INSIDE SL7 with setup-polaris-ap.sh sourced:
#   SL7_SETUP=$S/setup-polaris-ap.sh $S/in-polaris-sl7.sh $S/resync-operating-point-polaris.sh [workdir]
# Never hand-edit sbnd/pr-operating-point.jsonnet; this regenerates it and gates.
set -o pipefail
W="${1:-/lus/eagle/projects/neutrinoGPU/yuhw/production-prep/pr-opsync-$(date +%Y-%m-%d)}"
HERE="$(cd "$(dirname "$0")" && pwd)"
I17=$HERE/../../17-pr-operating-point-drift/scripts
SBND=${WCP_SBND:-/lus/eagle/projects/neutrinoGPU/yuhw/wcp-porting-validation/sbnd}
CLUS=${WCT_SRC:-/lus/eagle/projects/neutrinoGPU/yuhw/wire-cell-toolkit}/cfg/pgrapher/experiment/sbnd/clus.jsonnet
GEN="$SBND/pr-operating-point.jsonnet"
mkdir -p "$W"

echo "== 1/4  baseline: compile the BARE 1-step (pr() with structural args only)"
PR_OP=bare "$HERE/compile-both-polaris.sh" "$W/compiled-bare" > "$W/1-bare.log" 2>&1
echo "        drift before regeneration: $(tail -1 "$W/1-bare.log")"

echo "== 2/4  regenerate $GEN"
cp "$GEN" "$W/pr-operating-point.jsonnet.prev" 2>/dev/null
if ! python3 "$I17/gen-pr-operating-point.py" "$W/compiled-bare" "$CLUS" "$GEN" 2>&1 | sed 's/^/        /'; then
    echo "        GENERATION FAILED -- aborting (previous file left in place; do not trust a gate run now)."
    exit 1
fi
if [ -f "$W/pr-operating-point.jsonnet.prev" ]; then
    if diff -q "$W/pr-operating-point.jsonnet.prev" "$GEN" >/dev/null; then
        echo "        unchanged -- no knobs drifted"
    else
        echo "        CHANGED:"
        diff "$W/pr-operating-point.jsonnet.prev" "$GEN" | grep -E "^[<>]" | sed 's/^/          /'
    fi
fi

echo "== 3/4  GATE: compile sync and diff against Xin (must exit 0)"
PR_OP=sync "$HERE/compile-both-polaris.sh" "$W/compiled-sync" > "$W/3-gate.log" 2>&1
rc=$?
echo "        $(tail -1 "$W/3-gate.log")  [exit $rc]"
if [ $rc -ne 0 ]; then
    echo "        GATE FAILED -- knobs still adrift:"
    sed -n '/^### /,$p' "$W/3-gate.log" | sed 's/^/          /' | head -30
    exit 1
fi

echo "== 4/4  preflip must still reproduce the issue-16/18 config exactly"
PR_OP=preflip "$HERE/compile-both-polaris.sh" "$W/compiled-preflip" > "$W/4-preflip.log" 2>&1
echo "        preflip vs Xin: $(tail -1 "$W/4-preflip.log")  (expected: the full gap)"
echo "GATE PASSED. Commit $GEN together with the toolkit commit that caused the drift."
