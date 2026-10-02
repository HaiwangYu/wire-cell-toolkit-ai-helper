#!/usr/bin/env python
"""|a-b| histogram of recob::Wire products between two DetSim files (same events).
Usage: diff_magnitude.py A.root B.root [--products dnnsp,gauss,wiener] [--events 0,1]"""
import argparse, os, sys
import numpy as np, uproot
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                                "31-reco1-wire-reproducibility-twester-abhat", "scripts"))
from wirebytes import dense_wires
from compare_runs import basket_bytes
ap = argparse.ArgumentParser(); ap.add_argument("a"); ap.add_argument("b")
ap.add_argument("--products", default="dnnsp,gauss,wiener"); ap.add_argument("--events", default="")
args = ap.parse_args()
ta, tb = uproot.open(args.a)["Events"], uproot.open(args.b)["Events"]
evts = [int(x) for x in args.events.split(",")] if args.events else range(ta.num_entries)
edges = [0, 1e-4, 1e-2, 0.1, 1, 10, np.inf]
print("bins of |a-b| over samples that differ:", [f"[{edges[i]:g},{edges[i+1]:g})" for i in range(len(edges)-1)])
for p in prods if (prods := args.products.split(",")) else []:
    br = f"recob::Wires_simtpc2d_{p}_DetSim.obj"
    tot = np.zeros(len(edges) - 1, int); nsamp = 0; roi_tot = 0; nnz = 0
    for i in evts:
        a = dense_wires(basket_bytes(ta[br], i), 11276); b = dense_wires(basket_bytes(tb[br], i), 11276)
        d = np.abs(a - b); nz = d[d > 0]
        tot += np.histogram(nz, bins=edges)[0]; nsamp += d.size; nnz += nz.size
        roi_tot += int(((a != 0) | (b != 0)).sum())
    print(f"{p}: events={len(list(evts))} in-ROI samples={roi_tot} differing={nnz} ({100*nnz/max(roi_tot,1):.1f}% of in-ROI) "
          f"hist={tot.tolist()}  rel. to in-ROI: {[f'{100*x/max(roi_tot,1):.2f}%' for x in tot]}")
