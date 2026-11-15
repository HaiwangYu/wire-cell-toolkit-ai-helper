#!/bin/bash
# Issue 47 P4: step 2 of one #43 qlpctree with one arm, on the host (the #43 v2 run-step2.sh, test build).
#   run-step2.sh <qlpctree.tar.gz> <outdir> <sim|data> <arm> [cpu]
# arm: r7c   test build, vertex_method dv2_split_move, dv2_bundle r7_cloud
#      aur   test build, vertex_method dv2_split_move, dv2_bundle aurora_space
# Production step-2 settings (dl_vtx_dump, flat_tree, truth_match on sim) + dl_vtx_dump_space (T_dlvtx_space).
# DV2_HOOK_LOG (one record per DV2 call, with the input digest), 1 thread everywhere.
# Issue 45 workaround: pinned to one cpu (taskset) and GODEBUG=asyncpreemptoff=1.
set -u
TAR=${1:?tar}; OUT=${2:?outdir}; REAL=${3:?sim|data}; ARM=${4:?arm}; CPU=${5:-}
SETUP=/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/47-dv2max-aurora-space-model/porting_sbndbuild03/scripts/setup-aur-test.sh
TM=false; [ "$REAL" = sim ] && TM=true
case $ARM in
  r7c) B=dv2max/sbnd/r7_cloud/bundle.json ;;
  aur) B=dv2max/sbnd/aurora_space/bundle.json ;;
  *) echo "unknown arm $ARM" >&2; exit 2 ;;
esac
PIN=; [ -n "$CPU" ] && PIN="taskset -c $CPU"
rm -rf "$OUT"; mkdir -p "$OUT"
SL7_SETUP=$SETUP /exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh bash -c "
  cd $OUT; export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 DV2_THREADS=1 GOMAXPROCS=1 GODEBUG=asyncpreemptoff=1 DV2_HOOK_LOG=$OUT/dv2-hook.jsonl
  $PIN /usr/bin/time -v -o time.txt wire-cell -l stdout -L debug -c pgrapher/experiment/sbnd/wct-pr.jsonnet \
    --tla-str input=$TAR --tla-str reality=$REAL --tla-str vertex_method=dv2_split_move --tla-str dv2_bundle=$B \
    --tla-code dl_vtx_dump=true --tla-code dl_vtx_dump_space=true --tla-code flat_tree=true --tla-code truth_match=$TM > wct.log 2>&1
  echo \$? > rc
  grep -c 'DL vertex failed' wct.log > dl_fail
  gzip -f wct.log" > "$OUT/run.out" 2>&1
echo "$ARM $(basename "$OUT") rc=$(cat "$OUT/rc" 2>/dev/null) dl_fail=$(cat "$OUT/dl_fail" 2>/dev/null) wall=$(grep 'Elapsed (wall' "$OUT/time.txt" 2>/dev/null | awk '{print $NF}') cpu_s=$(awk -F': ' '/User time|System time/ {s+=$2} END {printf "%.0f", s}' "$OUT/time.txt" 2>/dev/null) maxrss_MB=$(grep 'Maximum resident' "$OUT/time.txt" 2>/dev/null | awk '{printf "%d", $NF/1024}')"
