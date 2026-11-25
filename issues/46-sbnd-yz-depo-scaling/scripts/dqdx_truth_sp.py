#!/usr/bin/env python3
"""Truth-track SP dQ/dx per plane, YZ scaling off vs on (ai-helper issue 46).

Method (after Ningclover/sbnd-wirecell-bdt docs/dqdx_data_mc.md, section 2):
  - Tracks: true MCParticle trajectories (muons; optionally protons), resampled in
    --step cm steps.  Each step is moved by the simulation's own space-charge
    displacement (SpaceChargeSBND TrueFwd, as larsim IonAndScint does), which gives
    the wire it lands on and its drift time; the step's TRUE length is its dx.
  - One "track" = the contiguous part of a particle inside the active volume of one
    TPC (a cathode crosser gives two).  The first and last --end-cut cm of it are dropped.
  - Per plane, per wire crossed: dx = true length whose charge lands on that wire,
    Q = SP charge of the channel in [tick_min - pad, tick_max + pad] of the steps on
    that wire, dQ/dx = Q / dx.  tick = (t_G4 + (202.05 - |x_sce|)/v_drift + 205 us)/0.5 us
    + a per-plane offset fitted on the data itself (pass 1, charge centre).
  - Skipped wires: bad channels (simtpc2d:badchannels), wires crossed twice (the
    steps on that wire are not one contiguous run), windows outside the readout,
    and windows where the track's family has < --min-purity of the SimChannel
    electrons on that channel (overlaps with other particles).
  - Per track and plane: median dQ/dx over the kept wires (>= --min-wires).
  - Expected on/off ratio of a track median: median(off_i * g_i) / median(off_i),
    g_i = the map of that plane at the wire's steps (SCE (y, z), the position the
    simulation looks the map up at), i.e. the off measurement scaled by the map.
Same G4 events in both files; truth from the off file (identical); SimChannels are
written before the scaling, so they are identical too.

Input: the npz dumps of dqdx_dump_art.py (run-dqdx-dump.sh) of the off and on files.
Usage (wire-cell-python venv):
  dqdx_truth_sp.py <dump-off-dir> <dump-on-dir> <outdir> [--products dnnsp,gauss]
       [--pdg 13,2212] [--min-len-mu 30] [--min-len-p 15] [--pad 10] [--end-cut 5]
       [--min-purity 0.8] [--min-wires 20] [--step 0.05]
Output: <outdir>/truth_sp_wires.npz (per wire), truth_sp_tracks.tsv (per track and
plane), truth_sp_summary.json.
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dqdx_common import (ACTIVE, FRAME_SCALE, NTICKS, PL, TPC, SCE, Geometry, YZMap,  # noqa: E402
                         robust_stats, tick_of)

ap = argparse.ArgumentParser()
ap.add_argument("off"); ap.add_argument("on"); ap.add_argument("outdir")
ap.add_argument("--products", default="dnnsp,gauss")
ap.add_argument("--pdg", default="13,2212")
ap.add_argument("--min-len-mu", type=float, default=30.0)
ap.add_argument("--min-len-p", type=float, default=15.0)
ap.add_argument("--pad", type=float, default=10.0)
ap.add_argument("--pad-cal", type=float, default=40.0)
ap.add_argument("--end-cut", type=float, default=5.0)
ap.add_argument("--min-purity", type=float, default=0.8)
ap.add_argument("--min-wires", type=int, default=20)
ap.add_argument("--step", type=float, default=0.05)
ap.add_argument("--sc-broad", type=float, default=200.0)
ap.add_argument("--sc-off0", type=float, default=(1700.0 - 205.0) / 0.5)
ap.add_argument("--max-events", type=int, default=-1)
a = ap.parse_args()
os.makedirs(a.outdir, exist_ok=True)
prods = a.products.split(",")
pdgs = [int(x) for x in a.pdg.split(",")]

geo, sce, ymap = Geometry(), SCE(), YZMap()


def dense(d, inst):
    """recob::Wire ROIs -> dense (channel, tick) float32 SP electrons."""
    arr = np.zeros((2 * 5638, NTICKS), np.float32)
    ch, st, ln, val = (d[f"wire_{inst}_{k}"] for k in ("ch", "start", "len", "val"))
    off = 0
    for c, s, n in zip(ch, st, ln):
        arr[c, s:s + n] = val[off:off + n]
        off += n
    return arr / FRAME_SCALE


def family(d, tid):
    ids, mot = d["mcp_all_id"], d["mcp_all_mother"]
    fam = {int(tid)}
    kids = {}
    for i, m in zip(ids, mot):
        kids.setdefault(int(m), []).append(int(i))
    todo = [int(tid)]
    while todo:
        x = todo.pop()
        for k in kids.get(x, []):
            if k not in fam:
                fam.add(k)
                todo.append(k)
    return np.array(sorted(fam))


def pieces(d):
    """Resampled, SCE-moved steps of the selected particles, split into
    contiguous active-volume runs per TPC."""
    out = []
    off = np.concatenate([[0], np.cumsum(d["mcp_n"])])
    for i, (tid, pdg) in enumerate(zip(d["mcp_id"], d["mcp_pdg"])):
        if abs(pdg) not in pdgs:
            continue
        sl = slice(off[i], off[i + 1])
        P = np.stack([d["trj_x"][sl], d["trj_y"][sl], d["trj_z"][sl]], 1).astype(float)
        T = d["trj_t"][sl].astype(float)
        seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
        # resample: steps of a.step cm, midpoints
        L = np.concatenate([[0], np.cumsum(seg)])
        if L[-1] < 1:
            continue
        s = np.arange(0.5 * a.step, L[-1], a.step)
        Pm = np.stack([np.interp(s, L, P[:, k]) for k in range(3)], 1)
        Tm = np.interp(s, L, T)
        inside = ((Pm[:, 0] > ACTIVE["x"][0]) & (Pm[:, 0] < ACTIVE["x"][1]) & (Pm[:, 1] > ACTIVE["y"][0])
                  & (Pm[:, 1] < ACTIVE["y"][1]) & (Pm[:, 2] > ACTIVE["z"][0]) & (Pm[:, 2] < ACTIVE["z"][1]))
        tpc = (Pm[:, 0] >= 0).astype(int)
        lab = np.where(inside, tpc, -1)
        # contiguous runs of the same label
        brk = np.flatnonzero(np.diff(lab) != 0) + 1
        for r in np.split(np.arange(len(s)), brk):
            if lab[r[0]] < 0:
                continue
            length = len(r) * a.step
            minlen = a.min_len_mu if abs(pdg) == 13 else a.min_len_p
            if length < minlen:
                continue
            Ps = sce(Pm[r, 0], Pm[r, 1], Pm[r, 2])
            out.append(dict(tid=int(tid), pdg=int(pdg), tpc=int(lab[r[0]]), P=Pm[r], Ps=Ps,
                            t=Tm[r], s=np.arange(len(r)) * a.step + 0.5 * a.step, L=length,
                            primary=int(d["mcp_proc"][i]), e0=float(d["mcp_e0"][i])))
    return out


def wires_of(pc, plane, toff):
    """Per wire crossed once: (iw, step index array)."""
    w = geo.wire_coord(pc["tpc"], plane, pc["Ps"][:, 1], pc["Ps"][:, 2])
    iw = np.rint(w).astype(int)
    brk = np.flatnonzero(np.diff(iw) != 0) + 1
    runs = np.split(np.arange(len(iw)), brk)
    cnt = {}
    for r in runs:
        cnt[iw[r[0]]] = cnt.get(iw[r[0]], 0) + 1
    tick = tick_of(pc["t"], pc["Ps"][:, 0]) + toff
    return [(iw[r[0]], r) for r in runs if cnt[iw[r[0]]] == 1], tick, cnt


def measure(evs, toff, sc_off, pad, calib=False):
    rows = []
    for (rse, d0, d1, dens0, dens1) in evs:
        bad = set(d0["bad"].tolist())
        sco = np.argsort(d0["sc_ch"], kind="stable")
        sc_ch, sc_tdc, sc_tid, sc_ne = (d0[f"sc_{k}"][sco] for k in ("ch", "tdc", "tid", "ne"))
        for pc in pieces(d0):
            fam = family(d0, pc["tid"])
            for plane in range(3):
                wl, tick, cnt = wires_of(pc, plane, toff[pc["tpc"], plane])
                ndouble = sum(1 for v in cnt.values() if v > 1)
                for iw, r in wl:
                    ch = int(geo.channel(pc["tpc"], plane, iw))
                    if ch < 0:
                        continue
                    smin, smax = pc["s"][r[0]], pc["s"][r[-1]]
                    if smin < a.end_cut or smax > pc["L"] - a.end_cut:
                        continue
                    t0, t1 = tick[r].min(), tick[r].max()
                    lo, hi = int(np.floor(t0 - pad)), int(np.ceil(t1 + pad)) + 1
                    if lo < 0 or hi > NTICKS:
                        continue
                    # SimChannel: electrons on this channel in the window, family fraction
                    i0, i1 = np.searchsorted(sc_ch, [ch, ch + 1])
                    tdc = sc_tdc[i0:i1] - sc_off
                    inw = (tdc >= lo) & (tdc < hi)
                    ne_all = sc_ne[i0:i1][inw].sum()
                    fm = inw & np.isin(sc_tid[i0:i1], fam)
                    ne_fam = sc_ne[i0:i1][fm].sum()
                    # family electrons near the track on this channel (broad, for the TDC calibration)
                    fb = (np.abs(tdc - 0.5 * (t0 + t1)) < a.sc_broad) & np.isin(sc_tid[i0:i1], fam)
                    sc_cen = (np.average(tdc[fb], weights=sc_ne[i0:i1][fb]) + sc_off
                              if sc_ne[i0:i1][fb].sum() > 0 else np.nan)
                    row = dict(ev=rse, tid=pc["tid"], pdg=pc["pdg"], tpc=pc["tpc"], plane=plane, ch=ch,
                               bad=int(ch in bad), s=0.5 * (smin + smax), L=pc["L"],
                               y=pc["Ps"][r, 1].mean(), z=pc["Ps"][r, 2].mean(), x=pc["Ps"][r, 0].mean(),
                               dx=len(r) * a.step, tc=0.5 * (t0 + t1), tw=t1 - t0,
                               g=ymap(pc["tpc"], plane, pc["Ps"][r, 1], pc["Ps"][r, 2]).mean(),
                               purity=ne_fam / ne_all if ne_all > 0 else 0.0, ne=ne_fam, sc_cen=sc_cen,
                               ndouble=ndouble, primary=pc["primary"], e0=pc["e0"],
                               cosx=(pc["P"][-1, 0] - pc["P"][0, 0]) / max(np.linalg.norm(pc["P"][-1] - pc["P"][0]), 1e-6))
                    for prod in prods:
                        for tag, dn in (("off", dens0), ("on", dens1)):
                            wf = dn[prod][ch, lo:hi]
                            q = float(wf.sum())
                            row[f"q_{tag}_{prod}"] = q
                            if tag == "off":
                                tt = np.arange(lo, hi)
                                row[f"cen_{prod}"] = float((wf * tt).sum() / q) if q > 0 else np.nan
                    rows.append(row)
    return rows


# ---- load events
f0 = sorted(glob.glob(f"{a.off}/evt_*.npz"))
evs = []
for fn in f0[: a.max_events if a.max_events > 0 else None]:
    fn1 = f"{a.on}/{os.path.basename(fn)}"
    if not os.path.exists(fn1):
        print(f"no on-file for {fn}; skipped")
        continue
    d0, d1 = dict(np.load(fn)), dict(np.load(fn1))
    if not np.array_equal(d0["mcp_id"], d1["mcp_id"]) or not np.array_equal(d0["trj_x"], d1["trj_x"]):
        raise SystemExit(f"truth differs between off and on for {fn}")
    rse = tuple(int(x) for x in d0["rse"])
    evs.append((rse, d0, d1, {p: dense(d0, p) for p in prods}, {p: dense(d1, p) for p in prods}))
print(f"{len(evs)} events")

# ---- pass 0: SimChannel TDC offset w.r.t. the nominal tick (family electrons within +-sc_broad ticks)
toff = np.zeros((2, 3))
# SimChannel TDCs count from the G4 reference time (-1.7 ms), the readout from -205 us: nominally +2990 ticks
cal0 = measure(evs, toff, a.sc_off0, a.pad_cal, calib=True)
sc_off = float(np.nanmedian([r["sc_cen"] - r["tc"] for r in cal0 if r["tw"] < 5]))
# ---- pass 1: tick offset per (tpc, plane) from the SP charge centre (broad window), on clean wires
cal = measure(evs, toff, sc_off, a.pad_cal, calib=True)
C = {k: np.array([r[k] for r in cal]) for k in ("tpc", "plane", "purity", "bad", "tc", "sc_cen", "tw", f"cen_{prods[0]}", "ne")}
good = (C["purity"] > 0.95) & (C["bad"] == 0) & (C["tw"] < 5) & (C["ne"] > 0)
calib = {}
for t in range(2):
    for p in range(3):
        m = good & (C["tpc"] == t) & (C["plane"] == p)
        if m.sum() < 20:
            continue
        res = C[f"cen_{prods[0]}"][m] - C["tc"][m]
        toff[t, p] = np.nanmedian(res)
        calib[f"{TPC[t]} {PL[p]}"] = dict(n=int(m.sum()), sp_centre_minus_nominal=robust_stats(res),
                                          simch_tdc_minus_nominal=robust_stats(C["sc_cen"][m] - C["tc"][m]))
print("tick offsets (SP centre - nominal), per TPC x plane:\n", np.round(toff, 2), "\nSimChannel TDC offset", round(sc_off, 2))

# ---- pass 2: the measurement
rows = measure(evs, toff, sc_off, a.pad)
# containment: same wires, window pad vs pad_cal
cal_q = {(r["ev"], r["tid"], r["tpc"], r["plane"], r["ch"]): r[f"q_off_{prods[0]}"] for r in measure(evs, toff, sc_off, a.pad_cal)}
keys = ["ev", "tid", "pdg", "tpc", "plane", "ch", "bad", "s", "L", "x", "y", "z", "dx", "tc", "tw", "g", "purity", "ne",
        "sc_cen", "ndouble", "primary", "e0", "cosx"] + [f"q_{t}_{p}" for p in prods for t in ("off", "on")] + [f"cen_{p}" for p in prods]
W = {k: np.array([r[k] for r in rows]) for k in keys if k != "ev"}
W["ev"] = np.array([r["ev"] for r in rows])
W["q_cal"] = np.array([cal_q.get((r["ev"], r["tid"], r["tpc"], r["plane"], r["ch"]), np.nan) for r in rows])
W["use"] = (W["bad"] == 0) & (W["purity"] >= a.min_purity) & (W["ne"] > 0)
for p in prods:
    W[f"dqdx_off_{p}"] = W[f"q_off_{p}"] / W["dx"]
    W[f"dqdx_on_{p}"] = W[f"q_on_{p}"] / W["dx"]
W["dqdx_true"] = W["ne"] / W["dx"]
np.savez_compressed(f"{a.outdir}/truth_sp_wires.npz", **W, toff=toff, sc_off=sc_off)

# ---- per track and plane
trk = []
key = np.array([f"{e[0]}_{e[1]}_{e[2]}_{t}_{tp}" for e, t, tp in zip(W["ev"], W["tid"], W["tpc"])])
for k in np.unique(key):
    for p in range(3):
        m = (key == k) & (W["plane"] == p) & W["use"]
        if m.sum() < a.min_wires:
            continue
        i0 = np.flatnonzero(m)[0]
        r = dict(key=k, run=int(W["ev"][i0][0]), subrun=int(W["ev"][i0][1]), event=int(W["ev"][i0][2]),
                 tid=int(W["tid"][i0]), pdg=int(W["pdg"][i0]), tpc=int(W["tpc"][i0]), plane=p, nw=int(m.sum()),
                 L=float(W["L"][i0]), primary=int(W["primary"][i0]), cosx=float(W["cosx"][i0]),
                 y=float(np.median(W["y"][m])), z=float(np.median(W["z"][m])), gmean=float(W["g"][m].mean()),
                 gmed=float(np.median(W["g"][m])), true=float(np.median(W["dqdx_true"][m])))
        for prod in prods:
            off, on = W[f"dqdx_off_{prod}"][m], W[f"dqdx_on_{prod}"][m]
            r[f"off_{prod}"] = float(np.median(off))
            r[f"on_{prod}"] = float(np.median(on))
            r[f"ratio_{prod}"] = r[f"on_{prod}"] / r[f"off_{prod}"]
            r[f"exp_{prod}"] = float(np.median(off * W["g"][m]) / np.median(off))
        trk.append(r)
cols = list(trk[0].keys()) if trk else []
with open(f"{a.outdir}/truth_sp_tracks.tsv", "w") as fp:
    fp.write("\t".join(cols) + "\n")
    for r in trk:
        fp.write("\t".join(f"{r[c]:.6g}" if isinstance(r[c], float) else str(r[c]) for c in cols) + "\n")

# ---- summary
S = dict(inputs=dict(off=a.off, on=a.on), events=len(evs), args=vars(a), tick_offset_per_tpc_plane=toff.tolist(),
         simch_tdc_offset=sc_off, calibration=calib, products={})
u = W["use"]
S["wires"] = dict(total=int(len(u)), bad=int(W["bad"].sum()), low_purity=int((W["purity"] < a.min_purity).sum()), used=int(u.sum()))
S["containment"] = {}
for t in range(2):
    for p in range(3):
        m = u & (W["tpc"] == t) & (W["plane"] == p) & (W["q_cal"] > 0)
        if m.any():
            S["containment"][f"{TPC[t]} {PL[p]}"] = robust_stats(W[f"q_off_{prods[0]}"][m] / W["q_cal"][m])
for prod in prods:
    P = S["products"][prod] = {}
    for p in range(3):
        for tsel, tname in ((None, "both"), (0, "East"), (1, "West")):
            for pdg, pname in ((13, "mu"), (2212, "p")):
                tr = [r for r in trk if r["plane"] == p and abs(r["pdg"]) == pdg and (tsel is None or r["tpc"] == tsel)]
                if not tr:
                    continue
                ratio = np.array([r[f"ratio_{prod}"] for r in tr])
                exp = np.array([r[f"exp_{prod}"] for r in tr])
                m = (u & (W["plane"] == p) & (np.abs(W["pdg"]) == pdg) & ((W["tpc"] == tsel) if tsel is not None else True)
                     & (W[f"q_off_{prod}"] > 0) & (W[f"q_on_{prod}"] > 0))
                wr = W[f"dqdx_on_{prod}"][m] / W[f"dqdx_off_{prod}"][m]
                P[f"{pname} {PL[p]} {tname}"] = dict(
                    tracks=len(tr), wires=int(m.sum()),
                    track_ratio=robust_stats(ratio), track_expected=robust_stats(exp),
                    track_ratio_over_expected=robust_stats(ratio / exp),
                    corr_track_ratio_expected=float(np.corrcoef(ratio, exp)[0, 1]) if len(tr) > 2 else None,
                    off_median_ke_cm=float(np.median([r[f"off_{prod}"] for r in tr]) / 1e3),
                    on_median_ke_cm=float(np.median([r[f"on_{prod}"] for r in tr]) / 1e3),
                    true_median_ke_cm=float(np.median([r["true"] for r in tr]) / 1e3),
                    wire_ratio=robust_stats(wr), wire_g=robust_stats(W["g"][m]),
                    wire_ratio_over_g=robust_stats(wr / W["g"][m]),
                    corr_wire_ratio_g=float(np.corrcoef(wr, W["g"][m])[0, 1]) if m.sum() > 2 else None,
                    wire_core_fraction=float((np.abs(wr / W["g"][m] - 1) < 0.1).mean()) if m.sum() else None,
                    corr_wire_ratio_g_core=float(np.corrcoef(wr[np.abs(wr / W["g"][m] - 1) < 0.1],
                                                             W["g"][m][np.abs(wr / W["g"][m] - 1) < 0.1])[0, 1])
                    if m.sum() > 2 else None,
                    sum_on_over_off=float(W[f"q_on_{prod}"][m].sum() / W[f"q_off_{prod}"][m].sum()),
                    sum_expected=float((W[f"q_off_{prod}"][m] * W["g"][m]).sum() / W[f"q_off_{prod}"][m].sum()))
# ---- global: whole-event SP charge per TPC and plane, on/off, vs the SimChannel-weighted map
from dqdx_common import tpc_plane  # noqa: E402
G = {}
for (rse, d0, d1, dens0, dens1) in evs:
    chs = np.arange(2 * 5638)
    tp, pl = tpc_plane(chs)
    sc_t, sc_p = tpc_plane(d0["sc_ch"])
    for t in range(2):
        for p in range(3):
            k = f"{TPC[t]} {PL[p]}"
            g = G.setdefault(k, {"ne": 0.0, "ne_g": 0.0, **{f"{x}_{pr}": 0.0 for pr in prods for x in ("off", "on")}})
            msk = (tp == t) & (pl == p)
            for pr in prods:
                g[f"off_{pr}"] += float(dens0[pr][msk].sum()); g[f"on_{pr}"] += float(dens1[pr][msk].sum())
            ms = (sc_t == t) & (sc_p == p)
            g["ne"] += float(d0["sc_ne"][ms].sum())
            g["ne_g"] += float((d0["sc_ne"][ms] * ymap(t, p, d0["sc_y"][ms], d0["sc_z"][ms])).sum())
S["global_event_charge"] = {k: dict(expected_simch_weighted_map=v["ne_g"] / v["ne"] if v["ne"] else None,
                                    simch_electrons=v["ne"],
                                    **{f"on_over_off_{pr}": v[f"on_{pr}"] / v[f"off_{pr}"] for pr in prods})
                            for k, v in G.items()}
json.dump(S, open(f"{a.outdir}/truth_sp_summary.json", "w"), indent=1)
print("global whole-event SP charge on/off per TPC-plane (expected = SimChannel-electron-weighted map):")
for k, v in S["global_event_charge"].items():
    print(f"  {k}: expected {v['expected_simch_weighted_map']:.4f}  " +
          "  ".join(f"{pr} {v[f'on_over_off_{pr}']:.4f}" for pr in prods))

print(f"wires: {S['wires']}")
for prod in prods:
    print(f"\n{prod}: per track (median dQ/dx on/off) vs expected; per wire on/off vs g")
    print("| | tracks | ratio median | half-68 | expected median | ratio/exp median | corr | wire ratio/g rms | sum on/off (exp) |")
    for k, v in S["products"][prod].items():
        if "both" not in k:
            continue
        print(f"| {k} | {v['tracks']} | {v['track_ratio']['median']:.4f} | {v['track_ratio']['half68']:.4f} | "
              f"{v['track_expected']['median']:.4f} | {v['track_ratio_over_expected']['median']:.4f} | "
              f"{v['corr_track_ratio_expected'] if v['corr_track_ratio_expected'] is None else round(v['corr_track_ratio_expected'], 3)} | "
              f"{v['wire_ratio_over_g']['rms']:.4f} | {v['sum_on_over_off']:.4f} ({v['sum_expected']:.4f}) |")
print(f"\nwrote {a.outdir}/truth_sp_wires.npz, truth_sp_tracks.tsv, truth_sp_summary.json")
