"""Hand-scan reference vertices (Xin's round-2 scan sheet) vs the two arms of issue 47 task A.
ref = scanner's (x,y,z) for 'Not OK'/'Not good' rows that give one; else Xin's round-2 reco vertex (the common start of
the top-level particles of the Bee 'mc' layer of his round-2 set) for 'Good'/'OK' rows."""
import csv, re, json, sys, math, urllib.request
math.dist = lambda p, q: math.sqrt(sum((a - b) ** 2 for a, b in zip(p, q)))
from collections import Counter
cand = sys.argv[1]; out = sys.argv[2]
C = {}
for r in csv.DictReader(open(cand)):
    if r["selected_A"] == "1":
        C[(int(r["run"]), int(r["event"]))] = r
def xin_vtx(link):
    u = link.rstrip("/") + "/mc/"
    d = json.load(urllib.request.urlopen(u, timeout=60))
    starts = [tuple(round(v, 2) for v in n["data"]["start"]) for n in d if "data" in n]
    if not starts: return None, 0
    s, n = Counter(starts).most_common(1)[0]
    return s, len(set(starts))
# Sheet RSE typos, checked against the runNo/subRunNo/eventNo of Xin's round-2 Bee event of that row:
SHEET_FIX = {(18255, 234538): (18255, 234638), (18355, 40074): (18355, 400474)}
rows_out = []
for f, samp in (("t0.csv", "nuecc48"), ("r2.csv", "ncpi0")):
    R = list(csv.reader(open(f)))
    i = [k for k, r in enumerate(R) if r and r[0].lower().startswith("round 2")][0]
    for r in R[i + 1:]:
        if not r or not re.match(r"\d+-\d+", r[0]): continue
        run, evt = (int(x) for x in r[0].split("-"))
        run, evt = SHEET_FIX.get((run, evt), (run, evt))
        verdict = r[2].strip(); text = " | ".join(x.strip() for x in r[3:5] if x.strip())
        m = re.search(r"\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)", text)
        bad = verdict.lower() in ("not ok", "not good", "not idea")
        xv, nstart = xin_vtx(r[1])
        if bad and m: ref, src = tuple(float(v) for v in m.groups()), "scanner xyz" + (" (?)" if "?" in text else "")
        elif not bad and xv: ref, src = xv, "Xin r2 vertex"
        else: ref, src = None, "none (Not good, no xyz)"
        c = C.get((run, evt))
        def d(p): return math.dist(p, ref) if (p and ref) else float("nan")
        o = (float(c["orig_x"]), float(c["orig_y"]), float(c["orig_z"])) if c else None
        a = (float(c["aur_x"]), float(c["aur_y"]), float(c["aur_z"])) if c else None
        rows_out.append(dict(sample=samp, run=run, event=evt, verdict=verdict, ref_source=src,
            ref=ref, d_orig=d(o), d_aur=d(a), d_xin_orig=math.dist(o, xv) if (o and xv) else float("nan"),
            n_xin_starts=nstart, in_table=c is not None, comment=text[:90]))
with open(out, "w") as fo:
    w = csv.writer(fo); w.writerow(["sample","run","event","verdict","ref_source","ref_x","ref_y","ref_z","d_orig_cm","d_aur_cm","d_orig_to_xin_r2_cm","n_distinct_top_starts","comment"])
    for r in rows_out:
        rf = r["ref"] or ("", "", "")
        w.writerow([r["sample"], r["run"], r["event"], r["verdict"], r["ref_source"], *rf, f"{r['d_orig']:.2f}", f"{r['d_aur']:.2f}", f"{r['d_xin_orig']:.2f}", r["n_xin_starts"], r["comment"]])
print("rows", len(rows_out), "matched to our table", sum(r["in_table"] for r in rows_out))
