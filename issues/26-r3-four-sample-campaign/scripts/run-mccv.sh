#!/bin/bash
P=/exp/sbnd/data/users/yuhw/production-prep/r3-mc-cv-2026-09-09
H=/exp/sbnd/data/users/yuhw/wcp-porting-img/sbnd/img-clus-matching-eval/prabhjot-100file-Aug5-debug-25evt/chain/scripts/run-harness.sh
SL7=/exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh
nohup $P/memwatch.sh > $P/memwatch.log 2>&1 &
echo $! > $P/memwatch.pid
$SL7 bash -c "$H $P/lists/mc.manifest $P/run 20 1 wcls-img-clus-matching-xin.fcl" > $P/harness.log 2>&1
echo "HARNESS_RC=$?" >> $P/harness.log
kill $(cat $P/memwatch.pid) 2>/dev/null
echo "MCCV_DONE $(/bin/date)" >> $P/harness.log
