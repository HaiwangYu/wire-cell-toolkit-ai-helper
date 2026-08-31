#!/usr/bin/env python3
"""Is nue_score = -15 a CLIP on a discriminant, or a 'not evaluated' sentinel?
A clip shows a pile-up at BOTH ends and a populated middle; a sentinel shows one
spike and nothing near it."""
import sys, glob, collections
from multiprocessing import Pool
def read(p):
    import ROOT
    ROOT.gErrorIgnoreLevel = ROOT.kFatal
    f = ROOT.TFile.Open(p); 
    if not f or f.IsZombie(): return None
    tk=f.Get('T_kine'); tt=f.Get('T_tagger')
    if not (tk and tk.GetEntries() and tt and tt.GetEntries()): f.Close(); return None
    tk.GetEntry(0); tt.GetEntry(0)
    r=(tk.kine_reco_Enu, tt.nue_score, tt.numu_score) if tk.kine_reco_Enu>0 else None
    f.Close(); return r
if __name__=='__main__':
    files=sorted(glob.glob(sys.argv[1]+'/*.root'))
    with Pool(16) as pool: v=[x for x in pool.map(read,files,chunksize=32) if x]
    nue=[x[1] for x in v]; n=len(nue)
    c=collections.Counter(round(x,4) for x in nue)
    print("  %s : %d candidates" % (sys.argv[2], n))
    print("    most common nue_score values:")
    for val,cnt in c.most_common(5):
        print("      %+9.4f : %5d  (%.1f%%)" % (val,cnt,100.*cnt/n))
    interior=[x for x in nue if -14.9 < x < 4.30]
    print("    strictly interior (-14.9 < s < 4.30): %d = %.1f%%" % (len(interior),100.*len(interior)/n))
    if interior:
        interior.sort(); q=lambda f: interior[min(len(interior)-1,int(f*len(interior)))]
        print("      interior median %+.3f  p10 %+.3f  p90 %+.3f" % (q(.5),q(.1),q(.9)))
