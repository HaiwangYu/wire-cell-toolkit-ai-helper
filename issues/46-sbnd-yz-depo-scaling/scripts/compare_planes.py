#!/usr/bin/env python3
"""Compare the SBND YZ non-uniformity maps of the U, V, Y planes per TPC.

g_p = 1/CzyHist_p  (relative response of plane p; data x C = uniform).
Usage: compare_planes.py <map.root> <outdir> [min_hits]
"""
import sys, json
import numpy as np, uproot
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

fn, outdir = sys.argv[1], sys.argv[2]
min_hits = float(sys.argv[3]) if len(sys.argv) > 3 else 100
f = uproot.open(fn)
PL, TPC = ["U", "V", "Y"], ["East", "West"]

def h(name):
    o = f[name]; v = o.values()            # shape (nz, ny): x axis = z, y axis = y
    return v, o.axes[0].edges(), o.axes[1].edges()

res = {}
for t in (0, 1):
    C = np.array([h(f"CzyHist_{p}_{t}")[0] for p in range(3)])
    N = np.array([h(f"zynhits_{p}_{t}")[0] for p in range(3)])
    _, ze, ye = h(f"CzyHist_0_{t}")
    good = np.all(C > 0, axis=0) & np.all(N >= min_hits, axis=0)
    g = np.where(C > 0, 1.0 / np.where(C > 0, C, 1), np.nan)
    gm = np.where(good, g, np.nan)
    r = {"bins": int(C[0].size), "good_bins": int(good.sum()),
         "dead_bins": {PL[p]: int((C[p] == 0).sum()) for p in range(3)},
         "lowhit_bins": {PL[p]: int(((N[p] < min_hits) & (C[p] > 0)).sum()) for p in range(3)}}
    gv = gm[:, good]                          # (3, ngood)
    r["rms_g"] = {PL[p]: float(np.std(gv[p])) for p in range(3)}
    r["p05_p95_g"] = {PL[p]: [float(x) for x in np.percentile(gv[p], [5, 95])] for p in range(3)}
    corr = np.corrcoef(gv)
    r["corr"] = {f"{PL[a]}-{PL[b]}": float(corr[a, b]) for a, b in ((0, 1), (0, 2), (1, 2))}
    for a, b in ((0, 2), (1, 2), (0, 1)):
        q = gv[a] / gv[b]
        r[f"ratio_{PL[a]}/{PL[b]}"] = {
            "mean": float(q.mean()), "rms": float(q.std()),
            "p05": float(np.percentile(q, 5)), "p95": float(np.percentile(q, 95)),
            "frac_gt2pct": float(np.mean(abs(q - 1) > 0.02)),
            "frac_gt5pct": float(np.mean(abs(q - 1) > 0.05)),
            "frac_gt10pct": float(np.mean(abs(q - 1) > 0.10))}
    # residual non-uniformity of each plane if one map is used for all planes
    gavg = gv.mean(axis=0)
    r["residual_rms"] = {}
    for name, used in (("none", np.ones_like(gavg)), ("Y", gv[2]), ("avg", gavg)):
        r["residual_rms"][name] = {PL[p]: float(np.std(gv[p] / used)) for p in range(3)}
    spread = (np.nanmax(gm, axis=0) - np.nanmin(gm, axis=0)) / np.nanmean(gm, axis=0)
    r["spread_(max-min)/mean"] = {"median": float(np.nanmedian(spread)),
                                  "p95": float(np.nanpercentile(spread, 95))}
    res[TPC[t]] = r

    # ---- figure: maps, ratios, spread
    ext = [ze[0], ze[-1], ye[0], ye[-1]]
    fig, ax = plt.subplots(3, 3, figsize=(16, 12))
    for p in range(3):
        im = ax[0, p].imshow(g[p].T, origin="lower", extent=ext, aspect="auto",
                             vmin=0.7, vmax=1.3, cmap="RdBu_r")
        ax[0, p].set_title(f"{TPC[t]} {PL[p]}: g = 1/C  (rms {r['rms_g'][PL[p]]:.3f})")
        fig.colorbar(im, ax=ax[0, p])
    for k, (a, b) in enumerate(((0, 2), (1, 2), (0, 1))):
        im = ax[1, k].imshow((gm[a] / gm[b]).T, origin="lower", extent=ext, aspect="auto",
                             vmin=0.85, vmax=1.15, cmap="RdBu_r")
        rr = r[f"ratio_{PL[a]}/{PL[b]}"]
        ax[1, k].set_title(f"g_{PL[a]}/g_{PL[b]}  rms {rr['rms']:.3f}, |Δ|>5%: {100*rr['frac_gt5pct']:.0f}%")
        fig.colorbar(im, ax=ax[1, k])
    im = ax[2, 0].imshow(spread.T, origin="lower", extent=ext, aspect="auto", vmin=0, vmax=0.3, cmap="viridis")
    ax[2, 0].set_title("(max-min)/mean over U,V,Y"); fig.colorbar(im, ax=ax[2, 0])
    for a, c in ((0, "C0"), (1, "C1")):
        ax[2, 1].scatter(gv[2], gv[a], s=2, c=c, alpha=0.4, label=f"{PL[a]} vs Y (corr {corr[a,2]:.2f})")
    ax[2, 1].plot([0.6, 1.4], [0.6, 1.4], "k--", lw=1); ax[2, 1].set_xlim(0.6, 1.4); ax[2, 1].set_ylim(0.6, 1.4)
    ax[2, 1].set_xlabel("g_Y"); ax[2, 1].set_ylabel("g_U, g_V"); ax[2, 1].legend(markerscale=5)
    bins = np.linspace(0.7, 1.3, 121)
    for a, b, c in ((0, 2, "C0"), (1, 2, "C1"), (0, 1, "C2")):
        ax[2, 2].hist(gv[a] / gv[b], bins=bins, histtype="step", color=c, label=f"g_{PL[a]}/g_{PL[b]}")
    ax[2, 2].set_xlabel("ratio"); ax[2, 2].legend(); ax[2, 2].set_yscale("log")
    for a_ in ax[:2].flat:
        a_.set_xlabel("z [cm]"); a_.set_ylabel("y [cm]")
    ax[2, 0].set_xlabel("z [cm]"); ax[2, 0].set_ylabel("y [cm]")
    fig.suptitle(f"SBND {TPC[t]} TPC: plane-to-plane comparison (good bins: C>0 on all planes, hits>={min_hits:g})")
    fig.tight_layout(); fig.savefig(f"{outdir}/planes_{TPC[t]}.png", dpi=90); plt.close(fig)

    # ---- figure: 1D profiles along z and y
    fig, ax = plt.subplots(1, 2, figsize=(14, 4.5))
    zc, yc = 0.5 * (ze[1:] + ze[:-1]), 0.5 * (ye[1:] + ye[:-1])
    for p in range(3):
        ax[0].plot(zc, np.nanmean(gm[p], axis=1), label=PL[p])
        ax[1].plot(yc, np.nanmean(gm[p], axis=0), label=PL[p])
    ax[0].set_xlabel("z [cm]"); ax[1].set_xlabel("y [cm]")
    for a_ in ax:
        a_.set_ylabel("<g> = <1/C>"); a_.legend(); a_.grid(alpha=0.3)
    fig.suptitle(f"SBND {TPC[t]} TPC: profiles (good bins)")
    fig.tight_layout(); fig.savefig(f"{outdir}/profiles_{TPC[t]}.png", dpi=90); plt.close(fig)

json.dump(res, open(f"{outdir}/plane_compare.json", "w"), indent=1)
print(json.dumps(res, indent=1))

# ---- large-scale vs fine structure: smooth each plane's g with a box of
# SMOOTH x SMOOTH bins (5 cm bins), using good bins only (normalized convolution).
from scipy.ndimage import uniform_filter
SMOOTH = 9                                      # 45 cm
for t in (0, 1):
    C = np.array([h(f"CzyHist_{p}_{t}")[0] for p in range(3)])
    N = np.array([h(f"zynhits_{p}_{t}")[0] for p in range(3)])
    good = np.all(C > 0, axis=0) & np.all(N >= min_hits, axis=0)
    g = np.where(good, 1.0 / np.where(C > 0, C, 1), 0.0)
    w = uniform_filter(good.astype(float), SMOOTH, mode="nearest")
    gs = np.array([uniform_filter(g[p], SMOOTH, mode="nearest") / np.where(w > 0, w, 1) for p in range(3)])
    sv, fv = gs[:, good], (g / np.where(gs > 0, gs, 1))[:, good]
    cs, cf = np.corrcoef(sv), np.corrcoef(fv)
    r = {"smooth_cm": SMOOTH * 5,
         "rms_smooth": {PL[p]: float(sv[p].std()) for p in range(3)},
         "rms_fine": {PL[p]: float(fv[p].std()) for p in range(3)},
         "corr_smooth": {f"{PL[a]}-{PL[b]}": float(cs[a, b]) for a, b in ((0, 1), (0, 2), (1, 2))},
         "corr_fine": {f"{PL[a]}-{PL[b]}": float(cf[a, b]) for a, b in ((0, 1), (0, 2), (1, 2))},
         "rms_smooth_ratio_to_Y": {PL[p]: float((sv[p] / sv[2]).std()) for p in (0, 1)}}
    res[TPC[t]]["scales"] = r
    ext = [0, 500, -200, 200]
    fig, ax = plt.subplots(2, 3, figsize=(16, 8))
    for p in range(3):
        im = ax[0, p].imshow(np.where(good, gs[p], np.nan).T, origin="lower", extent=ext, aspect="auto", vmin=0.9, vmax=1.1, cmap="RdBu_r")
        ax[0, p].set_title(f"{TPC[t]} {PL[p]}: g smoothed {SMOOTH*5} cm (rms {r['rms_smooth'][PL[p]]:.3f})"); fig.colorbar(im, ax=ax[0, p])
        im = ax[1, p].imshow(np.where(good, g[p] / np.where(gs[p] > 0, gs[p], 1), np.nan).T, origin="lower", extent=ext, aspect="auto", vmin=0.9, vmax=1.1, cmap="RdBu_r")
        ax[1, p].set_title(f"{PL[p]}: g / smoothed (rms {r['rms_fine'][PL[p]]:.3f})"); fig.colorbar(im, ax=ax[1, p])
    for a_ in ax.flat:
        a_.set_xlabel("z [cm]"); a_.set_ylabel("y [cm]")
    fig.suptitle(f"SBND {TPC[t]}: large-scale part (top; corr U-Y {cs[0,2]:.2f}, V-Y {cs[1,2]:.2f}, U-V {cs[0,1]:.2f}) and fine part (bottom)")
    fig.tight_layout(); fig.savefig(f"{outdir}/scales_{TPC[t]}.png", dpi=90); plt.close(fig)
    print(TPC[t], json.dumps(r))
json.dump(res, open(f"{outdir}/plane_compare.json", "w"), indent=1)
