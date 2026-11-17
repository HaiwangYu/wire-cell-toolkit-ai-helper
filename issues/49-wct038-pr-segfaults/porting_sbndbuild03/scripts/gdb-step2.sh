#!/bin/bash
# Issue 49: run-step2.sh's command under gdb (batch): stop at the SIGSEGV, print the stack and
# the frames' arguments/locals.  usage: gdb-step2.sh <qlpctree.tar.gz> <outdir> <sim|data> <split|snap|orig|r7> [cpu] [gdb cmds file]
set -u
TAR=${1:?tar}; OUT=${2:?outdir}; REAL=${3:?}; ARM=${4:?}; CPU=${5:-}; CMDS=${6:-}
SETUP=/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/48-wclocal-2026nov16-productions/porting_sbndbuild03/scripts/setup-wcl.sh
TM=false; [ "$REAL" = sim ] && TM=true
BUNDLE=dv2max/sbnd/aurora_space/bundle.json; SP=false
case $ARM in split) VM=dv2_split_move; SP=true;; snap) VM=dv2_snap;; orig) VM=original;; r7) VM=dv2_split_move; BUNDLE=dv2max/sbnd/r7_cloud/bundle.json;; *) exit 2;; esac
PIN=; [ -n "$CPU" ] && PIN="taskset -c $CPU"
rm -rf "$OUT"; mkdir -p "$OUT"
[ -n "$CMDS" ] || { CMDS=$OUT/gdb.cmds; cat > $CMDS <<'G'
set pagination off
set print pretty on
handle SIGURG nostop noprint pass
handle SIGPIPE nostop noprint pass
run
bt 20
frame 7
info args
info locals
frame 8
info args
info locals
frame 9
info locals
G
}
SL7_SETUP=$SETUP /exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh bash -c "
  cd $OUT; export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 DV2_THREADS=1 GOMAXPROCS=1 GODEBUG=asyncpreemptoff=1
  $PIN gdb -batch -x $CMDS --args \$(which wire-cell) -l stdout -L info -c pgrapher/experiment/sbnd/wct-pr.jsonnet \
    --tla-str input=$TAR --tla-str reality=$REAL --tla-str 'evt_subdir=pr_evt{run}_{subrun}_{event}' \
    --tla-str vertex_method=$VM --tla-str dv2_bundle=$BUNDLE \
    --tla-code dl_vtx_dump=true --tla-code dl_vtx_dump_space=$SP --tla-code flat_tree=true --tla-code truth_match=$TM > gdb.log 2>&1" > "$OUT/run.out" 2>&1
grep -n 'SIGSEGV' "$OUT/gdb.log" | head -2
