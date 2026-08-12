#!/bin/bash
# Merge one leg's per-event mabc.zip files into a single BEE set and upload.
#   ./campaign-bee.sh <mc|data> [--no-upload]
# Each per-event zip holds data/0/0-<alg>.json (every event is index 0 in its own
# job), so re-index them 0..N-1 in worklist order before zipping, otherwise they
# would all collide on index 0.
set -eo pipefail
LEG="$1"; NOUP="$2"
HERE=$(cd "$(dirname "$0")" && pwd); D=$(dirname "$HERE")
C="$D/data/validation-20260812"
W="$C/$LEG-worklist.txt"
[ -f "$W" ] || { echo "no worklist: $W" >&2; exit 1; }
STAGE="$C/bee-$LEG"; rm -rf "$STAGE"; mkdir -p "$STAGE/data"
i=0; MAP="$C/bee-$LEG-index.txt"; : > "$MAP"
while read -r lbl rest; do
    [ -z "$lbl" ] && continue
    Z="$C/$LEG/$lbl/mabc.zip"
    if [ ! -e "$Z" ]; then echo "  MISSING $lbl (skipped, indices stay contiguous)"; continue; fi
    T=$(mktemp -d); unzip -o -q "$Z" -d "$T"
    mkdir -p "$STAGE/data/$i"
    for f in "$T"/data/0/0-*.json; do
        [ -e "$f" ] || continue
        b=$(basename "$f"); mv "$f" "$STAGE/data/$i/${i}-${b#0-}"
    done
    echo "$i $lbl" >> "$MAP"; echo "  idx $i = $lbl"
    rm -rf "$T"; i=$((i+1))
done < "$W"
cd "$STAGE"; zip -q -r "../bee-$LEG.zip" data
echo "built $C/bee-$LEG.zip with $i events (index map: $MAP)"
[ "$NOUP" = "--no-upload" ] && exit 0
cd "$C"; bash /exp/sbnd/app/users/yuhw/wcp-porting-img/upload-to-bee.sh "$C/bee-$LEG.zip"
