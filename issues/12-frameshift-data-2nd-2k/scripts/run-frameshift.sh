#!/bin/bash
# Add the FrameShift product to one group of Gen2 data reco1 files.
#   ./run-frameshift.sh <list.lst> <out.root> <logdir>
# GOTCHA: capture positional params BEFORE sourcing (sourcing clobbers $1/$2).
LIST="$1"; OUT="$2"; LOGD="$3"
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1
set -uo pipefail
# Own cwd: concurrent lar jobs collide on art's sqlite (MemoryTracker /
# TFileService) files -> "SQLExecutionError: disk I/O error".
WD="$LOGD/wd_$(basename "$OUT" .root)"; mkdir -p "$WD"; cd "$WD"
lar -c run_frameshift.fcl -S "$LIST" -n 1000 -o "$OUT" > "$LOGD/$(basename "$OUT" .root).log" 2>&1
rc=$?
echo "$(basename "$OUT") rc=$rc $(ls -la "$OUT" 2>/dev/null | awk '{printf "%.2f GB", $5/1073741824}')"
exit $rc
