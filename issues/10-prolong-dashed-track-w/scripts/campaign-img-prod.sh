#!/bin/bash
# One event of a PRODUCTION reco1 file through img -> clus -> QL matching.
#   ./campaign-img-prod.sh <fcl> <production.root> <entry> <outdir>
# -> <outdir>/mabc.zip
FCL="$1"; IN="$2"; ENT="$3"; OUT="$4"      # capture BEFORE sourcing
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-ap.sh >/dev/null 2>&1
export FHICL_FILE_PATH=/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd:$FHICL_FILE_PATH
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"; cd "$OUT"
timeout 2400 lar -n 1 --nskip "$ENT" -c "$HERE/$FCL" -s "$IN" --no-output > img.log 2>&1
rm -f nugraph.h5 trash-all-apa.tar.gz *.db tf-default.root mabc-pr.zip
ls -la mabc.zip 2>/dev/null | awk '{printf "  %.2f MB %s\n",$5/1048576,$NF}'
