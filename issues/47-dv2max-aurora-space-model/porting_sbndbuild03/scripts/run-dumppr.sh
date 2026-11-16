#!/bin/bash
# task B: wait for the two builds; doctests of each; then the 81 step-2 runs (16 slots, pinned)
L=/exp/sbnd/data/users/yuhw/production-prep/issue47; S=/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/47-dv2max-aurora-space-model/porting_sbndbuild03/scripts
for t in dumppr dumpgate; do
  while ! grep -q '^rc=' $L/dumppr/build-$t.log 2>/dev/null; do sleep 20; done
  grep -q '^rc=0' $L/dumppr/build-$t.log || { echo "build $t failed"; exit 1; }
done
for t in dumppr dumpgate; do
  /exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh bash -c "$S/run-doctests.sh /exp/sbnd/data/users/yuhw/wct-$t $L/dumppr/tests-$t" 2>&1 | grep -v X11 > $L/dumppr/tests-$t.summary
done
cd $L
parallel -j 16 --joblog logs/dumppr-joblog.txt 'eval {} $((39+{%}))' :::: tasks-dumppr.txt > logs/dumppr-runs.out 2>&1
echo done
