#!/bin/bash
# N concurrent repeats of run-detsim.sh on the same g4 file.
# Usage (host): bash repeat-detsim.sh <cvmfs|patched> <label> <nrep> <g4.root> <nevents>
# -> $OUTBASE/<label>/rep<k>/detsim.root ; runs inside SL7 via in-gpvm-sl7.sh.
set -eo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
mode=$1; label=$2; nrep=$3; g4=$4; nev=$5
OUTBASE=${OUTBASE:-/exp/sbnd/data/users/yuhw/wct-0.32.x-randomness}
mkdir -p "$OUTBASE/$label"
SL7_SETUP=none /exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh bash -c '
  here=$1; mode=$2; out=$3; nrep=$4; g4=$5; nev=$6
  pids=()
  for k in $(seq 0 $((nrep-1))); do
    bash "$here/run-detsim.sh" "$mode" "$g4" "$nev" "$out/rep$k" > "$out/rep$k.launch.log" 2>&1 &
    pids+=($!)
  done
  rc=0
  for p in "${pids[@]}"; do wait $p || rc=1; done
  for k in $(seq 0 $((nrep-1))); do tail -1 "$out/rep$k.launch.log"; done
  exit $rc
' _ "$here" "$mode" "$OUTBASE/$label" "$nrep" "$g4" "$nev"
