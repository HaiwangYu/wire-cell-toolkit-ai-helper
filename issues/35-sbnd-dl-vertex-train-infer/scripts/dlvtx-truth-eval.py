#!/usr/bin/env python3
"""Truth evaluation of the dumped DL-vertex calls with the TRAINING selection (issue 35 M4).
Run INSIDE SL7 or with setup-uan-root.sh (PyROOT).
usage: dlvtx-truth-eval.py [--edep-min MeV] [--contain cm] [--tsv out.tsv] <tracking-pr.root> ...

Per EVENT (one tracking-pr.root), from T_dlvtx_call (truth_* from the issue-33 truth_nu table,
max-edep interaction) and T_dlvtx_cloud:
  1. truth usable: the interaction deposited >= edep-min (GeV*1e3 from truth_nu via truth_edep is
     not in the tree, so the proxy is: the truth vertex lies inside the SBND active volume
     |x| < 200, |y| < 200, 0 < z < 500 cm);
  2. the candidate that IS the true interaction: among the event's candidates (nu_index), the one
     whose production cloud has a point within `contain` cm of the SCE-shifted truth vertex;
     ties -> the closest.  Events with no such candidate are counted separately.
On the selected candidates it reports, vs the truth vertex, for both passes: the model's own
top-1 voxel (raw prediction), the accepted DL vertex, the traditional vertex; and the hint and
final vertex.  This is the number the retrained model has to match or beat."""
import argparse, collections, math, sys
import numpy as np
import ROOT
ROOT.gErrorIgnoreLevel = ROOT.kError

ap = argparse.ArgumentParser()
ap.add_argument('--contain', type=float, default=3.0)
ap.add_argument('--tsv', default=None)
ap.add_argument('files', nargs='+')
a = ap.parse_args()

def inside(x, y, z): return abs(x) < 200 and abs(y) < 200 and 0 < z < 500

evt = collections.Counter(); rows = []
dist = collections.defaultdict(list)
for fn in a.files:
    f = ROOT.TFile.Open(fn); tc, tp = f.Get('T_dlvtx_call'), f.Get('T_dlvtx_cloud')
    if not tc: continue
    calls = {}
    for e in tc:
        calls[(e.nu_index, getattr(e, 'pass'))] = dict(
            truth=(e.truth_valid, e.truth_reco_x, e.truth_reco_y, e.truth_reco_z),
            top1=np.array(list(e.payload), dtype=np.float32)[:3] if e.n_points else None,
            accepted=e.accepted, dl=(e.dl_x, e.dl_y, e.dl_z), trad=(e.trad_valid, e.trad_x, e.trad_y, e.trad_z),
            final=(e.final_valid, e.final_x, e.final_y, e.final_z), hint=(getattr(e, 'hint_valid', 0), getattr(e, 'hint_x', 0), getattr(e, 'hint_y', 0), getattr(e, 'hint_z', 0)),
            ci=e.call_index, rse=(e.runNo, e.subRunNo, e.eventNo))
    if not calls: evt['no candidate (no DL call)'] += 1; continue
    tv = next(iter(calls.values()))['truth']
    if not tv[0]: evt['no truth'] += 1; continue
    t = np.array(tv[1:])
    if not inside(*t): evt['truth outside the active volume'] += 1; continue
    # nearest production-cloud point per candidate
    near = collections.defaultdict(lambda: 1e9)
    for p in tp:
        if p.is_vertex < 0: continue
        k = (p.nu_index, 0)
        if k in calls and p.call_index == calls[k]['ci']:
            d = math.sqrt((p.x - t[0])**2 + (p.y - t[1])**2 + (p.z - t[2])**2)
            if d < near[p.nu_index]: near[p.nu_index] = d
    if not near: evt['truth inside, no production call'] += 1; continue
    nu, dmin = min(near.items(), key=lambda kv: kv[1])
    if dmin > a.contain: evt['truth inside, no candidate contains it (>%g cm)' % a.contain] += 1; continue
    evt['selected (true interaction found as a candidate)'] += 1
    evt['  of which with >1 candidate in the event'] += (len(near) > 1)
    for pname, pidx in (('prod', 0), ('off', 1)):
        c = calls.get((nu, pidx))
        if not c: continue
        if c['top1'] is not None: dist[pname + ': own top-1 voxel'].append(float(np.linalg.norm(c['top1'] - t)))
        if c['accepted']: dist[pname + ': accepted DL vertex'].append(float(np.linalg.norm(np.array(c['dl']) - t)))
        if c['trad'][0]: dist[pname + ': traditional vertex'].append(float(np.linalg.norm(np.array(c['trad'][1:]) - t)))
        if pname == 'prod':
            if c['final'][0]: dist['final vertex'].append(float(np.linalg.norm(np.array(c['final'][1:]) - t)))
            if c['hint'][0]: dist['OFF-pass final vertex (hint)'].append(float(np.linalg.norm(np.array(c['hint'][1:]) - t)))
            rows.append((c['rse'], nu, dmin, dist['prod: own top-1 voxel'][-1] if c['top1'] is not None else -1,
                         dist['final vertex'][-1] if c['final'][0] else -1))
print('events: ' + '; '.join('%s %d' % (k, v) for k, v in evt.items()))
print('selected candidates vs the SCE-shifted truth vertex (cm):')
for k in sorted(dist):
    v = np.array(dist[k])
    print('   %-32s n=%-4d median %.2f  <1 cm %4d (%.0f%%)  <2 cm %4d (%.0f%%)  >5 cm %4d (%.0f%%)'
          % (k, len(v), np.median(v), (v < 1).sum(), 100 * (v < 1).mean(), (v < 2).sum(), 100 * (v < 2).mean(), (v > 5).sum(), 100 * (v > 5).mean()))
if a.tsv:
    with open(a.tsv, 'w') as o:
        o.write('run\tsubrun\tevent\tnu_index\tcloud_to_truth_cm\tprod_top1_to_truth_cm\tfinal_to_truth_cm\n')
        for (r, s, e), nu, dmin, d1, df in rows: o.write('%d\t%d\t%d\t%d\t%.2f\t%.2f\t%.2f\n' % (r, s, e, nu, dmin, d1, df))
    print('wrote', a.tsv)
