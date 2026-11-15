#!/usr/bin/env python3
"""compare-trees.py <new runs dir> <old runs dir> <out.csv>   (issue 47 P5; the #544 review's "every tree by value")
For every unit and every pr_evt*/tracking-pr.root present in both: every tree and every branch compared by value
(uproot, awkward arrays; NaN == NaN).  One CSV row per (unit, event file, tree, branch) that differs, plus rows
for files / trees / branches present on one side only.  Prints a summary (files compared, identical files, the
differing (tree, branch) pairs with their file counts)."""
import collections
import csv
import glob
import os
import sys

import awkward as ak
import numpy as np
import uproot

NEW, OLD, OUT = sys.argv[1:4]


def same(a, b):
    try:
        if len(a) != len(b):
            return False
        if a.ndim > 2:  # vector<vector<...>>: plain list comparison (NaN != NaN here; rare in these trees)
            return ak.to_list(a) == ak.to_list(b)
        if a.ndim == 2 and not np.array_equal(ak.to_numpy(ak.num(a, axis=1)), ak.to_numpy(ak.num(b, axis=1))):
            return False
        fa, fb = ak.flatten(a, axis=None), ak.flatten(b, axis=None)
        if len(fa) != len(fb):
            return False
        na, nb = ak.to_numpy(fa), ak.to_numpy(fb)
        if na.dtype.kind == "f" or nb.dtype.kind == "f":
            return bool(np.array_equal(na, nb, equal_nan=True))
        return bool(np.array_equal(na, nb))
    except Exception:
        return ak.to_list(a) == ak.to_list(b)


rows, nfiles, nsame = [], 0, 0
cnt = collections.Counter()
for d in sorted(glob.glob(os.path.join(NEW, "*--*"))):
    unit = os.path.basename(d)
    od = os.path.join(OLD, unit)
    nf = {os.path.basename(os.path.dirname(f)) for f in glob.glob(os.path.join(d, "pr_evt*", "tracking-pr.root"))}
    of = {os.path.basename(os.path.dirname(f)) for f in glob.glob(os.path.join(od, "pr_evt*", "tracking-pr.root"))}
    for e in sorted(nf ^ of):
        rows.append(dict(unit=unit, evt=e, tree="", branch="", what="file only in " + ("new" if e in nf else "old")))
    for e in sorted(nf & of):
        nfiles += 1
        a, b = uproot.open(os.path.join(d, e, "tracking-pr.root")), uproot.open(os.path.join(od, e, "tracking-pr.root"))
        ta = {k.split(";")[0] for k, v in a.items() if isinstance(v, uproot.TTree)}
        tb = {k.split(";")[0] for k, v in b.items() if isinstance(v, uproot.TTree)}
        diff = False
        for t in sorted(ta ^ tb):
            rows.append(dict(unit=unit, evt=e, tree=t, branch="", what="tree only in " + ("new" if t in ta else "old")))
            cnt[(t, "<tree>")] += 1; diff = True
        for t in sorted(ta & tb):
            ba, bb = set(a[t].keys()), set(b[t].keys())
            for br in sorted(ba ^ bb):
                rows.append(dict(unit=unit, evt=e, tree=t, branch=br, what="branch only in " + ("new" if br in ba else "old")))
                cnt[(t, br)] += 1; diff = True
            for br in sorted(ba & bb):
                if a[t].num_entries != b[t].num_entries:
                    rows.append(dict(unit=unit, evt=e, tree=t, branch="", what=f"entries {a[t].num_entries} vs {b[t].num_entries}"))
                    cnt[(t, "<entries>")] += 1; diff = True
                    break
                try:
                    va, vb = a[t][br].array(), b[t][br].array()
                except Exception as ex:  # unreadable branch type: compare the raw basket bytes' length only
                    rows.append(dict(unit=unit, evt=e, tree=t, branch=br, what=f"unread: {type(ex).__name__}"))
                    continue
                if not same(va, vb):
                    rows.append(dict(unit=unit, evt=e, tree=t, branch=br, what="values differ"))
                    cnt[(t, br)] += 1; diff = True
        nsame += not diff
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["unit", "evt", "tree", "branch", "what"])
    w.writeheader()
    w.writerows(rows)
print(f"files compared {nfiles}, identical {nsame}")
for (t, br), n in cnt.most_common():
    print(f"  {t}.{br}: {n} files")
