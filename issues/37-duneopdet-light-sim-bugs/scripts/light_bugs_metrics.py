#!/usr/bin/env python3
"""Issue 37: per-event metrics for the two duneopdet light-simulation bugs of fdvd_sim doc 08a.

usage (inside dunesw):  light_bugs_metrics.py detsim_rerun.root ophit.root lt.npz stored_reco.root metrics.json

- hashes (FNV-1a over channel, timestamp, samples / OpDet, time, trackID, PE) of the rerun's raw::OpDetWaveforms and
  sim::OpDetDivRecs vs the products the original Stage A job stored (process "detsim") in reco.root;
- bug 1: snippet samples stored more than once on the same channel (and how many of those differ in ADC), snippets
  sharing a start tick; OpHits repeating an earlier hit's (OpChannel, PeakTime) and their PE;
- bug 2: MARLEY photons on the Ar backtracker products (lt.npz 'btm') and MARLEY PE in the DivRecs (lt.npz 'div'),
  so that PE per photon can be compared between samples and builds.
"""
import json
import sys

import numpy as np
import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gSystem.Load("libgallery")
for h in ("gallery/Event.h", "lardataobj/RawData/OpDetWaveform.h", "lardataobj/RecoBase/OpHit.h", "dunecore/DuneObj/OpDetDivRec.h"):
    ROOT.gInterpreter.ProcessLine(f'#include "{h}"')
ROOT.gInterpreter.Declare(r'''
#include <map>
#include <cmath>
#include <cstring>
#include <cstdint>
namespace i37 {
inline void fnv(uint64_t& h, const void* p, size_t n) {
  auto c = static_cast<const unsigned char*>(p);
  for (size_t i = 0; i < n; ++i) { h ^= c[i]; h *= 1099511628211ULL; }
}
std::string wfhash(const std::vector<raw::OpDetWaveform>& v) {
  uint64_t h = 1469598103934665603ULL;
  for (auto& w : v) { unsigned ch = w.ChannelNumber(); double t = w.TimeStamp();
    fnv(h, &ch, sizeof ch); fnv(h, &t, sizeof t); if (!w.empty()) fnv(h, w.data(), w.size() * sizeof(w[0])); }
  return std::to_string(v.size()) + ":" + std::to_string(h);
}
std::string divhash(const std::vector<sim::OpDetDivRec>& v) {
  uint64_t h = 1469598103934665603ULL; size_t n = 0;
  for (auto& r : v) { int od = r.OpDetNum(); fnv(h, &od, sizeof od);
    for (auto& tc : r.GetTimeChans()) { double t = tc.time; fnv(h, &t, sizeof t);
      for (auto& p : tc.phots) { int tid = p.trackID; double ph = p.phot; fnv(h, &tid, sizeof tid); fnv(h, &ph, sizeof ph); ++n; } } }
  return std::to_string(n) + ":" + std::to_string(h);
}
// samples, samples stored again, of which differing ADC, snippets sharing a start tick with an earlier one
std::vector<double> dupcheck(const std::vector<raw::OpDetWaveform>& v) {
  std::map<int, std::map<long, unsigned short>> seen; std::map<int, std::map<long, int>> starts;
  double total = 0, again = 0, differ = 0, same_start = 0;
  for (auto& w : v) {
    if (std::abs(w.TimeStamp()) > 1e6) continue;
    long t0 = std::lround((w.TimeStamp() + 4255.0) / 0.016); auto& m = seen[w.ChannelNumber()];
    if (starts[w.ChannelNumber()][t0]++ > 0) same_start += 1;
    for (size_t k = 0; k < w.size(); ++k) { total += 1; auto it = m.find(t0 + (long)k);
      if (it == m.end()) m[t0 + (long)k] = w[k]; else { again += 1; if (it->second != w[k]) differ += 1; } }
  }
  return {total, again, differ, same_start};
}
// per snippet: RMS of the first n samples (pre-trigger baseline; the CFD fires >= PreTrigger = 20 ticks after the start)
std::vector<double> prerms(const std::vector<raw::OpDetWaveform>& v, size_t n) {
  std::vector<double> out;
  for (auto& w : v) { if (w.size() < n) continue; double s = 0, s2 = 0;
    for (size_t k = 0; k < n; ++k) { s += w[k]; s2 += double(w[k]) * w[k]; }
    double mu = s / n; out.push_back(std::sqrt(std::max(0.0, s2 / n - mu * mu))); }
  return out;
}
}
''')


def event(f):
    ev = ROOT.gallery.Event(ROOT.std.vector("string")(1, f))
    assert not ev.atEnd()
    return ev


def prod(ev, cls, tag):
    return ev.getValidHandle[ROOT.std.vector(cls)](ROOT.art.InputTag(tag)).product()


rerun, ophit, ltf, stored, out = sys.argv[1:6]
DIV = ["sipmAr10ppm", "sipmXe10ppm", "sipmAr10ppmExt", "sipmXe10ppmExt"]
M = {}
er, es = event(rerun), event(stored)
wr = prod(er, "raw::OpDetWaveform", "opdigi10ppm::DetsimRerun")
M["wf_hash"] = str(ROOT.i37.wfhash(wr))
try:
    M["wf_hash_stored"] = str(ROOT.i37.wfhash(prod(es, "raw::OpDetWaveform", "opdigi10ppm::detsim")))
except Exception as e:  # noqa: BLE001
    M["wf_hash_stored"] = f"missing: {e}"
M["div_hash"] = {d: str(ROOT.i37.divhash(prod(er, "sim::OpDetDivRec", d + "::DetsimRerun"))) for d in DIV}
M["div_hash_stored"] = {d: str(ROOT.i37.divhash(prod(es, "sim::OpDetDivRec", d + "::detsim"))) for d in DIV}
d = list(ROOT.i37.dupcheck(wr))
M["samples"], M["samples_again"], M["samples_again_differ"], M["snippets_same_start"] = d
M["snippets"] = int(wr.size())
pr = np.array(list(ROOT.i37.prerms(wr, 15)))
M["prerms15_median"], M["prerms15_mean"], M["prerms15_n"] = float(np.median(pr)), float(pr.mean()), int(len(pr))
# OpHits repeating an earlier hit's (OpChannel, PeakTime); per group the largest-area copy is kept
# (the stageB/dedup_ophits.py rule)
eh = event(ophit)  # keep the gallery Event alive while its product is read
hv = prod(eh, "recob::OpHit", "ophit10ppm::OpHitV")
hits = np.array([(x.OpChannel(), x.PeakTime(), x.Area(), x.PE()) for x in hv]).reshape(-1, 4)
groups = {}
for j, (ch, pt, _, _) in enumerate(hits):
    groups.setdefault((int(ch), float(pt)), []).append(j)
dup = np.zeros(len(hits), bool)
for js in groups.values():
    if len(js) > 1:
        best = max(js, key=lambda j: hits[j, 2])
        dup[[j for j in js if j != best]] = True
M["hits"], M["hits_dup"] = int(len(hits)), int(dup.sum())
M["hit_pe"], M["hit_pe_dup"] = float(hits[:, 3].sum()), float(hits[dup, 3].sum())

lt = np.load(ltf)
gl = [str(x).lower() for x in lt["gen_labels"]]
mi = gl.index("marley")
bl = [str(x) for x in lt["bt_labels"]]
btm = lt["btm"]
M["marley_photons"] = {lab: float(btm[btm[:, 0] == k, 3].sum()) for k, lab in enumerate(bl)}
div, dl = lt["div"], [str(x) for x in lt["div_labels"]]
M["marley_pe"] = {lab: float(div[(div[:, 0] == q) & (div[:, 3] == mi), 4].sum()) for q, lab in enumerate(dl)}
M["all_pe"] = {lab: float(div[div[:, 0] == q, 4].sum()) for q, lab in enumerate(dl)}
json.dump(M, open(out, "w"), indent=1)
print(json.dumps(M, indent=1))
