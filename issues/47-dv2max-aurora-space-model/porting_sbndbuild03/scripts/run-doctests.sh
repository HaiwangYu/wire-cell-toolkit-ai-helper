#!/bin/bash
# Issue 47 P2: run the clus / pyutil / root doctests and the pyutil Python tests of one built tree (SL7 container,
# the production run environment for torch / lightgbm).
#   run-doctests.sh <wct source tree with build/> <outdir>
# Writes <outdir>/<suite>.log and a one-line summary per suite.
T=${1:?tree}; O=${2:?outdir}; mkdir -p $O
source /exp/sbnd/app/users/yuhw/sbnd-wirecell-production/aurora/env/fnal/setup-fnal-run.sh >/dev/null 2>&1
B=$T/build
export LD_LIBRARY_PATH=$(ls -d $B/*/ | tr '\n' ':')$LD_LIBRARY_PATH
export WIRECELL_PATH=$T/cfg:/exp/sbnd/app/users/yuhw/wire-cell-data:/exp/sbnd/data/users/yuhw/production-prep/issue47/wcdata:$WIRECELL_PATH
export PYTHONPATH=$T/pyutil/python:/exp/sbnd/app/users/yuhw/pyenv-dv2:$PYTHONPATH
export OMP_NUM_THREADS=1 DV2_THREADS=1 GODEBUG=asyncpreemptoff=1
cd $T
for s in clus pyutil root; do
  x=$B/$s/wcdoctest-$s
  [ -x $x ] || { echo "$s: no binary"; continue; }
  $x > $O/$s.log 2>&1; rc=$?
  echo "$s rc=$rc $(grep -a '\[doctest\] test cases' $O/$s.log | tail -1)"
  grep -a "^TEST CASE:" $O/$s.log | sort -u > $O/$s.case-messages   # cases that printed a message (failures are in the summary line)
done
for t in pyutil/test/test_*.py; do
  [ -f $t ] || continue
  n=$(basename $t .py)
  (cd pyutil/test && python3 -m unittest $n) > $O/py-$n.log 2>&1; rc=$?
  echo "py $n rc=$rc $(grep -aE '^Ran |^OK|^FAILED' $O/py-$n.log | tr '\n' ' ')"
done
