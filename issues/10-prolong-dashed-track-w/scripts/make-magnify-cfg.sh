#!/bin/bash
# Generate a LOCAL WIRECELL_PATH cfg override that turns the SBND sim+NF+SP job
# into a full Magnify dump (every SP intermediate stage), without touching the
# shared sbndcode checkout.
#
# Background: the stock jsonnet defines the magnify sinks but leaves every
#   //sinks.*_pipe[n]
# line commented out, and `magoutput` is hard-coded to 'sbnd-data-check.root'.
# That is how w-gap/sbnd-data-check.root was made in Jun 2026 (the sink lines
# were uncommented in-place in the sbndcode checkout and later reverted, so the
# recipe was lost).  Here we keep the edit local and reproducible instead.
#
# What we change vs the CVMFS original:
#  1. magoutput            -> magnify-270-6-46.root
#  2. roi=="trad" override -> add use_roi_debug_mode:true and KEEP sp.jsonnet's
#     default *_tag values (the roi=="both" branch blanks tight_lf/cleanup_roi/
#     break_roi/shrink_roi/extend_roi tags, which would drop those traces).
#  3. uncomment sinks.{orig,raw,decon,debug}_pipe in the roi=="trad" graph
#     branch (the only branch with all four slots; roi=="both" is a g.intern
#     with explicit edges and no sink slots).
#  4. magnify-sinks.jsonnet: add 'decon_charge<n>' to the magdebug frame list
#     (the stock list omits it, yet sp.jsonnet does tag it).
#
# Result: 3 planes x 2 APAs x 12 stages = 72 TH2F
#   orig, raw, tight_lf, loose_lf, decon_charge, break_roi_1st, break_roi_2nd,
#   shrink_roi, extend_roi, cleanup_roi, gauss, wiener
set -e
HERE=$(cd "$(dirname "$0")" && pwd); D=$(dirname "$HERE")
SRC=/cvmfs/sbnd.opensciencegrid.org/products/sbnd/sbndcode/v10_14_02_03/wire-cell-cfg/pgrapher/experiment/sbnd
DST=$D/cfg/pgrapher/experiment/sbnd
mkdir -p "$DST"

J=$DST/wcls-sim-drift-depoflux-nf-sp.jsonnet
M=$DST/magnify-sinks.jsonnet
cp "$SRC/wcls-sim-drift-depoflux-nf-sp.jsonnet" "$J"
cp "$SRC/magnify-sinks.jsonnet"                 "$M"

# 1. output file name
sed -i "s|local magoutput = 'sbnd-data-check.root';|local magoutput = 'magnify-270-6-46.root';|" "$J"

# 2. roi=="trad" sp override: enable the ROI debug traces, keep default tags
perl -0pi -e 's/(else if roi == "trad" then \{\n\s*sparse: true,\n)(\};)/$1    use_roi_debug_mode: true,\n$2/' "$J"

# 3. uncomment the sink pipes, but ONLY inside the roi=="trad" GRAPH branch
#    (anchor on the last `else if roi == "trad" then` line so the earlier
#     sp-override branch and the multipass2 block are untouched)
#    NB: use '#' as the sed delimiter -- with 's|...|...|' the escaped '\|'
#    needed for BRE alternation collides with the delimiter and the whole
#    substitution silently does nothing.
TRAD=$(grep -n 'else if roi == "trad" then$' "$J" | tail -1 | cut -d: -f1)
sed -i "${TRAD},\$ s#// *sinks\.\(orig\|raw\|decon\|debug\)_pipe\[n\],#sinks.\1_pipe[n],#" "$J"

# 4. magdebug: also dump decon_charge
sed -i "s|'shrink_roi%d' %n, 'extend_roi%d' %n\]|'shrink_roi%d' %n, 'extend_roi%d' %n, 'decon_charge%d' %n]|" "$M"

echo "wrote override cfg under $D/cfg"
echo "--- verification ---"
grep -n "local magoutput" "$J"
sed -n "/else if roi == \"trad\" then {/,/};/p" "$J" | sed 's/^/    /'
grep -nE "^\s+sinks\.[a-z_]+_pipe\[n\]" "$J" | sed 's/^/    /'
grep -n "decon_charge" "$M" | sed 's/^/    /'
