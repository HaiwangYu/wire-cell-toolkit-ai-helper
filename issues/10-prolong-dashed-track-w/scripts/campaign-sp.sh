#!/bin/bash
# One event: NF+SP re-run (roi:"both" -> dnnsp for the img chain) + the magnify
# dump (roi:"trad", the only graph carrying the magnify sinks), against the cfg
# override that holds all three fixes.
#   ./campaign-sp.sh <input.root> <entry> <outdir>
# -> <outdir>/sp.root, <outdir>/magnify.root  (+ sp.log, magnify.log)
IN="$1"; ENT="$2"; OUT="$3"          # capture BEFORE sourcing (ups clobbers $1..)
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1
set -e
HERE=$(cd "$(dirname "$0")" && pwd); D=$(dirname "$HERE")
path-prepend /cvmfs/sbnd.opensciencegrid.org/products/sbnd/sbndcode/v10_14_02_03/wire-cell-cfg WIRECELL_PATH
path-prepend "$D/cfg" WIRECELL_PATH
# keep each job to ~1 core: torch/BLAS would otherwise fan out over all 64
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
mkdir -p "$OUT"; cd "$OUT"           # per-event cwd: art sqlite isolation + magnify lands here
lar -c "$HERE/rerun-fixed-sp.fcl"   -s "$IN" -n 1 --nskip "$ENT" -o sp.root        > sp.log      2>&1
lar -c "$HERE/magnify-dump-fixed.fcl" -s "$IN" -n 1 --nskip "$ENT" -o magnifyjob.root > magnify.log 2>&1
# the WCT magnify sink writes the name hard-coded in the cfg; normalise it
for f in magnify-*.root; do [ -e "$f" ] && mv -f "$f" magnify.root && break; done
rm -f *.db hists_*.root opDetDigitizerRes.root
ls -la sp.root magnify.root 2>/dev/null | awk '{printf "  %.1f MB %s\n",$5/1048576,$NF}'
