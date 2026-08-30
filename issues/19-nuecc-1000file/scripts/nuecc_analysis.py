#!/usr/bin/env python3
"""Signal efficiency + score distributions for the nueCC exclusive sample.

Every event here contains a true nueCC interaction (the sample is filtered), so
the fraction with a usable reconstruction IS the signal efficiency -- something
the CV and data campaigns could not measure.

"Usable" = kine_reco_Enu > 0, i.e. a reconstructed main vertex.  File size and
T_rec_charge>0 both over-count (issue 18): a tagger verdict with no main vertex
still books T_tagger's 1216 branches into a ~200 kB file.
"""
import sys, glob
from multiprocessing import Pool
def one(p):
    import ROOT
    ROOT.gErrorIgnoreLevel = ROOT.kFatal
    f = ROOT.TFile.Open(p)
    if not f or f.IsZombie(): return None
    r = {'enu': 0.0, 'numu': None, 'nue': None, 'npts': 0, 'trees': 0}
    r['trees'] = len(f.GetListOfKeys())
    tk = f.Get('T_kine')
    if tk and tk.GetEntries(): tk.GetEntry(0); r['enu'] = tk.kine_reco_Enu
    tt = f.Get('T_tagger')
    if tt and tt.GetEntries():
        tt.GetEntry(0); r['numu'] = tt.numu_score; r['nue'] = tt.nue_score
    tc = f.Get('T_rec_charge')
    if tc: r['npts'] = tc.GetEntries()
    f.Close(); return r

if __name__ == '__main__':
    files = sorted(glob.glob(sys.argv[1] + '/*.root'))
    with Pool(16) as pool: res = [r for r in pool.map(one, files, chunksize=32) if r]
    n = len(res)
    usable = [r for r in res if r['enu'] > 0]
    print("  events with output      : %d" % n)
    print("  usable reconstruction   : %d  = %.1f%%   <-- nueCC signal efficiency" % (len(usable), 100.*len(usable)/n))
    print("  (T_rec_charge>0)        : %d  = %.1f%%" % (sum(1 for r in res if r['npts']>0), 100.*sum(1 for r in res if r['npts']>0)/n))
    print("  (file has T_tagger)     : %d  = %.1f%%" % (sum(1 for r in res if r['numu'] is not None), 100.*sum(1 for r in res if r['numu'] is not None)/n))
    e = sorted(r['enu'] for r in usable)
    q = lambda f: e[min(len(e)-1, int(f*len(e)))]
    print("\n  kine_reco_Enu (usable): median %.0f  p10 %.0f  p90 %.0f  max %.0f MeV" % (q(.5), q(.1), q(.9), e[-1]))
    for lbl, key, floor in (('nue_score', 'nue', -15.0), ('numu_score', 'numu', None)):
        v = sorted(r[key] for r in usable)
        qq = lambda f: v[min(len(v)-1, int(f*len(v)))]
        line = "  %-11s median %6.3f  p10 %6.3f  p90 %6.3f  min %6.3f  max %6.3f" % (lbl, qq(.5), qq(.1), qq(.9), v[0], v[-1])
        if floor is not None:
            nf = sum(1 for x in v if abs(x - floor) < 1e-6)
            line += "   floored at %.1f: %d/%d = %.1f%%" % (floor, nf, len(v), 100.*nf/len(v))
        print(line)
    pos = sum(1 for r in usable if r['nue'] > 0)
    print("\n  nue_score > 0 (signal-like): %d/%d = %.1f%%" % (pos, len(usable), 100.*pos/len(usable)))
