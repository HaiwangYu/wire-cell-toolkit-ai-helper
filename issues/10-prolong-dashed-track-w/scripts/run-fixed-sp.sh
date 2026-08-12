#!/bin/bash
# SP re-run with roi:"both" (so dnnsp exists for the img/clus chain) against the
# LOCAL cfg override -- which now carries all three fixes: nf.jsonnet
# partial_enable=false, chndb-base W max_rms_cut=100, sp.jsonnet roi_mad_rms +
# r_break_roi_loop_planes.
#   ./run-fixed-sp.sh
# -> data/evt-270-6-46_fixed_sp.root
#
# Unlike run-nonf.sh this moves ONLY the expected output up into data/: the
# override jsonnet still hard-codes magoutput=magnify-270-6-46-fixed.root, and a
# blanket "mv *.root" would clobber the verified magnify dump.
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1
set -e
HERE=$(cd "$(dirname "$0")" && pwd); D=$(dirname "$HERE")
path-prepend /cvmfs/sbnd.opensciencegrid.org/products/sbnd/sbndcode/v10_14_02_03/wire-cell-cfg WIRECELL_PATH
path-prepend "$D/cfg" WIRECELL_PATH
RUNDIR="$D/data/run-fixed-sp"; mkdir -p "$RUNDIR"; cd "$RUNDIR"
/usr/bin/time -v lar -c "$HERE/rerun-fixed-sp.fcl" -s "$D/data/evt-270-6-46.root" -n 1 \
    > "$D/data/fixed-sp.log" 2>&1
echo "rerun-fixed-sp.fcl rc=$?"
[ -e evt-270-6-46_fixed_sp.root ] && mv -f evt-270-6-46_fixed_sp.root "$D/data/"
ls -la "$D/data/evt-270-6-46_fixed_sp.root" 2>/dev/null | awk '{printf "  %.1f MB %s\n",$5/1048576,$NF}'
