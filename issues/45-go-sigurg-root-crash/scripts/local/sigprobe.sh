#!/bin/bash
# sigprobe.sh <arm: master|pr>  -- start wire-cell on a small input inside SL7, read the installed signal handlers
# with gdb after configure (90 s), then kill it.  Answers: who owns SIGURG/SIGCHLD/..., with or without SA_ONSTACK.
ARM=$1; D=/exp/sbnd/data/users/yuhw/production-prep/pr543-review; G=$D/v2/crash-study/sig.gdb
case $ARM in master) SETUP=/exp/sbnd/app/users/yuhw/sbnd-wirecell-production/aurora/env/fnal/setup-fnal-run.sh; VM=;;
             pr) SETUP=$D/v2/setup-pr543v2.sh; VM="--tla-str vertex_method=original";; esac
O=$D/v2/crash-study/sigprobe-$ARM; rm -rf $O; mkdir -p $O
SL7_SETUP=$SETUP /exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh bash -c "
  cd $O; export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  wire-cell -l stdout -L debug -c pgrapher/experiment/sbnd/wct-pr.jsonnet --tla-str input=$D/inputs/data--ncpi0-s0-7.qlpctree.tar.gz \
     --tla-str reality=data $VM --tla-code dl_vtx_dump=true --tla-code flat_tree=true --tla-code truth_match=false > wct.log 2>&1 &
  P=\$!; sleep 90; grep -c . wct.log; gdb -q -batch -p \$P -x $G 2>&1 | grep -E '^SIG|^No symbol|^[A-Za-z_:.]+ in section|rror'; kill -9 \$P"
