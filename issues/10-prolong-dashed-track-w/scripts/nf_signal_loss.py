#!/usr/bin/env python3
"""Test 2 — how much TRUE signal does the noise filter remove?

Compares the Magnify `orig` (digitised ADC) and `raw` (after OmnibusNoiseFilter)
waveforms, but only over (channel, tick) regions where the SimChannel truth says
ionisation charge actually arrived.  This avoids the trap of a plain
|raw|/|orig| ratio, which conflates legitimate noise reduction with signal loss.

Truth must come from the SAME job as the waveforms (each re-run has its own
drift/noise realisation), i.e. the magnify job's own art output.

Usage (inside the SL7 container, sbndcode env):
    python3 nf_signal_loss.py [magnify.root] [magnifyjob.root]
"""
import sys
import numpy as np
import ROOT

MAG = (sys.argv[1] if len(sys.argv) > 1 else
       "/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/"
       "10-prolong-dashed-track-w/data/magnify-270-6-46.root")
ART = (sys.argv[2] if len(sys.argv) > 2 else
       "/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/"
       "10-prolong-dashed-track-w/data/evt-270-6-46_magnifyjob.root")
SC_BRANCH = "sim::SimChannels_simtpc2d_simpleSC_ReDetSim."
NOMBASE = {"u": 2001.0, "v": 2001.0, "w": 650.0}
NFREQS, MAXPOWER = 4, 6000.0        # Diagnostics::Partial magic numbers
PAD = 10                            # dilate the truth signal region, ticks
QTHRESH = 100.0                     # electrons per (channel, tick) to count as signal

sys.path.insert(0, "/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/"
                   "issues/10-prolong-dashed-track-w/scripts")
import os
os.environ["MAGNIFY_NO_SERVE"] = "1"
import magnify_viewer as mv


def read_truth(art_path, nticks):
    """channel -> array(nticks) of true electrons, indexed by RAW TDC."""
    f = ROOT.TFile.Open(art_path)
    t = f.Get("Events")
    t.GetEntry(0)
    scs = getattr(t, SC_BRANCH).product()
    out = {}
    for sc in scs:
        ch = int(sc.Channel())
        m = sc.TDCIDEMap()
        if not m.size():
            continue
        a = np.zeros(nticks + 4096, dtype=np.float32)   # room for the tdc offset
        for pair in m:
            tdc = int(pair.first)
            if 0 <= tdc < a.size:
                a[tdc] = float(sc.Charge(tdc))
        out[ch] = a
    return out


def dilate(mask, pad):
    if pad <= 0:
        return mask
    out = mask.copy()
    for k in range(1, pad + 1):
        out[k:] |= mask[:-k]
        out[:-k] |= mask[k:]
    return out


def main():
    m = mv.MagFile(MAG)
    nt = m.array("w", "orig", 1)[0].shape[0]
    truth = read_truth(ART, nt)
    print("SimChannel truth: %d channels with IDEs" % len(truth))

    # ---- calibrate the TDC -> tick offset by maximising truth/|orig| overlap ----
    best = (None, -1)
    probe = []
    for apa in (0, 1):
        arr, ch0, _ = m.array("w", "orig", apa)
        ped = np.median(arr, axis=0)
        strength = np.abs(arr - ped).sum(axis=0)
        for j in np.argsort(strength)[-25:]:
            ch = ch0 + j
            if ch in truth:
                probe.append((np.abs(arr[:, j] - ped[j]), truth[ch]))
    for off in range(-3200, -2700, 10):
        tot = 0.0
        for sig, tr in probe:
            idx = np.arange(nt) - off                 # tick -> tdc
            ok = (idx >= 0) & (idx < tr.size)
            tot += float((sig[ok] * tr[idx[ok]]).sum())
        if tot > best[1]:
            best = (off, tot)
    OFF = best[0]
    print("best TDC->tick offset: tick = tdc + %d  (overlap metric %.4g)" % (OFF, best[1]))

    # ---- per-channel truth-restricted comparison ----
    rows = []
    for apa in (0, 1):
        ao, ch0, _ = m.array("w", "orig", apa)
        ar, _, _ = m.array("w", "raw", apa)
        ped = np.median(ao, axis=0)
        sig_fft = ao - NOMBASE["w"]
        mag = np.abs(np.fft.rfft(sig_fft, axis=0))[1:NFREQS + 2, :]
        partial = np.all(mag[0:1, :] > mag[1:, :], axis=0) & (mag.mean(axis=0) > MAXPOWER)
        tick = np.arange(nt)
        for j in range(ao.shape[1]):
            ch = ch0 + j
            tr = truth.get(ch)
            if tr is None:
                continue
            idx = tick - OFF
            ok = (idx >= 0) & (idx < tr.size)
            q = np.zeros(nt, dtype=np.float32)
            q[ok] = tr[idx[ok]]
            mask = dilate(q > QTHRESH, PAD)
            if mask.sum() < 5:
                continue
            o = np.abs(ao[:, j] - ped[j])[mask].sum()
            r = np.abs(ar[:, j])[mask].sum()
            rows.append((ch, apa, bool(partial[j]), float(q.sum()),
                         int(mask.sum()), float(o), float(r), float(r / max(o, 1e-9))))
    rows.sort(key=lambda x: x[7])
    part = [x for x in rows if x[2]]
    npart = [x for x in rows if not x[2]]
    print("\nW-plane channels with truth signal: %d  (is_partial: %d)"
          % (len(rows), len(part)))

    def stats(label, rs):
        if not rs:
            print("  %-14s (none)" % label); return
        rat = np.array([x[7] for x in rs])
        print("  %-14s n=%5d   median raw/orig = %.4f   mean = %.4f   min = %.4f"
              % (label, len(rs), np.median(rat), rat.mean(), rat.min()))
    print("\n=== |raw|/|orig| restricted to TRUE signal regions ===")
    stats("is_partial", part)
    stats("not partial", npart)

    print("\n=== the is_partial channels ===")
    print("  %-7s %-4s %-12s %-7s %-11s %-11s %s"
          % ("ch", "apa", "truth e-", "nticks", "|orig|", "|raw|", "raw/orig"))
    for ch, apa, p, q, nm, o, r, rr in sorted(part):
        print("  %-7d %-4d %-12.4g %-7d %-11.4g %-11.4g %.4f" % (ch, apa, q, nm, o, r, rr))

    print("\n=== worst 12 non-partial channels (for contrast) ===")
    for ch, apa, p, q, nm, o, r, rr in npart[:12]:
        print("  ch %-6d apa%d truth=%-11.4g nticks=%-6d raw/orig=%.4f" % (ch, apa, q, nm, rr))

    tot_o = sum(x[5] for x in rows); tot_r = sum(x[6] for x in rows)
    tot_op = sum(x[5] for x in part); tot_rp = sum(x[6] for x in part)
    print("\n=== integrated over all W channels with truth signal ===")
    print("  all channels : |orig|=%.4g  |raw|=%.4g   -> %.2f%% retained" % (tot_o, tot_r, 100*tot_r/tot_o))
    if tot_op:
        print("  is_partial   : |orig|=%.4g  |raw|=%.4g   -> %.2f%% retained" % (tot_op, tot_rp, 100*tot_rp/tot_op))
        print("  charge lost on is_partial channels = %.4g ADC-ticks (%.2f%% of ALL W true-signal |orig|)"
              % (tot_op - tot_rp, 100*(tot_op - tot_rp)/tot_o))


main()
