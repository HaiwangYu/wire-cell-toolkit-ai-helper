#!/bin/bash
# issue 38: species in sequence through run-2step-pool.sh, plus a resource sampler.
#   run-all.sh <base dir> [species ...]   (lists in <base>/lists/<species>.units.tsv; reality data for beam-*)
#   default species: the #30 set mc-cv mc-nuecc beam-off
set -u
B=${1:?base dir}; shift; SPECIES=${*:-mc-cv mc-nuecc beam-off}; S=$(dirname $(readlink -f $0))
( while true; do
    echo "$(/bin/date '+%F %T') $(ps -u $USER -o rss=,comm= | awk '$2 ~ /^(lar|wire-cell)$/ {s+=$1; n++} END {printf "procs=%d rss_gb=%.1f", n, s/1048576}') load=$(cut -d' ' -f1 /proc/loadavg) mem_avail_gb=$(awk '/MemAvailable/ {printf "%.0f", $2/1048576}' /proc/meminfo)"
    /usr/bin/sleep 60; done ) >> $B/memwatch.log 2>&1 &
W=$!
for s in $SPECIES; do
  real=sim; case $s in beam*) real=data ;; esac
  echo "$(/bin/date '+%F %T') start $s"
  bash $S/run-2step-pool.sh $B/lists/$s.units.tsv $B/$s $real ${MAXPAR:-28}
  echo "$(/bin/date '+%F %T') done $s"
done
kill $W
echo "$(/bin/date '+%F %T') ALL DONE"
