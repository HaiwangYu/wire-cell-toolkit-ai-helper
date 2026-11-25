#!/usr/bin/env python3
"""Compare the simtpc2d products of detsim files (issue 46 RNG study).

  rngcmp.py groups <file>... [--entry N]
      Per product (RawDigits, recob::Wire dnnsp/gauss/wiener, SimChannels):
      group the files by bit-identical product content and, for each file,
      count the channels that differ from the first file (per TPC/plane).

  rngcmp.py noise <fileA>[@entry] <fileB>[@entry] [--margin 0]
      Raw-digit noise comparison of two events (e.g. YZ off vs on, or two
      different events).  Channels are "quiet" if neither event has SimChannel
      charge on any channel within +-near (20) channels of the same plane
      (induction reaches neighbouring wires), "signal" otherwise.  Reports for
      quiet channels how many are bit-identical and the rms of A-B; for signal
      channels the median fraction of ticks where A != B, and the number of
      channels whose A-B is zero outside the SimChannel tick range of either
      event (+- margin ticks, default 500: induction and electronics tails).

Run in the sbndcode environment (PyROOT).  No LD_PRELOAD needed.
"""
import argparse
import hashlib
import sys

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("mode", choices=["groups", "noise"])
ap.add_argument("files", nargs="+")
ap.add_argument("--entry", type=int, default=0)
ap.add_argument("--process", default="DetSim")
ap.add_argument("--margin", type=int, default=500)
ap.add_argument("--near", type=int, default=20,
                help="quiet = no SimChannel charge within +-near channels of the same plane")
ap.add_argument("--tick-offset", type=int, default=None,
                help="raw tick = SimChannel TDC + offset (default: fit from data)")
a = ap.parse_args()

import ROOT  # noqa: E402
ROOT.gROOT.SetBatch(True)

NCH_TPC, NU, NV = 5638, 1984, 1984
PL, TPC = ["U", "V", "Y"], ["E", "W"]


def tpc_plane(ch):
    tpc, local = divmod(ch, NCH_TPC)
    return tpc, (0 if local < NU else (1 if local < NU + NV else 2))


def branches(tree):
    out = {}
    for b in tree.GetListOfBranches():
        n = b.GetName()
        if not n.endswith(f"_{a.process}.") or "_simtpc2d_" not in n:
            continue
        cls = n.split("_")[0]
        inst = n.split("_")[2]
        if cls in ("raw::RawDigits", "recob::Wires", "sim::SimChannels"):
            out[f"{cls.split('::')[1]}:{inst}"] = n
    return out


def open_entry(spec):
    fn, _, ent = spec.partition("@")
    f = ROOT.TFile.Open(fn)
    t = f.Get("Events")
    t.GetEntry(int(ent) if ent else a.entry)
    aux = t.EventAuxiliary
    return f, t, (aux.run(), aux.subRun(), aux.event())


def raw_arrays(t, b):
    out = {}
    for rd in getattr(t, b).product():
        out[rd.Channel()] = np.array(rd.ADCs(), dtype=np.int16)
    return out


def wire_arrays(t, b):
    out = {}
    for w in getattr(t, b).product():
        parts = []
        for r in w.SignalROI().get_ranges():
            parts.append(np.array([r.begin_index()], dtype=np.float64).view(np.uint8))
            parts.append(np.array(r.data(), dtype=np.float32).view(np.uint8))
        out[w.Channel()] = np.concatenate(parts) if parts else np.zeros(0, np.uint8)
    return out


def simch(t, b):
    """channel -> (sum electrons, sorted array of TDCs with charge, digest)"""
    out = {}
    for sc in getattr(t, b).product():
        tdcs, h, ne = [], hashlib.sha1(), 0.0
        for tdc_ides in sc.TDCIDEMap():
            tdc = tdc_ides.first
            q = sum(i.numElectrons for i in tdc_ides.second)
            if q > 0:
                tdcs.append(tdc)
            ne += q
            h.update(np.array([tdc, q], dtype=np.float64).tobytes())
        out[sc.Channel()] = (ne, np.array(tdcs, dtype=np.int64), h.hexdigest())
    return out


def digests(t, brs):
    res = {}
    for key, b in sorted(brs.items()):
        if key.startswith("RawDigits"):
            arr = raw_arrays(t, b)
            res[key] = {ch: hashlib.sha1(v.tobytes()).hexdigest() for ch, v in arr.items()}
        elif key.startswith("Wires"):
            arr = wire_arrays(t, b)
            res[key] = {ch: hashlib.sha1(v.tobytes()).hexdigest() for ch, v in arr.items()}
        elif key.startswith("SimChannels"):
            res[key] = {ch: v[2] for ch, v in simch(t, b).items()}
    return res


def plane_counts(chs):
    c = {}
    for ch in chs:
        tpc, pl = tpc_plane(ch)
        k = TPC[tpc] + PL[pl]
        c[k] = c.get(k, 0) + 1
    return " ".join(f"{k}:{v}" for k, v in sorted(c.items())) or "-"


if a.mode == "groups":
    allres, ids = [], []
    for fn in a.files:
        f, t, eid = open_entry(fn)
        allres.append(digests(t, branches(t)))
        ids.append(eid)
        f.Close()
    print("events:", ids)
    ref = allres[0]
    for key in sorted(ref):
        prod_digest = []
        for r in allres:
            d = r.get(key, {})
            h = hashlib.sha1()
            for ch in sorted(d):
                h.update(f"{ch}:{d[ch]};".encode())
            prod_digest.append(h.hexdigest()[:12])
        groups = {}
        for i, pd in enumerate(prod_digest):
            groups.setdefault(pd, []).append(i)
        print(f"\n{key}: {len(ref[key])} channels; {len(groups)} distinct product(s): "
              + "  ".join(f"{pd}={[i + 1 for i in v]}" for pd, v in groups.items()))
        for i, r in enumerate(allres[1:], start=2):
            d = r.get(key, {})
            chs = set(ref[key]) | set(d)
            diff = [ch for ch in chs if ref[key].get(ch) != d.get(ch)]
            print(f"   file {i} vs 1: {len(diff)} channels differ  [{plane_counts(diff)}]")
    sys.exit(0)

# noise mode
fa, ta, ida = open_entry(a.files[0])
fb, tb, idb = open_entry(a.files[1])
ba, bb = branches(ta), branches(tb)
rawkey = [k for k in ba if k.startswith("RawDigits")]
if not rawkey:
    raise SystemExit("no RawDigits in " + a.files[0])
rawkey = rawkey[0]
RA, RB = raw_arrays(ta, ba[rawkey]), raw_arrays(tb, bb[rawkey])
SA, SB = simch(ta, ba["SimChannels:simpleSC"]), simch(tb, bb["SimChannels:simpleSC"])
print(f"A = {a.files[0]} event {ida}\nB = {a.files[1]} event {idb}\nproduct {rawkey}, {len(RA)} channels")

# Tick offset between SimChannel TDC and raw tick: the argmax of |A - median| on
# the channels with the most charge vs their charge-weighted TDC.
if a.tick_offset is None:
    offs = []
    for ch, (ne, tdcs, _) in sorted(SA.items(), key=lambda kv: -kv[1][0])[:200]:
        tpc, pl = tpc_plane(ch)
        if pl != 2 or len(tdcs) == 0:
            continue
        w = RA[ch].astype(float) - np.median(RA[ch])
        offs.append(int(np.argmax(w)) - int(np.median(tdcs)))
    tick_offset = int(np.median(offs)) if offs else 0
else:
    tick_offset = a.tick_offset
print(f"tick offset (raw tick - SimChannel TDC): {tick_offset}")

sigch = {ch for S in (SA, SB) for ch, v in S.items() if v[0] > 0}
near = set()
for ch in sigch:
    tpc, pl = tpc_plane(ch)
    for c in range(ch - a.near, ch + a.near + 1):
        if 0 <= c < 2 * NCH_TPC and tpc_plane(c) == (tpc, pl):
            near.add(c)
rows = {}
for ch in sorted(RA):
    da = RA[ch].astype(np.int32) - RB[ch].astype(np.int32)
    tpc, pl = tpc_plane(ch)
    k = TPC[tpc] + PL[pl]
    sig = ch in near
    r = rows.setdefault(k, {"quiet": 0, "quiet_same": 0, "quiet_ss": 0.0, "quiet_n": 0,
                            "sig": 0, "sig_nz_frac": [], "sig_clean": 0})
    if not sig:
        r["quiet"] += 1
        r["quiet_same"] += int(not da.any())
        r["quiet_ss"] += float((da.astype(float) ** 2).sum())
        r["quiet_n"] += da.size
    else:
        r["sig"] += 1
        r["sig_nz_frac"].append(float(np.count_nonzero(da)) / da.size)
        tdcs = np.concatenate([S[ch][1] for S in (SA, SB) if ch in S and len(S[ch][1])] or [np.zeros(0, np.int64)])
        mask = np.ones(da.size, bool)
        if len(tdcs):
            lo = max(int(tdcs.min()) + tick_offset - a.margin, 0)
            hi = min(int(tdcs.max()) + tick_offset + a.margin + 1, da.size)
            if lo < hi:
                mask[lo:hi] = False
        r["sig_clean"] += int(not da[mask].any())

print(f"\n| plane | quiet ch | quiet bit-identical | rms(A-B) quiet [ADC] | near-signal ch | median frac ticks A!=B | of which A-B = 0 outside SimChannel ticks +-{a.margin} |")
print("|---|---|---|---|---|---|---|")
for k in sorted(rows):
    r = rows[k]
    rms = (r["quiet_ss"] / r["quiet_n"]) ** 0.5 if r["quiet_n"] else float("nan")
    med = np.median(r["sig_nz_frac"]) if r["sig_nz_frac"] else float("nan")
    print(f"| {k} | {r['quiet']} | {r['quiet_same']} | {rms:.3f} | {r['sig']} | {med:.4f} | {r['sig_clean']} |")
