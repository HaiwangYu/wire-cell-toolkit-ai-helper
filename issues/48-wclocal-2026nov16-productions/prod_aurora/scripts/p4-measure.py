"""P4 pilot: per sample units, events, both validations, failed tries, disk (pr/, pr-dv2snap/, merged/), process wall/CPU per step."""
import sys, os, glob, json, csv, collections, subprocess
W = sys.argv[1]; P = sys.argv[2]   # p4 dir, pairs ids dir
samp = {}
for s in ("bnb", "nuecc", "ncdr"):
    for l in open(f"{P}/{s}-ids.tsv"):
        f = l.rstrip("\n").split("\t"); samp[f[0]] = (s, int(f[4]))
def du(p):
    t = 0
    for r, _, fs in os.walk(p):
        for f in fs:
            try:
                st = os.lstat(os.path.join(r, f)); t += st.st_size
            except OSError: pass
    return t
agg = collections.defaultdict(lambda: collections.Counter())
bad = []
for d in glob.glob(f"{W}/run/node*/*/"):
    uid = os.path.basename(d.rstrip("/")); s, nev = samp[uid]; a = agg[s]
    a["units"] += 1; a["events"] += nev
    a["st_" + open(d + "status").read().split()[0]] += 1
    for vj in ("validate.json", "validate-pr-dv2snap.json"):
        v = json.load(open(d + vj)); a[f"{vj}:{v['verdict']}"] += 1
        if v["verdict"] != "PASS": bad.append((uid, vj))
    a["attempts"] += len(glob.glob(d + "attempts/*"))
    a["wfail"] += sum(int(open(x).read().strip() or 0) for x in glob.glob(d + "pr*/*/weights_fail"))
    a["b_pr"] += du(d + "pr"); a["b_snap"] += du(d + "pr-dv2snap"); a["b_merged"] += du(d + "merged")
    a["b_all"] += du(d)
    for row in csv.reader(open(d + "cost.tsv"), delimiter="\t"):
        if len(row) >= 6 and row[0] and not row[0].startswith("#"):
            try: a["w_" + row[0]] += float(row[4]); a["c_" + row[0]] += float(row[5])
            except ValueError: pass
print("bad validations:", bad)
for s, a in agg.items():
    ev = a["events"]
    print(f"== {s}: units {a['units']} events {ev}; " + " ".join(f"{k}={v}" for k, v in sorted(a.items()) if k.startswith(("st_", "validate", "attempts", "wfail"))))
    print("   MB/event: pr %.2f snap %.2f merged %.2f unit-total %.2f (ql hardlinks counted in total)" % tuple(a[k] / ev / 1e6 for k in ("b_pr", "b_snap", "b_merged", "b_all")))
    print("   wall s/event: " + " ".join(f"{k[2:]} {v/ev:.2f}" for k, v in sorted(a.items()) if k.startswith("w_")))
    print("   cpu  s/event: " + " ".join(f"{k[2:]} {v/ev:.2f}" for k, v in sorted(a.items()) if k.startswith("c_")))
