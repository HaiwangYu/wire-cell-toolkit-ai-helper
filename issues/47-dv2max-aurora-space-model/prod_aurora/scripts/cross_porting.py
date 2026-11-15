"""ai-helper #47 (prod_aurora): Aurora data per-call table (ana_calls.py) vs porting's percall-aur.csv, by event + nu_index;
reports digest equality and pick distance (raw reco frame).  usage: python cross_porting.py AURORA_CALLS PORTING_PERCALL OUT_CSV"""
import sys, numpy as np, pandas as pd
a = pd.read_csv(sys.argv[1]); p = pd.read_csv(sys.argv[2]); p = p[p.run.str.startswith("data")].copy()
a["rse"] = a.key.str.split(":").str[1:4].str.join("/"); a["nu_index"] = a.key.str.split(":").str[4].astype(int)
a["pass"] = a.key.str.split(":").str[5].str[1:].astype(int)
a["raw_x"] = a.px + np.sign(a.px) * 0.29
p["rse"] = p.runNo.astype(str) + "/" + p.subRunNo.astype(str) + "/" + p.eventNo.astype(str)
m = a.merge(p, on=["rse", "nu_index", "pass"], how="outer", indicator=True, suffixes=("_aurora", "_porting"))
m["same_digest"] = m.digest == m.input_sha1
m["d_pick_cm"] = np.sqrt((m.raw_x - m.hook_x) ** 2 + (m.py - m.hook_y) ** 2 + (m.pz - m.hook_z) ** 2)
m["dscore"] = (m.score - m.hook_score).abs()
out = m[["rse", "nu_index", "pass", "_merge", "digest", "input_sha1", "same_digest", "n_aurora", "n_porting", "n_space", "n_space_hook",
         "raw_x", "py", "pz", "hook_x", "hook_y", "hook_z", "d_pick_cm", "score", "hook_score", "dscore"]]
out.to_csv(sys.argv[3], index=False)
print("calls aurora", len(a), "porting", len(p), "matched", int((m._merge == "both").sum()), "same digest", int(m.same_digest.sum()),
      "| pick distance max (same digest)", m.d_pick_cm[m.same_digest].max(), "| score |diff| max", m.dscore[m.same_digest].max(),
      "| different digest", int((~m.same_digest & (m._merge == "both")).sum()))
