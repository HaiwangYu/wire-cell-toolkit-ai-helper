#!/usr/bin/env python3
"""Summarize compare_detsim.tsv: measured (q_yzmap/q_nominal) vs predicted factor.

Usage: plot_detsim.py <compare_detsim.tsv> <outdir> [min_ne=20000]
Channels with fewer than min_ne SimChannel electrons or no SP charge in either
file are left out.
"""
import json
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

tsv, outdir = sys.argv[1], sys.argv[2]
min_ne = float(sys.argv[3]) if len(sys.argv) > 3 else 20000
d = np.genfromtxt(tsv, names=True, delimiter="\t")
PL, TPC = ["U", "V", "Y"], ["East", "West"]

sel = (d["n_e"] >= min_ne) & (d["q_nominal"] > 0) & (d["q_yzmap"] > 0)
res = {"min_ne": min_ne, "channels_all": int(len(d)), "channels_used": int(sel.sum())}
fig, ax = plt.subplots(2, 3, figsize=(16, 9))
for p in range(3):
    for t in range(2):
        m = sel & (d["plane"] == p) & (d["tpc"] == t)
        if not m.any():
            continue
        pred, meas = d["predicted"][m], d["q_yzmap"][m] / d["q_nominal"][m]
        dev = meas / pred - 1
        # Plane totals: sum q_yz / sum q_nom vs charge-weighted predicted factor.
        tot_meas = d["q_yzmap"][m].sum() / d["q_nominal"][m].sum()
        tot_pred = (d["predicted"][m] * d["q_nominal"][m]).sum() / d["q_nominal"][m].sum()
        res[f"{TPC[t]} {PL[p]}"] = {
            "channels": int(m.sum()),
            "predicted_rms": float(pred.std()),
            "measured/predicted - 1: median": float(np.median(dev)),
            "measured/predicted - 1: rms": float(dev.std()),
            "measured/predicted - 1: 5-95%": [float(x) for x in np.percentile(dev, [5, 95])],
            "corr(measured, predicted)": float(np.corrcoef(meas, pred)[0, 1]),
            "total measured": float(tot_meas), "total predicted": float(tot_pred)}
        a = ax[0, p]
        a.scatter(pred, meas, s=3, alpha=0.5, label=f"{TPC[t]} (corr {res[f'{TPC[t]} {PL[p]}']['corr(measured, predicted)']:.2f})")
        ax[1, p].hist(dev, bins=np.linspace(-0.15, 0.15, 61), histtype="step", label=f"{TPC[t]}")
    ax[0, p].plot([0.5, 1.3], [0.5, 1.3], "k--", lw=1)
    ax[0, p].set_xlim(0.8, 1.2); ax[0, p].set_ylim(0.8, 1.2)
    ax[0, p].set_xlabel("predicted factor (map at SimChannel IDEs)")
    ax[0, p].set_ylabel("measured: q_yzmap / q_nominal (SP gauss)")
    ax[0, p].set_title(f"plane {PL[p]}"); ax[0, p].legend(markerscale=4)
    ax[1, p].set_xlabel("measured / predicted - 1"); ax[1, p].legend()
fig.suptitle(f"SBND long muons: per-channel YZ scaling, channels with >= {min_ne:g} electrons")
fig.tight_layout(); fig.savefig(f"{outdir}/detsim_scaling.png", dpi=90)
json.dump(res, open(f"{outdir}/detsim_scaling.json", "w"), indent=1)
print(json.dumps(res, indent=1))
