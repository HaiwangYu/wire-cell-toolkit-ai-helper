#!/usr/bin/env python3
"""How many channels per event did the OLD code damage, and where are they now?

Re-applies Diagnostics::Partial (nfreqs=4, maxpower=6000 -- the magic numbers the
un-patched Microboone.cxx hard-coded) to the `orig` waveforms in each event's
magnify dump.  Any channel it flags is one the old NF would have run through
RawAdapativeBaselineAlg, deleting most of a prolonged pulse, AND denied the RC-RC
deconvolution.  For each such channel we then report what the FIXED chain
reconstructs against SimChannel truth.

This gives the before/after per event without re-running the pre-fix chain: the
"before" is the flag itself (a flagged W channel lost 43-90 % of its charge, see
the issue doc), the "after" is the measured ratio.
"""
import glob, os, sys
import numpy as np
import ROOT

C = sys.argv[1] if len(sys.argv) > 1 else (
    "/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/"
    "10-prolong-dashed-track-w/data/validation-20260812")
os.environ["MAGNIFY_NO_SERVE"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import magnify_viewer as mv

SC = "sim::SimChannels_simtpc2d_simpleSC_ReDetSim."
NFREQS, MAXPOWER = 4, 6000.0
BASE = {"u": 2001.0, "v": 2001.0, "w": 650.0}
SCALE = 50.0


def partial_channels(m, pl, apa):
    a, ch0, _ = m.array(pl, "orig", apa)
    if a is None:
        return []
    mag = np.abs(np.fft.rfft(a.astype(np.float64) - BASE[pl], axis=0))[1:NFREQS + 2, :]
    hit = np.all(mag[0:1, :] > mag[1:, :], axis=0) & (mag.mean(axis=0) > MAXPOWER)
    return (ch0 + np.where(hit)[0]).tolist()


def main():
    tot_flag, tot_ok, rows = 0, 0, []
    for spp in sorted(glob.glob(os.path.join(C, "mc", "*", "sp.root"))):
        d = os.path.dirname(spp); lbl = os.path.basename(d)
        magp = os.path.join(d, "magnify.root")
        if not os.path.exists(magp):
            continue
        m = mv.MagFile(magp)
        flagged = []
        for pl in ("u", "v", "w"):
            for apa in (0, 1):
                flagged += [(pl, c) for c in partial_channels(m, pl, apa)]
        f = ROOT.TFile.Open(spp); t = f.Get("Events"); t.GetEntry(0)
        truth = {}
        for sc in getattr(t, SC).product():
            s = 0.0
            for p in sc.TDCIDEMap():
                s += float(sc.Charge(int(p.first)))
            truth[int(sc.Channel())] = s
        got = {}
        for w in getattr(t, "recob::Wires_simtpc2d_gauss_ReDetSim.").product():
            got[int(w.Channel())] = float(
                np.abs(np.asarray(w.Signal(), dtype=np.float64)).sum()) * SCALE
        f.Close()
        rat = []
        for pl, c in flagged:
            T = truth.get(c, 0.0)
            if T > 5e4:
                rat.append(got.get(c, 0.0) / T)
        n_ok = sum(1 for r in rat if r > 0.8)
        tot_flag += len(rat); tot_ok += n_ok
        rows.append((lbl, len(flagged), len(rat), n_ok,
                     min(rat) if rat else float("nan"),
                     float(np.median(rat)) if rat else float("nan")))
    print("%-11s %-9s %-11s %-11s %-9s %-9s"
          % ("event", "flagged", "w/ truth", "ratio>0.8", "min", "median"))
    for r in rows:
        print("%-11s %-9d %-11d %-11d %-9.3f %-9.3f" % r)
    if tot_flag:
        print("\nTOTAL: %d flagged channels carrying real charge; %d (%.0f%%) now "
              "reconstruct >0.8 of truth" % (tot_flag, tot_ok, 100.0 * tot_ok / tot_flag))


main()
