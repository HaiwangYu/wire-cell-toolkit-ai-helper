#!/usr/bin/env python3
"""Per-event neutrino summary scalars from tracking-pr.root files -> JSON.
usage: extract-scores.py <out.json> <E>=<file> [<E>=<file> ...]   (run INSIDE SL7)
Writes {E: {"numu_score", "nue_score", "kine_reco_Enu", "trees"}} from T_tagger / T_kine entry 0
(absent tree -> null), the same scalars MultiAlgBlobClustering::pf_summary_node prints into the
Bee "mc" summary text ("reco nu <Enu> MeV numu <s> nue <s>")."""
import sys, json, ROOT
ROOT.gErrorIgnoreLevel = ROOT.kFatal
out = {}
for arg in sys.argv[2:]:
    e, fn = arg.split('=', 1)
    f = ROOT.TFile.Open(fn); d = {'trees': len(f.GetListOfKeys()) if f else 0}
    tt, tk = (f.Get('T_tagger'), f.Get('T_kine')) if f else (None, None)
    if tt and tt.GetEntries(): tt.GetEntry(0); d['numu_score'] = float(tt.numu_score); d['nue_score'] = float(tt.nue_score)
    else: d['numu_score'] = d['nue_score'] = None
    if tk and tk.GetEntries(): tk.GetEntry(0); d['kine_reco_Enu'] = float(tk.kine_reco_Enu)
    else: d['kine_reco_Enu'] = None
    out[e] = d
json.dump(out, open(sys.argv[1], 'w'), indent=1); print('wrote', sys.argv[1], len(out), 'events')
