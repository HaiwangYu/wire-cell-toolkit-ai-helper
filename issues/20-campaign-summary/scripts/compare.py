#!/usr/bin/env python3
"""Compare Xin's 2-step against our synchronised 1-step, event by event."""
import sys, os, glob, ROOT
ROOT.gErrorIgnoreLevel = ROOT.kFatal
def sig(p):
    f = ROOT.TFile.Open(p)
    if not f or f.IsZombie(): return None
    d = {'trees': sorted(k.GetName() for k in f.GetListOfKeys()), 'enu': None,
         'numu': None, 'nue': None, 'npts': 0, 'rse': None}
    tr = f.Get('Trun')
    if tr and tr.GetEntries(): tr.GetEntry(0); d['rse'] = (tr.runNo, tr.subRunNo, tr.eventNo)
    tk = f.Get('T_kine')
    if tk and tk.GetEntries(): tk.GetEntry(0); d['enu'] = tk.kine_reco_Enu
    tt = f.Get('T_tagger')
    if tt and tt.GetEntries(): tt.GetEntry(0); d['numu'] = tt.numu_score; d['nue'] = tt.nue_score
    tc = f.Get('T_rec_charge')
    if tc: d['npts'] = tc.GetEntries()
    f.Close(); return d
W, ONE = sys.argv[1], sys.argv[2]
print("  %-16s %-34s %-34s %s" % ("event", "Xin 2-step", "our 1-step (sync)", "verdict"))
agree = disagree = 0
for d in sorted(glob.glob(W + '/evt_*')):
    tag = os.path.basename(d)[4:]
    a = sig(d + '/tracking-pr.root')
    b = sig(ONE + '/tracking-pr_%s.root' % tag)
    if not a or not b: print("  %-16s MISSING" % tag); continue
    ca = a['enu'] is not None and a['enu'] > 0
    cb = b['enu'] is not None and b['enu'] > 0
    fa = ("Enu=%7.1f numu=%+6.3f nue=%+7.3f" % (a['enu'], a['numu'], a['nue'])) if ca else "no candidate"
    fb = ("Enu=%7.1f numu=%+6.3f nue=%+7.3f" % (b['enu'], b['numu'], b['nue'])) if cb else "no candidate"
    if ca != cb:
        v = "CANDIDATE MISMATCH"; disagree += 1
    elif not ca:
        v = "agree (both none)"; agree += 1
    else:
        de = abs(a['enu'] - b['enu']); dn = abs(a['numu'] - b['numu']); du = abs(a['nue'] - b['nue'])
        if de < 0.05 and dn < 1e-3 and du < 1e-3:
            v = "IDENTICAL"; agree += 1
        else:
            v = "differ: dEnu=%.2f dnumu=%.4f dnue=%.4f" % (de, dn, du); disagree += 1
    print("  %-16s %-34s %-34s %s" % (tag, fa, fb, v))
    if a['rse'] != b['rse']: print("      RSE MISMATCH %s vs %s" % (a['rse'], b['rse']))
print("\n  agree %d/10, disagree %d/10" % (agree, agree + disagree - agree + disagree - disagree if False else disagree))
