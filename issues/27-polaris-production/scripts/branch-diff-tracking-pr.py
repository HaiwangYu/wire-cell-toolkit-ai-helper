#!/usr/bin/env python3
"""Branch-level diff of tracking-pr.root trees between two arms (ROOT only, no uproot).
usage: tagger_branch_diff.py <W: dir with evt_<e>/tracking-pr.root> <arm: dir with tracking-pr_<e>.root> [trees...]
Reports, per (tree, branch), the number of events it differs in and the max abs / rel difference."""
import sys, os, glob, math, ROOT
ROOT.gErrorIgnoreLevel = ROOT.kFatal
W, ARM = sys.argv[1], sys.argv[2]
TREES = sys.argv[3:] or ['T_tagger', 'T_kine', 'T_cluster', 'Trun']
def vals(t, nm):
    v = getattr(t, nm)
    if hasattr(v, '__len__') and not isinstance(v, str):
        return [float(x) for x in v]
    return [float(v)]
diffs = {}   # (tree, branch) -> [nevt, maxabs, maxrel, example]
nev = 0
for d in sorted(glob.glob(W + '/evt_*')):
    e = os.path.basename(d)[4:]
    fa = ROOT.TFile.Open(d + '/tracking-pr.root'); fb = ROOT.TFile.Open(ARM + '/tracking-pr_%s.root' % e)
    if not fa or not fb: continue
    nev += 1
    for tn in TREES:
        ta, tb = fa.Get(tn), fb.Get(tn)
        if not ta or not tb: continue
        n = min(ta.GetEntries(), tb.GetEntries())
        if ta.GetEntries() != tb.GetEntries():
            diffs.setdefault((tn, '<entries>'), [0, 0, 0, '']); diffs[(tn, '<entries>')][0] += 1
        for b in ta.GetListOfBranches():
            nm = b.GetName()
            mx = mr = 0.0; hit = False; ex = ''
            for i in range(n):
                ta.GetEntry(i); tb.GetEntry(i)
                try: a = vals(ta, nm); c = vals(tb, nm)
                except Exception: continue
                if len(a) != len(c):
                    hit = True; ex = 'len %d vs %d' % (len(a), len(c)); break
                for x, y in zip(a, c):
                    if x == y or (math.isnan(x) and math.isnan(y)): continue
                    hit = True; da = abs(x - y); mx = max(mx, da)
                    mr = max(mr, da / max(abs(x), abs(y), 1e-300))
                    if not ex: ex = '%s: %.9g vs %.9g' % (e, x, y)
            if hit:
                r = diffs.setdefault((tn, nm), [0, 0.0, 0.0, ex]); r[0] += 1; r[1] = max(r[1], mx); r[2] = max(r[2], mr)
print("events compared:", nev)
print("%-12s %-36s %6s %12s %12s  %s" % ('tree', 'branch', 'nevt', 'max_abs', 'max_rel', 'example (W vs arm)'))
for (tn, nm), (k, mx, mr, ex) in sorted(diffs.items(), key=lambda kv: (-kv[1][0], kv[0])):
    print("%-12s %-36s %6d %12.4g %12.4g  %s" % (tn, nm, k, mx, mr, ex))
print("differing (tree,branch) pairs:", len(diffs))
