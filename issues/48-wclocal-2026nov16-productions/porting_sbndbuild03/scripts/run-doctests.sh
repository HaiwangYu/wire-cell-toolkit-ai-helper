#!/bin/bash
# Issue 48 P0: the clus / pyutil / root doctests and the pyutil Python tests of the 0.38.0 tree, in the release
# environment (scripts/setup-wcl.sh: torch from scn, lightgbm + scipy from pydv2).  Run inside SL7.
#   run-doctests.sh <wct source tree with build/> <outdir>
T=${1:?tree}; O=${2:?outdir}; mkdir -p $O
source $(dirname "$(readlink -f "$0")")/setup-wcl.sh >/dev/null 2>&1
B=$T/build
export LD_LIBRARY_PATH=$(ls -d $B/*/ | tr '\n' ':')$LD_LIBRARY_PATH
export WIRECELL_PATH=$T/cfg:/exp/sbnd/app/users/yuhw/wire-cell-data:$WIRECELL_PATH
export PYTHONPATH=$T/pyutil/python:$PYTHONPATH
export OMP_NUM_THREADS=1 DV2_THREADS=1 GODEBUG=asyncpreemptoff=1
cd $T
for s in clus pyutil root; do
  x=$B/$s/wcdoctest-$s
  [ -x $x ] || { echo "$s: no binary"; continue; }
  $x > $O/$s.log 2>&1; rc=$?
  echo "$s rc=$rc $(grep -a '\[doctest\] test cases' $O/$s.log | tail -1)"
done
for t in pyutil/test/test_*.py; do
  [ -f $t ] || continue
  n=$(basename $t .py)
  (cd pyutil/test && python3 -m unittest $n) > $O/py-$n.log 2>&1; rc=$?
  echo "py $n rc=$rc $(grep -aE '^Ran |^OK|^FAILED' $O/py-$n.log | tr '\n' ' ')"
done
