#!/bin/bash
L=/exp/sbnd/data/users/yuhw/production-prep/issue47/dumppr2; S=/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/47-dv2max-aurora-space-model/porting_sbndbuild03/scripts
(time /exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh bash -c "J=16 $S/build.sh /exp/sbnd/data/users/yuhw/wct-dumppr /exp/sbnd/data/users/yuhw/opt-dumppr install && J=16 $S/build.sh /exp/sbnd/data/users/yuhw/wct-dumppr /exp/sbnd/data/users/yuhw/opt-dumppr doctest wcdoctest-clus,wcdoctest-pyutil,wcdoctest-root") > $L/build.log 2>&1 || { echo build failed; exit 1; }
/exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh bash -c "$S/run-doctests.sh /exp/sbnd/data/users/yuhw/wct-dumppr $L/tests" 2>&1 | grep -v X11 > $L/tests.summary
cd /exp/sbnd/data/users/yuhw/production-prep/issue47
parallel -j 16 --joblog logs/dumppr2-joblog.txt 'eval {} $((39+{%}))' :::: tasks-dumppr2.txt > logs/dumppr2-runs.out 2>&1
mkdir -p $L/runs/master-off-aur; for d in dataA/runs/aur/data--*; do ln -sfn $(readlink -f $d) $L/runs/master-off-aur/; done
echo done
