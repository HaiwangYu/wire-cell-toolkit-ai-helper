#!/usr/bin/env python
"""Compare the recob::Wire products of N repeated DetSim runs event by event.

Usage: compare_runs.py [--products dnnsp,gauss,wiener] [--label-prefix P] out1/detsim.root out2/detsim.root ...

For every event and product: SHA-256 of the decompressed basket bytes (one
basket = one event for these multi-MB branches; asserted).  Runs are grouped
into distinct states per (event, product).  Where states differ, the baskets
are decoded (wirebytes.py from issue 31) and the number of differing channels,
channels whose ROI (offset, length) list differs, differing samples and
max|a-b| vs the first run are reported.  Runs on the host with the
wire-cell-python venv (uproot), no ROOT needed.
"""
import argparse, hashlib, os, sys
import numpy as np
import uproot
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "31-reco1-wire-reproducibility-twester-abhat", "scripts"))
from wirebytes import decode_wires, decode_rse, dense_wires

def basket_bytes(branch, i):
    # art writes one basket per entry for these branches; verify and read.
    for k in range(branch.num_baskets):
        a, b = branch.basket_entry_start_stop(k)
        if a <= i < b:
            assert b - a == 1, f"{branch.name}: basket {k} holds entries [{a},{b}), cannot split"
            return bytes(branch.basket(k).data)
    raise IndexError(i)

def rse_of(tree, i):
    br = tree["EventAuxiliary"]
    try:
        return decode_rse(basket_bytes(br, i))
    except AssertionError:
        return ("entry", i)

def roi_sig(rois):
    return [[(o, v.size) for o, v in r] for r in rois]

def diff(a, b):
    ca, va, na, ra = decode_wires(a)
    cb, vb, nb, rb = decode_wires(b)
    assert (ca == cb).all() and na == nb
    da, db = dense_wires(a, int(ca.max()) + 1), dense_wires(b, int(cb.max()) + 1)
    d = np.abs(da - db)
    chdiff = np.where(d.max(axis=1) > 0)[0]
    sa, sb = roi_sig(ra), roi_sig(rb)
    roidiff = [int(ca[k]) for k in range(len(ca)) if sa[k] != sb[k]]
    return dict(nch=len(chdiff), ch=[int(c) for c in chdiff[:12]], nroi=len(roidiff),
                nsamp=int((d > 0).sum()), maxd=float(d.max()))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--products", default="dnnsp,gauss,wiener")
    ap.add_argument("--process", default="DetSim")
    ap.add_argument("--module", default="simtpc2d")
    ap.add_argument("files", nargs="+")
    args = ap.parse_args()
    prods = args.products.split(",")
    trees = [uproot.open(f)["Events"] for f in args.files]
    n = trees[0].num_entries
    assert all(t.num_entries == n for t in trees), [t.num_entries for t in trees]
    print(f"runs={len(args.files)} events={n} products={prods}")
    for k, f in enumerate(args.files):
        print(f"  run{k}: {f}")
    summary = {p: dict(identical=0, differing=0) for p in prods}
    for i in range(n):
        rse = [rse_of(t, i) for t in trees]
        assert all(r == rse[0] for r in rse), rse
        line = [f"evt {i} RSE {'/'.join(map(str, rse[0]))}:"]
        for p in prods:
            br = f"recob::Wires_{args.module}_{p}_{args.process}.obj"
            bts = [basket_bytes(t[br], i) for t in trees]
            hs = [hashlib.sha256(b).hexdigest()[:10] for b in bts]
            states = {}
            for k, h in enumerate(hs):
                states.setdefault(h, []).append(k)
            if len(states) == 1:
                summary[p]["identical"] += 1
                line.append(f"{p}=IDENTICAL({hs[0]})")
            else:
                summary[p]["differing"] += 1
                desc = " ".join(f"{h}:{v}" for h, v in states.items())
                worst = max((diff(bts[0], bts[k]) for k in range(1, len(bts)) if hs[k] != hs[0]),
                            key=lambda d: d["nsamp"])
                line.append(f"{p}=DIFFER[{len(states)} states {desc}; vs run0 worst: "
                            f"nch={worst['nch']} roi-list-changed={worst['nroi']} nsamp={worst['nsamp']} "
                            f"max|d|={worst['maxd']:.3g} ch={worst['ch']}]")
        print("\n    ".join(line))
    print("SUMMARY (events identical across all runs / events with >1 state):")
    for p in prods:
        s = summary[p]
        print(f"  {p}: identical {s['identical']}/{n}, differing {s['differing']}/{n}")

if __name__ == "__main__":
    main()
