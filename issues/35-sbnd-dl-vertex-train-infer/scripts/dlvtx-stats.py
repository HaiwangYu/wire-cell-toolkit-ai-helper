#!/usr/bin/env python3
"""Decision statistics of the dumped DL-vertex calls (T_dlvtx_call; ai-helper issue 35).
Run INSIDE SL7 (PyROOT).
usage: dlvtx-stats.py <tracking-pr.root> ...

Per pass (off = dual-chain exclusion-free pass, prod = production pass):
  calls, DL accepted (the main vertex was switched to a DL-chosen candidate),
  dual_transferred (prod only: the snap to the OFF-pass vertex REPLACED production's own
  rerank pick, or supplied one where the rerank had none), and how far the prod call's
  own top-1 voxel lies from the vertex finally accepted -- i.e. whether production's own
  inference or the OFF-pass hint decided."""
import collections, math, sys
import numpy as np
import ROOT
ROOT.gErrorIgnoreLevel = ROOT.kError

cnt = collections.defaultdict(collections.Counter)
d_top1_final, d_top1_dl, d_trad_dl = [], [], []
for fn in sys.argv[1:]:
    f = ROOT.TFile.Open(fn); tc = f.Get('T_dlvtx_call')
    if not tc: continue
    for e in tc:
        p = 'off' if getattr(e, 'pass') == 1 else 'prod'
        cnt[p]['calls'] += 1; cnt[p]['accepted'] += e.accepted; cnt[p]['dual_transferred'] += e.dual_transferred
        cnt[p]['accepted_and_transferred'] += (e.accepted and e.dual_transferred)
        cnt[p]['payload_from_off'] += e.payload_from_off
        pl = np.array(list(e.payload), dtype=np.float32)
        if p == 'prod' and len(pl) >= 4:
            t1 = pl[:3]
            if e.final_valid: d_top1_final.append(math.dist(t1, (e.final_x, e.final_y, e.final_z)))
            if e.accepted:
                d_top1_dl.append(math.dist(t1, (e.dl_x, e.dl_y, e.dl_z)))
                if e.trad_valid: d_trad_dl.append(math.dist((e.trad_x, e.trad_y, e.trad_z), (e.dl_x, e.dl_y, e.dl_z)))
for p in ('off', 'prod'):
    c = cnt[p]
    print('pass %-4s: calls %d, DL accepted %d, dual_transferred %d (accepted & transferred %d), payload_from_off %d'
          % (p, c['calls'], c['accepted'], c['dual_transferred'], c['accepted_and_transferred'], c['payload_from_off']))
def summ(name, v):
    if not v: return
    v = np.array(v); print('   %-42s n=%-3d median %.2f cm, <1 cm %d, <2 cm %d, >5 cm %d' % (name, len(v), np.median(v), (v < 1).sum(), (v < 2).sum(), (v > 5).sum()))
summ('prod own top-1 voxel -> accepted DL vertex', d_top1_dl)
summ('prod own top-1 voxel -> final vertex', d_top1_final)
summ('traditional vertex -> accepted DL vertex', d_trad_dl)
