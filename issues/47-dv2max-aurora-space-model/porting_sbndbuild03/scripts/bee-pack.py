#!/usr/bin/env python3
"""bee-pack.py <order.csv> <out dir> <arm>=<runs dir> ...   (issue 47, task A)

One Bee zip per arm (<out dir>/bee-<arm>.zip) from the step-2 mabc-pr.zip of every unit, re-indexed to ONE event
order shared by all arms, so Bee event k is the same RSE in every set (flip between the sets with the same k).
<order.csv>: columns unit, run, subrun, event in the wanted order (data-compare.py's event table, sorted).
The mabc-pr.zip events are matched by (unit, eventNo) -- the Bee JSON's eventNo; its runNo is not reliable in
step 2 (rse_from_ident gives the event only).  Writes <out dir>/bee-index.csv (arm, unit, run, subrun, event,
bee_index, src_index); an event missing from an arm's zip is listed with an empty bee_index."""
import csv
import json
import os
import re
import sys
import zipfile

ORDER, OUT = sys.argv[1], sys.argv[2]
ARMS = [a.split("=", 1) for a in sys.argv[3:]]
os.makedirs(OUT, exist_ok=True)
order = [(r["unit"], int(r["run"]), int(r["subrun"]), int(r["event"])) for r in csv.DictReader(open(ORDER))]
pat = re.compile(r"^data/(\d+)/\1-(.+\.json)$")
idx = []
for arm, R in ARMS:
    src = {}   # (unit, eventNo) -> (zip path, src index, [(name, alg)])
    for unit in sorted({u for u, *_ in order}):
        zp = os.path.join(R, "data--" + unit, "mabc-pr.zip")
        z = zipfile.ZipFile(zp)
        by = {}
        for n in z.namelist():
            m = pat.match(n)
            if m:
                by.setdefault(int(m.group(1)), []).append((n, m.group(2)))
        for i, files in by.items():
            js = [json.loads(z.read(n)) for n, _ in files]
            ev = {int(j["eventNo"]) for j in js if isinstance(j, dict) and "eventNo" in j}   # some layers are lists
            assert len(ev) == 1, (zp, i, ev)
            key = (unit, ev.pop())
            assert key not in src, ("duplicate event", arm, key)
            src[key] = (zp, i, files)
    with zipfile.ZipFile(os.path.join(OUT, f"bee-{arm}.zip"), "w", zipfile.ZIP_DEFLATED) as zo:
        k = 0
        for unit, run, sub, evt in order:
            s = src.get((unit, evt))
            if s is None:
                idx.append(dict(arm=arm, unit=unit, run=run, subrun=sub, event=evt, bee_index="", src_index=""))
                continue
            zp, i, files = s
            with zipfile.ZipFile(zp) as zi:
                for n, alg in files:
                    zo.writestr(f"data/{k}/{k}-{alg}", zi.read(n))
            idx.append(dict(arm=arm, unit=unit, run=run, subrun=sub, event=evt, bee_index=k, src_index=i))
            k += 1
    print(arm, "events", k, "of", len(order), "->", os.path.join(OUT, f"bee-{arm}.zip"))
with open(os.path.join(OUT, "bee-index.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(idx[0]))
    w.writeheader()
    w.writerows(idx)
