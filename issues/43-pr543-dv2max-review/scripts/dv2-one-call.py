import sys, os, numpy as np, uproot
os.environ.pop('DV2_HOOK_LOG', None)
import DV2_Vertex as DV
run, evt, bundle = sys.argv[1], sys.argv[2], sys.argv[3]
u = uproot.open('%s/%s/tracking-pr.root' % (run, evt))
c = u['T_dlvtx_call'].arrays(library='np'); p = u['T_dlvtx_cloud'].arrays(['nu_index','call_index','pass','ipoint','x','y','z','q'], library='np')
i = 0
m = (p['nu_index']==c['nu_index'][i]) & (p['call_index']==c['call_index'][i]) & (p['pass']==c['pass'][i]); o = np.argsort(p['ipoint'][m])
x,y,z,q = (p[k][m][o].astype(np.float32) for k in ('x','y','z','q'))
trad = np.array([c['trad_x'][i], c['trad_y'][i], c['trad_z'][i]], dtype=np.float32)
for rep in range(3):
    r = np.frombuffer(DV.DV2_Vertex(bundle, x.tobytes(), y.tobytes(), z.tobytes(), q.tobytes(), int(c['n_vertex_rows'][i]), trad.tobytes(), float(c['q_scale'][i]), float(c['q_offset'][i])), dtype=np.float32)
    print("rep", rep, [round(float(v),4) for v in r], {k: DV._LAST.get(k) for k in ("n", "n_vertex_rows", "n_cand", "source", "score_raw")})
