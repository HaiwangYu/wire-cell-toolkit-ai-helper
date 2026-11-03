#!/bin/bash
# PR #543 review: step 2 of one qlpctree with one "arm" (vertexing method), on the host.
#   run-step2.sh <qlpctree.tar.gz> <outdir> <sim|data> <arm>
# arm: master            production build (opt, toolkit sbnd-wc-flatcaf = master b7bd2a1a + #39/#41), uboone SCN net
#      pr-<method>       the PR build (opt-pr543 = the same branch + PR #543), --tla-str vertex_method=<method>,
#                        <method> = original | dv2_snap | dv2_split | dv2_split_move
# The same step-2 settings as production (aurora/bin/step2.sh): dl_vtx_dump, flat_tree, truth_match on sim.
# DV2_STRICT=1 (a Python error fails the job), DV2_HOOK_LOG (one record per DV2 call), 1 thread everywhere.
# Writes <outdir>/time.txt (/usr/bin/time -v), wct.log.gz, rc, dl_fail.
set -u
TAR=${1:?tar}; OUT=${2:?outdir}; REAL=${3:?sim|data}; ARM=${4:?arm}
D=/exp/sbnd/data/users/yuhw/production-prep/pr543-review
TM=false; [ "$REAL" = sim ] && TM=true
case $ARM in
  master) SETUP=/exp/sbnd/app/users/yuhw/sbnd-wirecell-production/aurora/env/fnal/setup-fnal-run.sh; VM= ;;
  pr-*)   SETUP=$D/setup-pr543.sh; VM="--tla-str vertex_method=${ARM#pr-}" ;;
  *) echo "unknown arm $ARM" >&2; exit 2 ;;
esac
rm -rf "$OUT"; mkdir -p "$OUT"
SL7_SETUP=$SETUP /exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh bash -c "
  cd $OUT; export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 DV2_THREADS=1 DV2_STRICT=1 DV2_HOOK_LOG=$OUT/dv2-hook.jsonl
  /usr/bin/time -v -o time.txt wire-cell -l stdout -L debug -c pgrapher/experiment/sbnd/wct-pr.jsonnet \
    --tla-str input=$TAR --tla-str reality=$REAL $VM \
    --tla-code dl_vtx_dump=true --tla-code flat_tree=true --tla-code truth_match=$TM > wct.log 2>&1
  echo \$? > rc
  grep -c 'DL vertex failed' wct.log > dl_fail
  gzip -f wct.log" > "$OUT/run.out" 2>&1
echo "$ARM $(basename "$OUT") rc=$(cat "$OUT/rc" 2>/dev/null) dl_fail=$(cat "$OUT/dl_fail" 2>/dev/null) wall=$(grep 'Elapsed (wall' "$OUT/time.txt" 2>/dev/null | awk '{print $NF}') cpu_s=$(awk -F': ' '/User time|System time/ {s+=$2} END {printf "%.0f", s}' "$OUT/time.txt" 2>/dev/null) maxrss_MB=$(grep 'Maximum resident' "$OUT/time.txt" 2>/dev/null | awk '{printf "%d", $NF/1024}')"
