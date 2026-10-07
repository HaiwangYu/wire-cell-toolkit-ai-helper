#!/bin/bash
# Lay a 2-step run out as a run-2step.pbs REFERENCE (the 1-step layout: <ref>/evt<k>/{tracking-pr.root,mabc.zip}
# + rse-by-nskip.tsv), so a later 2-step run can be compared against it event by event with the same tools.
#   make-ref-from-2step.sh <2-step run dir (after its own compare: cmp/bee-arm/evt_<E>/mabc.zip)> <out ref dir> <rse-by-nskip.tsv of the same reco1 file/order>
set -u
RUN=${1:?}; OUT=${2:?}; RSE=${3:?}
mkdir -p $OUT; cp $RSE $OUT/rse-by-nskip.tsv; n=0; miss=0
while IFS=$'\t' read -r k r s e t b; do
  [ "$k" = nskip ] && continue; [ "$e" = - ] && continue
  src=$(ls -d $RUN/pr/c*/pr_evt$e 2>/dev/null | head -1)
  [ -n "$src" ] && [ -f $src/tracking-pr.root ] || { miss=$((miss+1)); continue; }
  mkdir -p $OUT/evt$k; ln -sfn $src/tracking-pr.root $OUT/evt$k/tracking-pr.root
  [ -f $RUN/cmp/bee-arm/evt_$e/mabc.zip ] && ln -sfn $RUN/cmp/bee-arm/evt_$e/mabc.zip $OUT/evt$k/mabc.zip
  n=$((n+1))
done < $RSE
echo "$OUT: $n events linked from $RUN, $miss rows of $RSE without a 2-step tracking-pr.root"
