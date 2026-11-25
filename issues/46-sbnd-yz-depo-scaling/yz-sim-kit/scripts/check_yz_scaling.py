#!/usr/bin/env python3
"""Check that the YZ scaling worked: per channel, measured on/off SP charge
ratio vs the map's prediction (ai-helper issue 46).

Inputs: two detsim files of the SAME g4 events, one run with yz_scaling "off"
and one with "on" (run-yz-detsim.sh), and the map file.  For every channel with
SimChannel charge:
  predicted = map value of the channel's plane and TPC at the channel's
              SimChannel IDEs (y, z), weighted by electrons.  SimChannels are
              written before the scaling, so they are the same in both files.
  measured  = sum of the channel's recob::Wire charge (all ROIs), on / off.
Channels with fewer than --min-ne SimChannel electrons, or no charge in either
file, are left out.  Per plane and TPC it prints: channels, rms of the
predicted factor, median, rms and robust rms (1.4826 x median absolute
deviation) of measured/predicted - 1, the number of channels with
|measured/predicted - 1| > 5 %, its 5-95 % range, corr(measured, predicted)
(all channels, and without the > 5 % ones), and the plane totals (sum on / sum off vs the
charge-weighted predicted factor).

Usage (sbndcode environment; PyROOT; NO LD_PRELOAD needed):
  check_yz_scaling.py <off/detsim.root> <on/detsim.root> <map.json.bz2> <outdir>
                      [--labels simtpc2d:dnnsp,simtpc2d:gauss] [--process DetSim]
                      [--min-ne 20000]
The map file: $YZ_MAP_PATH/sbnd/sbnd-yzmap-run2-gen2-bnblight-v1.json.bz2.
Output: <outdir>/yzcheck_<instance>.tsv, yzcheck.json, yzcheck.png, and the
table on stdout.
"""
import argparse
import bz2
import json
import math
import os

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("off"); ap.add_argument("on"); ap.add_argument("map"); ap.add_argument("outdir")
ap.add_argument("--labels", default="simtpc2d:dnnsp,simtpc2d:gauss")
ap.add_argument("--simch", default="simtpc2d:simpleSC")
ap.add_argument("--process", default="DetSim")
ap.add_argument("--min-ne", type=float, default=20000)
a = ap.parse_args()
os.makedirs(a.outdir, exist_ok=True)

import ROOT  # noqa: E402  (after argparse so --help works without ROOT)
ROOT.gROOT.SetBatch(True)

# SBND channels (sbnd-wires-geometry-v0206): 5638 per TPC; U 1984, V 1984, Y 1670.
NCH_TPC, NU, NV = 5638, 1984, 1984
PL, TPC = ["U", "V", "Y"], ["East", "West"]
KEYS = ["AnodePlane:apa0", "AnodePlane:apa1"]
NZ, NY, DZ, DY, Z0, Y0 = 100, 80, 5.0, 5.0, 0.0, -200.0  # cm, as in the jsonnet YZMap


def tpc_plane(ch):
    tpc, local = divmod(ch, NCH_TPC)
    return tpc, (0 if local < NU else (1 if local < NU + NV else 2))


ymap = json.load(bz2.open(a.map, "rt"))


def mapval(tpc, plane, y, z):
    grid = ymap[KEYS[tpc]][str(plane)]
    iz = min(max(int(math.floor((z - Z0) / DZ)), 0), NZ - 1)
    iy = min(max(int(math.floor((y - Y0) / DY)), 0), NY - 1)
    return grid[iz][iy]


def bname(tree, cls, tag):
    label, inst = tag.split(":")
    n = f"{cls}_{label}_{inst}_{a.process}."
    if not tree.GetBranch(n):
        raise SystemExit(f"no branch {n} in {tree.GetCurrentFile().GetName()}")
    return n


def wire_q(tree, b):
    out = {}
    for w in getattr(tree, b).product():
        q = 0.0
        for rng in w.SignalROI().get_ranges():
            for v in rng.data():
                q += v
        out[w.Channel()] = q
    return out


def evid(tree):
    aux = tree.EventAuxiliary
    return (aux.run(), aux.subRun(), aux.event())


f0, f1 = ROOT.TFile.Open(a.off), ROOT.TFile.Open(a.on)
t0, t1 = f0.Get("Events"), f1.Get("Events")
if t0.GetEntries() != t1.GetEntries():
    raise SystemExit(f"different number of events: {t0.GetEntries()} vs {t1.GetEntries()}")
labels = a.labels.split(",")
bs = bname(t0, "sim::SimChannels", a.simch)
bw = {lab: bname(t0, "recob::Wires", lab) for lab in labels}
for lab in labels:
    bname(t1, "recob::Wires", lab)

rows = {lab: [] for lab in labels}
for ev in range(t0.GetEntries()):
    t0.GetEntry(ev); t1.GetEntry(ev)
    if evid(t0) != evid(t1):
        raise SystemExit(f"entry {ev}: event {evid(t0)} vs {evid(t1)}")
    pred = {}
    for sc in getattr(t0, bs).product():
        ch = sc.Channel()
        tpc, plane = tpc_plane(ch)
        ne = wsum = 0.0
        for tdc_ides in sc.TDCIDEMap():
            for ide in tdc_ides.second:
                ne += ide.numElectrons
                wsum += ide.numElectrons * mapval(tpc, plane, ide.y, ide.z)
        if ne > 0:
            pred[ch] = (ne, wsum / ne)
    for lab in labels:
        q0, q1 = wire_q(t0, bw[lab]), wire_q(t1, bw[lab])
        for ch, (ne, p) in pred.items():
            tpc, plane = tpc_plane(ch)
            rows[lab].append((ev, ch, tpc, plane, ne, p, q0.get(ch, 0.0), q1.get(ch, 0.0)))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

res = {"off": a.off, "on": a.on, "map": a.map, "events": int(t0.GetEntries()), "min_ne": a.min_ne}
fig, ax = plt.subplots(2 * len(labels), 3, figsize=(16, 8.5 * len(labels)), squeeze=False)
for il, lab in enumerate(labels):
    inst = lab.split(":")[1]
    with open(f"{a.outdir}/yzcheck_{inst}.tsv", "w") as fp:
        fp.write("event\tchannel\ttpc\tplane\tn_e\tpredicted\tq_off\tq_on\n")
        for r in rows[lab]:
            fp.write("\t".join(str(x) for x in r) + "\n")
    d = np.array(rows[lab], dtype=float).reshape(-1, 8)
    ne, pr, q0, q1 = d[:, 4], d[:, 5], d[:, 6], d[:, 7]
    sel = (ne >= a.min_ne) & (q0 > 0) & (q1 > 0)
    R = res[inst] = {"channels_with_simch": int(len(d)), "channels_used": int(sel.sum())}
    print(f"\n{lab}: {int(sel.sum())} of {len(d)} channel-events used (>= {a.min_ne:g} electrons, charge in both)")
    print("| | channels | predicted rms | meas/pred-1 median | rms | robust rms | > 5 % | 5-95 % | corr | corr w/o > 5 % | total meas / pred |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for t in range(2):
        for p in range(3):
            m = sel & (d[:, 3] == p) & (d[:, 2] == t)
            if not m.any():
                continue
            meas = q1[m] / q0[m]
            dev = meas / pr[m] - 1
            lo, hi = np.percentile(dev, [5, 95])
            tm = q1[m].sum() / q0[m].sum()
            tp = (pr[m] * q0[m]).sum() / q0[m].sum()
            corr = float(np.corrcoef(meas, pr[m])[0, 1])
            rrms = float(1.4826 * np.median(np.abs(dev - np.median(dev))))
            out = np.abs(dev) > 0.05
            corr_in = float(np.corrcoef(meas[~out], pr[m][~out])[0, 1])
            R[f"{TPC[t]} {PL[p]}"] = {
                "channels": int(m.sum()), "predicted_rms": float(pr[m].std()),
                "dev_median": float(np.median(dev)), "dev_rms": float(dev.std()),
                "dev_robust_rms": rrms, "n_dev_gt_5pc": int(out.sum()), "corr_without_gt_5pc": corr_in,
                "dev_5_95": [float(lo), float(hi)], "corr": corr,
                "total_measured": float(tm), "total_predicted": float(tp)}
            print(f"| {TPC[t]} {PL[p]} | {m.sum()} | {pr[m].std()*100:.1f} % | {np.median(dev)*100:+.2f} % "
                  f"| {dev.std()*100:.2f} % | {rrms*100:.2f} % | {out.sum()} | {lo*100:+.1f} … {hi*100:+.1f} % | {corr:.2f} | {corr_in:.2f} | {tm:.4f} / {tp:.4f} |")
            a0, a1 = ax[2 * il, p], ax[2 * il + 1, p]
            a0.scatter(pr[m], meas, s=3, alpha=0.5, label=f"{TPC[t]} (corr {corr:.2f})")
            a1.hist(dev, bins=np.linspace(-0.15, 0.15, 61), histtype="step", label=TPC[t])
    for p in range(3):
        a0, a1 = ax[2 * il, p], ax[2 * il + 1, p]
        a0.plot([0.5, 1.5], [0.5, 1.5], "k--", lw=1)
        a0.set_xlim(0.8, 1.2); a0.set_ylim(0.8, 1.2)
        a0.set_xlabel("predicted factor (map at SimChannel IDEs)")
        a0.set_ylabel(f"measured: {inst} charge on / off")
        a0.set_title(f"{inst}, plane {PL[p]}"); a0.legend(markerscale=4)
        a1.set_xlabel("measured / predicted - 1"); a1.legend()
fig.suptitle(f"SBND YZ scaling check, channels with >= {a.min_ne:g} electrons")
fig.tight_layout(); fig.savefig(f"{a.outdir}/yzcheck.png", dpi=80)
json.dump(res, open(f"{a.outdir}/yzcheck.json", "w"), indent=1)
print(f"\nwrote {a.outdir}/yzcheck.json, yzcheck.png, yzcheck_*.tsv")
