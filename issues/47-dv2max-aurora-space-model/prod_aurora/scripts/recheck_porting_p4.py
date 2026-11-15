"""ai-helper #47 (prod_aurora): independent recomputation of porting_sbndbuild03's P4 headline numbers from its
tables/perevent.csv (no code of porting's used).  usage: python recheck_porting_p4.py perevent.csv"""
import csv, math, sys
from collections import defaultdict
rows = list(csv.DictReader(open(sys.argv[1])))
ev = defaultdict(dict)   # (sample, run, subrun, event) -> arm -> row
for r in rows: ev[(r["sample"], r["run"], r["subrun"], r["event"])][r["arm"]] = r
arms = ["original", "r7c", "aur", "v2_r7c"]
def wilson(k, n, z=1.959964):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(c - h, 3), round(c + h, 3)
def med(v): v = sorted(v); n = len(v); return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])
out = {}
for grp, pick in (("all MC", lambda s: s.startswith("mc")), ("CV", lambda s: s == "mc-cv"), ("nueCC", lambda s: s == "mc-nuecc")):
    E = [k for k, a in ev.items() if pick(k[0]) and all(a.get(x, {}).get("d_vtx", "") != "" for x in arms)]
    line = {"n": len(E)}
    for x in arms:
        d = [float(ev[k][x]["d_vtx"]) for k in E]; k1 = sum(v < 1 for v in d)
        line[x] = dict(lt1=round(k1 / len(d), 3), ci=wilson(k1, len(d)), lt2=round(sum(v < 2 for v in d) / len(d), 3), median=round(med(d), 3))
    g = [k for k in E if float(ev[k]["aur"]["d_vtx"]) < 1 <= float(ev[k]["r7c"]["d_vtx"])]
    l = [k for k in E if float(ev[k]["r7c"]["d_vtx"]) < 1 <= float(ev[k]["aur"]["d_vtx"])]
    line["aur_vs_r7c"] = dict(gained=len(g), lost=len(l), lost_events=[(k, ev[k]["r7c"]["d_vtx"][:5], ev[k]["aur"]["d_vtx"][:5]) for k in l])
    line["r7c_vs_v2_r7c_changed"] = sum(ev[k]["r7c"]["d_vtx"] != ev[k]["v2_r7c"]["d_vtx"] for k in E)
    out[grp] = line
sel = defaultdict(lambda: defaultdict(lambda: [0, 0]))
for k, a in ev.items():
    if not k[0].startswith("mc") or a["r7c"]["truth"] == "": continue
    for x in ("original", "r7c", "aur"):
        sel[a[x]["truth"]][x][0] += int(a[x]["nue"] == "1"); sel[a[x]["truth"]][x][1] += int(a[x]["numu"] == "1")
out["selections MC (truth class: nue/numu)"] = {t: {x: v for x, v in d.items()} | {"n": sum(1 for k, a in ev.items() if k[0].startswith("mc") and a["r7c"]["truth"] == t)} for t, d in sel.items()}
D = [k for k in ev if k[0] == "data"]
out["data"] = {x: {c: sum(int(ev[k][x][c] == "1") for k in D) for c in ("generic", "nue", "numu")} | {"events": len(D)} for x in ("r7c", "aur")}
out["data changed (r7c -> aur)"] = [dict(rse="/".join(k[1:]), **{c: f"{ev[k]['r7c'][c]}->{ev[k]['aur'][c]}" for c in ("nue", "numu") if ev[k]["r7c"][c] != ev[k]["aur"][c]},
                                         numu_score=f"{ev[k]['r7c']['numu_score'][:6]}->{ev[k]['aur']['numu_score'][:6]}")
                                    for k in D if any(ev[k]["r7c"][c] != ev[k]["aur"][c] for c in ("generic", "nue", "numu"))]
import json; print(json.dumps(out, indent=1, default=str))
