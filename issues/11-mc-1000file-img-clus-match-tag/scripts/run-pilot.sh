#!/bin/bash
# 10-event pilot: event 0 of each of the first 10 files.  One event per file
# (rather than 10 from one file) so the measured cost includes a realistic
# dCache open per file, and so the BEE set shows 10 distinct events.
O=/exp/sbnd/data/users/yuhw/production-prep/img-clus-match-tag-mc-1000file-2026-08-14
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-ap.sh >/dev/null 2>&1
set -uo pipefail
export FHICL_FILE_PATH=/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd:$FHICL_FILE_PATH
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
P=$O/pilot; mkdir -p $P/{work,zips,logs}
echo "idx,rc,wall_s,zip_bytes,intermediates_bytes,file" > $P/summary.csv
i=0
while read -r f; do
  ed=$P/work/e_$i; mkdir -p $ed; cd $ed
  t0=$(date +%s)
  taskset -c "$((i*2))-$((i*2+1))" timeout 1800 lar -n 1 --nskip 0 \
      -c wcls-img-clus-matching-xin.fcl -s "$f" --no-output > lar.log 2>&1
  rc=$?; t1=$(date +%s)
  # size the intermediates issue 8 discards, BEFORE deleting them
  inter=$(du -cb nugraph.h5 trash-all-apa.tar.gz tf-default.root mabc-pr.zip 2>/dev/null | tail -1 | cut -f1)
  [ -z "$inter" ] && inter=0
  ls -la > files-before-cleanup.txt
  rm -f nugraph.h5 trash-all-apa.tar.gz *.db tf-default.root mabc-pr.zip 2>/dev/null
  z=0
  if [ $rc -eq 0 ] && [ -f mabc.zip ]; then z=$(stat -c %s mabc.zip); cp mabc.zip $P/zips/z_$(printf '%02d' $i).zip; fi
  cp lar.log $P/logs/e_$i.log; cp files-before-cleanup.txt $P/logs/e_${i}_files.txt
  echo "$i,$rc,$((t1-t0)),$z,$inter,$f" >> $P/summary.csv
  echo "  evt $i rc=$rc $((t1-t0))s zip=$z"
  cd $P; i=$((i+1))
done < $P/files-10.lst
echo "pilot done $(date)"
