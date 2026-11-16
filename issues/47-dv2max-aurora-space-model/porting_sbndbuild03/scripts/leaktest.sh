#!/bin/bash
# Issue 47 / PR #547: repeat the DV2 reference-leak doctest case of one built tree (SL7 container, the run env of
# run-doctests.sh).  -s prints the passing CHECKs with their CAPTUREd growth[0..3], so every rep logs its numbers.
#   leaktest.sh <wct source tree with build/> <outdir> [reps=10] [cpu]
T=${1:?tree}; O=${2:?outdir}; N=${3:-10}; CPU=${4:-}; mkdir -p $O
source /exp/sbnd/app/users/yuhw/sbnd-wirecell-production/aurora/env/fnal/setup-fnal-run.sh >/dev/null 2>&1
B=$T/build
export LD_LIBRARY_PATH=$(ls -d $B/*/ | tr '\n' ':')$LD_LIBRARY_PATH
export WIRECELL_PATH=$T/cfg:/exp/sbnd/app/users/yuhw/wire-cell-data:/exp/sbnd/data/users/yuhw/production-prep/issue47/wcdata:$WIRECELL_PATH
export PYTHONPATH=$T/pyutil/python:/exp/sbnd/app/users/yuhw/pyenv-dv2:$PYTHONPATH
export OMP_NUM_THREADS=1 DV2_THREADS=1 GODEBUG=asyncpreemptoff=1
cd $T
PIN=${CPU:+taskset -c $CPU}
for i in $(seq 1 $N); do
  s=$(date +%s.%N)
  $PIN $B/pyutil/wcdoctest-pyutil -s -tc='DV2_Vertex / DV2_Load: no Python reference leaks*' > $O/rep$i.log 2>&1; rc=$?
  e=$(date +%s.%N)
  g=$(grep -aoE 'growth\[[0-3]\] := -?[0-9]+' $O/rep$i.log | awk '{print $NF}' | head -4 | paste -sd,)
  echo "$i,$rc,$(printf %.1f $(echo "$e - $s" | bc)),\"$g\",$(grep -a '\[doctest\] assertions' $O/rep$i.log | tail -1 | sed 's/.*assertions: *//')"
done
