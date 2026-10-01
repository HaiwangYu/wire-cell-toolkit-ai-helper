#!/usr/bin/env python3
"""Per-call detail of dlvtx-replay: recorded vs replayed payload (coords, scores, ranking), and whether the replay repeats within one process.
usage (SL7, setup-aurora-run.sh): dlvtx-call-diff.py <tracking-pr.root>"""
import ROOT, numpy as np, SCN_Vertex, os, sys
ROOT.gErrorIgnoreLevel = ROOT.kError
w = [os.path.join(d, 'uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth') for d in os.environ['WIRECELL_PATH'].split(':') if os.path.exists(os.path.join(d, 'uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth'))][0]
f = ROOT.TFile.Open(sys.argv[1]); tc = f.Get('T_dlvtx_call'); tp = f.Get('T_dlvtx_cloud')
pts = {}
for e in tp: pts.setdefault((e.nu_index, e.call_index), [[], [], [], []]); [pts[(e.nu_index, e.call_index)][i].append(v) for i, v in enumerate((e.x, e.y, e.z, e.q))]
for e in tc:
    key = (e.nu_index, e.call_index); x, y, z, q = (np.array(v, dtype=np.float32) for v in pts[key])
    rec = np.array(list(e.payload), dtype=np.float32).reshape(-1, 4)
    outs = [np.frombuffer(SCN_Vertex.SCN_Vertex(w, x.tobytes(), y.tobytes(), z.tobytes(), q.tobytes(), 'float32', e.top_k), dtype=np.float32).reshape(-1, 4) for _ in range(3)]
    print('call', key, 'pass', getattr(e, 'pass'), 'npts', len(x))
    print('  recorded :', np.round(rec, 5).tolist())
    print('  replay#1 :', np.round(outs[0], 5).tolist())
    print('  coords identical:', np.array_equal(rec[:, :3], outs[0][:, :3]), ' max |dscore|:', float(np.max(np.abs(rec[:, 3] - outs[0][:, 3]))), ' ranking same:', np.array_equal(rec[:, :3], outs[0][:, :3]))
    print('  replay repeatable in one process:', all(np.array_equal(outs[0], o) for o in outs[1:]))
