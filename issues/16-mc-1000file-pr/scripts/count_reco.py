#!/usr/bin/env python3
import sys, glob
from multiprocessing import Pool
def one(p):
    import ROOT
    ROOT.gErrorIgnoreLevel = ROOT.kFatal
    f = ROOT.TFile.Open(p)
    if not f or f.IsZombie(): return 2
    tc = f.Get('T_rec_charge')
    r = 2 if not tc else (0 if tc.GetEntries() > 0 else 1)
    f.Close()
    return r
if __name__ == '__main__':
    files = sorted(glob.glob(sys.argv[1] + '/*.root'))
    with Pool(16) as pool:
        res = pool.map(one, files, chunksize=32)
    print("  %-10s real reco: %5d/%d = %.1f%%   booked-but-empty: %4d   no trees: %5d"
          % (sys.argv[2], res.count(0), len(res), 100.0*res.count(0)/len(res), res.count(1), res.count(2)))
