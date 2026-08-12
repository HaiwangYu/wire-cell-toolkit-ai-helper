#!/usr/bin/env python3
"""Campaign validation, DATA leg: our re-run dnnsp vs PRODUCTION dnnsp.

Data has no SimChannel truth, so the reference is the production reco1 output for
the same events -- which was produced with the pre-fix configuration.  Per plane
we compare total |dnnsp| charge, and separately on the channels the OLD IS_RC
test would have flagged (recomputed from each event's magnify `orig`), where the
fixes are expected to *recover* charge.
"""
import glob, os, sys
import numpy as np
import ROOT

C = ("/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/"
     "10-prolong-dashed-track-w/data/validation-20260812")
PROD = ("/pnfs/sbn/data_add/sbn_nd/poms_production/data/MCP2025C/v10_14_02/"
        "Fall25-Run1_BNB_Dev_bnblight/reco1/bnblight/fe/"
        "data_filtered_decoded_reco1-fe6033f3-07a0-4971-cea5-16ce59269fba.root")
os.environ["MAGNIFY_NO_SERVE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import magnify_viewer as mv

NFREQS, MAXPOWER = 4, 6000.0
BASE = {"u": 2001.0, "v": 2001.0, "w": 650.0}


def plane_of(ch):
    c = ch % 5638
    return "u" if c < 1984 else ("v" if c < 3968 else "w")


def wires(tree, branch):
    out = {}
    for w in getattr(tree, branch).product():
        out[int(w.Channel())] = float(np.abs(np.asarray(w.Signal(), dtype=np.float64)).sum())
    return out


def flagged_channels(magp):
    m = mv.MagFile(magp)
    hits = []
    for pl in ("u", "v", "w"):
        for apa in (0, 1):
            a, ch0, _ = m.array(pl, "orig", apa)
            if a is None:
                continue
            mag = np.abs(np.fft.rfft(a.astype(np.float64) - BASE[pl], axis=0))[1:NFREQS + 2, :]
            hit = np.all(mag[0:1, :] > mag[1:, :], axis=0) & (mag.mean(axis=0) > MAXPOWER)
            hits += (ch0 + np.where(hit)[0]).tolist()
    return set(hits)


def main():
    fp = ROOT.TFile.Open(PROD)
    tp = fp.Get("Events")
    prod_idx = {}
    for i in range(tp.GetEntries()):
        tp.GetEntry(i)
        a = tp.EventAuxiliary
        prod_idx[(a.run(), a.subRun(), a.event())] = i

    print("%-16s %-6s %-13s %-13s %-8s | flagged chans %s"
          % ("event", "plane", "ours", "production", "ratio", "ours/prod"))
    agg = {}
    for spp in sorted(glob.glob(os.path.join(C, "data", "*", "sp.root"))):
        d = os.path.dirname(spp); lbl = os.path.basename(d)
        r, sr, e = (int(x) for x in lbl.split("-"))
        if (r, sr, e) not in prod_idx:
            print("%-16s  not in production file" % lbl); continue
        fo = ROOT.TFile.Open(spp); to = fo.Get("Events"); to.GetEntry(0)
        ours = wires(to, "recob::Wires_sptpc2d_dnnsp_WCLS.")
        tp.GetEntry(prod_idx[(r, sr, e)])
        prod = wires(tp, "recob::Wires_sptpc2d_dnnsp_Reco1.")
        flag = flagged_channels(os.path.join(d, "magnify.root")) if os.path.exists(
            os.path.join(d, "magnify.root")) else set()
        for pl in ("u", "v", "w"):
            chs = [c for c in set(ours) | set(prod) if plane_of(c) == pl]
            O = sum(ours.get(c, 0.0) for c in chs)
            P = sum(prod.get(c, 0.0) for c in chs)
            fo_ = [c for c in chs if c in flag]
            OF = sum(ours.get(c, 0.0) for c in fo_)
            PF = sum(prod.get(c, 0.0) for c in fo_)
            fr = ("%d ch, %.2fx" % (len(fo_), OF / PF)) if fo_ and PF > 0 else ("%d ch" % len(fo_))
            print("%-16s %-6s %-13.5g %-13.5g %-8.4f | %s" % (lbl, pl.upper(), O, P, O / P if P else float("nan"), fr))
            a = agg.setdefault(pl, [0.0, 0.0, 0.0, 0.0, 0])
            a[0] += O; a[1] += P; a[2] += OF; a[3] += PF; a[4] += len(fo_)
        fo.Close()
    print("\n=== data leg totals (ours / production) ===")
    for pl in ("u", "v", "w"):
        if pl not in agg:
            continue
        O, P, OF, PF, n = agg[pl]
        extra = ("   on the %d old-flagged channels: %.3fx" % (n, OF / PF)) if n and PF > 0 else ""
        print("%-3s all channels: %.4f%s" % (pl.upper(), O / P, extra))


main()
