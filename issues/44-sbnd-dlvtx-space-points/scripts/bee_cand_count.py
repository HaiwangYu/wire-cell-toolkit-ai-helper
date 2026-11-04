"""Per event: Bee clustering-pr points total vs. on the neutrino candidate's clusters (T_bundle / T_cluster / T_kine),
vs. traj-fit points (track_fit layer, T_rec_charge)."""
import sys, json, zipfile, glob, os
import numpy as np, uproot
rows = []
for d in sorted(glob.glob(os.path.join(sys.argv[1], "evt*/"))):
    z, t = os.path.join(d, "mabc.zip"), os.path.join(d, "tracking-pr.root")
    if not (os.path.exists(z) and os.path.exists(t)): continue
    zf = zipfile.ZipFile(z)
    def layer(suffix):
        n = [x for x in zf.namelist() if x.endswith(suffix)]
        return json.loads(zf.read(n[0])) if n else None
    pr = layer("-clustering-pr-global.json"); img = layer("-img-global.json"); tf = layer("-track_fit-global.json")
    f = uproot.open(t)
    names = [k.split(";")[0] for k in f.keys()]
    cand = set()
    if "T_kine" in names and f["T_kine"].num_entries:
        k = f["T_kine"].arrays(library="np")
        for v in k.get("kine_particle_cluster_id", []): cand.update(int(c) for c in v)
    if "T_bundle" in names and f["T_bundle"].num_entries:
        b = f["T_bundle"].arrays(library="np")
        if "sel_cluster_id" in b: cand.update(int(c) for c in b["sel_cluster_id"] if c >= 0)
    if not cand and "T_rec_charge" in names and f["T_rec_charge"].num_entries:
        rc = f["T_rec_charge"].arrays(["cluster_id", "real_cluster_id"], library="np")
        cand.update(int(c) for c in set(rc["cluster_id"]))
        cand.update(int(r) // 1000 for r in set(rc["real_cluster_id"]) if r >= 1000)
    main = set()
    if "T_cluster" in names:
        c = f["T_cluster"].arrays(library="np")
        cols = list(c.keys())
        if "flash_id" in c and "T_bundle" in names and f["T_bundle"].num_entries:
            gids = set(int(g) for g in f["T_bundle"].arrays(library="np")["gid"])
            main = set(int(cid) for cid, fid in zip(c["cluster_id"], c["flash_id"]) if int(fid) in gids)
    cl = np.asarray(pr["cluster_id"]) if pr else np.array([])
    n_pr = len(cl); n_cand = int(np.isin(cl, list(cand)).sum()) if cand else 0
    n_bund = int(np.isin(cl, list(main)).sum()) if main else 0
    n_tf = len(tf["x"]) if tf else 0
    n_rc = f["T_rec_charge"].num_entries if "T_rec_charge" in names else 0
    rows.append((os.path.basename(d.rstrip("/")), len(img["x"]) if img else 0, n_pr, len(cand), n_cand, len(main), n_bund, n_tf, n_rc))
print("evt img_pts clus_pr_pts n_kine_clusters pts_on_kine_clusters n_bundle_clusters pts_on_bundle_clusters trackfit_pts T_rec_charge_rows")
for r in rows: print(*r)
a = np.array([r[1:] for r in rows], float)
w = a[:, 3] > 0
print("events", len(rows), "with candidate", int(w.sum()))
for i, nme in enumerate(["img", "clus_pr", "nkc", "kine_pts", "nbc", "bundle_pts", "trackfit", "rec_charge"]):
    print(f"{nme:11s} median(all) {np.median(a[:, i]):9.0f}  median(cand evts) {np.median(a[w, i]) if w.any() else 0:9.0f}  mean(cand) {a[w, i].mean() if w.any() else 0:9.0f}")
