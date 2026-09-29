#!/usr/bin/env python3
"""Split multi-event Bee zips (a 2-step run: step 1's mabc.zip per lar job + step 2's mabc-pr.zip
per wire-cell job) into ONE zip per event, laid out as the 1-step's per-event mabc.zip
(data/0/0-<layer>.json), so the per-event comparison tools apply unchanged.
The event of an index directory data/<i>/ is the eventNo of its layers (the mc layer has none;
it takes its siblings').  Two zips carrying the same layer for the same event is an error.
usage: bee-split.py <out dir> <zip> [<zip> ...]   ->  <out dir>/evt_<E>/mabc.zip"""
import collections, json, os, re, sys, zipfile
OUT = sys.argv[1]; pat = re.compile(r'^data/(\d+)/\d+-(.*)$')
per_evt = collections.defaultdict(dict); bad = 0
for zp in sys.argv[2:]:
    z = zipfile.ZipFile(zp); groups = collections.defaultdict(dict)
    for n in z.namelist():
        m = pat.match(n)
        if m: groups[m.group(1)][m.group(2)] = z.read(n)
    for i, layers in sorted(groups.items(), key=lambda kv: int(kv[0])):
        evs = set()
        for nm, b in layers.items():
            j = json.loads(b)
            if isinstance(j, dict) and 'eventNo' in j: evs.add(str(j['eventNo']))
        if len(evs) != 1: print(f'ERROR {zp} data/{i}: eventNo set {sorted(evs)}'); bad += 1; continue
        e = evs.pop()
        for nm, b in layers.items():
            if nm in per_evt[e]: print(f'ERROR event {e}: layer {nm} in two zips'); bad += 1
            per_evt[e][nm] = b
for e, layers in sorted(per_evt.items(), key=lambda kv: int(kv[0])):
    d = os.path.join(OUT, 'evt_' + e); os.makedirs(d, exist_ok=True)
    with zipfile.ZipFile(os.path.join(d, 'mabc.zip'), 'w', zipfile.ZIP_DEFLATED) as zo:
        for nm in sorted(layers): zo.writestr(f'data/0/0-{nm}', layers[nm])
print(f'split {len(sys.argv) - 2} zips into {len(per_evt)} per-event zips under {OUT} ({bad} errors)')
sys.exit(1 if bad else 0)
