#!/bin/bash
# Re-synchronise the 1-step PR operating point with Xin's 2-step entry point.
#
#   ./resync-operating-point.sh [workdir]
#
# RUN THIS whenever the owner flips more knobs in
# cfg/pgrapher/experiment/sbnd/wct-pr-perevt.jsonnet -- i.e. after any toolkit
# pull whose log mentions "SBND PRODUCTION ON".  It is idempotent: if nothing
# drifted, the generated file is unchanged and the gate still exits 0.
#
# The whole point is that it is SCRIPTED.  Issue 17 exists because the operating
# point was once mirrored by hand (one knob of ~160) under a comment claiming
# the whole thing had been handled.  Never hand-edit sbnd/pr-operating-point.jsonnet.
set -o pipefail
W="${1:-/exp/sbnd/data/users/yuhw/production-prep/pr-opsync-$(date +%Y-%m-%d)}"
HERE="$(cd "$(dirname "$0")" && pwd)"
SBND=/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd
CLUS=/exp/sbnd/app/users/yuhw/wire-cell-toolkit/cfg/pgrapher/experiment/sbnd/clus.jsonnet
GEN="$SBND/pr-operating-point.jsonnet"
mkdir -p "$W"

echo "== 1/4  baseline: compile the BARE 1-step (pr() with structural args only)"
PR_OP=bare "$HERE/compile-both.sh" "$W/compiled-bare" > "$W/1-bare.log" 2>&1
echo "        drift before regeneration: $(tail -1 "$W/1-bare.log")"

echo "== 2/4  regenerate $GEN"
cp "$GEN" "$W/pr-operating-point.jsonnet.prev" 2>/dev/null
if ! python3 "$HERE/gen-pr-operating-point.py" "$W/compiled-bare" "$CLUS" "$GEN" 2>&1 | sed 's/^/        /'; then
    echo "        GENERATION FAILED -- aborting."
    echo "        (The previously generated file is still in place, so a gate run"
    echo "         here would PASS on stale content and hide this.  That is why"
    echo "         this check exists: the first run of this script crashed in"
    echo "         python3.6 and still printed GATE PASSED.)"
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
PR_OP=sync "$HERE/compile-both.sh" "$W/compiled-sync" > "$W/3-gate.log" 2>&1
rc=$?
echo "        $(tail -1 "$W/3-gate.log")  [exit $rc]"
if [ $rc -ne 0 ]; then
    echo "        GATE FAILED -- knobs still adrift:"
    sed -n '/^### /,$p' "$W/3-gate.log" | sed 's/^/          /' | head -30
    echo "        Do NOT run production on this config."
    exit 1
fi

echo "== 4/4  preflip must still reproduce the issue-16/18 config exactly"
PR_OP=preflip "$HERE/compile-both.sh" "$W/compiled-preflip" > "$W/4-preflip.log" 2>&1
echo "        preflip vs Xin: $(tail -1 "$W/4-preflip.log")  (expected: the full gap)"

echo
echo "GATE PASSED.  Next: A/B before trusting new physics --"
echo "  ab_compare.py <preflip-run-dir> <sync-run-dir>"
echo "and commit $GEN together with the toolkit commit that caused the drift."
