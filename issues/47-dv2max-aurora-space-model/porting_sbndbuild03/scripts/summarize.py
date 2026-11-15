#!/usr/bin/env python3
"""summarize.py <perevent.csv> [<percall csv> ...]  -- the headline numbers of P4 (issue 47) from the CSV tables only
(pandas).  Vertex: events where EVERY arm has the truth candidate (d_vtx not empty), < 1 cm, < 2 cm, median, with a
binomial 95 % interval (Wilson) and the paired gained/lost counts vs the reference arm (first arm on the command
line of perevent.py, i.e. the first arm in the CSV).  Selection: per MC truth class the fraction passing nue / numu /
generic.  Data: counts and event-by-event changes vs the reference arm.  Per call: digest matches, replay
agreement, space-point counts."""
import json
import math
import sys

import pandas as pd


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(c - h, 4), round(c + h, 4)]


ev = pd.read_csv(sys.argv[1])
arms = list(dict.fromkeys(ev["arm"]))
ref = arms[0]
ev["key"] = ev["sample"] + ":" + ev["run"].astype(str) + ":" + ev["subrun"].astype(str) + ":" + ev["event"].astype(str)
res = {"arms": arms, "reference": ref}
mc = ev[ev["sample"].str.startswith("mc")]
piv = mc.pivot_table(index=["key", "sample"], columns="arm", values="d_vtx", aggfunc="first")
for sample in ("mc-cv", "mc-nuecc", "mc"):
    s = piv if sample == "mc" else piv[piv.index.get_level_values("sample") == sample]
    s = s.dropna(subset=arms)
    out = {"n_events": int(len(s))}
    for a in arms:
        d = s[a]
        k = int((d < 1).sum())
        out[a] = dict(lt1=round(k / len(d), 4) if len(d) else None, lt1_ci95=wilson(k, len(d)),
                      lt2=round(float((d < 2).mean()), 4) if len(d) else None,
                      median_cm=round(float(d.median()), 3) if len(d) else None)
        if a != ref:
            out[a]["vs_ref_gained_lt1"] = int(((d < 1) & (s[ref] >= 1)).sum())
            out[a]["vs_ref_lost_lt1"] = int(((d >= 1) & (s[ref] < 1)).sum())
    res["vertex_" + sample] = out
sel = {}
for a in arms:
    m = mc[(mc["arm"] == a) & mc["truth"].notna() & (mc["truth"] != "")]
    sel[a] = {t: dict(n=int(len(g)), nue=int(g["nue"].sum()), numu=int(g["numu"].sum()), generic=int(g["generic"].sum()))
              for t, g in m.groupby("truth")}
res["selection_mc"] = sel
da = ev[ev["sample"] == "data"]
dd = {}
for a in arms:
    g = da[da["arm"] == a]
    dd[a] = dict(events=int(len(g)), generic=int(g["generic"].sum()), nue=int(g["nue"].sum()), numu=int(g["numu"].sum()))
    if a != ref:
        j = g.merge(da[da["arm"] == ref], on="key", suffixes=("", "_ref"))
        dd[a]["vs_ref"] = {f"{f}_{w}": int(((j[f] == (w == "gained")) & (j[f] != j[f + "_ref"])).sum())
                           for f in ("generic", "nue", "numu") for w in ("gained", "lost")}
        dd[a]["vs_ref_changed_events"] = sorted(j.loc[(j["nue"] != j["nue_ref"]) | (j["numu"] != j["numu_ref"]) |
                                                      (j["generic"] != j["generic_ref"]), "key"].tolist())
res["data"] = dd
for fn in sys.argv[2:]:
    c = pd.read_csv(fn)
    d = c["d_sa_hook_cm"].dropna()
    res["percall:" + fn.rsplit("/", 1)[-1]] = dict(
        calls=int(len(c)), digest_in_hook=int(c["digest_in_hook"].sum()),
        n_space_tree_eq_dump=int((c["n_space_tree"] == c["n_space_dump"]).sum()) if c["n_space_tree"].notna().any() else None,
        space_points=int(c["n_space_dump"].sum()), with_prediction=int(len(d)),
        replay_max_d_cm=float(d.max()) if len(d) else None, replay_within_1e_3cm=int((d < 1e-3).sum()),
        replay_max_dscore=float(c["dscore"].dropna().max()) if c["dscore"].notna().any() else None)
print(json.dumps(res, indent=1))
