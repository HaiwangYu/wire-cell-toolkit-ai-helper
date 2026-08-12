#!/bin/bash
# One DATA event: img -> clus -> QL matching on a campaign sp.root.
#   ./campaign-img-data.sh <outdir>
OUT="$1"
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-ap.sh >/dev/null 2>&1
export FHICL_FILE_PATH=/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd:$FHICL_FILE_PATH
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$OUT"
timeout 2400 lar -n 1 -c "$HERE/img-clus-data.fcl" -s sp.root --no-output > img.log 2>&1
rm -f nugraph.h5 trash-all-apa.tar.gz *.db tf-default.root mabc-pr.zip
ls -la mabc.zip 2>/dev/null | awk '{printf "  %.1f MB %s\n",$5/1048576,$NF}'
