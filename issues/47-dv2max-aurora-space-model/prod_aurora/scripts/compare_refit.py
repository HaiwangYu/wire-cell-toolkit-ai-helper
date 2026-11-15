"""ai-helper #47 (prod_aurora): in-chain aurora_space (ana_calls.py table) vs Sne's offline refit_test_fold0.csv.

Population: every refit key whose event is in the units of UNITS_TSV (labeled hold-out calls, pass 0 and 1).
A refit key without an in-chain prediction counts as a miss for the in-chain column (no 3 cm cut, as eval_test).
Per pass and class (all, bnb, nue, nue_cc, numu_cc, nc): n, < 1 cm vs label (in-chain, offline), paired difference
with a 95 % bootstrap CI over events (2,000 resamples, seed 47), pick agreement (distance in-chain - offline:
< 0.1 cm, < 1 cm, median, p99, max).
usage: python compare_refit.py CALLS_CSV UNITS_TSV P_DIR OUT_PREFIX"""
import csv, json, sys
import numpy as np
calls_csv, units_tsv, P, out = sys.argv[1:5]
CLASS = {("nue", "CC"): "nue_cc", ("anue", "CC"): "nue_cc", ("numu", "CC"): "numu_cc", ("anumu", "CC"): "numu_cc"}
units = {l.split("\t")[1] for l in open(units_tsv)}
evs = set()
for r in csv.DictReader(open(f"{P}/holdout_r2/holdout_events.tsv"), delimiter="\t"):
    if r["unit"] in units and r["status"] == "0": evs.add(f"{r['sample']}:{r['run']}:{r['subrun']}:{r['event']}")
off = {r["key"]: r for r in csv.DictReader(open(f"{P}/run/ranker_refit/refit_test_fold0.csv"))}
lab = {r["key"]: r for r in csv.DictReader(open(f"{P}/labels_refit_test_fold0.csv"))}
cls = {r["key"]: CLASS.get((r["flavor"], r["ccnc"]), "nc" if r["ccnc"] == "NC" else "other") for r in csv.DictReader(open(f"{P}/index_fold0.csv"))}
inc = {}
dup = 0
for r in csv.DictReader(open(calls_csv)):
    if r["key"] in inc: dup += 1; continue
    inc[r["key"]] = r
keys = sorted(k for k in off if k.rsplit(":", 2)[0] in evs)
X = lambda r, a: np.array([float(r[c]) for c in a])
rec = []
for k in keys:
    o = X(off[k], "xyz"); L = X(lab[k], ("lx", "ly", "lz"))
    r = inc.get(k)
    has = r is not None and r.get("px", "") not in ("", None)
    p = X(r, ("px", "py", "pz")) if has else None
    rec.append(dict(key=k, ev=k.rsplit(":", 2)[0], sample=k.split(":")[0], pass_=k.split(":")[-1], cls=cls.get(k, "?"),
                    in_chain=int(r is not None), has_pred=int(has), d_off=float(np.linalg.norm(o - L)),
                    d_inc=float(np.linalg.norm(p - L)) if has else np.inf, d_pick=float(np.linalg.norm(p - o)) if has else np.inf,
                    digest=r["digest"] if r else "", score_inc=r.get("score") if r else "", score_off=off[k].get("score")))
with open(out + "_percall.csv", "w", newline="") as f:
    w = csv.DictWriter(f, list(rec[0].keys())); w.writeheader(); [w.writerow(x) for x in rec]
rng = np.random.default_rng(47)
res = {"n_keys": len(keys), "n_in_chain": sum(x["in_chain"] for x in rec), "n_pred": sum(x["has_pred"] for x in rec),
       "duplicate_in_chain_keys": dup, "extra_in_chain_keys_p01": sum(1 for k in inc if k.split(":")[-1] in ("p0", "p1") and k.rsplit(":", 2)[0] in evs and k not in off)}
for ps in ("p0", "p1"):
    for g in ("all", "bnb", "nue", "nue_cc", "numu_cc", "nc"):
        S = [x for x in rec if x["pass_"] == ps and (g == "all" or x["sample"] == g or x["cls"] == g)]
        if not S: continue
        a = np.array([x["d_inc"] < 1 for x in S], float); b = np.array([x["d_off"] < 1 for x in S], float)
        dp = np.array([x["d_pick"] for x in S]); fin = np.isfinite(dp)
        ev = np.array([x["ev"] for x in S]); ue, inv = np.unique(ev, return_inverse=True)
        sa, sb, cnt = np.bincount(inv, a), np.bincount(inv, b), np.bincount(inv)
        bs = []
        for _ in range(2000):
            j = rng.integers(0, len(ue), len(ue)); c = np.bincount(j, minlength=len(ue))
            bs.append(((c * sa).sum() - (c * sb).sum()) / (c * cnt).sum())
        lo, hi = np.percentile(bs, [2.5, 97.5])
        res[f"{ps}_{g}"] = dict(n=len(S), eff_in_chain=round(a.mean(), 4), eff_offline=round(b.mean(), 4),
                               diff=round(a.mean() - b.mean(), 4), ci95=[round(lo, 4), round(hi, 4)],
                               pick_lt_0p1=round(float((dp < 0.1).mean()), 4), pick_lt_1=round(float((dp < 1).mean()), 4),
                               pick_median=round(float(np.median(dp[fin])), 5) if fin.any() else None,
                               pick_p99=round(float(np.percentile(dp[fin], 99)), 4) if fin.any() else None,
                               pick_max=round(float(dp[fin].max()), 4) if fin.any() else None,
                               no_pred=int((~fin).sum()))
json.dump(res, open(out + "_summary.json", "w"), indent=1)
print(json.dumps(res, indent=1))
