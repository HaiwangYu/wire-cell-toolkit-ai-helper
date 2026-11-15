#!/usr/bin/env python3
"""perevent.py <out.csv> <arm>=<runs dir> ...   (ai-helper issue 47, P4; the #43 analyze.py rules)

One CSV row per (arm, event) of every step-2 run <runs dir>/<unit>/pr_evt*/tracking-pr.root;
unit = mc-cv--<id> | mc-nuecc--<id> | data--<slice>.  Columns:
  vertex (MC): d_vtx = |final - truth_reco| of the candidate whose DL-vertex cloud has a point within 3 cm of
    the SCE-shifted truth vertex (T_dlvtx_call truth_reco_*; the #35/#43 rule), the closest such candidate;
    empty when no candidate qualifies.
  truth (MC): T_truth_nu, the interaction with the largest edep, vertex in the active volume
    (|x|, |y| < 200, 0 < z < 500): nueCC, numuCC, NC, other; empty = none in the AV.
  selection: T_tagger generic = numu_cc_flag >= 0, nue = generic && nue_score > 7,
    numu = generic && numu_score > 0.9 (the #43 cuts).
The headline numbers come from summarize.py, which reads only this CSV."""
import csv
import glob
import math
import os
import sys

import numpy as np
import uproot

OUT = sys.argv[1]
ARMS = [a.split("=", 1) for a in sys.argv[2:]]


def inside(x, y, z):
    return abs(x) < 200 and abs(y) < 200 and 0 < z < 500


def event_rows(fn):
    u = uproot.open(fn)
    r = dict(generic="", nue="", numu="", nue_score="", numu_score="", truth="", d_vtx="", n_calls=0)
    key = None
    if "T_tagger" in u and u["T_tagger"].num_entries:
        a = u["T_tagger"].arrays(["run", "subrun", "event", "numu_cc_flag", "nue_score", "numu_score"], library="np")
        key = (int(a["run"][0]), int(a["subrun"][0]), int(a["event"][0]))
        g = bool(a["numu_cc_flag"][0] >= 0)
        r.update(generic=int(g), nue=int(g and a["nue_score"][0] > 7), numu=int(g and a["numu_score"][0] > 0.9),
                 nue_score=float(a["nue_score"][0]), numu_score=float(a["numu_score"][0]))
    if "T_truth_nu" in u and u["T_truth_nu"].num_entries:
        n = u["T_truth_nu"].arrays(["runNo", "subRunNo", "eventNo", "pdg", "ccnc", "edep", "vtx_x", "vtx_y", "vtx_z"],
                                   library="np")
        key = key or (int(n["runNo"][0]), int(n["subRunNo"][0]), int(n["eventNo"][0]))
        i = int(np.argmax(n["edep"]))
        if n["edep"][i] > 0 and inside(n["vtx_x"][i], n["vtx_y"][i], n["vtx_z"][i]):
            pdg, cc = abs(int(n["pdg"][i])), int(n["ccnc"][i]) == 0
            r["truth"] = "nueCC" if (pdg == 12 and cc) else ("numuCC" if (pdg == 14 and cc) else ("NC" if not cc else "other"))
    if "T_dlvtx_call" in u and u["T_dlvtx_call"].num_entries:
        c = u["T_dlvtx_call"].arrays(["runNo", "subRunNo", "eventNo", "nu_index", "call_index", "pass", "final_valid",
                                      "final_x", "final_y", "final_z", "truth_valid", "truth_reco_x", "truth_reco_y",
                                      "truth_reco_z"], library="np")
        key = key or (int(c["runNo"][0]), int(c["subRunNo"][0]), int(c["eventNo"][0]))
        r["n_calls"] = len(c["nu_index"])
        p = u["T_dlvtx_cloud"].arrays(["nu_index", "call_index", "pass", "x", "y", "z"], library="np")
        best = None
        for i in range(len(c["nu_index"])):
            if not c["truth_valid"][i] or not c["final_valid"][i]:
                continue
            tv = np.array([c["truth_reco_x"][i], c["truth_reco_y"][i], c["truth_reco_z"][i]])
            m = (p["nu_index"] == c["nu_index"][i]) & (p["call_index"] == c["call_index"][i]) & (p["pass"] == c["pass"][i])
            if not m.any():
                continue
            dmin = float(np.min(np.sqrt((p["x"][m] - tv[0]) ** 2 + (p["y"][m] - tv[1]) ** 2 + (p["z"][m] - tv[2]) ** 2)))
            if dmin < 3.0 and (best is None or dmin < best[0]):
                best = (dmin, math.dist(tv, (c["final_x"][i], c["final_y"][i], c["final_z"][i])))
        if best:
            r["d_vtx"] = best[1]
    return key, r


F = ["arm", "sample", "unit", "run", "subrun", "event", "truth", "d_vtx", "n_calls", "generic", "nue", "numu",
     "nue_score", "numu_score"]
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=F)
    w.writeheader()
    for arm, R in ARMS:
        for d in sorted(glob.glob(os.path.join(R, "*--*"))):
            unit = os.path.basename(d)
            for fn in sorted(glob.glob(os.path.join(d, "pr_evt*", "tracking-pr.root"))):
                k, r = event_rows(fn)
                if k:
                    w.writerow(dict(arm=arm, sample=unit.split("--")[0], unit=unit.split("--")[1], run=k[0],
                                    subrun=k[1], event=k[2], **r))
print("wrote", OUT)
