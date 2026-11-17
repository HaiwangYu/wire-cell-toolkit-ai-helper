"""P5: per-sample tally of one full/<sample> tree: status, both validation verdicts, weights_fail, good events per pass, failed tries.
usage: p5-tally.py full/<sample> [nprocs]   (prints non-OK units, non-PASS validations, totals)"""
import sys, os, glob, json, collections
from multiprocessing import Pool

def one(d):
    r = {"unit": os.path.basename(d.rstrip("/")), "node": d.rstrip("/").split("/")[-2]}
    try: r["status"] = open(d + "status").read().split()[0]
    except (OSError, IndexError): r["status"] = "NONE"
    for vj in ("validate.json", "validate-pr-dv2snap.json"):
        try: r[vj] = json.load(open(d + vj))["verdict"]
        except (OSError, ValueError, KeyError): r[vj] = "MISSING"
    for g, k in (("good.txt", "good"), ("good-pr-dv2snap.txt", "good_snap")):
        try: r[k] = sum(1 for _ in open(d + g))
        except OSError: r[k] = 0
    r["wfail"] = 0
    for x in glob.glob(d + "pr*/*/weights_fail"):
        try: r["wfail"] += int(open(x).read().strip() or 0)
        except (OSError, ValueError): pass
    r["attempts"] = len(glob.glob(d + "attempts/*"))
    return r

if __name__ == "__main__":
    W = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 32
    units = sorted(d for d in glob.glob(f"{W}/node*/reco*/") if os.path.exists(d + "run_pair.log"))
    with Pool(n) as p: rows = p.map(one, units, chunksize=64)
    c = collections.Counter()
    for r in rows:
        c["units"] += 1; c["st_" + r["status"]] += 1
        for vj in ("validate.json", "validate-pr-dv2snap.json"): c[f"{vj}:{r[vj]}"] += 1
        c["good"] += r["good"]; c["good_snap"] += r["good_snap"]; c["wfail"] += r["wfail"]
        c["units_with_attempts"] += r["attempts"] > 0; c["attempt_dirs"] += r["attempts"]
        if r["status"] != "OK" or r["validate.json"] != "PASS" or r["validate-pr-dv2snap.json"] != "PASS" or r["wfail"] or r["good"] != r["good_snap"]:
            print("NONOK", r["node"], r["unit"], r["status"], r["validate.json"], r["validate-pr-dv2snap.json"], f"good={r['good']} snap={r['good_snap']} wfail={r['wfail']} attempts={r['attempts']}")
    print("TOTAL " + " ".join(f"{k}={v}" for k, v in sorted(c.items())))
