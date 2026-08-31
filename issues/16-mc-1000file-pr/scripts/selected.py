#!/usr/bin/env python3
"""Rate of events passing a nue_score > 0 selection -- the discriminant's own
verdict, not the raw candidate count.  A candidate whose nue_score saturates
negative is a rejected background event, not a false positive."""
import sys, glob
from multiprocessing import Pool
def read(p):
    import ROOT
    ROOT.gErrorIgnoreLevel = ROOT.kFatal
    f=ROOT.TFile.Open(p)
    if not f or f.IsZombie(): return (0,0,0)
    tk=f.Get('T_kine'); tt=f.Get('T_tagger')
    cand=sel=numu_sel=0
    if tk and tk.GetEntries() and tt and tt.GetEntries():
        tk.GetEntry(0); tt.GetEntry(0)
        if tk.kine_reco_Enu>0:
            cand=1
            sel = 1 if tt.nue_score>0 else 0
            numu_sel = 1 if tt.numu_score>0 else 0
    f.Close(); return (cand,sel,numu_sel)
if __name__=='__main__':
    files=sorted(glob.glob(sys.argv[1]+'/*.root'))
    with Pool(16) as pool: v=pool.map(read,files,chunksize=32)
    n=len(v); c=sum(x[0] for x in v); s=sum(x[1] for x in v); m=sum(x[2] for x in v)
    print("  %-18s n=%5d  candidates %5d (%5.1f%%)  nue_score>0 %5d (%5.2f%%)  numu_score>0 %5d (%5.1f%%)"
          %(sys.argv[2],n,c,100.*c/n,s,100.*s/n,m,100.*m/n))
