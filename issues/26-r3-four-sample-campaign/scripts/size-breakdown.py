#!/usr/bin/env python3
"""size-breakdown.py <label> <run-dir> <out.json>
Per-sample output size breakdown: dir sizes, Bee zip per-layer (compressed / uncompressed), tracking-pr.root per-TTree (zip bytes / tot bytes), and
candidate vs non-candidate split. Walks EVERY file (zip central directory only; ROOT keys only), no decompression."""
import os, sys, glob, json, zipfile, re, collections
import ROOT; ROOT.gErrorIgnoreLevel = ROOT.kError
label, run, out = sys.argv[1:4]

def du(path):
    tot = 0
    for dp, dn, fn in os.walk(path):
        for f in fn:
            try: tot += os.lstat(os.path.join(dp, f)).st_size
            except OSError: pass
    return tot

res = {'label': label, 'run': run, 'dirs': {}, 'bee': {}, 'root': {}}
for d in sorted(os.listdir(run)):
    p = os.path.join(run, d)
    res['dirs'][d] = du(p) if os.path.isdir(p) else os.lstat(p).st_size

# --- Bee zips: per layer, compressed + uncompressed, over all zips
lay = collections.defaultdict(lambda: [0, 0, 0])   # layer -> [n, compressed, uncompressed]
pat = re.compile(r'^[^/]+/\d+/\d+-(.*)$')
zips = sorted(glob.glob(run + '/bee/*.zip')); nz = 0; ztot = 0
for z in zips:
    try:
        zf = zipfile.ZipFile(z)
    except zipfile.BadZipFile:
        continue
    nz += 1; ztot += os.lstat(z).st_size
    for zi in zf.infolist():
        m = pat.match(zi.filename); name = m.group(1) if m else zi.filename
        L = lay[name]; L[0] += 1; L[1] += zi.compress_size; L[2] += zi.file_size
res['bee'] = {'nzips': nz, 'total_bytes': ztot, 'layers': {k: {'n': v[0], 'compressed': v[1], 'uncompressed': v[2]} for k, v in lay.items()}}

# --- tracking-pr.root: per tree zip/tot bytes, split candidate (has T_kine) vs not
trees = {'cand': collections.defaultdict(lambda: [0, 0, 0]), 'noncand': collections.defaultdict(lambda: [0, 0, 0])}
roots = sorted(glob.glob(run + '/tracking-pr/*.root')); nr = {'cand': 0, 'noncand': 0}; rtot = {'cand': 0, 'noncand': 0}
for p in roots:
    f = ROOT.TFile.Open(p)
    if not f or f.IsZombie(): continue
    keys = [k.GetName() for k in f.GetListOfKeys()]
    cls = 'cand' if 'T_kine' in keys else 'noncand'
    nr[cls] += 1; rtot[cls] += os.lstat(p).st_size
    for k in keys:
        t = f.Get(k)
        if not t or not t.InheritsFrom('TTree'): continue
        T = trees[cls][k]; T[0] += 1; T[1] += t.GetZipBytes(); T[2] += t.GetTotBytes()
    f.Close()
res['root'] = {c: {'nfiles': nr[c], 'total_bytes': rtot[c], 'trees': {k: {'n': v[0], 'zip': v[1], 'tot': v[2]} for k, v in trees[c].items()}} for c in ('cand', 'noncand')}
json.dump(res, open(out, 'w'), indent=1)
print(label, 'done: zips', nz, 'roots', sum(nr.values()))
