import csv, sys, math
P = sys.argv[1]
units = {l.split("\t")[1] for l in open(f"{P}/units-sel.tsv")}
ev = {}
for r in csv.DictReader(open(f"{P}/holdout_r2/holdout_events.tsv"), delimiter="\t"):
    if r["unit"] in units: ev[f"{r['sample']}:{r['run']}:{r['subrun']}:{r['event']}"] = r["status"]
lab = {r["key"]: r for r in csv.DictReader(open(f"{P}/labels_refit_test_fold0.csv"))}
n = {}; k1 = {}
for r in csv.DictReader(open(f"{P}/run/ranker_refit/refit_test_fold0.csv")):
    k = r["key"]; s, run, sub, e, nu, ps = k.split(":")
    if f"{s}:{run}:{sub}:{e}" not in ev or ps != "p0": continue
    L = lab[k]; d = math.dist([float(r[c]) for c in "xyz"], [float(L[c]) for c in ("lx","ly","lz")])
    n[s] = n.get(s, 0) + 1; k1[s] = k1.get(s, 0) + (d < 1)
for s in n: print(s, n[s], round(k1[s]/n[s], 4))
