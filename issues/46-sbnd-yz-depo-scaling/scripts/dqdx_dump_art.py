#!/usr/bin/env python3
"""Dump what the truth-track SP dQ/dx needs from an SBND art file into one
compressed npz per event (ai-helper issue 46).

Per event, <outdir>/evt_<run>_<subrun>_<event>.npz holds:
  wire_<inst>_{ch,start,len,val}  recob::Wire ROIs (flattened), one set per --wires label
  bad                             simtpc2d:badchannels (channel list)
  mcp_{id,pdg,mother,proc,e0,n}   MCParticles (largeant), proc 1 = "primary"
  mcp_all_{id,mother,pdg}         every MCParticle (for the family of a track)
  trj_{x,y,z,t,e}                 their trajectory points, concatenated (mcp_n per particle)
  sc_{ch,tdc,tid,ne,x,y,z}        SimChannel IDEs summed per (channel, tdc, |trackID|);
                                  x,y,z electron-weighted
Charged particles only (|pdg| in 11, 13, 211, 321, 2212) with >= 2 points and
>= --min-len cm of trajectory are stored.

Usage (SL7 + sbndcode PyROOT; e.g. after `source yz-sim-kit/setup-yz-env.sh`):
  dqdx_dump_art.py <art.root> <outdir> [--wires simtpc2d:dnnsp,simtpc2d:gauss]
                   [--process DetSim] [--mcp largeant] [--min-len 10] [--no-simch]
"""
import argparse
import os

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("art"); ap.add_argument("outdir")
ap.add_argument("--wires", default="simtpc2d:dnnsp,simtpc2d:gauss")
ap.add_argument("--process", default="DetSim")
ap.add_argument("--simch", default="simtpc2d:simpleSC")
ap.add_argument("--bad", default="simtpc2d:badchannels")
ap.add_argument("--mcp", default="largeant")
ap.add_argument("--mcp-process", default="G4")
ap.add_argument("--min-len", type=float, default=10.0)
ap.add_argument("--no-simch", action="store_true")
a = ap.parse_args()
os.makedirs(a.outdir, exist_ok=True)

import ROOT  # noqa: E402
ROOT.gROOT.SetBatch(True)
ROOT.gInterpreter.Declare(r'''
#include "lardataobj/RecoBase/Wire.h"
#include "lardataobj/Simulation/SimChannel.h"
#include "nusimdata/SimulationBase/MCParticle.h"
#include <map>
#include <tuple>
#include <cmath>
namespace dq {
struct Wires { std::vector<int> ch, start, len; std::vector<float> val; };
Wires wires(const std::vector<recob::Wire>& ws) {
  Wires o;
  for (auto const& w : ws) {
    for (auto const& r : w.SignalROI().get_ranges()) {
      o.ch.push_back(w.Channel()); o.start.push_back(r.begin_index());
      o.len.push_back(r.size());
      for (auto v : r.data()) o.val.push_back(v);
    }
  }
  return o;
}
struct Mcp { std::vector<int> id, pdg, mother, proc, n, all_id, all_mother, all_pdg; std::vector<float> e0, x, y, z, t, e; };
Mcp mcps(const std::vector<simb::MCParticle>& ps, double minlen) {
  Mcp o;
  for (auto const& p : ps) {
    o.all_id.push_back(p.TrackId()); o.all_mother.push_back(p.Mother()); o.all_pdg.push_back(p.PdgCode());
    int apdg = std::abs(p.PdgCode());
    if (!(apdg == 11 || apdg == 13 || apdg == 211 || apdg == 321 || apdg == 2212)) continue;
    int n = p.NumberTrajectoryPoints();
    if (n < 2) continue;
    double len = 0;
    for (int i = 1; i < n; ++i) len += (p.Position(i).Vect() - p.Position(i-1).Vect()).Mag();
    if (len < minlen) continue;
    o.id.push_back(p.TrackId()); o.pdg.push_back(p.PdgCode()); o.mother.push_back(p.Mother());
    o.proc.push_back(p.Process() == "primary" ? 1 : 0); o.n.push_back(n); o.e0.push_back(p.E());
    for (int i = 0; i < n; ++i) {
      o.x.push_back(p.Vx(i)); o.y.push_back(p.Vy(i)); o.z.push_back(p.Vz(i));
      o.t.push_back(p.T(i)); o.e.push_back(p.E(i));
    }
  }
  return o;
}
struct Sc { std::vector<int> ch, tdc, tid; std::vector<float> ne, x, y, z; };
Sc simch(const std::vector<sim::SimChannel>& scs) {
  Sc o;
  for (auto const& sc : scs) {
    for (auto const& ti : sc.TDCIDEMap()) {
      std::map<int, std::array<double,4>> agg;
      for (auto const& ide : ti.second) {
        auto& a = agg[std::abs(ide.trackID)];
        a[0] += ide.numElectrons; a[1] += ide.numElectrons*ide.x;
        a[2] += ide.numElectrons*ide.y; a[3] += ide.numElectrons*ide.z;
      }
      for (auto const& kv : agg) {
        if (kv.second[0] <= 0) continue;
        o.ch.push_back(sc.Channel()); o.tdc.push_back(ti.first); o.tid.push_back(kv.first);
        o.ne.push_back(kv.second[0]); o.x.push_back(kv.second[1]/kv.second[0]);
        o.y.push_back(kv.second[2]/kv.second[0]); o.z.push_back(kv.second[3]/kv.second[0]);
      }
    }
  }
  return o;
}
}
''')


def arr(v, dt):
    n = v.size()
    if n == 0:
        return np.zeros(0, dt)
    return np.array(np.frombuffer(v.data(), dtype=dt, count=n))


def bname(tree, cls, tag, proc):
    label, inst = (tag.split(":") + [""])[:2]
    n = f"{cls}_{label}_{inst}_{proc}."
    if not tree.GetBranch(n):
        raise SystemExit(f"no branch {n}")
    return n


f = ROOT.TFile.Open(a.art)
t = f.Get("Events")
bw = {lab.split(":")[1]: bname(t, "recob::Wires", lab, a.process) for lab in a.wires.split(",")}
bb = bname(t, "ints", a.bad, a.process)
bm = bname(t, "simb::MCParticles", a.mcp, a.mcp_process)
bs = None if a.no_simch else bname(t, "sim::SimChannels", a.simch, a.process)
for ev in range(t.GetEntries()):
    t.GetEntry(ev)
    aux = t.EventAuxiliary
    rse = (aux.run(), aux.subRun(), aux.event())
    out = {"rse": np.array(rse)}
    for inst, b in bw.items():
        w = ROOT.dq.wires(getattr(t, b).product())
        out[f"wire_{inst}_ch"] = arr(w.ch, np.int32); out[f"wire_{inst}_start"] = arr(w.start, np.int32)
        out[f"wire_{inst}_len"] = arr(w.len, np.int32); out[f"wire_{inst}_val"] = arr(w.val, np.float32)
    bad = getattr(t, bb).product()
    out["bad"] = np.array([bad[i] for i in range(bad.size())], np.int32)
    m = ROOT.dq.mcps(getattr(t, bm).product(), a.min_len)
    for k in ("id", "pdg", "mother", "proc", "n", "all_id", "all_mother", "all_pdg"):
        out[f"mcp_{k}"] = arr(getattr(m, k), np.int32)
    out["mcp_e0"] = arr(m.e0, np.float32)
    for k in "xyzte":
        out[f"trj_{k}"] = arr(getattr(m, k), np.float32)
    if bs:
        s = ROOT.dq.simch(getattr(t, bs).product())
        for k in ("ch", "tdc", "tid"):
            out[f"sc_{k}"] = arr(getattr(s, k), np.int32)
        for k in ("ne", "x", "y", "z"):
            out[f"sc_{k}"] = arr(getattr(s, k), np.float32)
    fn = f"{a.outdir}/evt_{rse[0]}_{rse[1]}_{rse[2]}.npz"
    np.savez_compressed(fn, **out)
    print(f"entry {ev} rse {rse}: {len(out['mcp_id'])} particles, "
          f"{len(out.get('sc_ch', []))} simch rows -> {fn}", flush=True)
