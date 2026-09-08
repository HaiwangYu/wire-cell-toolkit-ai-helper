#!/bin/bash
# Package the per-event Bee zips and nugraph h5s into two multi-event Bee zips.
#
#   ./package-bee.sh <rundir> <orderfile> <label>
#
# <orderfile> lines are "<idx> <run> <sub> <evt>" and set the Bee event order.
# merge_bee.py renumbers each input to its POSITION in the argument list, so the
# order file must be sorted by the index you want and be contiguous from 0 for
# the emitted Bee index to equal <idx>; that is asserted below rather than
# assumed.  Use lists/bee-orig-order.txt to reproduce the numbering of the
# source Bee set 763d6e03 (what a reviewer cross-referencing the two sets
# needs); lists/bee-order.txt is the RSE-sorted alternative.
set -uo pipefail
RUN="$1"; ORDER="$2"; LABEL="$3"
CH="$(cd "$(dirname "$0")/.." && pwd)"

if ! awk '{if ($1 != NR-1) {print "  order file is not contiguous from 0 at line " NR; exit 1}}' "$ORDER"; then
    echo "ERROR: Bee index would not match the order file's idx column." >&2
    exit 1
fi

beelist=(); nulist=(); missing=0
while read -r idx run sub evt; do
    tag="r${run}_s${sub}_e${evt}"
    b="$RUN/bee/bee_${tag}.zip"; n="$RUN/nugraph/nugraph_${tag}.h5"
    if [ ! -f "$b" ]; then
        # A gap would shift every later event's Bee index, silently
        # mis-numbering the set -- refuse rather than emit a wrong mapping.
        echo "ERROR: no bee zip for idx $idx ($run/$sub/$evt)" >&2; missing=1; continue
    fi
    beelist+=("$b")
    [ -f "$n" ] && nulist+=("$n")
done < "$ORDER"
[ "$missing" -ne 0 ] && { echo "ERROR: aborting on missing input(s)." >&2; exit 1; }

python3 "$CH/scripts/merge_bee.py"      "$CH/bee-${LABEL}.zip"     "${beelist[@]}" | tail -2
python3 "$CH/scripts/nugraph_to_bee.py" "$CH/nugraph-${LABEL}.zip" "${nulist[@]}" | tail -1
echo "  bee events: ${#beelist[@]}   nugraph events: ${#nulist[@]}"
ls -la "$CH/bee-${LABEL}.zip" "$CH/nugraph-${LABEL}.zip" | awk '{printf "  %-40s %.1f MB\n",$NF,$5/1048576}'
