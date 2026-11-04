#!/usr/bin/env python3
"""PR 544 review, item 1: compare two step-2 Bee zips (mabc-pr.zip) EVENT BY EVENT, keyed by RSE
rather than by the zip member name (a split of a merged event shifts every later Bee index).

    bee-by-rse.py <ref mabc-pr.zip> <new mabc-pr.zip>

Per zip: the Bee events (data/<i>/), each one's RSE set (from the members that carry
runNo/subRunNo/eventNo), duplicate member names.  A Bee event whose members carry more than
one RSE, or that has duplicate member names, is MERGED.
Comparison: for every RSE, the set of (member type -> JSON) of the Bee event(s) carrying it;
equal / differ / only-in-one.  mc.json (no RSE) is keyed by its Bee event's RSE."""
import sys, json, zipfile, collections


def load(path):
    z = zipfile.ZipFile(path)
    ev = collections.defaultdict(list)              # index -> [(type, json)]
    for info in z.infolist():                       # infolist: duplicate names kept
        parts = info.filename.split('/')
        if len(parts) != 3 or parts[0] != 'data':
            continue
        idx = int(parts[1])
        typ = parts[2].split('-', 1)[1].rsplit('.', 1)[0]
        ev[idx].append((typ, json.loads(z.read(info))))
    out = {}
    for idx, mem in ev.items():
        rses = {(d['runNo'], d['subRunNo'], d['eventNo']) for _, d in mem
                if isinstance(d, dict) and 'runNo' in d}
        names = [t for t, _ in mem]
        dup = sorted({t for t in names if names.count(t) > 1})
        out[idx] = dict(rses=rses, members=mem, dup=dup)
    return out


def by_rse(evs):
    m = collections.defaultdict(dict)
    for idx, e in evs.items():
        if len(e['rses']) != 1 or e['dup']:
            continue                                # merged: reported, not compared
        rse = next(iter(e['rses']))
        for t, d in e['members']:
            m[rse][t] = d
    return m


ref, new = load(sys.argv[1]), load(sys.argv[2])
for name, evs in (('ref', ref), ('new', new)):
    merged = {i: e for i, e in evs.items() if len(e['rses']) != 1 or e['dup']}
    print('%s: %d Bee events, %d merged' % (name, len(evs), len(merged)))
    for i, e in sorted(merged.items()):
        print('   index %d: RSEs %s, duplicate members %s' % (i, sorted(e['rses']), e['dup']))
R, N = by_rse(ref), by_rse(new)
merged_ref = set().union(*[e['rses'] for e in ref.values() if len(e['rses']) != 1 or e['dup']] or [set()])
same = differ = 0
for rse in sorted(set(R) | set(N)):
    if rse not in R or rse not in N:
        tag = '(merged in ref)' if rse in merged_ref else ''
        print('only in %s: %s %s' % ('new' if rse in N else 'ref', rse, tag))
        continue
    if R[rse] == N[rse]:
        same += 1
    else:
        differ += 1
        bad = sorted(t for t in set(R[rse]) | set(N[rse]) if R[rse].get(t) != N[rse].get(t))
        print('differ: %s %s' % (rse, bad))
print('events compared: %d equal, %d differ' % (same, differ))
