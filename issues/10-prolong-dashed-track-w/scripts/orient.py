#!/usr/bin/env python3
"""Orientation helpers for issue 10 (dashed W track, run 270/6/46).

1) decode SBND channel -> (APA, plane, wire-in-plane)
2) scan the BEE clustering-global JSON for clusters with 'dashed' structure
   (large gaps along the cluster's principal axis), to aim the waveform viewer.

Usage:  python3 orient.py [bee_clustering_global.json]
"""
import json, sys
import numpy as np

NCH_U, NCH_V, NCH_W = 1984, 1984, 1670
NCH_APA = NCH_U + NCH_V + NCH_W          # 5638


def decode(ch):
    apa, off = divmod(int(ch), NCH_APA)
    if off < NCH_U:
        return apa, "u", off
    if off < NCH_U + NCH_V:
        return apa, "v", off - NCH_U
    return apa, "w", off - NCH_U - NCH_V


def gap_scan(path, min_pts=50):
    """Per-cluster gap structure along the principal axis (dashed => big gaps)."""
    d = json.load(open(path))
    x = np.array(d["x"]); y = np.array(d["y"]); z = np.array(d["z"])
    cid = np.array(d["cluster_id"])
    rows = []
    for c in sorted(set(cid.tolist())):
        m = cid == c
        n = int(m.sum())
        if n < min_pts:
            continue
        P = np.vstack([x[m], y[m], z[m]]).T
        P0 = P - P.mean(0)
        # principal axis
        u = np.linalg.svd(P0, full_matrices=False)[2][0]
        t = np.sort(P0 @ u)
        L = t[-1] - t[0]
        gaps = np.diff(t)
        rows.append(dict(cid=int(c), npts=n, length_cm=float(L),
                         max_gap_cm=float(gaps.max()) if len(gaps) else 0.0,
                         ngap_gt1cm=int((gaps > 1.0).sum()),
                         ngap_gt3cm=int((gaps > 3.0).sum()),
                         gapfrac=float(gaps[gaps > 1.0].sum() / L) if L > 0 else 0.0))
    rows.sort(key=lambda r: -r["gapfrac"])
    return rows


if __name__ == "__main__":
    print("== channel decode of the viewer's top |A-B| channels ==")
    for ch in (9677, 10628, 9664, 4723):
        apa, pl, w = decode(ch)
        print("   ch %5d -> APA%d  %s-plane  wire %4d" % (ch, apa, pl, w))
    if len(sys.argv) > 1:
        print("\n== BEE clustering-global gap scan (most 'dashed' first) ==")
        print("   %-6s %-7s %-10s %-11s %-9s %-9s %s"
              % ("cid", "npts", "len[cm]", "maxgap[cm]", "n>1cm", "n>3cm", "gapfrac"))
        for r in gap_scan(sys.argv[1])[:12]:
            print("   %-6d %-7d %-10.1f %-11.1f %-9d %-9d %.3f"
                  % (r["cid"], r["npts"], r["length_cm"], r["max_gap_cm"],
                     r["ngap_gt1cm"], r["ngap_gt3cm"], r["gapfrac"]))
