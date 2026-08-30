#!/bin/bash
# Resolve the first N files of the nueCC exclusive definition to /pnfs paths.
#   ./make-file-list.sh <out.lst> [N]
# samweb needs SL7 + the ups environment (source setup-local-opt.sh, then
# `setup sam_web_client`); it does NOT work from the bare build node, and
# `getent hosts samweb.fnal.gov` fails even where samweb works -- never use DNS
# as the reachability test.
OUT="${1:?out}"; N="${2:-1000}"
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1
setup sam_web_client >/dev/null 2>&1
export SAM_EXPERIMENT=sbnd EXPERIMENT=sbnd
DEF=aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_EX_nuecc_v10_14_02_05_reco1_sbnd
TMP=$(mktemp)
samweb list-definition-files "$DEF" 2>/dev/null | head -"$N" > "$TMP"
echo "  filenames: $(wc -l < "$TMP")"
# locate-file is one round trip per file; 16-way keeps 1000 to a few minutes.
export -f 2>/dev/null || true
cat "$TMP" | xargs -P 16 -I{} bash -c '
  d=$(samweb locate-file "{}" 2>/dev/null | head -1 | sed "s/^[a-z]*://; s/(.*)$//")
  [ -n "$d" ] && echo "$d/{}"
' > "$OUT.unsorted"
# keep samweb list order (the owner asked for the first 1000 in that order)
awk 'NR==FNR{p[$0]=NR; next} {n=$0; sub(/.*\//,"",n); print p[n]"\t"$0}' "$TMP" "$OUT.unsorted" \
  | sort -n | cut -f2 > "$OUT"
rm -f "$TMP" "$OUT.unsorted"
echo "  resolved: $(wc -l < "$OUT") paths -> $OUT"
