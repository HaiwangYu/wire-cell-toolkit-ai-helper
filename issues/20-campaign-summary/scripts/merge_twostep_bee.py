#!/usr/bin/env python3
"""Combine the 2-step's FOUR per-event Bee zips into one multi-event set.

Xin's 2-step writes mabc-apa0-face0 / mabc-apa1-face0 / mabc-all-apa / mabc-pr
separately; our 1-step writes ONE zip via a shared Bee sink (issue 13 G4).  To
view the 2-step the same way, the four are combined here with the same collision
rules the shared sink applies:

  * channel-deadarea-* appears in three of the four -- take it ONCE (from
    all-apa), exactly as save_deadarea=false does for the 1-step's PR node.
  * clustering-global appears in BOTH all-apa and pr -- keep all-apa's, and
    rename pr's to clustering-pr-global, which is what the 1-step's shared sink
    renames it to.

  merge_twostep_bee.py <out.zip> <evtdir> [evtdir ...]
"""
import sys, os, re, zipfile

out, dirs = sys.argv[1], sys.argv[2:]
PAT = re.compile(r'^([^/]+)/(\d+)/(\d+)-(.*)$')
# (zip, layer) -> emitted name;  None = drop
PLAN = [
    ('mabc-apa0-face0.zip', {'clustering-apa0-face0.json': 'clustering-apa0-face0.json'}),
    ('mabc-apa1-face0.zip', {'clustering-apa1-face0.json': 'clustering-apa1-face0.json'}),
    ('mabc-all-apa.zip',    {'clustering-global.json': 'clustering-global.json',
                             'img-global.json': 'img-global.json',
                             'op.json': 'op.json',
                             'channel-deadarea-apa0-face0.json': 'channel-deadarea-apa0-face0.json',
                             'channel-deadarea-apa1-face0.json': 'channel-deadarea-apa1-face0.json'}),
    ('mabc-pr.zip',         {'clustering-global.json': 'clustering-pr-global.json',
                             'mc.json': 'mc.json',
                             'shower_track-global.json': 'shower_track-global.json',
                             'track_fit-global.json': 'track_fit-global.json',
                             'vertices-global.json': 'vertices-global.json'}),
]
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zo:
    for k, d in enumerate(dirs):
        wrote = []
        for zname, mapping in PLAN:
            p = os.path.join(d, zname)
            if not os.path.exists(p):
                print("  MISSING %s in %s" % (zname, d)); continue
            with zipfile.ZipFile(p) as zi:
                for n in zi.namelist():
                    m = PAT.match(n)
                    if not m: continue
                    prefix, _a, _b, layer = m.groups()
                    tgt = mapping.get(layer)
                    if tgt is None: continue
                    zo.writestr("%s/%d/%d-%s" % (prefix, k, k, tgt), zi.read(n))
                    wrote.append(tgt)
        print("  evt%d %-18s %d layers" % (k, os.path.basename(d)[4:], len(wrote)))
print("wrote %s : %d event(s)" % (out, len(dirs)))
