#!/bin/bash
# Write the campaign's sp.root list (input for compare_wires_viewer --list).
#   ./campaign-splist.sh            -> <campaign>/sp-list.txt (both legs)
HERE=$(cd "$(dirname "$0")" && pwd); D=$(dirname "$HERE")
C="${CAMPAIGN_DIR:-$D/data/validation-20260812}"
OUT="$C/sp-list.txt"
{
  echo "# issue #10 validation campaign $(basename $C): per-event SP outputs."
  echo "# All four fixes on: NF partial_enable=false, W max_rms_cut=100,"
  echo "# SP roi_mad_rms=true, r_break_roi_loop_planes=[2,2,0]."
  echo "# Each file carries gauss + dnnsp (+ wiener); MC also has simchannel truth."
  echo "# Use:  serve-viewer.sh 5011 --list <this file> gauss dnnsp"
  for leg in mc data; do
    W="$C/$leg-worklist.txt"; [ -f "$W" ] || continue
    echo "# --- $leg ---"
    while read -r lbl rest; do
      [ -z "$lbl" ] && continue
      f="$C/$leg/$lbl/sp.root"; [ -e "$f" ] && echo "$f"
    done < "$W"
  done
} > "$OUT"
grep -c "^/" "$OUT" | xargs -I{} echo "sp-list.txt: {} files -> $OUT"
