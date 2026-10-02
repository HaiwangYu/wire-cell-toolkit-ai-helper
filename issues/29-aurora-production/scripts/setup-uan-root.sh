#!/bin/bash
# ROOT 6.28 (the UPS build) directly on an Aurora LOGIN node -- no container, no job.
# Works because the UPS binaries only need three SL7 system libraries that the UAN lacks
# (libxxhash.so.0, libcrypto/libssl.so.10, libtinfo.so.5 ...); those were extracted once from
# the SL7 image with `unsquashfs -o 36864 $Y/images/fnal-dev-sl7.sif 'usr/lib64/...'` into
# $Y/tools/sl7-libs/x/usr/lib64 (2026-10-02).  `root -b -l`, TFile/TTree, Show/Scan/Draw to
# file all work; PyROOT does NOT (libcppyy needs more).  Source it:  source setup-uan-root.sh
L=/lus/flare/projects/neutrinoGPU/scisoft/larsoft
export ROOTSYS=$L/root/v6_28_12/Linux64bit+3.10-2.17-e26-p3915-prof
export LD_LIBRARY_PATH=$ROOTSYS/lib:$L/gcc/v12_1_0/Linux64bit+3.10-2.17/lib64:$L/python/v3_9_15/Linux64bit+3.10-2.17/lib:/lus/flare/projects/neutrinoGPU/yuhw/tools/sl7-libs/x/usr/lib64:$L/tbb/v2021_9_0/Linux64bit+3.10-2.17-e26/lib:$L/xrootd/v5_5_5a/Linux64bit+3.10-2.17-e26-p3915-prof/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export PATH=$ROOTSYS/bin:$PATH
