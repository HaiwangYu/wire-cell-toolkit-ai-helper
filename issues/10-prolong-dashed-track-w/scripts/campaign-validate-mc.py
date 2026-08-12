#!/usr/bin/env python3
"""Campaign validation, MC leg: reconstructed charge vs SimChannel truth.

For every event in the MC leg, per plane, over channels carrying real charge:
  gauss/truth and dnnsp/truth totals, the median per-channel ratio, and the
  fraction of channels reconstructing < 50 % of their truth (the failure mode the
  four fixes address -- a prolonged W pulse whose ROI collapses).

recob::Wire values are electrons/50 (DeconNorm), so they are scaled by 50 here.
Usage (SL7 container, sbndcode env):
    python3 campaign-validate-mc.py [campaign-dir]
"""
import glob, os, sys
import numpy as np
import ROOT

C = sys.argv[1] if len(sys.argv) > 1 else (
    "/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/"
    "10-prolong-dashed-track-w/data/validation-20260812")
SC = "sim::SimChannels_simtpc2d_simpleSC_ReDetSim."
SCALE, QMIN = 50.0, 5e4


def plane_of(ch):
    c = ch % 5638
    return "u" if c < 1984 else ("v" if c < 3968 else "w")


def read(path, tag):
    f = ROOT.TFile.Open(path)
    if not f or f.IsZombie():
        return None, None
    t = f.Get("Events")
    if not t or not t.GetEntries():
        return None, None
    t.GetEntry(0)
    truth = {}
    for sc in getattr(t, SC).product():
        s = 0.0
        for p in sc.TDCIDEMap():
            s += float(sc.Charge(int(p.first)))
        if s > QMIN:
            truth[int(sc.Channel())] = s
    got = {}
    br = "recob::Wires_simtpc2d_%s_ReDetSim." % tag
    for w in getattr(t, br).product():
        got[int(w.Channel())] = float(
            np.abs(np.asarray(w.Signal(), dtype=np.float64)).sum()) * SCALE
    f.Close()
    return truth, got


def main():
    evts = sorted(glob.glob(os.path.join(C, "mc", "*", "sp.root")))
    print("MC leg: %d events with sp.root\n" % len(evts))
    hdr = "%-11s %-5s %-6s %-11s %-11s %-9s %-9s"
    print(hdr % ("event", "plane", "nchan", "gauss/T", "dnnsp/T", "med g/T", "frac<0.5"))
    agg = {}
    for p in evts:
        lbl = os.path.basename(os.path.dirname(p))
        truth, g = read(p, "gauss")
        _, d = read(p, "dnnsp")
        if truth is None:
            print("%-11s  (unreadable)" % lbl); continue
        for pl in ("u", "v", "w"):
            chs = [c for c in truth if plane_of(c) == pl]
            if not chs:
                continue
            T = sum(truth[c] for c in chs)
            G = sum(g.get(c, 0.0) for c in chs)
            Dn = sum(d.get(c, 0.0) for c in chs)
            r = np.array([g.get(c, 0.0) / truth[c] for c in chs])
            print(hdr % (lbl, pl.upper(), len(chs), "%.4f" % (G / T),
                         "%.4f" % (Dn / T), "%.3f" % np.median(r),
                         "%.3f" % (r < 0.5).mean()))
            a = agg.setdefault(pl, [0.0, 0.0, 0.0, 0, 0])
            a[0] += T; a[1] += G; a[2] += Dn
            a[3] += len(chs); a[4] += int((r < 0.5).sum())
    print("\n=== campaign totals ===")
    print("%-6s %-8s %-11s %-11s %-14s" % ("plane", "nchan", "gauss/T", "dnnsp/T", "chans<0.5"))
    for pl in ("u", "v", "w"):
        if pl not in agg:
            continue
        T, G, Dn, n, bad = agg[pl]
        print("%-6s %-8d %-11.4f %-11.4f %d (%.2f%%)"
              % (pl.upper(), n, G / T, Dn / T, bad, 100.0 * bad / n))


main()
