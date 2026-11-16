#!/usr/bin/env python3
"""data-compare.py <outdir> <armA>=<runs dir> <armB>=<runs dir> [<bee index csv>]   (issue 47, task A)

Real data, two arms of the same build on the same step-1 tars.  Per (unit, event) of <runs dir>/<unit>/pr_evt*/:
  candidates (tables/data-orig-vs-aur-cand.csv): one row per neutrino candidate (T_dlvtx_call nu_index) present in
    either arm: the final vertex of each arm (T_dlvtx_call final_*, identical on every call of a candidate), whether
    it is DL-based (some call of the candidate has accepted = 1, i.e. the DL vertex was taken; 0 = the traditional
    vertex), the DL and traditional proposals of the last call, and |final_A - final_B|.
  events (tables/data-orig-vs-aur-event.csv): T_tagger of each arm (the selected candidate nu_index, nu_x/y/z, the
    #43 cuts generic = numu_cc_flag >= 0, nue = generic && nue_score > 7, numu = generic && numu_score > 0.9, the
    scores), |nu_A - nu_B|, and changed = any selection flag differs.
  Bee: with the index CSV (bee-pack.py) the per-event Bee index of each arm is joined in.
Prints a JSON summary (also <outdir>/data-orig-vs-aur-summary.json)."""
import csv
import glob
import json
import math
import os
import sys

import numpy as np
import uproot

OUT = sys.argv[1]
(A, RA), (B, RB) = (x.split("=", 1) for x in sys.argv[2:4])
BEE = sys.argv[4] if len(sys.argv) > 4 else None
os.makedirs(OUT, exist_ok=True)


def read(fn):
    u = uproot.open(fn)
    ev, cands = {}, {}
    if "T_tagger" in u and u["T_tagger"].num_entries:
        t = u["T_tagger"].arrays(["run", "subrun", "event", "nu_index", "nu_x", "nu_y", "nu_z", "numu_cc_flag",
                                  "nue_score", "numu_score"], library="np")
        g = bool(t["numu_cc_flag"][0] >= 0)
        ev = dict(rse=(int(t["run"][0]), int(t["subrun"][0]), int(t["event"][0])), sel_nu=int(t["nu_index"][0]),
                  nu=(float(t["nu_x"][0]), float(t["nu_y"][0]), float(t["nu_z"][0])), generic=int(g),
                  nue=int(g and t["nue_score"][0] > 7), numu=int(g and t["numu_score"][0] > 0.9),
                  nue_score=float(t["nue_score"][0]), numu_score=float(t["numu_score"][0]))
    if "T_dlvtx_call" in u and u["T_dlvtx_call"].num_entries:
        c = u["T_dlvtx_call"].arrays(["runNo", "subRunNo", "eventNo", "nu_index", "call_index", "pass", "accepted",
                                      "final_valid", "final_x", "final_y", "final_z", "dl_x", "dl_y", "dl_z",
                                      "trad_valid", "trad_x", "trad_y", "trad_z"], library="np")
        ev.setdefault("rse", (int(c["runNo"][0]), int(c["subRunNo"][0]), int(c["eventNo"][0])))
        for nu in np.unique(c["nu_index"]):
            m = np.flatnonzero(c["nu_index"] == nu)
            m = m[np.argsort(c["call_index"][m])]
            last = m[-1]
            fv = [i for i in m if c["final_valid"][i]]
            f = (float(c["final_x"][fv[-1]]), float(c["final_y"][fv[-1]]), float(c["final_z"][fv[-1]])) if fv else None
            spread = max((math.dist(f, (c["final_x"][i], c["final_y"][i], c["final_z"][i])) for i in fv), default=0.0)
            cands[int(nu)] = dict(final=f, final_spread=spread, dl_based=int(bool(c["accepted"][m].any())),
                                  n_calls=len(m), n_accepted=int(c["accepted"][m].sum()),
                                  dl=(float(c["dl_x"][last]), float(c["dl_y"][last]), float(c["dl_z"][last])),
                                  trad=(float(c["trad_x"][last]), float(c["trad_y"][last]), float(c["trad_z"][last]))
                                  if c["trad_valid"][last] else None)
    return ev, cands


def collect(R):
    res = {}
    for d in sorted(glob.glob(os.path.join(R, "data--*"))):
        unit = os.path.basename(d).split("--", 1)[1]
        for fn in sorted(glob.glob(os.path.join(d, "pr_evt*", "tracking-pr.root"))):
            ev, cands = read(fn)
            if "rse" in ev:
                res[(unit,) + ev["rse"]] = (ev, cands, os.path.basename(os.path.dirname(fn)))
    return res


da, db = collect(RA), collect(RB)
bee = {}
if BEE:
    for r in csv.DictReader(open(BEE)):
        bee[(r["arm"], r["unit"], int(r["run"]), int(r["subrun"]), int(r["event"]))] = int(r["bee_index"])
keys = sorted(set(da) | set(db), key=lambda k: (k[0].split("-")[0], k[1:]))
fmt = lambda v: "" if v is None else round(v, 3)  # noqa: E731
xyz = lambda p, i: "" if p is None else round(p[i], 2)  # noqa: E731
crows, erows = [], []
for k in keys:
    ea, ca, _ = da.get(k, ({}, {}, ""))
    eb, cb, _ = db.get(k, ({}, {}, ""))
    sample = "ncpi0" if k[0].startswith("ncpi0") else "nuecc48"
    for nu in sorted(set(ca) | set(cb)):
        a, b = ca.get(nu), cb.get(nu)
        fa, fb = (a or {}).get("final"), (b or {}).get("final")
        crows.append(dict(sample=sample, unit=k[0], run=k[1], subrun=k[2], event=k[3], nu_index=nu,
                          selected_A=int(ea.get("sel_nu") == nu), selected_B=int(eb.get("sel_nu") == nu),
                          **{f"{A}_x": xyz(fa, 0), f"{A}_y": xyz(fa, 1), f"{A}_z": xyz(fa, 2),
                             f"{A}_dl_based": "" if a is None else a["dl_based"],
                             f"{B}_x": xyz(fb, 0), f"{B}_y": xyz(fb, 1), f"{B}_z": xyz(fb, 2),
                             f"{B}_dl_based": "" if b is None else b["dl_based"],
                             f"{A}_n_calls": "" if a is None else a["n_calls"],
                             f"{B}_n_calls": "" if b is None else b["n_calls"],
                             f"{A}_final_spread_cm": "" if a is None else fmt(a["final_spread"]),
                             f"{B}_final_spread_cm": "" if b is None else fmt(b["final_spread"])},
                          d_final_cm=fmt(math.dist(fa, fb)) if (fa and fb) else ""))
    na, nb = ea.get("nu"), eb.get("nu")
    changed = any(ea.get(f) != eb.get(f) for f in ("generic", "nue", "numu"))
    erows.append(dict(sample=sample, unit=k[0], run=k[1], subrun=k[2], event=k[3],
                      **{f"{A}_sel_nu": ea.get("sel_nu", ""), f"{B}_sel_nu": eb.get("sel_nu", ""),
                         f"{A}_generic": ea.get("generic", ""), f"{B}_generic": eb.get("generic", ""),
                         f"{A}_nue": ea.get("nue", ""), f"{B}_nue": eb.get("nue", ""),
                         f"{A}_numu": ea.get("numu", ""), f"{B}_numu": eb.get("numu", ""),
                         f"{A}_nue_score": fmt(ea.get("nue_score")), f"{B}_nue_score": fmt(eb.get("nue_score")),
                         f"{A}_numu_score": fmt(ea.get("numu_score")), f"{B}_numu_score": fmt(eb.get("numu_score")),
                         f"{A}_dl_based": (ca.get(ea.get("sel_nu")) or {}).get("dl_based", ""),
                         f"{B}_dl_based": (cb.get(eb.get("sel_nu")) or {}).get("dl_based", ""),
                         f"{A}_bee": bee.get((A,) + k, ""), f"{B}_bee": bee.get((B,) + k, "")},
                      d_nu_cm=fmt(math.dist(na, nb)) if (na and nb) else "", changed=int(changed)))
for name, rows in (("cand", crows), ("event", erows)):
    with open(os.path.join(OUT, f"data-orig-vs-aur-{name}.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

d = np.array([r["d_final_cm"] for r in crows if r["d_final_cm"] != ""], float)
s = {"events": len(erows), "events_A": len(da), "events_B": len(db), "candidates": len(crows),
     "candidates_both": int(len(d)),
     "d_final_cm": dict(median=round(float(np.median(d)), 3), lt0p1=int((d < 0.1).sum()), lt1=int((d < 1).sum()),
                        lt2=int((d < 2).sum()), ge5=int((d >= 5).sum()), max=round(float(d.max()), 2)),
     "dl_based": {a: int(sum(1 for r in crows if r[f"{a}_dl_based"] == 1)) for a in (A, B)},
     "selection": {a: {f: int(sum(1 for r in erows if r[f"{a}_{f}"] == 1)) for f in ("generic", "nue", "numu")}
                   for a in (A, B)},
     "changed_events": [dict(unit=r["unit"], rse=f"{r['run']}/{r['subrun']}/{r['event']}",
                             **{k: r[k] for k in r if k.endswith(("_nue", "_numu", "_generic", "_score"))})
                        for r in erows if r["changed"]],
     "selected_candidate_differs": int(sum(1 for r in erows if r[f"{A}_sel_nu"] != r[f"{B}_sel_nu"]))}
for smp in ("nuecc48", "ncpi0"):
    s["selection_" + smp] = {a: {f: int(sum(1 for r in erows if r["sample"] == smp and r[f"{a}_{f}"] == 1))
                                 for f in ("generic", "nue", "numu")} for a in (A, B)}
json.dump(s, open(os.path.join(OUT, "data-orig-vs-aur-summary.json"), "w"), indent=1)
print(json.dumps(s, indent=1))
