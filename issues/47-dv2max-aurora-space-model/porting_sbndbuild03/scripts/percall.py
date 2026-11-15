#!/usr/bin/env python3
"""percall.py <bundle.json> <out.csv> <run dir> ...   (ai-helper issue 47, P4; the #43 method)

For every DL-vertex call recorded in a run (pr_evt*/tracking-pr.root, T_dlvtx_call + T_dlvtx_cloud
[+ T_dlvtx_space]):
  1. rebuild the exact DV2_Vertex arguments from the dump: the cloud (float32, ipoint order), n_vertex_rows,
     trad (NaN when trad_valid = 0), q_scale, q_offset; for a space-point bundle also the space points =
     the T_dlvtx_space rows whose cluster_id is in the call's space_cluster_id, in tree order;
  2. input digest of those bytes (DV2_Vertex.input_digest) -> look it up in the run's DV2_HOOK_LOG
     (the digest the in-chain call logged itself): equal = the chain's input == the dump (cloud AND space);
  3. replay the call standalone (DV2_Vertex.DV2_Vertex, same bundle) and compare with the in-chain
     prediction of the matched hook record (distance, score difference).
Run in the test-build environment (setup-aur-test.sh), with uproot on PYTHONPATH.
One CSV row per call."""
import csv
import glob
import json
import math
import os
import sys

import numpy as np
import uproot

os.environ.pop("DV2_HOOK_LOG", None)
os.environ["DV2_THREADS"] = "1"
import DV2_Vertex as DV  # noqa: E402

bundle, out = sys.argv[1], sys.argv[2]
space_bundle = json.loads(DV.DV2_Load(bundle)).get("space") is not None   # DV2_Load: JSON bytes
F = ["run", "evt", "runNo", "subRunNo", "eventNo", "nu_index", "call_index", "pass", "n", "n_vertex_rows",
     "n_space_dump", "n_space_tree", "n_space_hook", "digest_in_hook", "hook_x", "hook_y", "hook_z", "hook_score",
     "sa_x", "sa_y", "sa_z", "sa_score", "d_sa_hook_cm", "dscore", "exact", "accepted", "dl_x", "dl_y", "dl_z",
     "final_x", "final_y", "final_z", "truth_valid", "truth_reco_x", "truth_reco_y", "truth_reco_z", "ms_sa"]
rows = []
for run in sys.argv[3:]:
    hp = os.path.join(run, "dv2-hook.jsonl")
    hooks = [json.loads(x) for x in open(hp)] if os.path.exists(hp) else []
    by_dg = {}
    for h in hooks:
        by_dg.setdefault(h.get("input_sha1"), []).append(h)
    for fn in sorted(glob.glob(os.path.join(run, "pr_evt*", "tracking-pr.root"))):
        u = uproot.open(fn)
        if "T_dlvtx_call" not in u or u["T_dlvtx_call"].num_entries == 0:
            continue
        c = u["T_dlvtx_call"].arrays(library="np")
        p = u["T_dlvtx_cloud"].arrays(["nu_index", "call_index", "pass", "ipoint", "x", "y", "z", "q"], library="np")
        s = u["T_dlvtx_space"].arrays(["cluster_id", "x", "y", "z", "q"], library="np") \
            if "T_dlvtx_space" in u else None
        for i in range(len(c["nu_index"])):
            key = (c["nu_index"][i], c["call_index"][i], c["pass"][i])
            m = np.flatnonzero((p["nu_index"] == key[0]) & (p["call_index"] == key[1]) & (p["pass"] == key[2]))
            m = m[np.argsort(p["ipoint"][m], kind="stable")]
            x, y, z, q = (p[k][m].astype(np.float32) for k in ("x", "y", "z", "q"))
            trad = (np.array([c["trad_x"][i], c["trad_y"][i], c["trad_z"][i]], np.float64).astype(np.float32)
                    if c["trad_valid"][i] else np.full(3, np.nan, np.float32))
            nv, qs, qo = int(c["n_vertex_rows"][i]), float(c["q_scale"][i]), float(c["q_offset"][i])
            args = (x.tobytes(), y.tobytes(), z.tobytes(), q.tobytes(), nv, trad.tobytes(), qs, qo)
            sb, n_sp = None, 0
            if space_bundle:
                if s is None:
                    raise SystemExit(f"{fn}: a space-point bundle, but no T_dlvtx_space (run with dl_vtx_dump_space)")
                ids = np.asarray(c["space_cluster_id"][i], np.int64)
                sm = np.flatnonzero(np.isin(s["cluster_id"], ids))
                sb = tuple(s[k][sm].astype(np.float32).tobytes() for k in ("x", "y", "z", "q")) + \
                    (s["cluster_id"][sm].astype(np.int32).tobytes(),)
                n_sp = len(sm)
            dg = DV.input_digest(*args, "float32", sb)
            hh = by_dg.get(dg, [])
            h = hh[0] if hh else {}
            res = DV.DV2_Vertex(bundle, *args, "float32", *(sb or ()))
            sa = np.frombuffer(res, np.float32) if res else None
            hp_ = h.get("pred")
            d = math.dist(hp_, sa[:3]) if (sa is not None and hp_) else None
            ds = abs(h["score"] - float(sa[3])) if (sa is not None and h.get("score") is not None) else None
            g = lambda k: c[k][i] if k in c else None  # noqa: E731
            rows.append(dict(
                run=os.path.basename(os.path.normpath(run)), evt=os.path.basename(os.path.dirname(fn)),
                runNo=int(c["runNo"][i]), subRunNo=int(c["subRunNo"][i]), eventNo=int(c["eventNo"][i]),
                nu_index=int(key[0]), call_index=int(key[1]), **{"pass": int(key[2])}, n=len(q), n_vertex_rows=nv,
                n_space_dump=n_sp, n_space_tree=int(g("n_space")) if g("n_space") is not None else "",
                n_space_hook=h.get("n_space", ""), digest_in_hook=int(bool(hh)),
                hook_x=hp_[0] if hp_ else "", hook_y=hp_[1] if hp_ else "", hook_z=hp_[2] if hp_ else "",
                hook_score=h.get("score", ""),
                sa_x="" if sa is None else float(sa[0]), sa_y="" if sa is None else float(sa[1]),
                sa_z="" if sa is None else float(sa[2]), sa_score="" if sa is None else float(sa[3]),
                d_sa_hook_cm="" if d is None else d, dscore="" if ds is None else ds,
                exact=int(d is not None and d == 0.0 and ds == 0.0),
                accepted=int(c["accepted"][i]), dl_x=float(c["dl_x"][i]), dl_y=float(c["dl_y"][i]),
                dl_z=float(c["dl_z"][i]), final_x=float(c["final_x"][i]), final_y=float(c["final_y"][i]),
                final_z=float(c["final_z"][i]), truth_valid=int(c["truth_valid"][i]),
                truth_reco_x=float(c["truth_reco_x"][i]), truth_reco_y=float(c["truth_reco_y"][i]),
                truth_reco_z=float(c["truth_reco_z"][i]), ms_sa=DV._LAST.get("ms", "")))
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=F)
    w.writeheader()
    w.writerows(rows)
d = [r["d_sa_hook_cm"] for r in rows if r["d_sa_hook_cm"] != ""]
print(json.dumps(dict(calls=len(rows), digest_in_hook=sum(r["digest_in_hook"] for r in rows),
                      replay_exact=sum(r["exact"] for r in rows), with_pred=len(d),
                      max_d_cm=max(d) if d else None,
                      n_space_tree_eq=sum(1 for r in rows if r["n_space_tree"] != "" and r["n_space_tree"] == r["n_space_dump"]),
                      space_points=sum(r["n_space_dump"] for r in rows))))
