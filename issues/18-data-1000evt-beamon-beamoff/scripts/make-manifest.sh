#!/bin/bash
# Build a per-EVENT task manifest from a list of artROOT files.
#   ./make-manifest.sh <files.lst> <out.manifest> [max_events]
# Each output line:  <file>\t<event_index_in_file>\t<run>\t<subrun>\t<event>
#
# Why a manifest instead of the MC harness's file cursor: the data samples are
# ONE merged artROOT file holding 1000 events, so work must be distributed by
# event index, not by file.  Building it up front also means the RSE is known
# before any lar job runs, so every output file can be named for its event
# (RSE from EventAuxiliary, never from the log -- see issue 16).
#
# CRITICAL, learned the hard way 2026-08-21: `lar --nskip k` counts in art's
# LOGICAL order, which is the FileIndex order = sorted by (run, subrun, event).
# EventAuxiliary, however, is read in Events-TREE order = the order events were
# written.  For a single-run MC file the two coincide, so the issue-16 harness
# was correct by luck.  For a MERGED data file they do NOT: in
# data_MCP2025C_reco1_frameshift_2nd1k_part1.root the tree starts with run
# 18259 while art starts with run 18255, so --nskip 0 processed tree entry 300.
# Unsorted, every one of the 1000 outputs would have carried the wrong RSE in
# its filename while being internally self-consistent -- invisible unless
# cross-checked.  Hence the sort below, AND the harness's per-event
# verification of the manifest RSE against the job's own Trun.
LIST="$1"; OUT="$2"; MAX="${3:-0}"
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1
RSEPY="$(cd "$(dirname "$0")" && pwd)/rse_list.py"
: > "$OUT"
n=0
while read -r f; do
    [ -z "$f" ] && continue
    # sort into art's logical order, THEN assign the --nskip index
    k=0
    while read -r run sub evt; do
        [ -z "$run" ] && continue
        printf "%s\t%d\t%s\t%s\t%s\n" "$f" "$k" "$run" "$sub" "$evt" >> "$OUT"
        k=$((k+1)); n=$((n+1))
        if [ "$MAX" -gt 0 ] && [ "$n" -ge "$MAX" ]; then break; fi
    done < <(python3 "$RSEPY" "$f" 2>/dev/null | sort -k1,1n -k2,2n -k3,3n)
    if [ "$MAX" -gt 0 ] && [ "$n" -ge "$MAX" ]; then break; fi
done < "$LIST"
echo "manifest: $n event(s) -> $OUT (sorted into art --nskip order)"
