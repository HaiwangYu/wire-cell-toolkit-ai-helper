#!/bin/bash
# One event: img -> clus -> QL matching -> taggers/labeler on a campaign sp.root.
# Separate script because the img chain needs setup-ap.sh, not setup-local-opt.sh.
#   ./campaign-img.sh <outdir>          (expects <outdir>/sp.root)
# -> <outdir>/mabc.zip
OUT="$1"
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-ap.sh >/dev/null 2>&1
export FHICL_FILE_PATH=/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd:$FHICL_FILE_PATH
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$OUT"
timeout 2400 lar -n 1 -c "$HERE/img-clus-rerun.fcl" -s sp.root --no-output > img.log 2>&1
rm -f nugraph.h5 trash-all-apa.tar.gz *.db tf-default.root mabc-pr.zip
ls -la mabc.zip 2>/dev/null | awk '{printf "  %.1f MB %s\n",$5/1048576,$NF}'
