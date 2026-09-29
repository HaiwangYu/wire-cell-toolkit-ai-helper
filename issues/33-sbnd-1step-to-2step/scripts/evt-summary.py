#!/usr/bin/env python3
"""Per-event summary of tracking-pr.root files -> JSON (run INSIDE SL7).
usage: evt-summary.py <out.json> <E>=<file> [<E>=<file> ...]
{E: {trees, numu_score, nue_score, kine_reco_Enu (T_tagger / T_kine entry 0, null if absent),
     n_clusters (T_cluster entries), n_rec_charge (T_rec_charge entries),
     truth: null | {n_nu, nu: [{pdg, ccnc, int_type, E, edep, vtx_x, vtx_y, vtx_z}], n_pf}}}"""
import sys, json, ROOT
ROOT.gErrorIgnoreLevel = ROOT.kFatal
out = {}
for arg in sys.argv[2:]:
    e, fn = arg.split('=', 1)
    f = ROOT.TFile.Open(fn); d = {'trees': len(f.GetListOfKeys()) if f else 0}
    g = lambda n: f.Get(n) if f else None
    tt, tk, tc, tr = g('T_tagger'), g('T_kine'), g('T_cluster'), g('T_rec_charge')
    if tt and tt.GetEntries(): tt.GetEntry(0); d['numu_score'] = float(tt.numu_score); d['nue_score'] = float(tt.nue_score)
    else: d['numu_score'] = d['nue_score'] = None
    if tk and tk.GetEntries(): tk.GetEntry(0); d['kine_reco_Enu'] = float(tk.kine_reco_Enu)
    else: d['kine_reco_Enu'] = None
    d['n_clusters'] = tc.GetEntries() if tc else None
    d['n_rec_charge'] = tr.GetEntries() if tr else None
    tn, tp = g('T_truth_nu'), g('T_truth_pf')
    if tn:
        nus = []
        for i in range(tn.GetEntries()):
            tn.GetEntry(i)
            nus.append({k: (int(getattr(tn, k)) if k in ('pdg', 'ccnc', 'int_type') else float(getattr(tn, k)))
                        for k in ('pdg', 'ccnc', 'int_type', 'E', 'edep', 'vtx_x', 'vtx_y', 'vtx_z')})
        d['truth'] = {'n_nu': len(nus), 'nu': nus, 'n_pf': tp.GetEntries() if tp else 0}
    else: d['truth'] = None
    out[e] = d
json.dump(out, open(sys.argv[1], 'w'), indent=1); print('wrote', sys.argv[1], len(out), 'events')
