#!/bin/bash
# Issue 48 P1: a view of a runs dir with the production per-event names pr_evt<run>_<subrun>_<event> linked as
# pr_evt<event> (the default/task-A names), so compare-trees.py can pair the files.  Refuses a collision.
#   evtname-links.sh <runs dir> <view dir>
set -eu
S=$(realpath "$1"); V=$2; rm -rf "$V"; mkdir -p "$V"
for u in "$S"/*/; do
  n=$(basename "$u"); mkdir -p "$V/$n"
  for e in "$u"pr_evt*_*_*; do
    [ -d "$e" ] || continue
    ev=${e##*_}; t="$V/$n/pr_evt$ev"
    [ -e "$t" ] && { echo "collision $t" >&2; exit 1; }
    ln -s "$e" "$t"
  done
done
