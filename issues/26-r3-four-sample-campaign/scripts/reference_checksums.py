#!/usr/bin/env python3
"""reference_checksums.py <run-dir> > checksums.txt — per event: md5 of every Bee JSON member, and content hashes of
tracking-pr.root trees as deep_compare computes them (T_kine/T_tagger branch values, T_rec_charge points). Host-independent."""
import sys, glob, os, zipfile, hashlib, re, ROOT; ROOT.gErrorIgnoreLevel = ROOT.kError
R = sys.argv[1]; pat = re.compile(r'^([^/]+)/(\d+)/(\d+)-(.*)$')
for z in sorted(glob.glob(R+'/bee/*.zip')):
    zf = zipfile.ZipFile(z)
    for n in sorted(zf.namelist()):
        m = pat.match(n); print('bee', os.path.basename(z), m.group(4) if m else n, hashlib.md5(zf.read(n)).hexdigest())
for p in sorted(glob.glob(R+'/tracking-pr/*.root')):
    f = ROOT.TFile.Open(p); keys = sorted(k.GetName() for k in f.GetListOfKeys()); print('root', os.path.basename(p), 'trees', ','.join(keys))
    for tn in ('T_kine', 'T_tagger', 'T_rec_charge'):
        t = f.Get(tn)
        if not t: continue
        h = hashlib.md5()
        for i in range(t.GetEntries()):
            t.GetEntry(i)
            for b in t.GetListOfBranches():
                v = getattr(t, b.GetName())
                try: h.update(repr(float(v)).encode())
                except Exception: h.update(repr(list(v) if hasattr(v, '__len__') else v).encode())
        print('root', os.path.basename(p), tn, t.GetEntries(), h.hexdigest())
