#!/usr/bin/env python3
"""dv2-standalone.py <bundle.json> <out.tsv> <run dir> ...
Q2 of ai-helper #43: re-run every in-chain DV2-MAX call STANDALONE and compare.
For each pr_evt<E>/tracking-pr.root of a dv2_* run: the call's cloud (T_dlvtx_cloud rows of one (nu_index,
call_index, pass), in ipoint order, float32 as the C++ passes them), n_vertex_rows, q_scale, q_offset and the
traditional vertex (T_dlvtx_call) go through DV2_Vertex.DV2_Vertex -- the same function the chain calls,
here from plain Python.  Compared with the in-chain result: T_dlvtx_call dl_x/y/z (the vertex the chain got)
and the run's DV2_HOOK_LOG record (prediction + calibrated score), matched on (n, n_vertex_rows) and the
nearest prediction.  Run in the PR environment (setup-pr543.sh)."""
import glob, json, math, os, sys
import numpy as np, uproot
os.environ.pop('DV2_HOOK_LOG', None)
os.environ['DV2_STRICT'] = '1'
import DV2_Vertex as DV

bundle, out = sys.argv[1], sys.argv[2]
rows = []
for run in sys.argv[3:]:
    hooks = [json.loads(l) for l in open(os.path.join(run, 'dv2-hook.jsonl'))] if os.path.exists(os.path.join(run, 'dv2-hook.jsonl')) else []
    used = set()
    for fn in sorted(glob.glob(os.path.join(run, 'pr_evt*', 'tracking-pr.root'))):
        u = uproot.open(fn)
        if 'T_dlvtx_call' not in u or u['T_dlvtx_call'].num_entries == 0:
            continue
        c = u['T_dlvtx_call'].arrays(library='np')
        p = u['T_dlvtx_cloud'].arrays(['nu_index', 'call_index', 'pass', 'ipoint', 'x', 'y', 'z', 'q'], library='np')
        for i in range(len(c['nu_index'])):
            key = (c['nu_index'][i], c['call_index'][i], c['pass'][i])
            m = (p['nu_index'] == key[0]) & (p['call_index'] == key[1]) & (p['pass'] == key[2])
            o = np.argsort(p['ipoint'][m])
            x, y, z, q = (p[k][m][o].astype(np.float32) for k in ('x', 'y', 'z', 'q'))
            trad = np.array([c['trad_x'][i], c['trad_y'][i], c['trad_z'][i]], dtype=np.float32)
            nv = int(c['n_vertex_rows'][i])
            res = DV.DV2_Vertex(bundle, x.tobytes(), y.tobytes(), z.tobytes(), q.tobytes(), nv, trad.tobytes(),
                                float(c['q_scale'][i]), float(c['q_offset'][i]))
            sa = np.frombuffer(res, dtype=np.float32) if res else None
            rec = DV._LAST
            chain = (c['dl_x'][i], c['dl_y'][i], c['dl_z'][i]) if c['accepted'][i] else None
            # the in-chain hook record: same n and n_vertex_rows, nearest prediction, not used yet
            best, bd = None, 1e9
            for j, h in enumerate(hooks):
                if j in used or h.get('n') != len(q) or h.get('n_vertex_rows') != nv or not h.get('pred') or sa is None:
                    continue
                d = math.dist(h['pred'], sa[:3])
                if d < bd:
                    best, bd = j, d
            if best is not None:
                used.add(best)
            h = hooks[best] if best is not None else {}
            rows.append(dict(run=os.path.relpath(run), evt=os.path.basename(os.path.dirname(fn)), nu=int(key[0]),
                             call=int(key[1]), pas=int(key[2]), n=len(q), nv=nv,
                             sa=None if sa is None else [float(v) for v in sa[:3]], sa_score=None if sa is None else float(sa[3]),
                             hook=h.get('pred'), hook_score=h.get('score'),
                             d_hook=None if (sa is None or not h.get('pred')) else math.dist(h['pred'], sa[:3]),
                             d_chain=None if (sa is None or chain is None) else math.dist(chain, sa[:3]),
                             dscore=None if (sa is None or h.get('score') is None) else abs(h['score'] - float(sa[3])),
                             ms=rec.get('ms')))
with open(out, 'w') as f:
    for r in rows:
        f.write(json.dumps(r) + '\n')
d = [r['d_hook'] for r in rows if r['d_hook'] is not None]
ds = [r['dscore'] for r in rows if r['dscore'] is not None]
print('calls %d, with a hook match %d; |pred_standalone - pred_inchain| max %.3g cm, median %.3g; '
      'exact (< 1e-4 cm) %d; |score diff| max %.3g; vs T_dlvtx_call dl_xyz max %.3g cm; no prediction %d' % (
      len(rows), len(d), max(d) if d else float('nan'), float(np.median(d)) if d else float('nan'),
      sum(1 for v in d if v < 1e-4), max(ds) if ds else float('nan'),
      max([r['d_chain'] for r in rows if r['d_chain'] is not None] or [float('nan')]), sum(1 for r in rows if r['sa'] is None)))
