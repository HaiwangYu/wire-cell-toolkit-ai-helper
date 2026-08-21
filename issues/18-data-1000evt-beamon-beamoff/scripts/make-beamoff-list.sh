#!/bin/bash
# Resolve the beam-off SAM definition to a /pnfs path list.
#
# MUST BE RUN BY THE USER, not by the agent: samweb's hosts do not resolve from
# this build node (no DNS for *.fnal.gov SAM hosts, inside or outside the SL7
# container; verified 2026-08-21).  Everything downstream of this list is
# automated.
#
#   ./make-beamoff-list.sh [outfile]
#
# Output: one /pnfs path per line, ready for prep-beam-off.sh.
OUT="${1:-/exp/sbnd/data/users/yuhw/production-prep/img-clus-match-tag-pr-data-1000evt-2026-08-21/lists/beam-off-files.lst}"
DEF=data_MCP2025C_FallValidationII_RollingDev_offbeamlight_v10_14_00_reco1_sbnd

source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
setup sam_web_client
export SAM_EXPERIMENT=sbnd EXPERIMENT=sbnd

echo "definition: $DEF"
samweb describe-definition "$DEF" || { echo "cannot reach SAM / no such definition"; exit 1; }
echo "files in definition: $(samweb count-definition-files "$DEF")"

TMP=$(mktemp)
samweb list-definition-files "$DEF" > "$TMP" || exit 1
echo "listed $(wc -l < "$TMP") file name(s); resolving to /pnfs paths ..."

: > "$OUT"
n=0
while read -r fn; do
    [ -z "$fn" ] && continue
    # locate-file prints e.g. "enstore:/pnfs/sbn/data_add/...(...)"; keep the dir
    d=$(samweb locate-file "$fn" 2>/dev/null | head -1 | sed 's/^[a-z]*://; s/(.*)$//')
    [ -n "$d" ] && { echo "$d/$fn" >> "$OUT"; n=$((n+1)); }
    # 60 files is ample: the beam-on sample reached 1000 events from 20 files,
    # and prep-beam-off.sh caps at 1000 events with `lar -n 1000`, so any
    # surplus files are simply never read.
    [ "$n" -ge 60 ] && break
done < "$TMP"
rm -f "$TMP"
echo "wrote $n path(s) -> $OUT"
head -3 "$OUT"
