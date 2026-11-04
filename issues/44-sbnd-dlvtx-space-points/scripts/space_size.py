"""Size study for a candidate-only Bee-point tree.  Per event of the r7 step-2 output (Sne's copy): the Bee
clustering-pr-global points of the clusters that touch (<= 1 cm) ANY DL call's cloud (Sne's export_r7_space rule),
de-duplicated over calls; written as a flat ROOT tree (x, y, z, q float32, cluster_id int32) with uproot."""
import sys, glob, os, json, zipfile, numpy as np, uproot
from scipy.spatial import cKDTree
root, sample, nunits, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
units = sorted(glob.glob(f"{root}/{sample}/f*/pr/mabc-pr.zip"))[:nunits]
st = dict(ev=0, ev_call=0, calls=0, pts_call=[], pts_ev=[], pts_whole=[], cloud=[], trk_bytes=0, ncl=[])
cols = {k: [] for k in ("evt", "cluster_id", "x", "y", "z", "q")}
for zp in units:
    z = zipfile.ZipFile(zp); bee = {}
    for n in z.namelist():
        if n.endswith("-clustering-pr-global.json"):
            j = json.loads(z.read(n)); bee[int(j["eventNo"])] = j
    for tp in glob.glob(os.path.join(os.path.dirname(zp), "pr_evt*/tracking-pr.root")):
        st["ev"] += 1; st["trk_bytes"] += os.path.getsize(tp)
        f = uproot.open(tp); e = int(f["Trun"]["eventNo"].array(library="np")[0])
        if "T_dlvtx_cloud" not in f or f["T_dlvtx_cloud"].num_entries == 0 or e not in bee: continue
        c = f["T_dlvtx_cloud"].arrays(["call_index", "x", "y", "z"], library="np")
        j = bee[e]; I = np.stack([np.asarray(j[a], float) for a in "xyz"], 1)
        cid = np.asarray(j["cluster_id"], int); tree = cKDTree(I); keep = set()
        st["ev_call"] += 1; st["pts_whole"].append(len(cid))
        for ci in np.unique(c["call_index"]):
            m = c["call_index"] == ci; P = np.stack([c[a][m] for a in "xyz"], 1)
            hit = tree.query_ball_point(P, r=1.0)
            touched = set(cid[np.concatenate([np.asarray(h, int) for h in hit])]) if len(P) else set()
            st["calls"] += 1; st["cloud"].append(int(m.sum()))
            st["pts_call"].append(int(np.isin(cid, list(touched)).sum())); keep |= touched
        sel = np.isin(cid, list(keep)); st["pts_ev"].append(int(sel.sum())); st["ncl"].append(len(keep))
        o = np.argsort(cid[sel], kind="stable")
        cols["evt"].append(np.full(sel.sum(), e, np.int32)); cols["cluster_id"].append(cid[sel][o].astype(np.int32))
        for a in ("x", "y", "z", "q"): cols[a].append(np.asarray(j[a], np.float32)[sel][o])
arr = {k: np.concatenate(v) for k, v in cols.items()}
full = dict(arr); rng = np.random.default_rng(1)
for a in ("x", "y", "z"): full[a] = (arr[a].astype(np.float64) + rng.uniform(-5e-4, 5e-4, len(arr[a]))).astype(np.float32)
full["q"] = (arr["q"].astype(np.float64) * (1 + rng.uniform(-5e-4, 5e-4, len(arr["q"])))).astype(np.float32)
for comp, tag, data in ((uproot.ZLIB(1), "zlib1", arr), (uproot.LZMA(6), "lzma6", arr), (uproot.ZLIB(1), "zlib1-fullprec", full), (uproot.LZMA(6), "lzma6-fullprec", full)):
    arr_w = data
    p = f"{out}_{tag}.root"
    with uproot.recreate(p, compression=comp) as w: w["T_space"] = arr_w
    b = os.path.getsize(p); n = len(arr["x"])
    print(f"{sample} {tag}: {n} points  {b/1e6:.2f} MB  {b/n:.2f} B/point  {b/st['ev']/1e3:.1f} kB/event (all events)")
pc, pe = np.array(st["pts_call"]), np.array(st["pts_ev"])
print(f"{sample}: units {len(units)} events {st['ev']} with DL call {st['ev_call']} calls {st['calls']}")
print(f"  per call: space median {np.median(pc):.0f} mean {pc.mean():.0f} p90 {np.percentile(pc,90):.0f}; cloud median {np.median(st['cloud']):.0f}")
print(f"  per event (union over calls): median {np.median(pe):.0f} mean {pe.mean():.0f}; sum over calls / union = {pc.sum()/pe.sum():.2f}")
print(f"  touched clusters/event median {np.median(st['ncl']):.0f}; whole-event Bee points median {np.median(st['pts_whole']):.0f}")
print(f"  tracking-pr.root mean {st['trk_bytes']/st['ev']/1e3:.0f} kB/event")
