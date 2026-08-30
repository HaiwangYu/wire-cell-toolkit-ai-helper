#!/usr/bin/env python3
"""Compare the physics of two arms event by event."""
import sys, glob, os, ROOT
ROOT.gErrorIgnoreLevel = ROOT.kFatal
a_dir, b_dir = sys.argv[1], sys.argv[2]
def sig(p):
    f = ROOT.TFile.Open(p)
    if not f or f.IsZombie(): return None
    d = {'cand': 0, 'enu': 0.0, 'numu': None, 'nue': None, 'npts': 0}
    tk = f.Get('T_kine')
    if tk and tk.GetEntries():
        tk.GetEntry(0); d['enu'] = tk.kine_reco_Enu; d['cand'] = 1 if tk.kine_reco_Enu > 0 else 0
    tt = f.Get('T_tagger')
    if tt and tt.GetEntries():
        tt.GetEntry(0); d['numu'] = tt.numu_score; d['nue'] = tt.nue_score
    tc = f.Get('T_rec_charge')
    if tc: d['npts'] = tc.GetEntries()
    f.Close(); return d
print("  %-22s %-28s %-28s" % ("event", "preflip", "sync"))
na = nb = flip = 0
for p in sorted(glob.glob(b_dir + '/tracking-pr/*.root')):
    nm = os.path.basename(p)
    A = sig(a_dir + '/tracking-pr/' + nm); B = sig(p)
    if A is None or B is None: continue
    na += A['cand']; nb += B['cand']
    if A['cand'] != B['cand']: flip += 1
    fa = ("Enu=%7.1f numu=%6.3f nue=%7.3f" % (A['enu'], A['numu'], A['nue'])) if A['numu'] is not None else "no candidate"
    fb = ("Enu=%7.1f numu=%6.3f nue=%7.3f" % (B['enu'], B['numu'], B['nue'])) if B['numu'] is not None else "no candidate"
    mark = "  <-- CHANGED" if (A['cand'] != B['cand'] or abs(A['enu'] - B['enu']) > 0.05) else ""
    print("  %-22s %-28s %-28s%s" % (nm.replace('tracking-pr_', '').replace('.root', ''), fa, fb, mark))
print("\n  candidates: preflip %d/10, sync %d/10, verdict flips %d" % (na, nb, flip))
