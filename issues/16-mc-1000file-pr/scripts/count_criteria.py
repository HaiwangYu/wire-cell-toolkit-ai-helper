#!/usr/bin/env python3
"""Count events under three candidate criteria, side by side, so the right one
can be chosen on evidence rather than guessed a third time."""
import sys, glob
from multiprocessing import Pool
def one(p):
    import ROOT
    ROOT.gErrorIgnoreLevel = ROOT.kFatal
    f = ROOT.TFile.Open(p)
    if not f or f.IsZombie(): return (0,0,0,0)
    import os
    size_ok = 1 if os.path.getsize(p) > 20000 else 0
    tc = f.Get('T_rec_charge'); charge_ok = 1 if (tc and tc.GetEntries() > 0) else 0
    tk = f.Get('T_kine')
    enu_ok = 0
    if tk and tk.GetEntries():
        tk.GetEntry(0)
        enu_ok = 1 if tk.kine_reco_Enu > 0 else 0
    f.Close()
    return (1, size_ok, charge_ok, enu_ok)
if __name__ == '__main__':
    files = sorted(glob.glob(sys.argv[1] + '/*.root'))
    with Pool(16) as pool: res = pool.map(one, files, chunksize=32)
    tot = sum(r[0] for r in res)
    s   = sum(r[1] for r in res); c = sum(r[2] for r in res); e = sum(r[3] for r in res)
    print("  %-9s n=%5d | size>20kB %5d (%5.1f%%) | T_rec_charge>0 %5d (%5.1f%%) | kine_reco_Enu>0 %5d (%5.1f%%)"
          % (sys.argv[2], tot, s, 100.*s/tot, c, 100.*c/tot, e, 100.*e/tot))
