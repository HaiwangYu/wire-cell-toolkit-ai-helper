#!/bin/bash
# Issue 48: step 2 of one qlpctree with the 0.38.0 release, one production pass, on the host.
#   run-step2.sh <qlpctree.tar.gz> <outdir> <sim|data> <split|snap|split-a> [cpu]
#   split    vertex_method dv2_split_move, dl_vtx_dump_space true   (production pass 1 -> recTreeWireCell)
#   snap     vertex_method dv2_snap,       dl_vtx_dump_space false  (production pass 2 -> recTreeWireCell_dv2snap)
#   split-a  as split, but with issue 47 task A's TLAs: dl_vtx_dump_space false, evt_subdir default (pr_evt%1%)
# Both: dv2_bundle aurora_space (from wire-cell-data), dl_vtx_dump, flat_tree, truth_match on sim,
# evt_subdir pr_evt{run}_{subrun}_{event} (run_pair.py's).  Bee on (mabc-pr.zip).  DV2_HOOK_LOG has the
# input digest of each DV2 call.  One pinned cpu, 1 thread, GODEBUG=asyncpreemptoff=1 (ai-helper #45).
set -u
TAR=${1:?tar}; OUT=${2:?outdir}; REAL=${3:?sim|data}; ARM=${4:?arm}; CPU=${5:-}
SETUP=${SETUP:-$(dirname "$(readlink -f "$0")")/setup-wcl.sh}
TM=false; [ "$REAL" = sim ] && TM=true
SUB='pr_evt{run}_{subrun}_{event}'
case $ARM in
  split)   VM=dv2_split_move; SP=true ;;
  snap)    VM=dv2_snap;       SP=false ;;
  split-a) VM=dv2_split_move; SP=false; SUB='pr_evt%1%' ;;
  *) echo "unknown arm $ARM" >&2; exit 2 ;;
esac
PIN=; [ -n "$CPU" ] && PIN="taskset -c $CPU"
rm -rf "$OUT"; mkdir -p "$OUT"
SL7_SETUP=$SETUP /exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh bash -c "
  cd $OUT; export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 DV2_THREADS=1 GOMAXPROCS=1 GODEBUG=asyncpreemptoff=1 DV2_HOOK_LOG=$OUT/dv2-hook.jsonl
  $PIN /usr/bin/time -v -o time.txt wire-cell -l stdout -L debug -c pgrapher/experiment/sbnd/wct-pr.jsonnet \
    --tla-str input=$TAR --tla-str reality=$REAL --tla-str 'evt_subdir=$SUB' \
    --tla-str vertex_method=$VM --tla-str dv2_bundle=dv2max/sbnd/aurora_space/bundle.json \
    --tla-code dl_vtx_dump=true --tla-code dl_vtx_dump_space=$SP --tla-code flat_tree=true --tla-code truth_match=$TM > wct.log 2>&1
  echo \$? > rc
  grep -c 'DL vertex failed' wct.log > dl_fail
  grep -cE 'DV2.*(fallback|fell back)|falling back' wct.log > dv2_fallback
  gzip -f wct.log" > "$OUT/run.out" 2>&1
echo "$ARM $(basename "$OUT") rc=$(cat "$OUT/rc" 2>/dev/null) dl_fail=$(cat "$OUT/dl_fail" 2>/dev/null) fallback=$(cat "$OUT/dv2_fallback" 2>/dev/null) wall=$(grep 'Elapsed (wall' "$OUT/time.txt" 2>/dev/null | awk '{print $NF}') cpu_s=$(awk -F': ' '/User time|System time/ {s+=$2} END {printf "%.0f", s}' "$OUT/time.txt" 2>/dev/null) maxrss_MB=$(grep 'Maximum resident' "$OUT/time.txt" 2>/dev/null | awk '{printf "%d", $NF/1024}')"
