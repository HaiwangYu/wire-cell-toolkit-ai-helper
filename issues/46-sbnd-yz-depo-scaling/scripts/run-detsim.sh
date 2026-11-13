#!/bin/bash
# Run the TPC detsim of the issue-46 muon test with the opt-yz WCT build.
# Usage: run-detsim.sh <workdir> <nominal|yzmap> [nevents]
# Runs inside the SL7 container.
W=$1; V=$2; N=${3:--1}
S=/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/46-sbnd-yz-depo-scaling/scripts
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1
# The WCT build of the branch, and its own cfg (source tree) + the map in wire-cell-data.
# larwirecell (opt) carries an RPATH to opt/lib, which wins over LD_LIBRARY_PATH,
# so preload the branch's WCT libraries (same sonames) instead.  Header changes
# from opt's WCT (sbnd-wc-flatcaf) to master are additions; libWireCellLarsoft
# uses none of the flat-CAF classes master lacks.
Y=/exp/sbnd/app/users/yuhw/opt-yz/lib
export LD_LIBRARY_PATH=$Y:$LD_LIBRARY_PATH
export LD_PRELOAD=$(for l in Util Iface Aux Gen SigProc Root Pgraph Tbb Pytorch; do printf '%s/libWireCell%s.so:' $Y $l; done)
export WIRECELL_PATH=/exp/sbnd/app/users/yuhw/wct-yz/cfg:/exp/sbnd/app/users/yuhw/wire-cell-data:$WIRECELL_PATH
export FHICL_FILE_PATH=$S/fcl:$FHICL_FILE_PATH
mkdir -p $W/$V && cd $W/$V || exit 1   # one directory per job: art MemoryTracker keeps an SQLite file in the cwd
/usr/bin/time -v -o detsim_$V.time lar -c detsim_wct_$V.fcl -s $W/g4.root -o detsim_$V.root -n $N > detsim_$V.log 2>&1
echo "detsim $V rc $?"
