#!/usr/bin/env python3
"""Test 3 — do the dashed clusters' gaps land on the NF-damaged channels?

Maps the BEE `clustering-global` 3D points of the dashed candidate clusters
(cid 5, cid 11) onto W-plane channel numbers using the real SBND wire geometry,
then asks whether the channel-space gaps coincide with

  * the `is_partial` channels (Diagnostics::Partial -> adaptive-baseline damage),
  * the identically-zero (known dead) channels, or
  * neither (i.e. the loss must be downstream, in ROI/DNNROI).

Usage (SL7 container, sbndcode env):
    python3 nf_dash_to_channels.py
"""
import bz2, json, os, sys
import numpy as np

WIRES = ("/cvmfs/sbnd.opensciencegrid.org/products/sbnd/sbnd_data/"
         "v01_42_00/WireCell/sbnd-wires-geometry-v0206.json.bz2")
D = ("/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/"
     "10-prolong-dashed-track-w")
BEE = D + "/data/bee-clustering-global-evt29.json"
MAG = D + "/data/magnify-270-6-46.root"
CIDS = (5, 11)
W_LAYER = 2                      # collection plane index within a face

os.environ["MAGNIFY_NO_SERVE"] = "1"
sys.path.insert(0, D + "/scripts")
import magnify_viewer as mv


def load_wplanes():
    """-> list of dicts: {anode, xref, chans[], zs[]} for each W plane."""
    st = json.load(bz2.open(WIRES))["Store"]
    pts = [p["Point"] for p in st["points"]]
    wires = [w["Wire"] for w in st["wires"]]
    planes = [p["Plane"] for p in st["planes"]]
    faces = [f["Face"] for f in st["faces"]]
    anodes = [a["Anode"] for a in st["anodes"]]
    out = []
    for a in anodes:
        for fi in a["faces"]:
            face = faces[fi]
            for pi_idx, pi in enumerate(face["planes"]):
                pl = planes[pi]
                if pi_idx != W_LAYER:
                    continue
                ch, zs, xs = [], [], []
                for wi in pl["wires"]:
                    w = wires[wi]
                    t, h = pts[w["tail"]], pts[w["head"]]
                    ch.append(w["channel"])
                    zs.append(0.5 * (t["z"] + h["z"]))
                    xs.append(0.5 * (t["x"] + h["x"]))
                o = np.argsort(zs)
                out.append(dict(anode=a["ident"],
                                xref=float(np.mean(xs)) / 10.0,      # mm -> cm
                                chans=np.array(ch)[o],
                                zs=np.array(zs)[o] / 10.0))          # mm -> cm
    return out


def zero_channels(m, apa):
    ar, ch0, _ = m.array("w", "raw", apa)
    return set((ch0 + np.where(np.abs(ar).max(axis=0) == 0)[0]).tolist())


def partial_channels(m, apa, nfreqs=4, maxpower=6000.0, nombase=650.0):
    ao, ch0, _ = m.array("w", "orig", apa)
    mag = np.abs(np.fft.rfft(ao - nombase, axis=0))[1:nfreqs + 2, :]
    p = np.all(mag[0:1, :] > mag[1:, :], axis=0) & (mag.mean(axis=0) > maxpower)
    return set((ch0 + np.where(p)[0]).tolist())


def main():
    wp = load_wplanes()
    print("W planes found: " + ", ".join(
        "anode%d x=%.1fcm ch %d..%d z %.1f..%.1f cm"
        % (p["anode"], p["xref"], p["chans"].min(), p["chans"].max(),
           p["zs"].min(), p["zs"].max()) for p in wp))

    bee = json.load(open(BEE))
    x = np.array(bee["x"]); y = np.array(bee["y"]); z = np.array(bee["z"])
    cid = np.array(bee["cluster_id"])

    m = mv.MagFile(MAG)
    dead = {a: zero_channels(m, a) for a in (0, 1)}
    part = {a: partial_channels(m, a) for a in (0, 1)}
    print("dead (raw==0) channels: apa0=%d apa1=%d" % (len(dead[0]), len(dead[1])))
    print("is_partial channels:    apa0=%s apa1=%s" % (sorted(part[0]), sorted(part[1])))

    for c in CIDS:
        sel = cid == c
        if not sel.any():
            print("\ncid %d: not present" % c); continue
        xs, zs = x[sel], z[sel]
        # pick the W plane whose drift volume this cluster sits in (nearest xref)
        pl = min(wp, key=lambda p: abs(np.median(xs) - p["xref"]))
        apa = pl["anode"]
        # z -> nearest W wire channel
        j = np.clip(np.searchsorted(pl["zs"], zs), 1, len(pl["zs"]) - 1)
        j = np.where(np.abs(pl["zs"][j] - zs) < np.abs(pl["zs"][j - 1] - zs), j, j - 1)
        chans = pl["chans"][j]
        occ = np.unique(chans)
        lo, hi = occ.min(), occ.max()
        full = np.arange(lo, hi + 1)
        missing = np.setdiff1d(full, occ)
        print("\n=== cid %d  (%d points, x median %.1f cm -> anode %d) ===" %
              (c, sel.sum(), np.median(xs), apa))
        print("  z span %.1f..%.1f cm  ->  W channels %d..%d  (%d of %d occupied)"
              % (zs.min(), zs.max(), lo, hi, len(occ), len(full)))
        print("  channel-space gaps: %d missing channels" % len(missing))
        if len(missing):
            # group missing channels into runs
            runs, start = [], missing[0]
            for a, b in zip(missing, missing[1:]):
                if b != a + 1:
                    runs.append((start, a)); start = b
            runs.append((start, missing[-1]))
            print("  gap runs (%d): %s%s" % (len(runs),
                  ", ".join("%d-%d" % r if r[0] != r[1] else "%d" % r[0] for r in runs[:12]),
                  " ..." if len(runs) > 12 else ""))
            ms = set(missing.tolist())
            print("  of the %d missing channels:" % len(ms))
            print("     %4d are DEAD (raw==0)      -> %s" %
                  (len(ms & dead[apa]), sorted(ms & dead[apa])[:10]))
            print("     %4d are is_partial         -> %s" %
                  (len(ms & part[apa]), sorted(ms & part[apa])))
            other = ms - dead[apa] - part[apa]
            print("     %4d are NEITHER            (loss must be downstream/ROI)" % len(other))
        # and the reverse: are the damaged channels inside the cluster's span?
        print("  damaged channels within this cluster's channel span:")
        print("     dead:       %s" % sorted(cset for cset in dead[apa] if lo <= cset <= hi)[:12])
        print("     is_partial: %s" % sorted(cset for cset in part[apa] if lo <= cset <= hi))


main()
