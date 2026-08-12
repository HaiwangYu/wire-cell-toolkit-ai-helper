#!/bin/bash
# One DATA event: NF+SP (roi:both -> sp.root with gauss+dnnsp) then the magnify
# dump (roi:trad -> magnify.root).  Input is the decoded RawDigit file.
#   ./campaign-sp-data.sh <decoded.root> <entry> <outdir>
IN="$1"; ENT="$2"; OUT="$3"
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1
set -e
HERE=$(cd "$(dirname "$0")" && pwd); D=$(dirname "$HERE")
path-prepend /cvmfs/sbnd.opensciencegrid.org/products/sbnd/sbndcode/v10_14_02_03/wire-cell-cfg WIRECELL_PATH
path-prepend "$D/cfg" WIRECELL_PATH
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
mkdir -p "$OUT"; cd "$OUT"
lar -c "$HERE/campaign-sp-data.fcl"      -s "$IN" -n 1 --nskip "$ENT" > sp.log      2>&1
lar -c "$HERE/campaign-magnify-data.fcl" -s "$IN" -n 1 --nskip "$ENT" > magnify.log 2>&1
rm -f *.db hists_*.root decoder_hist.root
ls -la sp.root magnify.root 2>/dev/null | awk '{printf "  %.1f MB %s\n",$5/1048576,$NF}'
