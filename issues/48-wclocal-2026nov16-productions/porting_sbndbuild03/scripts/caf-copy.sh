#!/bin/bash
# Issue 48: copy the planned merged CAFs to persistent, then check dCache's ADLER32 of each copy against
# its source (porting_sbndbuild03).  Only ever writes under .../persistent/.../prod-fermigrid/WCLocal2026Nov16/.
#   caf-copy.sh copy   <plan.tsv> [jobs]   cp each src -> dst unless dst exists with the source's size
#   caf-copy.sh verify <plan.tsv> <out.tsv> [jobs]  sample id size src_adler dst_adler OK|BAD|MISSING
set -u
ck() { local f=$1; cat "$(dirname "$f")/.(get)($(basename "$f"))(checksum)" 2>/dev/null | grep -o 'ADLER32:[0-9a-f]*' | head -1; }
export -f ck
case $1 in
copy) xargs -a "$2" -d '\n' -P "${3:-8}" -n 1 bash -c '
  IFS=$'"'"'\t'"'"' read -r s i src dst frm st <<< "$0"
  case $dst in /pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/WCLocal2026Nov16/*) ;; *) echo "REFUSE $dst"; exit 0;; esac
  [ -f "$dst" ] && [ "$(stat -c %s "$dst")" = "$(stat -c %s "$src")" ] && exit 0
  mkdir -p "$(dirname "$dst")" && cp "$src" "$dst" || echo "CPFAIL $s $i"' ;;
verify) xargs -a "$2" -d '\n' -P "${4:-8}" -n 1 bash -c '
  IFS=$'"'"'\t'"'"' read -r s i src dst frm st <<< "$0"
  if [ ! -f "$dst" ]; then printf "%s\t%s\t0\t-\t-\tMISSING\n" "$s" "$i"; exit 0; fi
  a=$(ck "$src"); b=$(ck "$dst"); z=$(stat -c %s "$dst")
  [ -n "$a" ] && [ "$a" = "$b" ] && [ "$z" = "$(stat -c %s "$src")" ] && v=OK || v=BAD
  printf "%s\t%s\t%s\t%s\t%s\t%s\n" "$s" "$i" "$z" "${a:--}" "${b:--}" "$v"' > "$3" ;;
*) echo "usage: caf-copy.sh copy|verify ..." >&2; exit 2 ;;
esac
