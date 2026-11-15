"""ai-helper #47 (prod_aurora): per-call truth label of the aurora_space hold-out calls, read from Sne's export.
Reads only calls/{runNo,subRunNo,eventNo,nu_index,pass,label_ok,label_xyz} of every shard (no clouds), keeps the keys
of --pred (refit_test_fold0.csv), first copy of a key wins (as the cache). Writes key,lx,ly,lz,shard.
usage: python -I labels_from_export.py EXPORT_DIR PRED_CSV OUT_CSV"""
import csv, glob, sys
from pathlib import Path
import h5py
exp, pred_csv, out = sys.argv[1:4]
want = {r["key"] for r in csv.DictReader(open(pred_csv))}
got = {}
for sample, sd in (("nue", "nuecc"), ("bnb", "bnb")):
    for p in sorted(glob.glob(f"{exp}/aurora_{sd}.s????.h5")):
        with h5py.File(p, "r") as h:
            c = h["calls"]
            cols = [c[k][()] for k in ("runNo", "subRunNo", "eventNo", "nu_index", "pass")]
            ok, lab = c["label_ok"][()], c["label_xyz"][()]
            for i in range(len(ok)):
                k = f"{sample}:{cols[0][i]}:{cols[1][i]}:{cols[2][i]}:{cols[3][i]}:p{cols[4][i]}"
                if k in want and k not in got and ok[i]:
                    got[k] = (*map(float, lab[i]), Path(p).name)
        print(p, len(got), flush=True)
with open(out, "w") as f:
    w = csv.writer(f); w.writerow(["key", "lx", "ly", "lz", "shard"])
    for k in sorted(got): w.writerow([k, *got[k]])
print("labels", len(got), "of", len(want), "missing", len(want - set(got)))
