#!/usr/bin/env python3
"""Fitted dQ/dx after the full Wire-Cell reconstruction, YZ scaling off vs on
(ai-helper issue 46).

Source: step 2's pr_evt*/tracking-pr.root (WCT 0.38.0 SbndPrMagnifyTrackingVisitor):
  T_rec_charge: every fitted point of every neutrino candidate's PR graph
    (TrackFitting::dQ_dx_multi_fit).  q = dQ * 0.1 - 1000 (Trun.dQdx_scale/offset,
    dQ in electrons), nq = dx [cm], x/y/z [cm] (reco space), flag_vertex,
    flag_shower, real_cluster_id = cluster*1000 + segment graph index, nu_index.
    So dQ/dx = (q - offset) / scale / nq.
  T_overlap (truth_match=true): per (nu_index, segment_id = real_cluster_id) the
    charge of each true trackid (-1 = unlabeled); T_truth_track: trackid -> pdg.
Matching off <-> on BY TRUTH (the two runs share G4, not the reco): each segment
gets the trackid with the largest labeled charge if that is >= --min-purity of the
segment's charge; the fitted points (flag_vertex 0, dx > 0, without the first and
last --end-pts points of each segment) of all segments of one trackid form that
true particle's fitted track, in off and in on separately.  Tracks with >= --min-pts
points and >= --min-len cm (sum of dx) in both are compared.
Per track: median dQ/dx off and on, ratio; expectation = median(off_i * G_i) /
median(off_i), G_i = the map at the point's (y, z):
  G = mean of the three planes' g (main expectation: dQ_dx_multi_fit fits each
      point's charge to the 2D charge of all three planes), and g_U, g_V, g_Y alone.
Per point: each on point to the nearest off point of the same true track (< --point-dist cm).
Global: all fitted track points (flag_shower 0), sum dQ / sum dx and median, on/off.

Usage (wire-cell-python venv):
  dqdx_fit.py <off/step2> <on/step2> <outdir> [--min-len 10] [--min-pts 10] [--end-pts 1]
              [--min-purity 0.7] [--point-dist 1.0]
Also 10-cm bins (--bin-len) along each track's principal axis: sum dQ / sum dx off and on vs
the charge-weighted map of the bin.
Output: <outdir>/fit_points.npz, fit_bins.npz, fit_tracks.tsv, fit_summary.json
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
import uproot

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dqdx_common import PL, YZMap, robust_stats  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("off"); ap.add_argument("on"); ap.add_argument("outdir")
ap.add_argument("--min-len", type=float, default=10.0)
ap.add_argument("--min-pts", type=int, default=10)
ap.add_argument("--end-pts", type=int, default=1)
ap.add_argument("--min-purity", type=float, default=0.7)
ap.add_argument("--point-dist", type=float, default=1.0)
ap.add_argument("--bin-len", type=float, default=10.0)
a = ap.parse_args()
os.makedirs(a.outdir, exist_ok=True)
ymap = YZMap()
BR = ["x", "y", "z", "q", "nq", "flag_vertex", "flag_shower", "real_cluster_id", "particle_id", "nu_index"]


def gmaps(x, y, z):
    tpc = (np.asarray(x) >= 0).astype(int)
    g = np.ones((len(x), 3))
    for t in (0, 1):
        m = tpc == t
        for p in range(3):
            g[m, p] = ymap(t, p, y[m], z[m])
    return g


def load(step2):
    ev = {}
    for fn in sorted(glob.glob(f"{step2}/pr_evt*/tracking-pr.root")):
        f = uproot.open(fn)
        run = f["Trun"].arrays(["runNo", "subRunNo", "eventNo", "dQdx_scale", "dQdx_offset"], library="np")
        rse = (int(run["runNo"][0]), int(run["subRunNo"][0]), int(run["eventNo"][0]))
        sc, of = float(run["dQdx_scale"][0]), float(run["dQdx_offset"][0])
        t = f["T_rec_charge"]
        d = t.arrays([b for b in BR if b in t.keys()], library="np")
        if "nu_index" not in d:
            d["nu_index"] = np.zeros(len(d["x"]), int)
        d["dQ"] = (d["q"] - of) / sc
        # segment -> dominant true trackid
        o = f["T_overlap"].arrays(["nu_index", "segment_id", "trackid", "q"], library="np")
        seg2tid = {}
        for key in set(zip(o["nu_index"].tolist(), o["segment_id"].tolist())):
            if key[1] < 0:
                continue
            m = (o["nu_index"] == key[0]) & (o["segment_id"] == key[1])
            tot = o["q"][m].sum()
            lab = m & (o["trackid"] >= 0)
            if tot <= 0 or not lab.any():
                continue
            tids = np.unique(o["trackid"][lab])
            qs = np.array([o["q"][lab & (o["trackid"] == x)].sum() for x in tids])
            if qs.max() / tot >= a.min_purity:
                seg2tid[key] = int(tids[qs.argmax()])
        tt = f["T_truth_track"].arrays(["trackid", "pdg"], library="np")
        pdg = dict(zip(tt["trackid"].tolist(), tt["pdg"].tolist()))
        # per true track: point indices (segment points without the end points)
        tracks = {}
        sv = (d["flag_vertex"] == 0)
        for key in set(zip(d["nu_index"][sv].tolist(), d["real_cluster_id"][sv].tolist())):
            if key not in seg2tid:
                continue
            idx = np.flatnonzero(sv & (d["nu_index"] == key[0]) & (d["real_cluster_id"] == key[1]))
            idx = idx[a.end_pts:len(idx) - a.end_pts]
            idx = idx[d["nq"][idx] > 0]
            if len(idx):
                tracks.setdefault(seg2tid[key], []).append(idx)
        tracks = {k: np.concatenate(v) for k, v in tracks.items()}
        ev[rse] = dict(d=d, tracks=tracks, pdg=pdg, nseg_labeled=len(seg2tid), file=fn)
    return ev


E0, E1 = load(a.off), load(a.on)
common = sorted(set(E0) & set(E1))
print(f"events with tracking-pr.root: off {len(E0)}, on {len(E1)}, both {len(common)}")

# ---- global: every fitted track point (not vertex, not shower) with dx > 0
glob_stats = {}
for tag, E in (("off", E0), ("on", E1)):
    dq, dx = [], []
    for k in common:
        d = E[k]["d"]
        m = (d["flag_vertex"] == 0) & (d["flag_shower"] == 0) & (d["nq"] > 0)
        dq.append(d["dQ"][m]); dx.append(d["nq"][m])
    dq, dx = (np.concatenate(v) if v else np.zeros(0) for v in (dq, dx))
    glob_stats[tag] = dict(points=int(len(dq)), sum_dQ=float(dq.sum()), sum_dx=float(dx.sum()),
                           mean_dqdx=float(dq.sum() / dx.sum()) if len(dq) else None,
                           median_dqdx=float(np.median(dq / dx)) if len(dq) else None)

rows, prow, brow = [], [], []
for k in common:
    for tid in sorted(set(E0[k]["tracks"]) & set(E1[k]["tracks"])):
        ia, ib = E0[k]["tracks"][tid], E1[k]["tracks"][tid]
        d0, d1 = E0[k]["d"], E1[k]["d"]
        La, Lb = d0["nq"][ia].sum(), d1["nq"][ib].sum()
        if min(len(ia), len(ib)) < a.min_pts or min(La, Lb) < a.min_len:
            continue
        qa, qb = d0["dQ"][ia] / d0["nq"][ia], d1["dQ"][ib] / d1["nq"][ib]
        Pa = np.stack([d0["x"][ia], d0["y"][ia], d0["z"][ia]], 1)
        Pb = np.stack([d1["x"][ib], d1["y"][ib], d1["z"][ib]], 1)
        ga = gmaps(Pa[:, 0], Pa[:, 1], Pa[:, 2])
        gavg = ga.mean(1)
        r = dict(run=k[0], subrun=k[1], event=k[2], trackid=tid, pdg=int(E0[k]["pdg"].get(tid, 0)),
                 L_off=float(La), L_on=float(Lb), n_off=len(ia), n_on=len(ib),
                 y=float(np.median(Pa[:, 1])), z=float(np.median(Pa[:, 2])), tpc=int(np.median(Pa[:, 0]) >= 0),
                 off=float(np.median(qa)), on=float(np.median(qb)))
        r["ratio"] = r["on"] / r["off"]
        r["exp_avg"] = float(np.median(qa * gavg) / np.median(qa))
        for p in range(3):
            r[f"exp_{PL[p]}"] = float(np.median(qa * ga[:, p]) / np.median(qa))
        r["sum_ratio"] = float((d1["dQ"][ib].sum() / Lb) / (d0["dQ"][ia].sum() / La))
        r["sum_exp_avg"] = float((d0["dQ"][ia] * gavg).sum() / d0["dQ"][ia].sum())
        rows.append(r)
        # 10-cm bins along the principal axis of the off points: sum dQ / sum dx, off and on
        c0 = Pa.mean(0)
        ax_ = np.linalg.svd(Pa - c0, full_matrices=False)[2][0]
        ua, ub = (Pa - c0) @ ax_, (Pb - c0) @ ax_
        edges = np.arange(ua.min(), ua.max() + a.bin_len, a.bin_len)
        for i0 in range(len(edges) - 1):
            ma = (ua >= edges[i0]) & (ua < edges[i0 + 1])
            mb = (ub >= edges[i0]) & (ub < edges[i0 + 1])
            xa, xb = d0["nq"][ia][ma].sum(), d1["nq"][ib][mb].sum()
            if ma.sum() < 3 or mb.sum() < 3 or xa < 0.5 * a.bin_len or xb < 0.5 * a.bin_len:
                continue
            brow.append((k[0], k[1], k[2], len(rows) - 1, tid, Pa[ma, 0].mean(), Pa[ma, 1].mean(), Pa[ma, 2].mean(),
                         d0["dQ"][ia][ma].sum() / xa, d1["dQ"][ib][mb].sum() / xb,
                         *[(d0["dQ"][ia][ma] * ga[ma, p]).sum() / d0["dQ"][ia][ma].sum() for p in range(3)]))
        # per track from the common bins only (same stretch of track in both runs)
        bt = [b for b in brow if b[3] == len(rows) - 1]
        if len(bt) >= 3:
            bo, bn = np.array([b[8] for b in bt]), np.array([b[9] for b in bt])
            bg = np.array([(b[10] + b[11] + b[12]) / 3 for b in bt])
            r.update(nbins=len(bt), ratio_bins=float(np.median(bn) / np.median(bo)),
                     exp_bins=float(np.median(bo * bg) / np.median(bo)))
        else:
            r.update(nbins=len(bt), ratio_bins=float("nan"), exp_bins=float("nan"))
        # per point: nearest off point of the same true track
        gb = gmaps(Pb[:, 0], Pb[:, 1], Pb[:, 2])
        for i0 in range(0, len(ib), 2000):
            dist = np.linalg.norm(Pb[i0:i0 + 2000, None, :] - Pa[None, :, :], axis=2)
            jn = dist.argmin(1)
            dn = dist[np.arange(len(jn)), jn]
            for ii in np.flatnonzero(dn < a.point_dist):
                prow.append((k[0], k[1], k[2], len(rows) - 1, tid, Pb[i0 + ii, 0], Pb[i0 + ii, 1], Pb[i0 + ii, 2],
                             qa[jn[ii]], qb[i0 + ii], gb[i0 + ii, 0], gb[i0 + ii, 1], gb[i0 + ii, 2], dn[ii]))

cols = list(rows[0].keys()) if rows else []
with open(f"{a.outdir}/fit_tracks.tsv", "w") as fp:
    fp.write("\t".join(cols) + "\n")
    for r in rows:
        fp.write("\t".join(f"{r[c]:.6g}" if isinstance(r[c], float) else str(r[c]) for c in cols) + "\n")
Pp = np.array(prow, float).reshape(-1, 14)
np.savez_compressed(f"{a.outdir}/fit_points.npz", run=Pp[:, 0], subrun=Pp[:, 1], event=Pp[:, 2], track=Pp[:, 3],
                    trackid=Pp[:, 4], x=Pp[:, 5], y=Pp[:, 6], z=Pp[:, 7], dqdx_off=Pp[:, 8], dqdx_on=Pp[:, 9],
                    gU=Pp[:, 10], gV=Pp[:, 11], gY=Pp[:, 12], dist=Pp[:, 13])

Bb = np.array(brow, float).reshape(-1, 13)
np.savez_compressed(f"{a.outdir}/fit_bins.npz", run=Bb[:, 0], subrun=Bb[:, 1], event=Bb[:, 2], track=Bb[:, 3],
                    trackid=Bb[:, 4], x=Bb[:, 5], y=Bb[:, 6], z=Bb[:, 7], dqdx_off=Bb[:, 8], dqdx_on=Bb[:, 9],
                    gU=Bb[:, 10], gV=Bb[:, 11], gY=Bb[:, 12])
S = dict(inputs=dict(off=a.off, on=a.on), args=vars(a), events=dict(off=len(E0), on=len(E1), both=len(common)),
         true_tracks_with_fit=dict(off=sum(len(E0[k]["tracks"]) for k in common),
                                   on=sum(len(E1[k]["tracks"]) for k in common)),
         tracks_compared=len(rows), global_track_points=glob_stats)
if glob_stats["off"]["mean_dqdx"] and glob_stats["on"]["mean_dqdx"]:
    S["global_on_over_off_sum_dQ_over_sum_dx"] = glob_stats["on"]["mean_dqdx"] / glob_stats["off"]["mean_dqdx"]
    S["global_on_over_off_median_point_dqdx"] = glob_stats["on"]["median_dqdx"] / glob_stats["off"]["median_dqdx"]


def track_block(sel):
    R = {c: np.array([r[c] for r, s in zip(rows, sel) if s]) for c in cols}
    if not len(R.get("ratio", [])):
        return dict(tracks=0)
    B = dict(tracks=int(len(R["ratio"])), length_cm=robust_stats(R["L_off"]),
             off_median_ke_cm=float(np.median(R["off"]) / 1e3), on_median_ke_cm=float(np.median(R["on"]) / 1e3),
             ratio=robust_stats(R["ratio"]), exp_avg=robust_stats(R["exp_avg"]),
             ratio_over_exp_avg=robust_stats(R["ratio"] / R["exp_avg"]),
             ratio_bins=robust_stats(R["ratio_bins"]), exp_bins=robust_stats(R["exp_bins"]),
             ratio_bins_over_exp_bins=robust_stats(R["ratio_bins"] / R["exp_bins"]),
             corr_ratio_exp_avg=float(np.corrcoef(R["ratio"], R["exp_avg"])[0, 1]) if len(R["ratio"]) > 2 else None,
             sum_ratio=robust_stats(R["sum_ratio"]), sum_exp_avg=robust_stats(R["sum_exp_avg"]))
    for p in PL:
        B[f"exp_{p}"] = robust_stats(R[f"exp_{p}"])
        B[f"ratio_over_exp_{p}"] = robust_stats(R["ratio"] / R[f"exp_{p}"])
        B[f"corr_ratio_exp_{p}"] = float(np.corrcoef(R["ratio"], R[f"exp_{p}"])[0, 1]) if len(R["ratio"]) > 2 else None
    return B


if rows:
    pd = np.array([abs(r["pdg"]) for r in rows])
    S["tracks"] = {"all": track_block(np.ones(len(rows), bool)), "mu": track_block(pd == 13),
                   "p": track_block(pd == 2212), "other": track_block((pd != 13) & (pd != 2212))}
if len(Pp):
    rr = Pp[:, 9] / Pp[:, 8]
    gU, gV, gY = Pp[:, 10], Pp[:, 11], Pp[:, 12]
    gavg = (gU + gV + gY) / 3
    ok = np.isfinite(rr) & (rr > 0)
    S["points"] = dict(n=int(ok.sum()), ratio=robust_stats(rr[ok]), ratio_over_gavg=robust_stats((rr / gavg)[ok]),
                       corr_ratio_gavg=float(np.corrcoef(rr[ok], gavg[ok])[0, 1]),
                       corr_ratio_gU=float(np.corrcoef(rr[ok], gU[ok])[0, 1]),
                       corr_ratio_gV=float(np.corrcoef(rr[ok], gV[ok])[0, 1]),
                       corr_ratio_gY=float(np.corrcoef(rr[ok], gY[ok])[0, 1]),
                       gavg=robust_stats(gavg[ok]))
    # empirical plane weights: log(ratio) = sum_p w_p log(g_p), least squares, |log ratio| < 0.3
    m = ok & (np.abs(np.log(np.where(ok, rr, 1))) < 0.3)
    A = np.log(np.stack([gU, gV, gY], 1))[m]
    w, *_ = np.linalg.lstsq(A, np.log(rr[m]), rcond=None)
    S["points"]["lsq_plane_weights_UVY"] = w.tolist()
if len(Bb):
    rr = Bb[:, 9] / Bb[:, 8]
    gU, gV, gY = Bb[:, 10], Bb[:, 11], Bb[:, 12]
    gavg = (gU + gV + gY) / 3
    ok = np.isfinite(rr) & (rr > 0)
    S["bins"] = dict(bin_len_cm=a.bin_len, n=int(ok.sum()), ratio=robust_stats(rr[ok]),
                     ratio_over_gavg=robust_stats((rr / gavg)[ok]), ratio_over_gY=robust_stats((rr / gY)[ok]),
                     gavg=robust_stats(gavg[ok]),
                     corr_ratio_gavg=float(np.corrcoef(rr[ok], gavg[ok])[0, 1]),
                     corr_ratio_gU=float(np.corrcoef(rr[ok], gU[ok])[0, 1]),
                     corr_ratio_gV=float(np.corrcoef(rr[ok], gV[ok])[0, 1]),
                     corr_ratio_gY=float(np.corrcoef(rr[ok], gY[ok])[0, 1]))
    m = ok & (np.abs(np.log(np.where(ok, rr, 1))) < 0.3)
    A = np.log(np.stack([gU, gV, gY], 1))[m]
    w, *_ = np.linalg.lstsq(A, np.log(rr[m]), rcond=None)
    S["bins"]["lsq_plane_weights_UVY"] = w.tolist()
    # slope of ratio vs gavg (1 = follows the 3-plane mean map)
    S["bins"]["slope_ratio_vs_gavg"] = float(np.polyfit(gavg[ok] - 1, rr[ok] - 1, 1)[0])
json.dump(S, open(f"{a.outdir}/fit_summary.json", "w"), indent=1)
print(json.dumps({k: S[k] for k in ("events", "true_tracks_with_fit", "tracks_compared")}))
for k, B in S.get("tracks", {}).items():
    if B["tracks"]:
        print(f"{k}: {B['tracks']} tracks, ratio median {B['ratio']['median']:.4f} (half-68 {B['ratio']['half68']:.4f}), "
              f"exp (3-plane mean) {B['exp_avg']['median']:.4f}, ratio/exp median {B['ratio_over_exp_avg']['median']:.4f} "
              f"rms {B['ratio_over_exp_avg']['rms']:.4f}, corr {B['corr_ratio_exp_avg']}; common bins: "
              f"{B['ratio_bins_over_exp_bins']['n']} tracks, ratio {B['ratio_bins'].get('median', np.nan):.4f} "
              f"exp {B['exp_bins'].get('median', np.nan):.4f} ratio/exp median "
              f"{B['ratio_bins_over_exp_bins'].get('median', np.nan):.4f} rms {B['ratio_bins_over_exp_bins'].get('rms', np.nan):.4f}")
if "points" in S:
    P = S["points"]
    print(f"points: {P['n']}, ratio/gavg median {P['ratio_over_gavg']['median']:.4f} half-68 {P['ratio_over_gavg']['half68']:.3f}; "
          f"corr with gavg/gU/gV/gY {P['corr_ratio_gavg']:.3f}/{P['corr_ratio_gU']:.3f}/{P['corr_ratio_gV']:.3f}/"
          f"{P['corr_ratio_gY']:.3f}; lsq weights U,V,Y {np.round(P['lsq_plane_weights_UVY'], 3).tolist()}")
if "bins" in S:
    B = S["bins"]
    print(f"{a.bin_len:g}-cm bins: {B['n']}, ratio/gavg median {B['ratio_over_gavg']['median']:.4f} half-68 "
          f"{B['ratio_over_gavg']['half68']:.3f}; corr with gavg/gU/gV/gY {B['corr_ratio_gavg']:.3f}/{B['corr_ratio_gU']:.3f}/"
          f"{B['corr_ratio_gV']:.3f}/{B['corr_ratio_gY']:.3f}; slope vs gavg {B['slope_ratio_vs_gavg']:.2f}; "
          f"lsq weights U,V,Y {np.round(B['lsq_plane_weights_UVY'], 3).tolist()}")
if "global_on_over_off_sum_dQ_over_sum_dx" in S:
    print(f"global track points: sum dQ/sum dx on/off {S['global_on_over_off_sum_dQ_over_sum_dx']:.4f}, "
          f"median point dQ/dx on/off {S['global_on_over_off_median_point_dqdx']:.4f}")
print(f"wrote {a.outdir}/fit_points.npz, fit_tracks.tsv, fit_summary.json")
