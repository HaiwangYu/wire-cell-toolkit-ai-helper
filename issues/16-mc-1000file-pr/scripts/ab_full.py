#!/usr/bin/env python3
"""Per-event preflip-vs-sync A/B, matched by RSE.

  ab_full.py <label> <preflip_trackpr_dir> <sync_trackpr_dir>

Reports what synchronising the 151 PR knobs (issue 17) did to reconstruction on
the SAME events.  "Candidate" = kine_reco_Enu > 0, the criterion settled in
issue 18 (file size and T_rec_charge>0 both over-count).
"""
import sys, glob, os, statistics as st
from multiprocessing import Pool

def read(p):
    import ROOT
    ROOT.gErrorIgnoreLevel = ROOT.kFatal
    f = ROOT.TFile.Open(p)
    if not f or f.IsZombie(): return None
    d = {'enu': 0.0, 'numu': None, 'nue': None, 'npts': 0}
    tk = f.Get('T_kine')
    if tk and tk.GetEntries(): tk.GetEntry(0); d['enu'] = tk.kine_reco_Enu
    tt = f.Get('T_tagger')
    if tt and tt.GetEntries(): tt.GetEntry(0); d['numu'] = tt.numu_score; d['nue'] = tt.nue_score
    tc = f.Get('T_rec_charge')
    if tc: d['npts'] = tc.GetEntries()
    f.Close(); return d

def load(d):
    files = sorted(glob.glob(d + '/*.root'))
    with Pool(16) as pool: vals = pool.map(read, files, chunksize=32)
    return {os.path.basename(f): v for f, v in zip(files, vals) if v}

label, a_dir, b_dir = sys.argv[1], sys.argv[2], sys.argv[3]
A, B = load(a_dir), load(b_dir)
common = sorted(set(A) & set(B))
print("### %s" % label)
print("  events: preflip %d, sync %d, matched %d" % (len(A), len(B), len(common)))
only_a = sorted(set(A) - set(B)); only_b = sorted(set(B) - set(A))
if only_a: print("  in preflip ONLY (%d): %s" % (len(only_a), [x[12:-5] for x in only_a[:6]]))
if only_b: print("  in sync ONLY    (%d): %s" % (len(only_b), [x[12:-5] for x in only_b[:6]]))

ca = sum(1 for k in common if A[k]['enu'] > 0)
cb = sum(1 for k in common if B[k]['enu'] > 0)
gained = [k for k in common if A[k]['enu'] <= 0 < B[k]['enu']]
lost   = [k for k in common if B[k]['enu'] <= 0 < A[k]['enu']]
print("  candidates: preflip %d (%.1f%%)  sync %d (%.1f%%)   gained %d, lost %d"
      % (ca, 100.*ca/len(common), cb, 100.*cb/len(common), len(gained), len(lost)))

both = [k for k in common if A[k]['enu'] > 0 and B[k]['enu'] > 0]
if both:
    rel = sorted(100.0*(B[k]['enu'] - A[k]['enu'])/A[k]['enu'] for k in both)
    same = sum(1 for k in both if abs(A[k]['enu'] - B[k]['enu']) < 0.05)
    q = lambda f: rel[min(len(rel)-1, int(f*len(rel)))]
    print("  Enu (both candidates, n=%d): unchanged %d (%.1f%%)" % (len(both), same, 100.*same/len(both)))
    print("     relative shift  median %+.2f%%  p10 %+.1f%%  p90 %+.1f%%  min %+.1f%%  max %+.1f%%"
          % (q(.5), q(.1), q(.9), rel[0], rel[-1]))
    for key in ('nue', 'numu'):
        va = [A[k][key] for k in both if A[k][key] is not None]
        vb = [B[k][key] for k in both if B[k][key] is not None]
        fa = sum(1 for x in va if abs(x + 15) < 1e-6); fb = sum(1 for x in vb if abs(x + 15) < 1e-6)
        print("     %-4s_score  median %+.3f -> %+.3f   floored@-15: %.1f%% -> %.1f%%"
              % (key, st.median(va), st.median(vb), 100.*fa/len(va), 100.*fb/len(vb)))
print()
