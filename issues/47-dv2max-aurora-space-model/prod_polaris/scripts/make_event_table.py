"""Per-event table: hand scan (Xin round 2) vs `original` vs `aurora_space` on nueCC-48 + NCpi0-19 (issue 47).
usage: make_event_table.py <sheet nueCC round csv> <sheet NCpi0 round csv> <porting tables dir> <handscan-vs-arms.csv> <out.md>"""
import csv, re, sys, math
nue_csv, nc_csv, T, HS, OUT = sys.argv[1:6]
BO = "https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/%d/"
BA = "https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/%d/"
def sheet(f, samp):
    R = list(csv.reader(open(f))); i = [k for k, r in enumerate(R) if r and r[0].lower().startswith("round 2")][0]
    out = {}
    for r in R[i + 1:]:
        if r and re.match(r"\d+-\d+", r[0]):
            run, evt = (int(x) for x in r[0].split("-"))
            out[(run, evt)] = dict(sample=samp, link=r[1].strip(), verdict=r[2].strip(),
                                   note=" ".join(x.strip() for x in r[3:5] if x.strip()).replace("|", "/"))
    return out
S = {**sheet(nue_csv, "nuecc48"), **sheet(nc_csv, "ncpi0")}
E = {(int(r["run"]), int(r["event"])): r for r in csv.DictReader(open(f"{T}/data-orig-vs-aur-event.csv"))}
C = {(int(r["run"]), int(r["event"])): r for r in csv.DictReader(open(f"{T}/data-orig-vs-aur-cand.csv")) if r["selected_A"] == "1"}
Hs = {(int(r["run"]), int(r["event"])): r for r in csv.DictReader(open(HS))}
f = lambda x: float(x)
def sel(e, arm):
    s = [n for n, k in (("νe", "nue"), ("νμ", "numu")) if e[f"{arm}_{k}"] == "1"]
    return "+".join(s) if s else ("generic" if e[f"{arm}_generic"] == "1" else "none")
rows = []
for key in sorted(set(E) | set(S), key=lambda k: (int(E[k]["orig_bee"]) if k in E else 999, k)):
    e, s, h, c = E.get(key), S.get(key), Hs.get(key), C.get(key)
    run, evt = key; samp = (e or s)["sample"]
    rse = f"{run}/1/{evt}" if e else f"{run}/?/{evt}"
    ref, refsrc = "—", ""
    if h and h["ref_x"]:
        ref = f"({f(h['ref_x']):.1f}, {f(h['ref_y']):.1f}, {f(h['ref_z']):.1f})"
        refsrc = "scanner" if h["ref_source"].startswith("scanner") else "Xin r2 (scan OK)"
        if "(?)" in h["ref_source"]: refsrc += " ?"
    do = f(h["d_orig_cm"]) if h else float("nan"); da = f(h["d_aur_cm"]) if h else float("nan")
    mism = h is not None and not math.isnan(do) and min(do, da) > 10
    def summ(arm, d):
        if not e: return "not run"
        t = []
        if not math.isnan(d) and not mism: t.append(f"**{d:.2f} cm**" if d < 1 else f"{d:.2f} cm")
        t.append(f"sel {sel(e, arm)}")
        t.append(f"νe {f(e[arm + '_nue_score']):.1f} / νμ {f(e[arm + '_numu_score']):.2f}")
        if e[f"{arm}_dl_based"] != "1": t.append("trad. vertex")
        return "; ".join(t)
    notes = []
    if not e: notes.append("in the scan sheet, not in our sample")
    if e and not s: notes.append("not in the scan sheet")
    if e and e["changed"] == "1": notes.append(f"**selection changes** ({sel(e,'orig')} → {sel(e,'aur')})")
    if mism: notes.append("our candidate is a different interaction from the scanned one (both arms > 10 cm)")
    if e: notes.append(f"orig–aur {f(e['d_nu_cm']):.2f} cm")
    if not math.isnan(do) and not mism:
        if da + 1 < do: notes.append("aurora closer")
        elif do + 1 < da: notes.append("**aurora worse**")
    if s and s["note"]: notes.append("scan: " + s["note"][:120])
    xin = f"[{s['verdict'] or '?'}]({s['link']})" if s else "—"
    ob = f"[{e['orig_bee']}]({BO % int(e['orig_bee'])})" if e else "—"
    ab = f"[{e['aur_bee']}]({BA % int(e['aur_bee'])})" if e else "—"
    rows.append([samp, rse, ref + (f"<br>*{refsrc}*" if refsrc else ""), xin, ob, summ("orig", do), ab, summ("aur", da), "; ".join(notes)])
with open(OUT, "w") as o:
    o.write(open(OUT + ".head").read())
    o.write("| sample | RSE | hand-scan vertex (x, y, z) cm | Xin r2 Bee (scan verdict) | `original` Bee | `original` summary | `aurora` Bee | `aurora` summary | notes |\n|---|---|---|---|---|---|---|---|---|\n")
    for r in rows: o.write("| " + " | ".join(r) + " |\n")
print(len(rows), "rows")
