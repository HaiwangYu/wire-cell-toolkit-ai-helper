#!/usr/bin/env python3
"""Deep comparison: exact equality across T_kine (21), T_tagger (1216) and a
hash of every T_rec_charge point -- not just the few numbers a table shows."""
import sys, os, glob, hashlib, ROOT
ROOT.gErrorIgnoreLevel = ROOT.kFatal
def deep(p):
    f = ROOT.TFile.Open(p)
    if not f or f.IsZombie(): return None
    out = {}
    for tn in ('T_kine', 'T_tagger'):
        t = f.Get(tn)
        if not (t and t.GetEntries()): out[tn] = None; continue
        t.GetEntry(0)
        vals = []
        for b in t.GetListOfBranches():
            nm = b.GetName()
            try:
                v = getattr(t, nm)
                if hasattr(v, '__len__') and not isinstance(v, str):
                    vals.append((nm, tuple(round(float(x), 6) for x in v)))
                else:
                    vals.append((nm, round(float(v), 6)))
            except Exception:
                vals.append((nm, 'unreadable'))
        out[tn] = hashlib.md5(repr(sorted(vals)).encode()).hexdigest()[:12]
        out[tn + '_n'] = len(vals)
    tc = f.Get('T_rec_charge')
    if tc:
        pts = []
        for i in range(tc.GetEntries()):
            tc.GetEntry(i)
            pts.append((round(tc.x,5), round(tc.y,5), round(tc.z,5), round(tc.q,5),
                        int(tc.cluster_id), int(tc.flag_vertex), int(tc.flag_shower)))
        out['charge_n'] = len(pts)
        out['charge_hash'] = hashlib.md5(repr(pts).encode()).hexdigest()[:12]
    else:
        out['charge_n'] = -1; out['charge_hash'] = None
    f.Close(); return out
W, arm_dir, label = sys.argv[1], sys.argv[2], sys.argv[3]
print("### Xin 2-step vs %s" % label)
ident = 0; diff = 0; n = 0
for d in sorted(glob.glob(W + '/evt_*')):
    tag = os.path.basename(d)[4:]
    a = deep(d + '/tracking-pr.root')
    b = deep(arm_dir + '/tracking-pr_%s.root' % tag)
    if not a or not b: continue
    n += 1
    keys = ('T_kine', 'T_tagger', 'charge_n', 'charge_hash')
    same = all(a.get(k) == b.get(k) for k in keys)
    if same:
        ident += 1
        print("  %-16s IDENTICAL  (T_kine+T_tagger hashes match, %s charge pts)" % (tag, a['charge_n']))
    else:
        diff += 1
        bad = [k for k in keys if a.get(k) != b.get(k)]
        print("  %-16s DIFFERS in %s" % (tag, bad))
        if 'charge_n' in bad: print("      charge points: %s vs %s" % (a['charge_n'], b['charge_n']))
print("  => exact match %d/%d, differ %d/%d\n" % (ident, n, diff, n))
