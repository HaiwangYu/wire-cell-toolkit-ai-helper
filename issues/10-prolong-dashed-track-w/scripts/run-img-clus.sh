#!/bin/bash
# Run the 1-step img/clus/matching chain on a sim+SP re-run file.
#   ./run-img-clus.sh <input.root> <outdir-name>
# -> data/<outdir-name>/mabc.zip
# NOTE: capture args BEFORE sourcing (ups/.bashrc clobbers $1/$2), and give each
# run its own cwd (art sqlite dbs collide otherwise).
IN="$1"; OUT="$2"
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-ap.sh >/dev/null 2>&1
export FHICL_FILE_PATH=/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd:$FHICL_FILE_PATH
set -e
HERE=$(cd "$(dirname "$0")" && pwd); D=$(dirname "$HERE")
RUNDIR="$D/data/$OUT"; mkdir -p "$RUNDIR"; cd "$RUNDIR"
timeout 1200 lar -n 1 -c "$HERE/img-clus-rerun.fcl" -s "$IN" --no-output > "$D/data/$OUT.log" 2>&1
echo "$OUT rc=$?"
rm -f nugraph.h5 trash-all-apa.tar.gz *.db tf-default.root mabc-pr.zip 2>/dev/null
ls -la mabc.zip 2>/dev/null | awk '{printf "  %.1f MB %s\n",$5/1048576,$NF}'
