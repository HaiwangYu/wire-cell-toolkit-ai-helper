#!/bin/bash
# Count Events-tree entries per file, 10 concurrent (dCache opens are the cost).
#   ./count-events.sh <list> <out.tsv>
# GOTCHA: capture positional params BEFORE sourcing .bashrc/ups -- sourcing
# clobbers $1/$2 (we have seen $1 become "autoexpand").
LIST="$1"; OUT="$2"
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1
: > "$OUT"
one () { local n; n=$(python3 -c "
import ROOT
f=ROOT.TFile.Open('$1')
t=f.Get('Events') if f and not f.IsZombie() else None
print(t.GetEntries() if t else -1)" 2>/dev/null | tail -1); printf "%s\t%s\n" "$n" "$1" >> "$OUT"; }
i=0
while read -r f; do
  one "$f" & i=$((i+1))
  (( i % 10 == 0 )) && wait
done < "$LIST"
wait
