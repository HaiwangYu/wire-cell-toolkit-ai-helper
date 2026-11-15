"""ai-helper #47 (prod_aurora): per-call table of the in-chain aurora_space run on the hold-out units.

For every unit in RUN/<sample>/<unit>/: reads pr/pr_evt*/tracking-pr.root (T_dlvtx_call, T_dlvtx_cloud,
T_dlvtx_space) and dv2hook.jsonl (one line per DV2_Vertex call).  Recomputes each dumped call's input sha1 exactly
as DV2_Vertex.input_digest (cloud x,y,z,q float32 in ipoint order, trad float32 (NaN unless trad_valid),
'<nv>:<repr q_scale>:<repr q_offset>:float32', then ':space:' + the T_dlvtx_space rows of the call's
space_cluster_id clusters in increasing cluster id, tree order inside a cluster) and joins the hook record on it.
In-chain pick -> label frame: x - sign(x) * x_shift (bundle, 0.29 cm).

usage: python ana_calls.py RUN OUT_CSV [--x-shift 0.29] [--sne-py DIR]"""
import argparse, csv, glob, json, os, sys
import numpy as np
import uproot

ap = argparse.ArgumentParser()
ap.add_argument("run"); ap.add_argument("out")
ap.add_argument("--x-shift", type=float, default=0.29)
ap.add_argument("--sne-py", default="/lus/flare/projects/neutrinoGPU/yuhw/production-prep/dv2max-aurora-space/sne-py/pyutil/python")
a = ap.parse_args()
sys.path.insert(0, a.sne_py)
from DV2_Vertex import input_digest  # noqa: E402  (pure hashlib; the module imports numpy only)

F32 = np.float32
rows = []
stats = {"units": 0, "events": 0, "calls": 0, "hook": 0, "joined": 0, "hook_unjoined": 0}
for udir in sorted(glob.glob(os.path.join(a.run, "*", "*"))):
    if not os.path.isdir(udir): continue
    sample, unit = udir.split(os.sep)[-2:]
    hook = [json.loads(l) for l in open(os.path.join(udir, "dv2hook.jsonl"))] if os.path.exists(os.path.join(udir, "dv2hook.jsonl")) else []
    byd = {}
    for h in hook: byd.setdefault(h["input_sha1"], []).append(h)
    stats["units"] += 1; stats["hook"] += len(hook)
    used = 0
    for f in sorted(glob.glob(os.path.join(udir, "pr", "pr_evt*", "tracking-pr.root"))):
        with uproot.open(f) as R:
            C = R["T_dlvtx_call"].arrays(library="np")
            if len(C["runNo"]) == 0:
                stats["events"] += 1; continue
            L = R["T_dlvtx_cloud"].arrays(["call_index", "nu_index", "pass", "ipoint", "x", "y", "z", "q"], library="np")
            S = R["T_dlvtx_space"].arrays(["cluster_id", "x", "y", "z", "q"], library="np")
        stats["events"] += 1
        for i in range(len(C["runNo"])):
            ci = C["call_index"][i]
            m = np.where((L["call_index"] == ci) & (L["nu_index"] == C["nu_index"][i]) & (L["pass"] == C["pass"][i]))[0]
            m = m[np.argsort(L["ipoint"][m], kind="stable")]
            x, y, z, q = (L[k][m].astype(F32) for k in "xyzq")
            trad = np.array([C["trad_x"][i], C["trad_y"][i], C["trad_z"][i]], F32) if C["trad_valid"][i] else np.full(3, np.nan, F32)
            scids = sorted(set(int(c) for c in np.asarray(C["space_cluster_id"][i]).ravel()))
            sp = None
            if len(scids):
                sel = np.concatenate([np.where(S["cluster_id"] == c)[0] for c in scids])
                sp = tuple(S[k][sel].astype(F32).tobytes() for k in "xyzq") + (S["cluster_id"][sel].astype(np.int32).tobytes(),)
            nv = int(C["n_vertex_rows"][i])
            dg = input_digest(x.tobytes(), y.tobytes(), z.tobytes(), q.tobytes(), nv, trad.tobytes(),
                              float(C["q_scale"][i]), float(C["q_offset"][i]), "float32", sp)
            h = byd[dg].pop(0) if byd.get(dg) else None
            key = f"{sample}:{C['runNo'][i]}:{C['subRunNo'][i]}:{C['eventNo'][i]}:{C['nu_index'][i]}:p{C['pass'][i]}"
            r = {"key": key, "unit": unit, "call_index": int(ci), "n": len(q), "nv": nv, "n_space": len(sel) if sp else 0,
                 "digest": dg, "joined": int(h is not None)}
            stats["calls"] += 1
            if h is not None:
                stats["joined"] += 1; used += 1
                p = h.get("pred")
                if p:
                    sx = p[0] - np.sign(p[0]) * a.x_shift
                    r.update(px=sx, py=p[1], pz=p[2], score=h.get("score"), score_raw=h.get("score_raw"), source=h.get("source"), ms=h.get("ms"))
                else:
                    r.update(reason=h.get("reason"))
            for k in ("final_valid", "final_x", "final_y", "final_z", "accepted"):
                r[k] = C[k][i].item() if hasattr(C[k][i], "item") else C[k][i]
            rows.append(r)
    stats["hook_unjoined"] += len(hook) - used
cols = ["key", "unit", "call_index", "n", "nv", "n_space", "digest", "joined", "px", "py", "pz", "score", "score_raw",
        "source", "ms", "reason", "accepted", "final_valid", "final_x", "final_y", "final_z"]
with open(a.out, "w", newline="") as fo:
    w = csv.DictWriter(fo, cols, extrasaction="ignore"); w.writeheader()
    for r in rows: w.writerow(r)
print(json.dumps(stats))
