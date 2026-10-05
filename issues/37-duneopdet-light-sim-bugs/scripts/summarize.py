#!/usr/bin/env python3
"""Issue 37: summarize run-rerun.sh metrics over events and builds; print the gates and per-sample tables.

usage:  summarize.py [workarea, default /exp/dune/data/users/yuhw/wire-cell-toolkit-ai-helper-workarea/issue-37]
"""
import glob
import json
import os
import sys

WA = sys.argv[1] if len(sys.argv) > 1 else "/exp/dune/data/users/yuhw/wire-cell-toolkit-ai-helper-workarea/issue-37"
CFGS = ["stock", "legacy", "default", "track"]
R = {}
for f in glob.glob(os.path.join(WA, "rerun", "*", "*", "evt*", "metrics.json")):
    c, s, e = f.split(os.sep)[-4:-1]
    R[(c, s, int(e[3:]))] = json.load(open(f))
events = sorted({(s, i) for (_, s, i) in R})
L = []
p = L.append


def m(c, s, i):
    return R.get((c, s, i))


p("# Issue 37 rerun summary (" + ", ".join(f"{s} {i}" for s, i in events) + ")\n")
p("## Gates\n")
p("| event | stock == stored (wf, DivRec) | legacy == stored (wf, DivRec) | default: DivRec == stored | default: wf == stored | default: dup hits | track: Xe DivRec == stored |")
p("|---|---|---|---|---|---|---|")
for s, i in events:
    row = [f"{s} {i}"]
    for c in ("stock", "legacy"):
        x = m(c, s, i)
        row.append("n/a" if x is None else
                   ("yes" if x["wf_hash"] == x["wf_hash_stored"] else "**NO**") + ", " +
                   ("yes" if x["div_hash"] == x["div_hash_stored"] else "**NO**"))
    x = m("default", s, i)
    if x is None:
        row += ["n/a"] * 3
    else:
        row.append("yes" if x["div_hash"] == x["div_hash_stored"] else "**NO**")
        row.append("yes" if x["wf_hash"] == x["wf_hash_stored"] else "no (expected where legacy overlapped)")
        row.append(str(x["hits_dup"]))
    x = m("track", s, i)
    row.append("n/a" if x is None else
               ("yes" if all(x["div_hash"][d] == x["div_hash_stored"][d] for d in ("sipmXe10ppm", "sipmXe10ppmExt")) else "**NO**"))
    p("| " + " | ".join(row) + " |")

for smp in sorted({s for s, _ in events}):
    ev = [i for s, i in events if s == smp]
    p(f"\n## {smp} ({len(ev)} events: {', '.join(map(str, ev))})\n")
    p("| build | snippets | samples | stored again (frac) | of which differ | same-start snippets | hits | dup hits (frac) | hit PE | dup PE (frac) | pre-trigger RMS (median) | MARLEY Ar PE / Ar photon | MARLEY Ar+ArExt PE | MARLEY total PE | all PE |")
    p("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in CFGS:
        xs = [m(c, smp, i) for i in ev if m(c, smp, i)]
        if not xs:
            continue
        S = lambda k: sum(x[k] for x in xs)  # noqa: E731
        sa, ag, nh, nd, pe, ped = S("samples"), S("samples_again"), S("hits"), S("hits_dup"), S("hit_pe"), S("hit_pe_dup")
        arpe = sum(x["marley_pe"].get("sipmAr10ppm", 0) for x in xs)
        arph = sum(x["marley_photons"].get("PDFastSimAr", 0) for x in xs)
        arall = sum(x["marley_pe"].get("sipmAr10ppm", 0) + x["marley_pe"].get("sipmAr10ppmExt", 0) for x in xs)
        mt = sum(sum(x["marley_pe"].values()) for x in xs)
        at = sum(sum(x["all_pe"].values()) for x in xs)
        p(f"| {c} ({len(xs)}) | {S('snippets'):.0f} | {sa:.0f} | {ag:.0f} ({ag / sa:.4f}) | {S('samples_again_differ'):.0f} | "
          f"{S('snippets_same_start'):.0f} | {nh:.0f} | {nd:.0f} ({nd / max(nh, 1):.4f}) | {pe:.0f} | {ped:.0f} ({ped / max(pe, 1e-9):.4f}) | "
          f"{sum(x.get('prerms15_median', float('nan')) * x.get('prerms15_n', 0) for x in xs) / max(sum(x.get('prerms15_n', 0) for x in xs), 1):.3f} | "
          f"{arpe / max(arph, 1):.4f} | {arall:.0f} | {mt:.0f} | {at:.0f} |")
out = "\n".join(L) + "\n"
open(os.path.join(WA, "summary.md"), "w").write(out)
print(out)
