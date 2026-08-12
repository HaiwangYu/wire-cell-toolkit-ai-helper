#!/bin/bash
# Run a sim+SP job against the LOCAL cfg override (nf_pipes REMOVED) for the
# no-NF A/B test.
#   ./run-nonf.sh <fcl basename> <log basename>
#
# GOTCHA: capture the positional parameters BEFORE sourcing anything -- the
# ups/.bashrc setup clobbers $1/$2 of the *sourcing* script (we saw $1 become
# "autoexpand"), which silently made `lar -c <garbage>` fail.
FCL="$1"; LOG="$2"
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1
set -e
HERE=$(cd "$(dirname "$0")" && pwd); D=$(dirname "$HERE")
path-prepend /cvmfs/sbnd.opensciencegrid.org/products/sbnd/sbndcode/v10_14_02_03/wire-cell-cfg WIRECELL_PATH
path-prepend "$D/cfg" WIRECELL_PATH      # our no-NF jsonnets win
# each job gets its own cwd: art's MemoryTracker / TFileService sqlite files
# (memory.db, cputime.db) collide with "disk I/O error" if two lar jobs share one
RUNDIR="$D/data/run-$LOG"; mkdir -p "$RUNDIR"; cd "$RUNDIR"
/usr/bin/time -v lar -c "$HERE/$FCL" -s "$D/data/evt-270-6-46.root" -n 1 > "$D/data/$LOG.log" 2>&1
echo "$FCL rc=$?"
# publish the products up into data/
for f in *.root; do [ -e "$f" ] && mv -f "$f" "$D/data/"; done
