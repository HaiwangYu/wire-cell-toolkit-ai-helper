#!/bin/bash
# Run the issue-46 doctest cases from the wct-yz build (SL7 container).
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1
B=/exp/sbnd/app/users/yuhw/wct-yz/build
export LD_LIBRARY_PATH=$(ls -d $B/*/ | tr '\n' ':')$LD_LIBRARY_PATH
export WIRECELL_PATH=/exp/sbnd/app/users/yuhw/wct-yz/cfg:/exp/sbnd/app/users/yuhw/wire-cell-data
$B/gen/wcdoctest-gen --test-case='yzmap*,depotransformyz*' "$@"
