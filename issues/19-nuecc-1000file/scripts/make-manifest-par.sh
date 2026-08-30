#!/bin/bash
# Per-EVENT manifest from a file list, 16-way parallel.
#   ./make-manifest-par.sh <files.lst> <out.manifest>
# Lines: <file>\t<nskip_index>\t<run>\t<subrun>\t<event>
# RSE comes from EventAuxiliary and is SORTED into art's logical (FileIndex)
# order before the --nskip index is assigned -- see issue 18: art counts in
# RSE-sorted order, not Events-tree order, and the two differ in merged files.
LIST="${1:?list}"; OUT="${2:?out}"
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1
HERE="$(cd "$(dirname "$0")" && pwd)"
export HERE
cat "$LIST" | xargs -P 16 -I{} bash -c '
  python3 "$HERE/rse_list.py" "{}" 2>/dev/null | sort -k1,1n -k2,2n -k3,3n | \
    awk -v F="{}" "{printf \"%s\t%d\t%s\t%s\t%s\n\", F, NR-1, \$1, \$2, \$3}"
' > "$OUT"
echo "  manifest: $(wc -l < "$OUT") events from $(cut -f1 "$OUT" | sort -u | wc -l) files"
