#!/usr/bin/env python3
"""Check the YZ scaling in a pair of SBND detsim files (issue 46).

The two files hold the same events, simulated with the nominal and the
YZ-map jsonnet.  For each channel:
  - predicted factor: the YZ map value of the channel's plane and TPC,
    averaged over the SimChannel IDEs of the channel (weight: electrons);
    SimChannels come from the nominal file (they are unscaled in both);
  - measured factor: the ratio of signal-processed charge (recob::Wire
    "gauss", summed over all ROIs) yz / nominal.

Usage (in the sbndcode environment, PyROOT):
  compare_detsim.py <nominal.root> <yzmap.root> <map.json.bz2> <outdir> [label=simtpc2d] [process=DetSim]
"""
import bz2
import json
import math
import sys

import ROOT

ROOT.gROOT.SetBatch(True)

NOM, YZ, MAP, OUT = sys.argv[1:5]
LABEL = sys.argv[5] if len(sys.argv) > 5 else "simtpc2d"
PROC = sys.argv[6] if len(sys.argv) > 6 else "DetSim"

# SBND channels (sbnd-wires-geometry-v0206): 5638 per TPC; U 1984, V 1984, Y 1670.
NCH_TPC, NU, NV = 5638, 1984, 1984
KEYS = ["AnodePlane:apa0", "AnodePlane:apa1"]


def tpc_plane(ch):
    tpc, local = divmod(ch, NCH_TPC)
    plane = 0 if local < NU else (1 if local < NU + NV else 2)
    return tpc, plane


ymap = json.load(bz2.open(MAP, "rt"))
NZ, NY, DZ, DY, Z0, Y0 = 100, 80, 5.0, 5.0, 0.0, -200.0  # cm


def mapval(tpc, plane, y, z):
    grid = ymap[KEYS[tpc]][str(plane)]
    iz = min(max(int(math.floor((z - Z0) / DZ)), 0), NZ - 1)
    iy = min(max(int(math.floor((y - Y0) / DY)), 0), NY - 1)
    return grid[iz][iy]


def branch(tree, cls, inst):
    name = f"{cls}_{LABEL}_{inst}_{PROC}."
    if not tree.GetBranch(name):
        raise SystemExit(f"no branch {name}")
    return name


def wires(tree, bname):
    out = {}
    for w in getattr(tree, bname).product():
        q = 0.0
        for rng in w.SignalROI().get_ranges():
            for v in rng.data():
                q += v
        out[w.Channel()] = q
    return out


fn, fy = ROOT.TFile.Open(NOM), ROOT.TFile.Open(YZ)
tn, ty = fn.Get("Events"), fy.Get("Events")
assert tn.GetEntries() == ty.GetEntries()
bw = branch(tn, "recob::Wires", "gauss")
bs = branch(tn, "sim::SimChannels", "simpleSC")

rows = []   # (event, ch, tpc, plane, n_e, predicted, q_nom, q_yz)
for ev in range(tn.GetEntries()):
    tn.GetEntry(ev)
    ty.GetEntry(ev)
    pred = {}
    for sc in getattr(tn, bs).product():
        ch = sc.Channel()
        tpc, plane = tpc_plane(ch)
        ne = wsum = 0.0
        for tdc_ides in sc.TDCIDEMap():
            for ide in tdc_ides.second:
                ne += ide.numElectrons
                wsum += ide.numElectrons * mapval(tpc, plane, ide.y, ide.z)
        if ne > 0:
            pred[ch] = (ne, wsum / ne)
    qn, qy = wires(tn, bw), wires(ty, bw)
    for ch, (ne, p) in pred.items():
        tpc, plane = tpc_plane(ch)
        rows.append((ev, ch, tpc, plane, ne, p, qn.get(ch, 0.0), qy.get(ch, 0.0)))

with open(f"{OUT}/compare_detsim.tsv", "w") as fp:
    fp.write("event\tchannel\ttpc\tplane\tn_e\tpredicted\tq_nominal\tq_yzmap\n")
    for r in rows:
        fp.write("\t".join(str(x) for x in r) + "\n")
print(f"wrote {len(rows)} channel rows to {OUT}/compare_detsim.tsv")
