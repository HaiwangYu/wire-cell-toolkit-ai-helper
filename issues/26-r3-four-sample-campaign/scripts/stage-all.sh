#!/bin/bash
# 2 concurrent chunk jobs (I/O bound; the MC campaign owns the CPUs)
D=/exp/sbnd/data/users/yuhw/production-prep/r3-data-stage-2026-09-09
SL7=/exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh
for S in beam-on beam-off; do for K in 00 01 02 03 04 05 06 07 08 09; do echo "$S $K"; done; done | xargs -P 2 -n 2 sh -c "$SL7 $D/stage-chunk.sh \$0 \$1 2>&1 | grep -v X11"
echo STAGE_ALL_DONE
