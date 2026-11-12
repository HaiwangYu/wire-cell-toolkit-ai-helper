#!/usr/bin/env python3
"""digest-check.py <run dir> ...  (PR #543 re-review, the new DV2_HOOK_LOG input_sha1)
For each DV2 call recorded in the dump (T_dlvtx_call / T_dlvtx_cloud), rebuild the exact arguments the chain passes
(float32 cloud in ipoint order; trad = NaN when trad_valid = 0) and compute DV2_Vertex.input_digest.  Count how many
dumped calls find their digest among the run's hook records, and how many hook records are matched."""
import glob, json, os, sys
import numpy as np, uproot
import DV2_Vertex as DV
tot = hit = nh = 0; miss = []
for run in sys.argv[1:]:
    hooks = [json.loads(l) for l in open(os.path.join(run, 'dv2-hook.jsonl'))]
    hs = {h['input_sha1'] for h in hooks}; nh += len(hooks)
    for fn in sorted(glob.glob(os.path.join(run, 'pr_evt*', 'tracking-pr.root'))):
        u = uproot.open(fn)
        if 'T_dlvtx_call' not in u or u['T_dlvtx_call'].num_entries == 0: continue
        c = u['T_dlvtx_call'].arrays(library='np')
        p = u['T_dlvtx_cloud'].arrays(['nu_index', 'call_index', 'pass', 'ipoint', 'x', 'y', 'z', 'q'], library='np')
        for i in range(len(c['nu_index'])):
            m = (p['nu_index'] == c['nu_index'][i]) & (p['call_index'] == c['call_index'][i]) & (p['pass'] == c['pass'][i])
            o = np.argsort(p['ipoint'][m])
            x, y, z, q = (p[k][m][o].astype(np.float32).tobytes() for k in ('x', 'y', 'z', 'q'))
            trad = (np.array([c['trad_x'][i], c['trad_y'][i], c['trad_z'][i]], dtype=np.float32) if c['trad_valid'][i]
                    else np.full(3, np.nan, dtype=np.float32)).tobytes()
            dg = DV.input_digest(x, y, z, q, int(c['n_vertex_rows'][i]), trad, float(c['q_scale'][i]), float(c['q_offset'][i]))
            tot += 1
            if dg in hs: hit += 1
            else: miss.append((run, fn))
print(json.dumps(dict(dumped_calls=tot, digest_found=hit, hook_records=nh, misses=miss[:5])))
