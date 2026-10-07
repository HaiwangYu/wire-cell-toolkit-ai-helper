#!/bin/bash
# ROOT 6.28 (the UPS build) directly on an Aurora LOGIN node -- no container, no job.
# Works because the UPS binaries only need three SL7 system libraries that the UAN lacks
# (libxxhash.so.0, libcrypto/libssl.so.10, libtinfo.so.5 ...); those were extracted once from
# the SL7 image with `unsquashfs -o 36864 $Y/images/fnal-dev-sl7.sif 'usr/lib64/...'` into
# $Y/tools/sl7-libs/x/usr/lib64; only the 5 ROOT + PyROOT need (incl. libffi.so.6 for ctypes) are linked in sl7-libs/min (the full set
# breaks the UAN's own grep/ls).  `root -b -l`, TFile/TTree, Show/Scan/Draw to
# file all work.  PyROOT works too with the UPS python 3.9 (its _sysconfigdata reads three UPS
# variables, set below) and numpy from the scn venv's site-packages (same python).  `ups setup`
# itself does not work on the UAN (no lsb_release).  Source it:  source setup-uan-root.sh
L=/lus/flare/projects/neutrinoGPU/scisoft/larsoft
export ROOTSYS=$L/root/v6_28_12/Linux64bit+3.10-2.17-e26-p3915-prof
export LD_LIBRARY_PATH=$ROOTSYS/lib:$L/gcc/v12_1_0/Linux64bit+3.10-2.17/lib64:$L/python/v3_9_15/Linux64bit+3.10-2.17/lib:/lus/flare/projects/neutrinoGPU/yuhw/tools/sl7-libs/min:$L/tbb/v2021_9_0/Linux64bit+3.10-2.17-e26/lib:$L/xrootd/v5_5_5a/Linux64bit+3.10-2.17-e26-p3915-prof/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export PATH=$ROOTSYS/bin:$PATH
# PyROOT: the UPS python 3.9 + numpy (scn venv site-packages; torch/sparseconvnet are there too)
export PYTHON_ROOT=$L/python/v3_9_15/Linux64bit+3.10-2.17
export PYTHON_DIR=$PYTHON_ROOT
export SQLITE_FQ_DIR=$L/sqlite/v3_40_01_00/Linux64bit+3.10-2.17
export PATH=$PYTHON_ROOT/bin:$PATH
SCN_SP=/lus/flare/projects/neutrinoGPU/yuhw/products/scn/v01_00_00/Linux64bit+3.10-2.17/venv/lib/python3.9/site-packages
# + torch / sparseconvnet (the scn venv) and SCN_Vertex.py (installed by wcb into $OPT/python): the
# DL-vertex replay (issue 35 dlvtx-replay.py) runs on the UAN too, CPU.
export PYTHONPATH=$ROOTSYS/lib:$SCN_SP:$SCN_SP/sparseconvnet-0.2-py3.9-linux-x86_64.egg:/lus/flare/projects/neutrinoGPU/yuhw/opt/python${PYTHONPATH:+:$PYTHONPATH}
