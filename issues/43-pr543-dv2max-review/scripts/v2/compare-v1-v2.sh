#!/bin/bash
# PR #543 re-review: v2 (PR head f3767016) vs v1 (feb3ddeb) outputs, per arm and input, value by value.
# Ignored: the build name (wct_version) and dl_weights (v2 adds @sha256:<manifest> and the new bundle path).
# Also pr-original (v2) vs master.  Run with the wire-cell-python venv (uproot).
D=/exp/sbnd/data/users/yuhw/production-prep/pr543-review; PY=/exp/sbnd/app/users/yuhw/wire-cell-python/venv/bin/python
IGN="Trun.wct_version recTreeWireCell.wc.Trun.wct_version Trun.dl_weights recTreeWireCell.wc.Trun.dl_weights"
for arm in pr-original pr-dv2_snap pr-dv2_split pr-dv2_split_move; do
  for i in $(ls $D/runs/$arm); do
    [ "$(cat $D/v2/runs/$arm/$i/rc 2>/dev/null)" = 0 ] || { echo -e "$arm\t$i\tNOT-RUN-OR-FAILED"; continue; }
    echo "$arm $i"
  done
done | grep -v NOT-RUN > $D/v2/cmp/todo.txt
cat $D/v2/cmp/todo.txt | xargs -P 12 -L 1 sh -c '$0 '"$D"'/compare-arms.py '"$D"'/runs/$1/$2 '"$D"'/v2/runs/$1/$2 --ignore '"$IGN"' 2>&1 | tail -1 | sed "s|^|$1\t$2\t|"' $PY > $D/v2/cmp/v1-vs-v2.tsv
ls $D/runs/master | xargs -P 12 -I{} sh -c '[ "$(cat '"$D"'/v2/runs/pr-original/{}/rc 2>/dev/null)" = 0 ] && '"$PY $D"'/compare-arms.py '"$D"'/runs/master/{} '"$D"'/v2/runs/pr-original/{} --ignore Trun.wct_version recTreeWireCell.wc.Trun.wct_version 2>&1 | tail -1 | sed "s|^|{}\t|"' > $D/v2/cmp/master-vs-v2original.tsv
