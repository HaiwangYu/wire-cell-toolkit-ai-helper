"""Per-event summary of dv2_snap vs dv2_split_move (P1 data): final DL vertex shift, T_tagger nu vertex shift,
selection flags.  usage: snap_vs_split_summary.py <cmp dir with new/ and snap/> <out csv>"""
import sys, glob, os, csv
import numpy as np, uproot
cmp, out = sys.argv[1], sys.argv[2]
FL = ["nue_score", "numu_score", "numu_cc_flag", "nue_cc_flag" , "cosmict_flag", "match_isFC", "kine_reco_Enu"]
rows = []
for fs in sorted(glob.glob(f"{cmp}/new/*/*/tracking-pr.root")):
    rel = os.path.relpath(fs, f"{cmp}/new"); fn = f"{cmp}/snap/{rel}"
    r = {"evt": rel.split("/")[1]}
    for tag, p in (("split", fs), ("snap", fn)):
        f = uproot.open(p)
        c = f["T_dlvtx_call"].arrays(["final_x", "final_y", "final_z", "pass"] if "pass" in f["T_dlvtx_call"].keys() else ["final_x", "final_y", "final_z"], library="np")
        r[f"{tag}_ncall"] = len(c["final_x"])
        r[f"{tag}_final"] = np.stack([c["final_x"], c["final_y"], c["final_z"]], 1) if len(c["final_x"]) else np.zeros((0, 3))
        t = f["T_tagger"]; keys = set(t.keys())
        a = t.arrays([k for k in ("nu_x", "nu_y", "nu_z", "nue_score", "numu_score", "numu_cc_flag") if k in keys], library="np")
        for k, v in a.items(): r[f"{tag}_{k}"] = float(v[0]) if len(v) else np.nan
        k = f["T_kine"].arrays(["kine_reco_Enu"], library="np")["kine_reco_Enu"]
        r[f"{tag}_Enu"] = float(k[0]) if len(k) else np.nan
    a, b = r.pop("split_final"), r.pop("snap_final")
    r["final_dmax_cm"] = float(np.max(np.linalg.norm(a - b, axis=1))) if a.shape == b.shape and len(a) else np.nan
    r["nu_d_cm"] = float(np.linalg.norm([r["split_nu_x"] - r["snap_nu_x"], r["split_nu_y"] - r["snap_nu_y"], r["split_nu_z"] - r["snap_nu_z"]]))
    rows.append(r)
with open(out, "w", newline="") as fo:
    w = csv.DictWriter(fo, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
d = np.array([r["nu_d_cm"] for r in rows]); fd = np.array([r["final_dmax_cm"] for r in rows])
print("events", len(rows), "ncall split/snap", sum(r["split_ncall"] for r in rows), sum(r["snap_ncall"] for r in rows))
for name, x in (("T_tagger nu vtx shift", d), ("T_dlvtx_call final max shift", fd)):
    x = x[np.isfinite(x)]
    print(name, "n", len(x), "=0", int((x < 1e-4).sum()), "<0.5", int((x < 0.5).sum()), "<1", int((x < 1).sum()), "<3", int((x < 3).sum()), "median %.3f max %.2f" % (np.median(x), x.max()))
nue = lambda r, t: r[f"{t}_nue_score"] > 7.0
numu = lambda r, t: r.get(f"{t}_numu_cc_flag", np.nan) > 0 if False else r[f"{t}_numu_score"] > 0.9
for nm, fn in (("nue_score>7", nue), ("numu_score>0.9", numu)):
    s = sum(fn(r, "split") for r in rows); n = sum(fn(r, "snap") for r in rows)
    ch = [r["evt"] for r in rows if fn(r, "split") != fn(r, "snap")]
    print(nm, "split", s, "snap", n, "changed", ch)
print("Enu |diff| median %.1f MeV" % np.nanmedian([abs(r["split_Enu"] - r["snap_Enu"]) for r in rows]))
