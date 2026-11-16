#!/bin/bash
# Issue 48 P0/R1: step 2 from the grid code tarball in an emulated worker -- SL7 image, --contain --cleanenv, ONLY
# /cvmfs, /pnfs and the work dir mounted, tarball unpacked fresh -- so the DV2 env (torch from CVMFS scn, pydv2,
# the aurora_space bundle in the tarball) is tested without /exp or /nashome.
#   emulate-step2.sh <tarball> <qlpctree.tar.gz> <work dir> <sim|data> <split|snap> [cpu]
set -eu
TAR=$(realpath "$1"); IN=$(realpath "$2"); W=$3; REAL=$4; ARM=$5; CPU=${6:-}
mkdir -p "$W"/tar "$W"/run; W=$(realpath "$W"); [ -d "$W/tar/wc" ] || tar -C "$W/tar" -xzf "$TAR"; cp "$IN" "$W/run/in.tar.gz"
case $ARM in split) VM=dv2_split_move; SP=true ;; snap) VM=dv2_snap; SP=false ;; esac
TM=false; [ "$REAL" = sim ] && TM=true
PIN=; [ -n "$CPU" ] && PIN="taskset -c $CPU"
/cvmfs/oasis.opensciencegrid.org/mis/apptainer/current/bin/apptainer exec --contain --cleanenv -B /cvmfs,/pnfs,"$W" --pwd "$W/run" \
  /cvmfs/singularity.opensciencegrid.org/fermilab/fnal-dev-sl7:latest bash -c "
  export WC_TOP=$W/tar/wc; set +u; source \$WC_TOP/sbnd-wirecell-production/aurora/env/fnal/setup-fnal-run.sh > setup.log 2>&1; set -u
  echo python3 \$(command -v python3); echo GODEBUG=\$GODEBUG; echo \$PYTHONPATH | tr ':' '\n' | head -5
  python3 -c 'import scipy, lightgbm, torch, numpy, sparseconvnet; print(\"imports OK\", scipy.__version__, lightgbm.__version__, torch.__version__, numpy.__version__)'
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 DV2_THREADS=1 GOMAXPROCS=1 DV2_HOOK_LOG=$W/run/dv2-hook.jsonl
  $PIN /usr/bin/time -v -o time.txt wire-cell -l stdout -L debug -c pgrapher/experiment/sbnd/wct-pr.jsonnet \
    --tla-str input=$W/run/in.tar.gz --tla-str reality=$REAL --tla-str 'evt_subdir=pr_evt{run}_{subrun}_{event}' \
    --tla-str vertex_method=$VM --tla-str dv2_bundle=dv2max/sbnd/aurora_space/bundle.json \
    --tla-code dl_vtx_dump=true --tla-code dl_vtx_dump_space=$SP --tla-code flat_tree=true --tla-code truth_match=$TM > wct.log 2>&1
  echo rc=\$?; grep -c 'DL vertex failed' wct.log; grep -m2 'DV2-MAX bundle' wct.log | cut -c1-250"
