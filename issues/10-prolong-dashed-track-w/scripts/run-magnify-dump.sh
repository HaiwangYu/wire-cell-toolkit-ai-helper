#!/bin/bash
# Produce the full Magnify dump (all SP intermediate stages) for run 270/6/46.
# Uses the LOCAL cfg override from make-magnify-cfg.sh -- the shared sbndcode
# checkout is NOT modified.
#
# Output: data/magnify-270-6-46.root  (72 TH2F = 3 planes x 2 APAs x 12 stages)
#   orig, raw, tight_lf, loose_lf, decon_charge, break_roi_1st, break_roi_2nd,
#   shrink_roi, extend_roi, cleanup_roi, gauss, wiener
# View with:  standalone-sample/w-gap/vis_waveforms.py -f <file> -c <channel>
#             standalone-sample/plot_magnify.py --input <file> ...
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1
set -e
HERE=$(cd "$(dirname "$0")" && pwd); D=$(dirname "$HERE")
# cvmfs sbndcode cfg first (wires v0206 -- the local checkout is stale at v0202),
# then OUR override on top so the magnify-enabled jsonnets win.
path-prepend /cvmfs/sbnd.opensciencegrid.org/products/sbnd/sbndcode/v10_14_02_03/wire-cell-cfg WIRECELL_PATH
path-prepend "$D/cfg" WIRECELL_PATH
cd "$D/data"
/usr/bin/time -v lar -c "$HERE/magnify-dump.fcl" \
    -s "$D/data/evt-270-6-46.root" -n 1 \
    > "$D/data/magnify-dump.log" 2>&1
echo "lar rc=$?"
ls -la magnify-270-6-46.root 2>/dev/null | awk '{printf "  %.1f MB  %s\n",$5/1048576,$NF}'
