#!/usr/bin/env python3
"""Gate G3 (ai-helper issue 44): the in-chain T_dlvtx_space equals Sne's r7_space selection
re-done from the same run's Bee zip.

    g3-space-vs-bee.py [--touch 1.0] <pr dir> [<pr dir> ...]

For every event (pr_evt*/tracking-pr.root) and every T_dlvtx_call row:
  * from Bee: the layer clustering-pr-global of the matching event (run/subrun/event) in
    <pr dir>/mabc-pr.zip; the clusters (Bee cluster_id) with ANY point within --touch cm of
    ANY point of the call's cloud (T_dlvtx_cloud rows of that call) -- Sne's rule
    (export_r7_space.py, TOUCH_CM = 1.0), done here with a brute-force/grid search;
  * from the tree: T_dlvtx_call.space_cluster_id.
The cluster sets must be equal per call; n_space must equal the Bee point count of those
clusters; and per cluster, the T_dlvtx_space rows (x, y, z, q, in order) must equal the Bee
points to Bee's JSON precision.  Also reports the event's point totals (sizes).
Run with PyROOT (setup-uan-root.sh) + numpy."""
import sys, os, glob, json, zipfile, math
from collections import defaultdict
import numpy as np
import uproot, awkward as ak
args = sys.argv[1:]
TOUCH = 1.0
if args and args[0] == '--touch':
    TOUCH = float(args[1]); args = args[2:]

def bee_events(zpath):
    Z = zipfile.ZipFile(zpath)
    ev = {}
    # infolist, not namelist + read(name): a multi-event step-2 zip can hold two entries with the
    # same name (two events at one Bee index); every entry carries its own run/subrun/event.
    for zi in Z.infolist():
        if zi.filename.endswith('-clustering-pr-global.json'):
            d = json.loads(Z.open(zi).read())
            ev[(int(d['runNo']), int(d['subRunNo']), int(d['eventNo']))] = d
    return ev

def touched(cl_pts, cloud, touch):
    """cl_pts: dict cid -> (n,3) array; cloud: (m,3).  Brute force in chunks with a bbox prefilter."""
    out = set()
    if len(cloud) == 0: return out
    lo, hi = cloud.min(0) - touch, cloud.max(0) + touch
    t2 = touch * touch
    for cid, p in cl_pts.items():
        q = p[np.all((p >= lo) & (p <= hi), axis=1)]
        if not len(q): continue
        for s in range(0, len(q), 2048):
            d2 = ((q[s:s + 2048, None, :] - cloud[None, :, :]) ** 2).sum(-1)
            if (d2 <= t2).any():
                out.add(cid); break
    return out

tot = defaultdict(int)
fails = []
for prd in args:
    bee = bee_events(os.path.join(prd, 'mabc-pr.zip'))
    for f in sorted(glob.glob(os.path.join(prd, 'pr_evt*', 'tracking-pr.root'))):
        tf = uproot.open(f)
        names = {k.split(';')[0] for k in tf.keys()}
        if 'T_dlvtx_call' not in names or 'T_dlvtx_space' not in names:
            fails.append('%s: missing T_dlvtx_call/T_dlvtx_space' % f); continue
        tot['events'] += 1
        S = tf['T_dlvtx_space'].arrays(library='np')
        P = tf['T_dlvtx_cloud'].arrays(library='np')
        C = tf['T_dlvtx_call'].arrays(['nu_index', 'call_index', 'space_cluster_id', 'n_space', 'runNo', 'subRunNo', 'eventNo'], library='ak')
        space = defaultdict(list)
        for i in range(len(S['x'])):
            space[int(S['cluster_id'][i])].append((S['x'][i], S['y'][i], S['z'][i], S['q'][i], S['blob_index'][i]))
        tot['space_rows'] += len(S['x'])
        clouds = defaultdict(list)
        for i in range(len(P['x'])):
            clouds[(int(P['nu_index'][i]), int(P['call_index'][i]))].append((P['x'][i], P['y'][i], P['z'][i]))
        calls = [((int(C['nu_index'][i]), int(C['call_index'][i])), sorted(int(v) for v in C['space_cluster_id'][i]),
                  int(C['n_space'][i]), (int(C['runNo'][i]), int(C['subRunNo'][i]), int(C['eventNo'][i])))
                 for i in range(len(C))]
        if not calls:
            if len(S['x']): fails.append('%s: space rows without calls' % f)
            continue
        key = calls[0][3]
        if key not in bee:
            fails.append('%s: event %s not in the Bee zip' % (f, key)); continue
        d = bee[key]
        cid = np.asarray(d['cluster_id']); xyz = np.stack([np.asarray(d['x']), np.asarray(d['y']), np.asarray(d['z'])], 1)
        q = np.asarray(d['q'])
        cl_pts = {int(c): xyz[cid == c] for c in np.unique(cid)}
        tot['bee_points'] += len(cid)
        union = set()
        for (k, ids, nsp, _) in calls:
            tot['calls'] += 1
            exp = touched(cl_pts, np.asarray(clouds[k], dtype=float), TOUCH)
            union |= exp
            if set(ids) != exp:
                fails.append('%s call %s: tree clusters %s vs Bee %s' % (f, k, ids, sorted(exp)))
            nexp = sum(len(cl_pts[c]) for c in exp)
            if nsp != nexp:
                fails.append('%s call %s: n_space %d vs Bee %d' % (f, k, nsp, nexp))
        if set(space) != union:
            fails.append('%s: T_dlvtx_space clusters %s vs union %s' % (f, sorted(space), sorted(union)))
        for c in sorted(set(space) & union):
            rows = np.asarray([r[:4] for r in space[c]])
            b = np.concatenate([xyz[cid == c], q[cid == c][:, None]], 1)
            if rows.shape != b.shape:
                fails.append('%s cluster %d: %d rows vs Bee %d' % (f, c, len(rows), len(b))); continue
            dx = np.abs(rows[:, :3] - b[:, :3]).max()
            dq = (np.abs(rows[:, 3] - b[:, 3]) / np.maximum(1.0, np.abs(b[:, 3]))).max()
            tot['max_dxyz'] = max(tot['max_dxyz'], dx); tot['max_rel_dq'] = max(tot['max_rel_dq'], dq)
            if dx > 1e-3 or dq > 1e-4:
                fails.append('%s cluster %d: max |dxyz| %.2e cm, max rel dq %.2e' % (f, c, dx, dq))
print('G3 touch=%.2f cm: %d events, %d calls, %d space rows (%.1f%% of %d Bee points), max |dxyz| %.2e cm, max rel dq %.2e'
      % (TOUCH, tot['events'], tot['calls'], tot['space_rows'], 100.0 * tot['space_rows'] / max(1, tot['bee_points']),
         tot['bee_points'], tot['max_dxyz'], tot['max_rel_dq']))
print('failures: %d' % len(fails))
for l in fails[:40]: print('  ' + l)
sys.exit(1 if fails else 0)
