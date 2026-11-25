#!/usr/bin/env python3
"""Figures for the issue-46 dQ/dx off/on study (slide-sized PNGs).

Usage (wire-cell-python venv):
  plot_dqdx.py <analysis-dir> [--label "BNB CV-like, 10 events"] [--product dnnsp]
Reads <analysis-dir>/truth-sp/ (dqdx_truth_sp.py) and, if present, <analysis-dir>/fit/
(dqdx_fit.py); writes <analysis-dir>/figs/*.png.
"""
import argparse
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dqdx_common import PL, TPC, YZMap  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("adir")
ap.add_argument("--label", default="")
ap.add_argument("--products", default="dnnsp,gauss")
a = ap.parse_args()
FIG = f"{a.adir}/figs"
os.makedirs(FIG, exist_ok=True)
plt.rcParams.update({"font.size": 13, "axes.titlesize": 14, "axes.labelsize": 13, "legend.fontsize": 11,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": "#e4e3df", "grid.linewidth": 0.8, "figure.facecolor": "#fcfcfb",
                     "axes.facecolor": "#fcfcfb", "savefig.facecolor": "#fcfcfb"})
C_MEAS, C_EXP, C_GRAY = "#2a78d6", "#eb6834", "#52514e"
C_OFF, C_ON = "#2a78d6", "#eb6834"
ymap = YZMap()


def read_tsv(fn):
    with open(fn) as fp:
        rows = list(csv.DictReader(fp, delimiter="\t"))
    out = {}
    for k in rows[0].keys() if rows else []:
        try:
            if k == "key":   # "run_subrun_event_tid_tpc": float() accepts underscores
                raise ValueError
            out[k] = np.array([float(r[k]) for r in rows])
        except ValueError:
            out[k] = np.array([r[k] for r in rows])
    return out


def save(fig, name):
    fig.tight_layout()
    fig.savefig(f"{FIG}/{name}", dpi=110)
    plt.close(fig)
    print(f"wrote {FIG}/{name}")


def profile(x, y, bins):
    idx = np.digitize(x, bins) - 1
    c, m, e = [], [], []
    for i in range(len(bins) - 1):
        s = y[idx == i]
        if len(s) >= 5:
            c.append(0.5 * (bins[i] + bins[i + 1])); m.append(np.median(s))
            e.append(1.2533 * s.std() / np.sqrt(len(s)))
    return np.array(c), np.array(m), np.array(e)


# ====================================================================== truth SP
td = f"{a.adir}/truth-sp"
if os.path.exists(f"{td}/truth_sp_wires.npz"):
    W = dict(np.load(f"{td}/truth_sp_wires.npz", allow_pickle=True))
    T = read_tsv(f"{td}/truth_sp_tracks.tsv")
    u = W["use"]
    prods = [p for p in a.products.split(",") if f"q_off_{p}" in W]
    p0 = prods[0]

    # --- projection check
    fig, ax = plt.subplots(1, 3, figsize=(16, 5))
    res = W[f"cen_{p0}"] - W["tc"]
    clean = u & (W["purity"] > 0.95) & (W["tw"] < 5)
    for t in range(2):
        for p in range(3):
            m = clean & (W["tpc"] == t) & (W["plane"] == p)
            ax[0].hist(res[m], bins=np.linspace(-4, 4, 81), histtype="step", lw=1.6,
                       label=f"{TPC[t]} {PL[p]}: median {np.median(res[m]):+.2f}, half-68 "
                             f"{0.5 * np.diff(np.percentile(res[m], [16, 84]))[0]:.2f}")
    ax[0].set_xlabel(f"SP ({p0}) charge centre - predicted tick [ticks]")
    ax[0].set_ylabel("wires"); ax[0].legend(fontsize=9)
    ax[0].set_title(f"after the fitted offset {np.round(W['toff'].mean(), 2)} ticks")
    dd = 202.05 - np.abs(W["x"])
    for p in range(3):
        m = clean & (W["plane"] == p)
        c, med, e = profile(dd[m], res[m], np.linspace(0, 200, 21))
        ax[1].errorbar(c, med, e, marker="o", ms=5, lw=1.5, label=PL[p])
    ax[1].axhline(0, color=C_GRAY, lw=1)
    ax[1].set_xlabel("drift distance [cm]"); ax[1].set_ylabel("median residual [ticks]")
    ax[1].set_ylim(-1, 1); ax[1].legend(); ax[1].set_title("residual vs drift distance")
    cont = W[f"q_off_{p0}"] / W["q_cal"]
    for p in range(3):
        m = u & (W["plane"] == p) & (W["q_cal"] > 0)
        ax[2].hist(np.clip(cont[m], 0.8, 1.1), bins=np.linspace(0.8, 1.1, 61), histtype="step", lw=1.6,
                   label=f"{PL[p]}: median {np.median(cont[m]):.4f}")
    ax[2].set_yscale("log"); ax[2].set_xlabel("charge in window / charge in +-40-tick window")
    ax[2].legend(); ax[2].set_title("containment of the dQ window")
    fig.suptitle(f"Truth-track projection check {a.label}")
    save(fig, "truth_sp_projection.png")

    for prod in prods:
        # --- per-track ratio vs expected
        fig, ax = plt.subplots(2, 3, figsize=(16, 9))
        for p in range(3):
            m = T["plane"] == p
            mu = m & (np.abs(T["pdg"]) == 13); pr = m & (T["pdg"] == 2212)
            r, e = T[f"ratio_{prod}"], T[f"exp_{prod}"]
            lo = min(np.percentile(np.r_[r[m], e[m]], 0.5), 0.94) if m.any() else 0.94
            hi = max(np.percentile(np.r_[r[m], e[m]], 99.5), 1.06) if m.any() else 1.06
            b = np.linspace(lo, hi, 41)
            ax[0, p].hist(r[m], bins=b, histtype="stepfilled", alpha=0.35, color=C_MEAS,
                          label=f"measured on/off: median {np.median(r[m]):.4f}")
            ax[0, p].hist(e[m], bins=b, histtype="step", lw=2, color=C_EXP,
                          label=f"expected from map: median {np.median(e[m]):.4f}")
            ax[0, p].set_xlabel("track median dQ/dx, on / off"); ax[0, p].set_ylabel("tracks")
            ax[0, p].set_title(f"plane {PL[p]}: {int(m.sum())} tracks ({int(mu.sum())} mu, {int(pr.sum())} p)")
            ax[0, p].legend(fontsize=10)
            ax[1, p].plot([lo, hi], [lo, hi], color=C_GRAY, lw=1, ls="--")
            ax[1, p].scatter(e[mu], r[mu], s=22, color=C_MEAS, label="muons", edgecolor="white", lw=0.5)
            if pr.any():
                ax[1, p].scatter(e[pr], r[pr], s=22, color=C_EXP, marker="^", label="protons", edgecolor="white", lw=0.5)
            cc = np.corrcoef(r[m], e[m])[0, 1] if m.sum() > 2 else np.nan
            dev = r[m] / e[m] - 1
            ax[1, p].text(0.97, 0.03, f"measured/expected - 1:\nmedian {np.median(dev)*100:+.2f} %, "
                          f"rms {dev.std()*100:.2f} %\ncorr {cc:.2f}", transform=ax[1, p].transAxes,
                          ha="right", va="bottom", fontsize=11)
            ax[1, p].set_xlabel("expected on/off (map applied to the off wires)")
            ax[1, p].set_ylabel("measured on/off"); ax[1, p].set_xlim(lo, hi); ax[1, p].set_ylim(lo, hi)
            ax[1, p].legend(fontsize=10)
        fig.suptitle(f"Truth-track SP dQ/dx ({prod}): per-track median, YZ on / off {a.label}")
        save(fig, f"truth_sp_track_ratio_{prod}.png")

        # --- per wire: ratio vs g, residual vs y, z
        fig, ax = plt.subplots(3, 3, figsize=(16, 12))
        wr = W[f"q_on_{prod}"] / W[f"q_off_{prod}"]
        for p in range(3):
            m = u & (W["plane"] == p) & (W[f"q_off_{prod}"] > 0) & (W[f"q_on_{prod}"] > 0) & np.isfinite(wr)
            g = W["g"][m]
            c, med, e = profile(g, wr[m], np.linspace(0.85, 1.15, 31))
            ax[0, p].plot([0.85, 1.15], [0.85, 1.15], color=C_GRAY, lw=1, ls="--", label="measured = map")
            ax[0, p].errorbar(c, med, e, marker="o", ms=5, color=C_MEAS, lw=1.5, label="median per g bin")
            core = np.abs(wr[m] / g - 1) < 0.1
            cc = np.corrcoef(wr[m][core], g[core])[0, 1]
            ax[0, p].set_title(f"plane {PL[p]}: {int(m.sum())} wires, corr {cc:.2f} (|on/off/g-1| < 10 %: "
                               f"{core.mean()*100:.1f} %)", fontsize=12)
            ax[0, p].set_xlabel("map factor g at the wire"); ax[0, p].set_ylabel("wire charge on / off")
            ax[0, p].set_xlim(0.85, 1.15); ax[0, p].set_ylim(0.85, 1.15); ax[0, p].legend(fontsize=10)
            dev = wr[m] / g - 1
            for k, (var, lab, bins) in enumerate((("z", "z [cm]", np.linspace(0, 500, 26)),
                                                  ("y", "y [cm]", np.linspace(-200, 200, 21)))):
                c, med, e = profile(W[var][m], wr[m], bins)
                cg, mg, _ = profile(W[var][m], g, bins)
                ax[1 + k, p].errorbar(c, med, e, marker="o", ms=5, color=C_MEAS, lw=1.5, label="measured on/off")
                ax[1 + k, p].plot(cg, mg, marker="s", ms=5, color=C_EXP, lw=1.5, label="map g (same wires)")
                ax[1 + k, p].axhline(1, color=C_GRAY, lw=1)
                ax[1 + k, p].set_xlabel(lab); ax[1 + k, p].set_ylabel("median per bin")
                ax[1 + k, p].legend(fontsize=10)
            h68 = 0.5 * np.diff(np.percentile(dev, [16, 84]))[0]
            ax[1, p].set_title(f"wire on/off / g - 1: median {np.median(dev)*100:+.2f} %, half-68 {h68*100:.2f} %, "
                               f"rms {dev.std()*100:.1f} %", fontsize=11)
        fig.suptitle(f"Truth-track SP ({prod}), per wire: on/off vs the map {a.label}")
        save(fig, f"truth_sp_wire_vs_map_{prod}.png")

    # --- (z, y) of the wires: measured (smoothed along track) vs map, per TPC
    prod = p0
    for t in range(2):
        fig, ax = plt.subplots(2, 3, figsize=(17, 9))
        wr = W[f"q_on_{prod}"] / W[f"q_off_{prod}"]
        for p in range(3):
            m = u & (W["plane"] == p) & (W["tpc"] == t) & (W[f"q_off_{prod}"] > 0)
            idx = np.flatnonzero(m)
            # smooth along each track: running median over 15 wires
            key = np.array([f"{e[0]}_{e[1]}_{e[2]}_{k}" for e, k in zip(W["ev"][idx], W["tid"][idx])])
            sm = np.full(len(idx), np.nan)
            for kk in np.unique(key):
                j = np.flatnonzero(key == kk)
                j = j[np.argsort(W["s"][idx][j])]
                v = wr[idx][j]
                for n in range(len(j)):
                    sm[j[n]] = np.median(v[max(0, n - 7): n + 8])
            g = ymap.g[(t, p)]
            for row, (val, ttl) in enumerate(((sm, "measured on/off, running median of 15 wires"),
                                              (W["g"][idx], "map g at the same wires"))):
                axx = ax[row, p]
                axx.imshow(g.T, origin="lower", extent=(0, 500, -200, 200), cmap="Greys", vmin=0.85, vmax=1.15,
                           alpha=0.35, aspect="auto")
                sc = axx.scatter(W["z"][idx], W["y"][idx], c=val, s=4, cmap="RdBu_r", vmin=0.92, vmax=1.08)
                axx.set_title(f"{TPC[t]} {PL[p]}: {ttl}", fontsize=11)
                axx.set_xlabel("z [cm]"); axx.set_ylabel("y [cm]"); axx.grid(False)
                fig.colorbar(sc, ax=axx, fraction=0.04)
        fig.suptitle(f"Truth-track SP ({prod}) on/off along the tracks vs the map, {TPC[t]} TPC {a.label} "
                     "(grey background: the plane's map)")
        save(fig, f"truth_sp_yz_{TPC[t]}.png")

    # --- dQ/dx distributions of the track medians
    fig, ax = plt.subplots(len(prods), 3, figsize=(16, 4.6 * len(prods)), squeeze=False)
    for ip, prod in enumerate(prods):
        for p in range(3):
            m = (T["plane"] == p) & (np.abs(T["pdg"]) == 13)
            off, on = T[f"off_{prod}"][m] / 1e3, T[f"on_{prod}"][m] / 1e3
            b = np.linspace(np.percentile(np.r_[off, on], 1) - 1, np.percentile(np.r_[off, on], 99) + 1, 41)
            ax[ip, p].hist(off, bins=b, histtype="stepfilled", alpha=0.35, color=C_OFF,
                           label=f"off: median {np.median(off):.2f}")
            ax[ip, p].hist(on, bins=b, histtype="step", lw=2, color=C_ON, label=f"on: median {np.median(on):.2f}")
            ax[ip, p].hist(T["true"][m] / 1e3, bins=b, histtype="step", lw=1.2, ls="--", color=C_GRAY,
                           label=f"SimChannel truth: {np.median(T['true'][m]) / 1e3:.2f}")
            ax[ip, p].set_xlabel("track median dQ/dx [ke/cm]"); ax[ip, p].set_ylabel("muon tracks")
            ax[ip, p].set_title(f"{prod}, plane {PL[p]}: on/off of medians {np.median(on) / np.median(off):.4f}")
            ax[ip, p].legend(fontsize=10)
    fig.suptitle(f"Truth-track SP dQ/dx of muons (per-track medians), YZ off vs on {a.label}")
    save(fig, "truth_sp_dqdx_dist.png")

    # --- along-track examples: the 3 longest muon tracks
    m0 = (T["plane"] == 2) & (np.abs(T["pdg"]) == 13)
    keys = T["key"][m0][np.argsort(-T["nw"][m0])][:3]
    fig, ax = plt.subplots(len(keys), 3, figsize=(17, 3.8 * max(len(keys), 1)), squeeze=False)
    key = np.array([f"{e[0]}_{e[1]}_{e[2]}_{t}_{tp}" for e, t, tp in zip(W["ev"], W["tid"], W["tpc"])])
    wr = W[f"q_on_{p0}"] / W[f"q_off_{p0}"]
    for i, k in enumerate(keys):
        for p in range(3):
            m = (key == k) & (W["plane"] == p) & u
            j = np.flatnonzero(m)[np.argsort(W["s"][m])]
            v = wr[j]
            sm = np.array([np.median(v[max(0, n - 7): n + 8]) for n in range(len(j))])
            ax[i, p].plot(W["s"][j], v, ".", ms=2, color="#b7d3f6", label="per wire")
            ax[i, p].plot(W["s"][j], W["g"][j], color=C_EXP, lw=2.2, label="map g")
            ax[i, p].plot(W["s"][j], sm, color=C_MEAS, lw=1.2, label="running median (15 wires)")
            ax[i, p].set_ylim(0.85, 1.15); ax[i, p].set_xlabel("distance along track [cm]")
            ax[i, p].set_ylabel(f"{p0} on/off")
            ax[i, p].set_title(f"track {k}, plane {PL[p]}", fontsize=11)
            if i == 0 and p == 0:
                ax[i, p].legend(fontsize=9, loc="lower left")
    fig.suptitle(f"Along the longest muon tracks: wire on/off ({p0}) vs the map {a.label}")
    save(fig, "truth_sp_along_track.png")

# ====================================================================== fit
import glob  # noqa: E402
for fd in sorted(glob.glob(f"{a.adir}/fit*")):
    if not os.path.exists(f"{fd}/fit_tracks.tsv") or os.path.getsize(f"{fd}/fit_tracks.tsv") < 100:
        continue
    tag = os.path.basename(fd)
    S = read_tsv(f"{fd}/fit_tracks.tsv")
    Bn = dict(np.load(f"{fd}/fit_bins.npz"))
    fig, ax = plt.subplots(2, 3, figsize=(17, 9.5))
    r, e = S["ratio"], S["exp_avg"]
    pdg = np.abs(S["pdg"])
    lo, hi = min(np.percentile(np.r_[r, e], 0), 0.9), max(np.percentile(np.r_[r, e], 100), 1.1)
    b = np.linspace(lo, hi, 31)
    ax[0, 0].hist(r, bins=b, histtype="stepfilled", alpha=0.35, color=C_MEAS, label=f"measured: median {np.median(r):.4f}")
    ax[0, 0].hist(e, bins=b, histtype="step", lw=2, color=C_EXP, label=f"expected (3-plane mean g): {np.median(e):.4f}")
    ax[0, 0].set_xlabel("track median fitted dQ/dx, on / off"); ax[0, 0].set_ylabel("truth-matched tracks")
    ax[0, 0].set_title(f"{len(r)} tracks ({int((pdg == 13).sum())} mu, {int((pdg == 2212).sum())} p, "
                       f"{int(((pdg != 13) & (pdg != 2212)).sum())} other)")
    ax[0, 0].legend(fontsize=10)
    for k, (col, lab) in enumerate((("exp_avg", "3-plane mean g"), ("exp_Y", "g of Y only"))):
        axx = ax[0, 1 + k]
        axx.plot([lo, hi], [lo, hi], color=C_GRAY, lw=1, ls="--")
        for sel, mk, nm, cc_ in ((pdg == 13, "o", "muons", C_MEAS), (pdg == 2212, "^", "protons", C_EXP),
                                 ((pdg != 13) & (pdg != 2212), "s", "other", C_GRAY)):
            if sel.any():
                axx.scatter(S[col][sel], r[sel], s=40, marker=mk, color=cc_, edgecolor="white", lw=0.5, label=nm)
        dev = r / S[col] - 1
        cc = np.corrcoef(r, S[col])[0, 1] if len(r) > 2 else np.nan
        axx.text(0.97, 0.03, f"measured/expected - 1:\nmedian {np.median(dev)*100:+.2f} %, rms {dev.std()*100:.2f} %"
                 f"\ncorr {cc:.2f}", transform=axx.transAxes, ha="right", va="bottom", fontsize=11)
        axx.set_title(f"expectation: {lab}")
        axx.set_xlabel(f"expected on/off ({lab})"); axx.set_ylabel("measured on/off")
        axx.set_xlim(lo, hi); axx.set_ylim(lo, hi); axx.legend(fontsize=10, loc="upper left")
    if len(Bn.get("dqdx_off", [])):
        rr = Bn["dqdx_on"] / Bn["dqdx_off"]
        gavg = (Bn["gU"] + Bn["gV"] + Bn["gY"]) / 3
        ok = np.isfinite(rr) & (rr > 0)
        ax[1, 0].plot([0.9, 1.1], [0.9, 1.1], color=C_GRAY, lw=1, ls="--", label="measured = 3-plane mean g")
        ax[1, 0].scatter(gavg[ok], rr[ok], s=10, color="#9ec5f4", label="10-cm bins")
        c, med, er = profile(gavg[ok], rr[ok], np.linspace(0.94, 1.06, 9))
        ax[1, 0].errorbar(c, med, er, marker="o", ms=6, color=C_MEAS, lw=1.5, label="median per g bin")
        ax[1, 0].set_xlabel("3-plane mean g of the bin"); ax[1, 0].set_ylabel("bin sum dQ / sum dx, on / off")
        cc = np.corrcoef(gavg[ok], rr[ok])[0, 1]
        ax[1, 0].set_title(f"{int(ok.sum())} common 10-cm bins, corr {cc:.2f}")
        ax[1, 0].set_xlim(0.92, 1.08); ax[1, 0].set_ylim(0.85, 1.15); ax[1, 0].legend(fontsize=9)
        q = rr[ok] / gavg[ok]
        ax[1, 1].hist(np.clip(q, 0.8, 1.2), bins=np.linspace(0.8, 1.2, 61), color=C_MEAS, alpha=0.6, label="on/off / gavg")
        ax[1, 1].hist(np.clip(rr[ok], 0.8, 1.2), bins=np.linspace(0.8, 1.2, 61), histtype="step", color=C_GRAY, lw=1.5,
                      label="on/off")
        ax[1, 1].set_xlabel("10-cm bin ratio"); ax[1, 1].set_ylabel("bins"); ax[1, 1].legend(fontsize=10)
        ax[1, 1].set_title(f"on/off/gavg: median {np.median(q):.4f}, half-68 "
                           f"{0.5 * np.diff(np.percentile(q, [16, 84]))[0]:.3f}; gavg rms {gavg[ok].std():.3f}",
                           fontsize=11)
    off, on = S["off"] / 1e3, S["on"] / 1e3
    b = np.linspace(min(off.min(), on.min()) * 0.95, max(off.max(), on.max()) * 1.05, 31)
    ax[1, 2].hist(off, bins=b, histtype="stepfilled", alpha=0.35, color=C_OFF, label=f"off: median {np.median(off):.1f}")
    ax[1, 2].hist(on, bins=b, histtype="step", lw=2, color=C_ON, label=f"on: median {np.median(on):.1f}")
    ax[1, 2].set_xlabel("track median fitted dQ/dx [ke/cm]"); ax[1, 2].set_ylabel("tracks"); ax[1, 2].legend()
    fig.suptitle(f"Fitted dQ/dx (TrackFitting, T_rec_charge, truth-matched), YZ on / off {a.label} [{tag}]")
    save(fig, f"{tag}_dqdx.png")
