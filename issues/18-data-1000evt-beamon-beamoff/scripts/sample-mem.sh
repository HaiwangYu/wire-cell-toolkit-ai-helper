#!/bin/bash
# Sample the summed RSS of all concurrent `lar` processes every INTERVAL s.
# /usr/bin/time -v gives each job's PEAK in isolation; the number that decides
# how many jobs fit in a memory budget is the CONCURRENT sum, which only a
# sampler can see.  Writes "epoch njobs total_rss_kb" lines.
OUT="${1:?out file}"; INTERVAL="${2:-5}"
while :; do
    read -r n s <<< "$(ps -eo rss,comm,user --no-headers 2>/dev/null \
        | awk '$2=="lar" && $3=="yuhw" {n++; s+=$1} END {print n+0, s+0}')"
    echo "$(date +%s) $n $s" >> "$OUT"
    sleep "$INTERVAL"
done
