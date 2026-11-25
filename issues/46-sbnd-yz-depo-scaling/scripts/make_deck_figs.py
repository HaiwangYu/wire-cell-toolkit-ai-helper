#!/usr/bin/env python3
"""Slide figures and numbers for the issue-46 deck (SBND YZ map file summary).

Usage: make_deck_figs.py <map.root> <outdir>

Reads Kento's YZ map file (zy_, CzyHist_, zynhits_, zydqdx_, dqdxHist_ per
plane p = 0 U, 1 V, 2 Y and TPC t = 0 East, 1 West), writes slide-sized PNGs
and deck_numbers.json into <outdir>.  Read-only on the input.

Definitions
  g      = 1/C (relative response; zy * C = constant).
  g_norm = g / mean(g over pixels with C > 0) per plane and TPC, empty -> 1
           (what convert-yzmap-sbnd.py --factor inv-norm writes).
  good   = C > 0 on all three planes and >= MIN_HITS hits on all three
           (same selection as compare_planes.py).
"""
import sys, json
import warnings
import numpy as np
warnings.filterwarnings("ignore", "Mean of empty slice")
import uproot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import uniform_filter, binary_dilation

fn, outdir = sys.argv[1], sys.argv[2]
MIN_HITS = 100
SMOOTH = 9                       # 45 cm box for the large-scale part
PL, TPC = ["U", "V", "Y"], ["East", "West"]
COL = {"U": "#2a78d6", "V": "#eb6834", "Y": "#1baf7a"}
TPC_LS = {"East": "-", "West": "--"}
SMALL = {"font.size": 16, "axes.titlesize": 16, "axes.labelsize": 16,
         "legend.fontsize": 14, "xtick.labelsize": 14, "ytick.labelsize": 14}
plt.rcParams.update({"font.size": 16, "axes.titlesize": 16, "axes.labelsize": 16,
                     "legend.fontsize": 14, "xtick.labelsize": 14, "ytick.labelsize": 14,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.dpi": 150, "figure.dpi": 150})
DIV = plt.get_cmap("RdBu_r").copy(); DIV.set_bad("#9a9a96")
SEQ = plt.get_cmap("Blues").copy(); SEQ.set_bad("#9a9a96")

f = uproot.open(fn)


def h2(name):
    o = f[name]
    return o.values().astype(float), o.axes[0].edges(), o.axes[1].edges()


C, N, Z = {}, {}, {}
for t in (0, 1):
    for p in range(3):
        C[t, p], ze, ye = h2(f"CzyHist_{p}_{t}")
        N[t, p] = h2(f"zynhits_{p}_{t}")[0]
        Z[t, p] = h2(f"zy_{p}_{t}")[0]
EXT = [ze[0], ze[-1], ye[0], ye[-1]]
zc, yc = 0.5 * (ze[1:] + ze[:-1]), 0.5 * (ye[1:] + ye[:-1])
ZZ, YY = np.meshgrid(zc, yc, indexing="ij")          # shape (nz, ny)
EDGE = (ZZ < ze[0] + 10) | (ZZ > ze[-1] - 10) | (YY < ye[0] + 10) | (YY > ye[-1] - 10)   # outer 2 pixels

out = {"input": fn, "min_hits": MIN_HITS,
       "binning": {"nz": len(zc), "ny": len(yc), "dz_cm": float(ze[1] - ze[0]),
                   "dy_cm": float(ye[1] - ye[0]), "z_cm": [float(ze[0]), float(ze[-1])],
                   "y_cm": [float(ye[0]), float(ye[-1])]},
       "titles": {"zy": f["zy_0_0"].member("fTitle"), "CzyHist": f["CzyHist_0_0"].member("fTitle"),
                  "zynhits": f["zynhits_0_0"].member("fTitle"), "zydqdx": f["zydqdx_0_0"].member("fTitle"),
                  "dqdxHist": f["dqdxHist_0_0"].member("fTitle"),
                  "dqdxHist_xaxis": f["dqdxHist_0_0"].axes[0].member("fTitle"),
                  "zy_xaxis": f["zy_0_0"].axes[0].member("fTitle"),
                  "zy_yaxis": f["zy_0_0"].axes[1].member("fTitle")},
       "per": {}}

G, GN = {}, {}
for t in (0, 1):
    for p in range(3):
        c, n, z = C[t, p], N[t, p], Z[t, p]
        have = c > 0
        g = np.where(have, 1.0 / np.where(have, c, 1), np.nan)
        G[t, p] = g
        gn = np.where(have, g / np.nanmean(g), np.nan)
        GN[t, p] = gn
        prod = (z * c)[have]
        gmed = float(np.median(z[have]))
        imax = np.unravel_index(np.argmax(np.where(have, c, -1)), c.shape)
        d = h2(f"zydqdx_{p}_{t}")[0]
        out["per"][f"{TPC[t]} {PL[p]}"] = {
            "pixels_with_data": int(have.sum()), "empty_C0": int((~have).sum()),
            "empty_with_hits": int(((~have) & (n > 0)).sum()),
            "hits_total": float(n.sum()),
            "hits_min_median_max": [float(n[have].min()), float(np.median(n[have])), float(n.max())],
            "lowhit_lt100": int((have & (n < 100)).sum()), "lowhit_lt200": int((have & (n < 200)).sum()),
            "lowhit_lt500": int((have & (n < 500)).sum()),
            "zy_pixel_median": gmed,
            "zy_hit_weighted_mean": float((z * n)[have].sum() / n[have].sum()),
            "zyC_min_max": [float(prod.min()), float(prod.max())],
            "zyC_over_pixel_median_maxdev": float(np.max(np.abs(prod / gmed - 1))),
            "C_min_max": [float(c[have].min()), float(c[have].max())],
            "C_max_at_z_y_cm_hits": [float(zc[imax[0]]), float(yc[imax[1]]), float(n[imax])],
            "g_raw_mean": float(np.nanmean(g)),
            "gnorm_rms": float(np.nanstd(gn)),
            "gnorm_min_max": [float(np.nanmin(gn)), float(np.nanmax(gn))],
            "gnorm_rms_hits_ge100": float(np.nanstd(gn[have & (n >= MIN_HITS)])),
            "C_min_at_z_y_cm_hits": [float(zc[np.unravel_index(np.argmin(np.where(have, c, 1e9)), c.shape)[0]]),
                                     float(yc[np.unravel_index(np.argmin(np.where(have, c, 1e9)), c.shape)[1]]),
                                     float(n[np.unravel_index(np.argmin(np.where(have, c, 1e9)), c.shape)])],
            "gnorm_p05_p95": [float(x) for x in np.nanpercentile(gn, [5, 95])],
            "C_gt_1.3": {"pixels": int((c > 1.3).sum()), "in_outer_10cm": int(((c > 1.3) & EDGE).sum()),
                         "hits_median": float(np.median(n[c > 1.3])) if (c > 1.3).any() else None,
                         "hits_min": float(n[c > 1.3].min()) if (c > 1.3).any() else None},
            "C_gt_1.5_pixels": int((c > 1.5).sum()),
            "lowhit_lt100_next_to_empty": int((have & (n < 100) & binary_dilation(~have)).sum()),
            "lowhit_lt100_in_outer_10cm": int((have & (n < 100) & EDGE).sum()),
            "lowhit_lt100_C_min_max": [float(c[have & (n < 100)].min()), float(c[have & (n < 100)].max())] if (have & (n < 100)).any() else None,
            "zydqdx_nan_pixels": int(np.isnan(d).sum()),
            "zydqdx_over_nhits_median": float(np.median((d / np.maximum(n, 1))[np.isfinite(d) & (d != 0)])),
        }

# ---------------------------------------------------------------- 1D dQ/dx
def hstats(vals, flows, edges):
    tot = flows.sum()
    cum = np.cumsum(flows)                             # flows: [uf, bins..., of]
    k = np.searchsorted(cum, 0.5 * tot)                # index into flows
    b = k - 1                                          # bin index
    prev = cum[k - 1] if k > 0 else 0
    med = edges[b] + (0.5 * tot - prev) / flows[k] * (edges[b + 1] - edges[b])
    cen = 0.5 * (edges[1:] + edges[:-1])
    i = int(np.argmax(vals))
    j = slice(max(i - 3, 0), i + 4)
    a2, a1, _ = np.polyfit(cen[j], vals[j], 2)
    return {"entries": float(tot), "in_range": float(vals.sum()), "underflow": float(flows[0]),
            "overflow": float(flows[-1]), "median_incl_flows": float(med),
            "peak_parabola": float(-a1 / (2 * a2)), "peak_bin_center": float(cen[i]),
            "mean_in_range": float((vals * cen).sum() / vals.sum()),
            "bin_width": float(edges[1] - edges[0])}

H = {}
out["dqdxHist"] = {}
for t in (0, 1):
    for p in range(3):
        o = f[f"dqdxHist_{p}_{t}"]
        e = o.axes[0].edges()
        H[t, p] = (o.values().astype(float), e)
        s = hstats(H[t, p][0], o.values(flow=True).astype(float), e)
        s["entries_minus_EastplusWest_nhits"] = s["entries"] - float(N[0, p].sum() + N[1, p].sum())
        out["dqdxHist"][f"{p}_{t}"] = s
for p in range(3):
    v0, v1 = H[0, p][0], H[1, p][0]
    out["dqdxHist"][f"{p}_1_vs_{p}_0"] = {
        "max_abs_bin_diff_over_peak": float(np.max(np.abs(v1 - v0)) / v0.max()),
        "median_diff": out["dqdxHist"][f"{p}_1"]["median_incl_flows"] - out["dqdxHist"][f"{p}_0"]["median_incl_flows"]}

sc = {}
for p in range(3):
    e, w = out["per"][f"East {PL[p]}"], out["per"][f"West {PL[p]}"]
    sc[PL[p]] = {"West/East-1 pixel_median": w["zy_pixel_median"] / e["zy_pixel_median"] - 1,
                 "West/East-1 hit_weighted_mean": w["zy_hit_weighted_mean"] / e["zy_hit_weighted_mean"] - 1}
for t in (0, 1):
    y = out["per"][f"{TPC[t]} Y"]["zy_pixel_median"]
    for p in (0, 1):
        sc[f"{TPC[t]} Y/{PL[p]}-1 pixel_median"] = y / out["per"][f"{TPC[t]} {PL[p]}"]["zy_pixel_median"] - 1
for p in range(3):
    sc[f"dqdxHist {PL[p]}: (_1 - _0) median, rel"] = out["dqdxHist"][f"{p}_1_vs_{p}_0"]["median_diff"] / out["dqdxHist"][f"{p}_0"]["median_incl_flows"]
for t in (0, 1):
    for p in (0, 1):
        sc[f"dqdxHist_{t}: Y/{PL[p]}-1 median"] = out["dqdxHist"][f"2_{t}"]["median_incl_flows"] / out["dqdxHist"][f"{p}_{t}"]["median_incl_flows"] - 1
        sc[f"dqdxHist_{t}: Y/{PL[p]}-1 peak"] = out["dqdxHist"][f"2_{t}"]["peak_parabola"] / out["dqdxHist"][f"{p}_{t}"]["peak_parabola"] - 1
out["scale_differences"] = sc

# ---------------------------------------------------------------- plane comparison (as compare_planes.py)
out["planes"] = {}
FINE, GOOD = {}, {}
for t in (0, 1):
    c3 = np.array([C[t, p] for p in range(3)]); n3 = np.array([N[t, p] for p in range(3)])
    good = np.all(c3 > 0, axis=0) & np.all(n3 >= MIN_HITS, axis=0)
    GOOD[t] = good
    gv = np.array([G[t, p][good] for p in range(3)])
    corr = np.corrcoef(gv); gavg = gv.mean(axis=0)
    r = {"good_pixels": int(good.sum()),
         "rms_g": {PL[p]: float(gv[p].std()) for p in range(3)},
         "p05_p95_g": {PL[p]: [float(x) for x in np.percentile(gv[p], [5, 95])] for p in range(3)},
         "corr": {f"{PL[a]}-{PL[b]}": float(corr[a, b]) for a, b in ((0, 2), (1, 2), (0, 1))},
         "residual_rms_Ymap": {PL[p]: float(np.std(gv[p] / gv[2])) for p in range(3)},
         "residual_rms_avgmap": {PL[p]: float(np.std(gv[p] / gavg)) for p in range(3)}}
    for a in (0, 1):
        q = gv[a] / gv[2]
        r[f"g{PL[a]}/gY_frac_gt5pct"] = float(np.mean(np.abs(q - 1) > 0.05))
    # large-scale (45 cm) vs fine part
    g0 = np.array([np.where(good, G[t, p], 0.0) for p in range(3)])
    w = uniform_filter(good.astype(float), SMOOTH, mode="nearest")
    gs = np.array([uniform_filter(g0[p], SMOOTH, mode="nearest") / np.where(w > 0, w, 1) for p in range(3)])
    FINE[t] = np.array([np.where(good, g0[p] / np.where(gs[p] > 0, gs[p], 1), np.nan) for p in range(3)])
    cs = np.corrcoef(gs[:, good])
    r["corr_smooth45"] = {f"{PL[a]}-{PL[b]}": float(cs[a, b]) for a, b in ((0, 2), (1, 2), (0, 1))}
    out["planes"][TPC[t]] = r

# z profile of g_norm (good pixels) around the z = 250 cm line, and y-profile ends
out["z_profile_near_250"] = {"z_cm": [float(x) for x in zc[47:54]]}
out["y_profile_ends"] = {"y_cm": [float(yc[0]), float(yc[-1])]}
for t in (0, 1):
    for p in range(3):
        gm = np.where(GOOD[t], GN[t, p], np.nan)
        out["z_profile_near_250"][f"{TPC[t]} {PL[p]}"] = [round(float(x), 4) for x in np.nanmean(gm, axis=1)[47:54]]
        py = np.nanmean(gm, axis=0)
        out["y_profile_ends"][f"{TPC[t]} {PL[p]}"] = [round(float(py[0]), 4), round(float(py[-1]), 4)]

# ---------------------------------------------------------------- stripe direction of the fine part
# theta: stripe direction measured from +y (vertical) toward +z.  For each
# theta, pixels are binned (5 cm) in the coordinate across the stripe,
# s = z cos(theta) - y sin(theta); score = variance of the bin means / total variance.
THETA = np.arange(-90, 90, 1.0)
STRIPE = {}
out["stripes"] = {}
for t in (0, 1):
    for p in range(3):
        fv = FINE[t][p]; m = np.isfinite(fv)
        x = fv[m] - fv[m].mean(); zz, yy = ZZ[m], YY[m]
        sc_ = []
        for th in np.radians(THETA):
            s = zz * np.cos(th) - yy * np.sin(th)
            k = np.floor(s / 5.0).astype(int); k -= k.min()
            cnt = np.bincount(k); sm = np.bincount(k, x)
            ok = cnt >= 10
            sc_.append(np.sum(sm[ok] ** 2 / cnt[ok]) / np.sum(x ** 2))
        sc_ = np.array(sc_); STRIPE[t, p] = sc_
        i = int(np.argmax(sc_))
        out["stripes"][f"{TPC[t]} {PL[p]}"] = {"theta_deg_from_vertical": float(THETA[i]),
                                              "explained_fraction": float(sc_[i]),
                                              "explained_at_m60_0_p60deg": [float(sc_[THETA == a][0]) for a in (-60, 0, 60)]}

# ---------------------------------------------------------------- figures
def save(fig, name):
    fig.savefig(f"{outdir}/{name}", bbox_inches="tight"); plt.close(fig)

BIG = {"font.size": 21, "axes.titlesize": 21, "axes.labelsize": 21,
       "legend.fontsize": 18, "xtick.labelsize": 18, "ytick.labelsize": 18}


def zylabels(a, left=True, bottom=True):
    if bottom:
        a.set_xlabel("z [cm]")
    if left:
        a.set_ylabel("y [cm]")


# 1) hits per pixel, 6 maps
plt.rcParams.update(BIG)
fig, ax = plt.subplots(2, 3, figsize=(12, 6.8), sharex=True, sharey=True, constrained_layout=True)
for t in (0, 1):
    for p in range(3):
        a = ax[t, p]
        n = np.where(C[t, p] > 0, N[t, p], np.nan)
        im = a.imshow(n.T, origin="lower", extent=EXT, aspect="auto", cmap=SEQ, vmin=0, vmax=2000)
        k = out["per"][f"{TPC[t]} {PL[p]}"]
        a.set_title(f"{TPC[t]} {PL[p]}: {k['hits_total']/1e6:.2f}M")
        zylabels(a, p == 0, t == 1)
fig.colorbar(im, ax=ax, label="hits per pixel", shrink=0.9)
save(fig, "fig_nhits.png")
plt.rcParams.update(SMALL)

# 2) the three variables, for every plane and TPC (fig_vars_<TPC><plane>.png)
for t in (0, 1):
    for p in range(3):
        M = out["per"][f"{TPC[t]} {PL[p]}"]["zy_pixel_median"]
        fig, ax = plt.subplots(1, 3, figsize=(14, 4.6), sharey=True, constrained_layout=True)
        zz_ = np.where(C[t, p] > 0, Z[t, p], np.nan)
        im = ax[0].imshow(zz_.T, origin="lower", extent=EXT, aspect="auto", cmap=SEQ,
                          vmin=10 * round(0.89 * M / 10), vmax=10 * round(1.115 * M / 10))
        fig.colorbar(im, ax=ax[0], label="median dQ/dx [ADC/cm]", location="bottom", shrink=0.9)
        ax[0].set_title(f"zy_{p}_{t}: median dQ/dx")
        im = ax[1].imshow(np.where(C[t, p] > 0, C[t, p], np.nan).T, origin="lower", extent=EXT, aspect="auto",
                          cmap=DIV, vmin=0.85, vmax=1.15)
        fig.colorbar(im, ax=ax[1], label="C", location="bottom", shrink=0.9)
        ax[1].set_title(f"CzyHist_{p}_{t}: C")
        im = ax[2].imshow(np.where(C[t, p] > 0, N[t, p], np.nan).T, origin="lower", extent=EXT, aspect="auto",
                          cmap=SEQ, vmin=0, vmax=2000)
        fig.colorbar(im, ax=ax[2], label="hits", location="bottom", shrink=0.9)
        ax[2].set_title(f"zynhits_{p}_{t}: hits")
        for i, a in enumerate(ax):
            zylabels(a, i == 0)
        save(fig, f"fig_vars_{TPC[t]}{PL[p]}.png")

# 3) g_norm maps, 6
plt.rcParams.update(BIG)
fig, ax = plt.subplots(2, 3, figsize=(12, 6.8), sharex=True, sharey=True, constrained_layout=True)
for t in (0, 1):
    for p in range(3):
        a = ax[t, p]; k = out["per"][f"{TPC[t]} {PL[p]}"]
        im = a.imshow(GN[t, p].T, origin="lower", extent=EXT, aspect="auto", cmap=DIV, vmin=0.85, vmax=1.15)
        a.set_title(f"{TPC[t]} {PL[p]}: rms {100*k['gnorm_rms']:.1f} %")
        zylabels(a, p == 0, t == 1)
fig.colorbar(im, ax=ax, label="g = 1/C, mean 1", shrink=0.9, extend="both")
save(fig, "fig_g_maps.png")

# 4) profiles
plt.rcParams.update(BIG)
fig, ax = plt.subplots(2, 2, figsize=(10, 6.4), sharey=True, sharex="col", constrained_layout=True)
for t in (0, 1):
    for p in range(3):
        gm = np.where(GOOD[t], GN[t, p], np.nan)
        ax[t, 0].plot(zc, np.nanmean(gm, axis=1), color=COL[PL[p]], lw=1.6, label=PL[p])
        ax[t, 1].plot(yc, np.nanmean(gm, axis=0), color=COL[PL[p]], lw=1.6, label=PL[p])
    ax[t, 0].axvline(250, color="0.5", lw=0.8, ls=":")
    ax[t, 0].set_ylabel(f"{TPC[t]}: mean g")
    ax[t, 1].legend(ncol=3, loc="lower center", frameon=False, fontsize=17)
ax[0, 0].text(253, 1.07, "z = 250 cm", color="0.35", fontsize=16)
ax[0, 0].set_title("along z (mean over y)"); ax[0, 1].set_title("along y (mean over z)")
ax[1, 0].set_xlabel("z [cm]"); ax[1, 1].set_xlabel("y [cm]")
for a in ax.flat:
    a.grid(alpha=0.25); a.set_ylim(0.9, 1.1)
save(fig, "fig_profiles.png")
plt.rcParams.update(SMALL)

# 5) fine part (g / 45 cm smoothed), East, plus stripe-angle score
fig, ax = plt.subplots(1, 4, figsize=(15, 4.4), constrained_layout=True,
                       gridspec_kw={"width_ratios": [1, 1, 1, 1.05]})
for p in range(3):
    a = ax[p]
    im = a.imshow(FINE[0][p].T, origin="lower", extent=EXT, aspect="equal", cmap=DIV, vmin=0.93, vmax=1.07)
    a.set_title(f"East {PL[p]}: fine part")
    zylabels(a, p == 0)
fig.colorbar(im, ax=ax[:3], location="bottom", shrink=0.5, label="g / (45 cm box average)")
a = ax[3]
for t in (0, 1):
    for p in range(3):
        a.plot(THETA, STRIPE[t, p], color=COL[PL[p]], ls=TPC_LS[TPC[t]], lw=1.5, label=f"{TPC[t]} {PL[p]}")
a.set_xlabel("line angle from vertical [deg]"); a.set_ylabel("variance fraction")
a.set_xticks([-90, -60, 0, 60, 90]); a.grid(alpha=0.25); a.set_ylim(0, 0.52)
a.legend(fontsize=11, ncol=2, frameon=False, loc="upper center")
save(fig, "fig_stripes.png")

# 6) edges: C vs hits
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True, constrained_layout=True)
for t in (0, 1):
    a = ax[t]
    for p in range(3):
        m = C[t, p] > 0
        a.scatter(N[t, p][m], C[t, p][m], s=3, alpha=0.35, color=COL[PL[p]], label=PL[p], rasterized=True)
    a.axvline(MIN_HITS, color="0.4", lw=0.8, ls=":")
    a.set_xscale("log"); a.set_xlabel("hits per pixel"); a.set_title(f"{TPC[t]} TPC")
    a.grid(alpha=0.25); a.legend(markerscale=4, frameon=False)
ax[0].set_ylabel("C (pixels with C > 0)")
save(fig, "fig_C_vs_hits.png")

# 7) plane comparison scatter
plt.rcParams.update(BIG)
fig, ax = plt.subplots(1, 2, figsize=(8.6, 5.0), sharey=True, constrained_layout=True)
for t in (0, 1):
    a = ax[t]; good = GOOD[t]
    for p in (0, 1):
        a.scatter(G[t, 2][good], G[t, p][good], s=2, alpha=0.25, color=COL[PL[p]], rasterized=True,
                  label=f"{PL[p]} (corr {out['planes'][TPC[t]]['corr'][PL[p]+'-Y']:.2f})")
    a.plot([0.7, 1.3], [0.7, 1.3], color="0.3", lw=0.8, ls="--")
    a.set_xlim(0.8, 1.2); a.set_ylim(0.8, 1.2); a.set_aspect("equal"); a.set_xticks([0.8, 1.0, 1.2]); a.set_yticks([0.8, 0.9, 1.0, 1.1, 1.2])
    a.set_xlabel("$g_Y$"); a.set_title(f"{TPC[t]} ({good.sum()} pixels)")
    a.legend(markerscale=6, frameon=False, loc="upper left", fontsize=18, handletextpad=0.1, borderaxespad=0.2); a.grid(alpha=0.25)
ax[0].set_ylabel("$g_U$, $g_V$")
save(fig, "fig_plane_scatter.png")
plt.rcParams.update(SMALL)

# 8) 1D dQ/dx
fig, ax = plt.subplots(1, 3, figsize=(14, 4.4), sharey=True, constrained_layout=True)
for p in range(3):
    a = ax[p]
    for t in (0, 1):
        v, e = H[t, p]; cen = 0.5 * (e[1:] + e[:-1]); s = out["dqdxHist"][f"{p}_{t}"]
        a.step(cen, v / 1e3, where="mid", color=COL[PL[p]], ls=TPC_LS[TPC[t]], lw=1.4,
               label=f"{p}_{t}: median {s['median_incl_flows']:.0f}, peak {s['peak_parabola']:.0f}")
    a.set_xlabel("dQ/dx [ADC/cm]"); a.set_title(f"dqdxHist, plane {PL[p]}"); a.set_xticks([500, 1000, 1500, 2000]); a.grid(alpha=0.25)
    a.legend(frameon=False, fontsize=12, loc="upper right"); a.set_ylim(0, 600)
ax[0].set_ylabel("hits / 9 ADC/cm [$10^3$]")
save(fig, "fig_dqdx_1d.png")

# 8b) distribution of the pixel medians (zy)
plt.rcParams.update(BIG)
fig, ax = plt.subplots(figsize=(8, 5.2), constrained_layout=True)
bins = np.linspace(950, 1350, 81)
for t in (0, 1):
    for p in range(3):
        m = C[t, p] > 0; k = out["per"][f"{TPC[t]} {PL[p]}"]
        ax.hist(Z[t, p][m], bins=bins, histtype="step", color=COL[PL[p]], ls=TPC_LS[TPC[t]], lw=1.4,
                label=f"{TPC[t]} {PL[p]}: {k['zy_pixel_median']:.0f}")
ax.set_xlabel("zy [ADC/cm]"); ax.set_xlim(1000, 1320); ax.set_ylabel("pixels")
ax.legend(frameon=False, ncol=2, fontsize=15, title="median over pixels", title_fontsize=15, loc="upper right")
ax.set_ylim(0, 1250)
ax.grid(alpha=0.25)
save(fig, "fig_zy_pixel_hist.png")

json.dump(out, open(f"{outdir}/deck_numbers.json", "w"), indent=1)
print(json.dumps({"per": out["per"], "dqdxHist": out["dqdxHist"], "scale": sc,
                  "stripes": out["stripes"], "planes": out["planes"]}, indent=1))
