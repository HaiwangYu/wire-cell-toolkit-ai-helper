#!/usr/bin/env python3
"""Is the production-pass network input coupled to the dual-chain OFF pass?  (ai-helper issue 35)
Compares, event by event and candidate by candidate, the PRODUCTION-pass call of two dumps:
  A: dual chain ON (production), B: dual chain OFF (pr_knobs={dl_vtx_dual_chain:false}).
If the OFF pass leaves no residue in the state the production pass fits, A's and B's prod
clouds (the exact float32 x,y,z,q) and payloads are bit-identical; only the decision
(accepted / dl_*, which the hint snap feeds) may differ.  Run INSIDE SL7.
usage: dlvtx-decouple.py <A run dir> <B run dir>     (both: pr/c*/pr_evt<E>/tracking-pr.root)"""
import glob, os, sys
import numpy as np
import ROOT
ROOT.gErrorIgnoreLevel = ROOT.kError

def load(d):
    out = {}
    for fn in glob.glob(d + '/pr/c*/pr_evt*/tracking-pr.root'):
        f = ROOT.TFile.Open(fn); tc, tp = f.Get('T_dlvtx_call'), f.Get('T_dlvtx_cloud')
        if not tc or not tp: continue
        calls = {}
        for e in tc:
            if getattr(e, 'pass') != 0: continue
            calls[(e.eventNo, e.nu_index)] = dict(ci=e.call_index, payload=np.array(list(e.payload), dtype=np.float32),
                                                  accepted=e.accepted, dl=(e.dl_x, e.dl_y, e.dl_z), final=(e.final_x, e.final_y, e.final_z),
                                                  trad=(e.trad_x, e.trad_y, e.trad_z), pts=[[], [], [], []])
        for e in tp:
            k = (e.eventNo, e.nu_index)
            if k in calls and e.call_index == calls[k]['ci']:
                for i, v in enumerate((e.x, e.y, e.z, e.q)): calls[k]['pts'][i].append(v)
        out.update(calls)
    return out

A, B = load(sys.argv[1]), load(sys.argv[2])
keys = sorted(set(A) & set(B))
print('prod-pass calls: A %d, B %d, common %d; only A %s; only B %s' % (len(A), len(B), len(keys), sorted(set(A) - set(B)), sorted(set(B) - set(A))))
n_cloud = n_pay = n_dec = 0
for k in keys:
    a, b = A[k], B[k]
    pa = [np.array(v, dtype=np.float32) for v in a['pts']]; pb = [np.array(v, dtype=np.float32) for v in b['pts']]
    cloud_same = all(len(x) == len(y) and np.array_equal(x, y) for x, y in zip(pa, pb))
    pay_same = len(a['payload']) == len(b['payload']) and np.array_equal(a['payload'], b['payload'])
    dec_same = a['accepted'] == b['accepted'] and a['dl'] == b['dl']
    n_cloud += cloud_same; n_pay += pay_same; n_dec += dec_same
    if not (cloud_same and pay_same):
        print('  evt %d nu %d: cloud %s (%d vs %d pts), payload %s' % (k[0], k[1], 'same' if cloud_same else 'DIFFERS', len(pa[0]), len(pb[0]), 'same' if pay_same else 'DIFFERS'))
    elif not dec_same:
        print('  evt %d nu %d: cloud+payload same; decision differs: accepted %d->%d, dl %s -> %s, final %s -> %s'
              % (k[0], k[1], a['accepted'], b['accepted'], tuple(round(x, 2) for x in a['dl']), tuple(round(x, 2) for x in b['dl']),
                 tuple(round(x, 2) for x in a['final']), tuple(round(x, 2) for x in b['final'])))
print('=> %d common prod calls: cloud identical %d, payload identical %d, decision identical %d' % (len(keys), n_cloud, n_pay, n_dec))
