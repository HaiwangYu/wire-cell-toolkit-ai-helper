#!/usr/bin/env python3
"""Per-event, per-layer EXACT comparison (json.loads equality) of Bee zips.
usage: bee-diff.py <ref dir: evt_<E>/mabc.zip> <arm dir: evt_<E>/mabc.zip> [--ignore <layer>,...]
Prints one line per event: identical, or the differing / ref-only / arm-only layers.
For a differing layer it names the top-level keys that differ (and, for per-point arrays, how many entries)."""
import glob, json, os, re, sys, zipfile
A, B = sys.argv[1], sys.argv[2]
IGN = set(sys.argv[sys.argv.index('--ignore') + 1].split(',')) if '--ignore' in sys.argv else set()
pat = re.compile(r'^data/\d+/\d+-(.*)\.json$')
def mem(z):
    zf = zipfile.ZipFile(z); return {pat.match(n).group(1): zf.read(n) for n in zf.namelist() if pat.match(n)}
def what(ja, jb):
    if type(ja) != type(jb): return 'type'
    if isinstance(ja, dict):
        out = []
        for k in sorted(set(ja) | set(jb)):
            if ja.get(k) == jb.get(k): continue
            va, vb = ja.get(k), jb.get(k)
            if isinstance(va, list) and isinstance(vb, list):
                n = sum(1 for x, y in zip(va, vb) if x != y)
                out.append(f'{k}[{n}/{len(va)}' + (f', len {len(va)} vs {len(vb)}' if len(va) != len(vb) else '') + ']')
            else: out.append(k)
        return ' '.join(out)
    return 'list' + (f' len {len(ja)} vs {len(jb)}' if len(ja) != len(jb) else '')
ident = tot = 0
for za in sorted(glob.glob(A + '/evt_*/mabc.zip'), key=lambda p: int(p.split('evt_')[1].split('/')[0])):
    e = za.split('evt_')[1].split('/')[0]; zb = os.path.join(B, 'evt_' + e, 'mabc.zip'); tot += 1
    if not os.path.exists(zb): print(f'{e}: MISSING in arm'); continue
    ma, mb = mem(za), mem(zb); parts = []
    ro = sorted(set(ma) - set(mb) - IGN); ao = sorted(set(mb) - set(ma) - IGN)
    if ro: parts.append('ref-only ' + ','.join(ro))
    if ao: parts.append('arm-only ' + ','.join(ao))
    for k in sorted((set(ma) & set(mb)) - IGN):
        if ma[k] == mb[k]: continue
        ja, jb = json.loads(ma[k]), json.loads(mb[k])
        if ja != jb: parts.append(f'{k}: {what(ja, jb)}')
    if parts: print(f'{e}: ' + ' | '.join(parts))
    else: ident += 1; print(f'{e}: identical ({len(set(ma) - IGN)} layers)')
print(f'=> {tot} events: Bee identical {ident}, differing {tot - ident}' + (f' (ignored layers: {sorted(IGN)})' if IGN else ''))
