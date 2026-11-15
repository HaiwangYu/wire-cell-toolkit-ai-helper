#!/usr/bin/env python3
"""recheck_aurora_holdout.py <index_fold0.csv> <refit_test_fold0.csv> <holdout500-percall.csv> <holdout500-inchain-calls.csv> <out.json>

Independent recomputation (porting_sbndbuild03) of prod_aurora's hold-out numbers (issue 47, Track 2).

Labels and classes come from a DIFFERENT source than prod_aurora's: Sne's cache index
(cache/aurora_space/index.csv, fold-0 rows: tx, ty, tz = the target in the label frame; flavor, ccnc), where
prod_aurora read label_xyz from the export's calls tables.  Picks:
  offline  = refit_test_fold0.csv x, y, z (label frame), Sne's re-fit ranker;
  in-chain = holdout500-inchain-calls.csv px, py, pz (prod_aurora moved them to the label frame,
             x - sign(x) * 0.29 cm); checked here against final_x where the chain placed the vertex on the pick.
Steps:
  0. sanity: offline < 1 cm on ALL 15,000 fold-0 pass-0 keys must give Sne's score_refit.md 0.9288;
  1. population = prod_aurora's pass-0 keys (holdout500-percall.csv, pass_ == p0);
  2. < 1 cm per class, in-chain and offline (class: nue_cc = nue CC, numu_cc = numu CC, nc = NC; a missing
     prediction is a miss);
  3. pick agreement in-chain vs offline (my own distance), compared with prod_aurora's d_pick per key, and the
     offline score vs refit_test_fold0.csv score (prod_aurora's score_off);
  4. prod_aurora's d_off / d_inc vs my distances to the cache target."""
import json
import sys

import numpy as np
import pandas as pd

IDX, REFIT, PC, IC, OUT = sys.argv[1:6]
ix = pd.read_csv(IDX)
rf = pd.read_csv(REFIT)
pc = pd.read_csv(PC)
ic = pd.read_csv(IC)
X_SHIFT = 0.29


def cls(r):
    f, c = str(r["flavor"]), str(r["ccnc"])
    if c == "NC":
        return "nc"
    return {"nue": "nue_cc", "anue": "nue_cc", "numu": "numu_cc", "anumu": "numu_cc"}.get(f, "other_cc")  # antineutrinos with their flavour


ix["cls_idx"] = ix.apply(cls, axis=1)
res = {}

# 0. sanity on the full hold-out, pass 0
full = ix[ix["key"].str.endswith(":p0")].merge(rf, on="key", how="left")
d = np.sqrt((full.x - full.tx) ** 2 + (full.y - full.ty) ** 2 + (full.z - full.tz) ** 2)
res["sanity_full_holdout_pass0"] = dict(n=int(len(full)), offline_lt1=round(float((d < 1).mean()), 4),
                                        sne_score_refit_md=0.9288,
                                        by_class={k: round(float((d[full.cls_idx == k] < 1).mean()), 4)
                                                  for k in ("nue_cc", "numu_cc", "nc")})

# 1. population
p0 = pc[pc["pass_"] == "p0"].copy()
res["population"] = dict(pass0_keys=int(len(p0)), unique=int(p0["key"].nunique()))
t = p0.merge(ix[["key", "tx", "ty", "tz", "cls_idx"]], on="key", how="left").merge(
    rf.rename(columns={"x": "ox", "y": "oy", "z": "oz", "score": "oscore"})[["key", "ox", "oy", "oz", "oscore"]],
    on="key", how="left")
icp = ic[ic["key"].str.endswith(":p0")]
res["inchain_calls_per_key"] = icp.groupby("key").size().value_counts().to_dict()
icp = icp.drop_duplicates("key")
t = t.merge(icp[["key", "px", "py", "pz", "score", "final_x", "accepted"]].rename(columns={"score": "iscore"}),
            on="key", how="left")
res["joins"] = dict(no_target=int(t.tx.isna().sum()), no_refit=int(t.ox.isna().sum()),
                    no_inchain=int(t.px.isna().sum()),
                    class_mismatch_vs_prod_aurora=int((t.cls_idx != t.cls).sum()))
# label-frame check of px: where the chain put the vertex on the pick, final_x = px + sign(px) * 0.29
on_pick = t.final_x.notna() & t.px.notna() & (np.abs(t.final_x - (t.px + np.sign(t.px) * X_SHIFT)) < 1e-3)
res["px_label_frame_check"] = dict(final_eq_px_unshifted=int(on_pick.sum()),
                                   final_eq_px_as_is=int((np.abs(t.final_x - t.px) < 1e-3).sum()), n=int(len(t)))

dist = lambda a, b, c, p, q, r: np.sqrt((a - p) ** 2 + (b - q) ** 2 + (c - r) ** 2)  # noqa: E731
t["my_d_off"] = dist(t.ox, t.oy, t.oz, t.tx, t.ty, t.tz)
t["my_d_inc"] = dist(t.px, t.py, t.pz, t.tx, t.ty, t.tz)
t["my_d_pick"] = dist(t.px, t.py, t.pz, t.ox, t.oy, t.oz)

# 2. < 1 cm per class (NaN distance = no prediction = miss)
eff = {}
for k, g in [("all", t)] + [(c, t[t.cls_idx == c]) for c in ("nue_cc", "numu_cc", "nc")] + \
        [("bnb", t[t["sample"] == "bnb"]), ("nue_sample", t[t["sample"] == "nue"])]:
    eff[k] = dict(n=int(len(g)), inchain=round(float((g.my_d_inc < 1).mean()), 4),
                  offline=round(float((g.my_d_off < 1).mean()), 4),
                  inchain_minus_offline_events=int((g.my_d_inc < 1).sum() - (g.my_d_off < 1).sum()))
res["lt1cm_pass0"] = eff
res["prod_aurora_reported"] = {"all": 0.9232, "nue_cc": 0.9557, "numu_cc": 0.9591, "nc": 0.7093}

# 3. pick agreement
dp = t.my_d_pick.dropna()
flips = t[(t.my_d_pick > 1)]
res["pick_agreement"] = dict(
    n=int(len(dp)), within_0p1cm=round(float((dp < 0.1).mean()), 4), within_1cm=round(float((dp < 1).mean()), 4),
    median_cm=float(dp.median()), p99_cm=float(dp.quantile(0.99)),
    flips_gt1cm=int(len(flips)),
    flips=[dict(key=r.key, cls=r.cls_idx, d_off=round(r.my_d_off, 3), d_inc=round(r.my_d_inc, 3))
           for r in flips.itertuples()],
    net_lt1_among_flips=int((flips.my_d_inc < 1).sum() - (flips.my_d_off < 1).sum()),
    crossing_1cm=[dict(key=r.key, d_off=round(r.my_d_off, 3), d_inc=round(r.my_d_inc, 3), d_pick=round(r.my_d_pick, 3))
                  for r in t[(t.my_d_inc < 1) != (t.my_d_off < 1)].itertuples()])
both = t.dropna(subset=["my_d_pick", "d_pick"])
both = both[np.isfinite(both.d_pick)]
res["vs_prod_aurora_columns"] = dict(
    d_pick_max_absdiff=float((both.my_d_pick - both.d_pick).abs().max()),
    d_off_max_absdiff=float((t.my_d_off - t.d_off).abs().max()),
    d_inc_max_absdiff=float((t.my_d_inc - t.d_inc)[np.isfinite(t.d_inc)].abs().max()),
    score_off_vs_refit_max_absdiff=float((t.score_off - t.oscore).abs().max()),
    score_inc_vs_inchain_calls_max_absdiff=float((t.score_inc - t.iscore).abs().max()))
json.dump(res, open(OUT, "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
