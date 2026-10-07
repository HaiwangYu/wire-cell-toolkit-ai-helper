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
# vs MC truth (truth_reco_*, the SCE-shifted truth vertex in the cloud frame), per pass:
# the model's OWN top-1 voxel (raw prediction, before rerank/snap), the accepted DL vertex,
# the traditional vertex; and the OFF pass's final vertex (hint) read from the prod row.
tr = collections.defaultdict(list)
for fn in sys.argv[1:]:
    f = ROOT.TFile.Open(fn); tc = f.Get('T_dlvtx_call')
    if not tc: continue
    for e in tc:
        p = 'off' if getattr(e, 'pass') == 1 else 'prod'
        cnt[p]['calls'] += 1; cnt[p]['accepted'] += e.accepted; cnt[p]['dual_transferred'] += e.dual_transferred
        cnt[p]['accepted_and_transferred'] += (e.accepted and e.dual_transferred)
        cnt[p]['payload_from_off'] += e.payload_from_off
        pl = np.array(list(e.payload), dtype=np.float32)
        if e.truth_valid:
            t = (e.truth_reco_x, e.truth_reco_y, e.truth_reco_z)
            if len(pl) >= 3: tr[p + ': own top-1 voxel'].append(math.dist(pl[:3], t))
            if e.accepted: tr[p + ': accepted DL vertex'].append(math.dist((e.dl_x, e.dl_y, e.dl_z), t))
            if e.trad_valid: tr[p + ': traditional vertex'].append(math.dist((e.trad_x, e.trad_y, e.trad_z), t))
            if p == 'prod':
                if e.final_valid: tr['final vertex'].append(math.dist((e.final_x, e.final_y, e.final_z), t))
                if getattr(e, 'hint_valid', 0): tr['OFF-pass final vertex (hint)'].append(math.dist((e.hint_x, e.hint_y, e.hint_z), t))
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
if tr:
    print('vs MC truth (SCE-shifted, cm):')
    for k in sorted(tr):
        v = np.array(tr[k]); print('   %-32s n=%-4d median %.2f, <1 cm %4d (%.0f%%), <2 cm %4d (%.0f%%), >5 cm %4d' % (k, len(v), np.median(v), (v<1).sum(), 100*(v<1).mean(), (v<2).sum(), 100*(v<2).mean(), (v>5).sum()))
