"""P5: apparent sizes of pr/, pr-dv2snap/, merged/ per sample (parallel walk), and the merged-CAF list.
usage: p5-sizes.py full/<sample> <list-out> [nprocs]"""
import sys, os, glob
from multiprocessing import Pool

def walk(p):
    t = 0
    for r, _, fs in os.walk(p):
        for f in fs:
            try: t += os.lstat(os.path.join(r, f)).st_size
            except OSError: pass
    return t

def one(d):
    cafs = sorted(glob.glob(d + "merged/*.caf.root"))
    return walk(d + "pr"), walk(d + "pr-dv2snap"), sum(os.lstat(c).st_size for c in cafs), cafs

if __name__ == "__main__":
    W, L = sys.argv[1], sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 48
    units = sorted(d for d in glob.glob(f"{W}/node*/reco*/") if os.path.exists(d + "run_pair.log"))
    with Pool(n) as p: rows = p.map(one, units, chunksize=64)
    pr, sn, mg = (sum(r[i] for r in rows) for i in range(3))
    cafs = [c for r in rows for c in r[3]]
    with open(L, "w") as f: f.write("".join(os.path.abspath(c) + "\n" for c in cafs))
    G = 1e9
    print(f"{W}: units {len(units)} cafs {len(cafs)}; pr {pr/G:.1f} GB, pr-dv2snap {sn/G:.1f} GB, merged CAFs {mg/G:.1f} GB, total {(pr+sn+mg)/G:.1f} GB")
