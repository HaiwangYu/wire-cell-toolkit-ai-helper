#!/usr/bin/env python3
"""compare_bee_zips.py <dirA> <dirB> [--rtol 1e-9]
Compare per-event Bee zips (same basenames in both dirs) layer by layer.
Level 1: member md5 identical.  Level 2 (if not): parse JSON and compare structure with numeric tolerance,
so a last-digit float-formatting difference between hosts is reported as 'numeric-only' rather than as a real change."""
import sys, os, glob, zipfile, hashlib, json, math, re
A, B = sys.argv[1], sys.argv[2]; rtol = float(sys.argv[sys.argv.index('--rtol')+1]) if '--rtol' in sys.argv else 1e-9
pat = re.compile(r'^([^/]+)/(\d+)/(\d+)-(.*)$')
def members(z):
    zf = zipfile.ZipFile(z); out = {}
    for n in zf.namelist():
        m = pat.match(n); key = m.group(4) if m else n
        out[key] = zf.read(n)
    return out
def numdiff(x, y, path, bad, maxrel):
    if isinstance(x, dict) and isinstance(y, dict):
        if set(x) != set(y): bad.append(f'{path}: keys differ {sorted(set(x)^set(y))[:5]}'); return
        for k in x: numdiff(x[k], y[k], path+'/'+k, bad, maxrel)
    elif isinstance(x, list) and isinstance(y, list):
        if len(x) != len(y): bad.append(f'{path}: length {len(x)} vs {len(y)}'); return
        for i, (a, b) in enumerate(zip(x, y)): numdiff(a, b, path+f'[{i}]', bad, maxrel)
    elif isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool):
        if x != y:
            rel = abs(x-y)/max(abs(x), abs(y), 1e-300); maxrel[0] = max(maxrel[0], rel)
            if rel > rtol or math.isnan(rel): bad.append(f'{path}: {x} vs {y}')
    elif x != y: bad.append(f'{path}: {str(x)[:40]!r} vs {str(y)[:40]!r}')
tot = ident = numonly = real = 0
for za in sorted(glob.glob(A+'/*.zip')):
    zb = os.path.join(B, os.path.basename(za))
    if not os.path.exists(zb): print('MISSING in B:', os.path.basename(za)); continue
    ma, mb = members(za), members(zb); tot += 1
    if set(ma) != set(mb): print(os.path.basename(za), 'LAYER SET DIFFERS', sorted(set(ma)^set(mb))); real += 1; continue
    ev_num, ev_real = [], []
    for k in sorted(ma):
        if hashlib.md5(ma[k]).digest() == hashlib.md5(mb[k]).digest(): continue
        try: ja, jb = json.loads(ma[k]), json.loads(mb[k])
        except Exception as e: ev_real.append(f'{k}: not JSON ({e})'); continue
        bad, maxrel = [], [0.0]; numdiff(ja, jb, k, bad, maxrel)
        if bad: ev_real.append(f'{k}: {len(bad)} diffs, e.g. {bad[0]}')
        else: ev_num.append(f'{k}: numeric-only, max rel {maxrel[0]:.1e}')
    if ev_real: real += 1; print(os.path.basename(za), 'DIFFERS:', '; '.join(ev_real[:4]))
    elif ev_num: numonly += 1; print(os.path.basename(za), 'numeric-only:', '; '.join(ev_num[:4]))
    else: ident += 1
print(f'=> {tot} events: identical {ident}, numeric-only (<= rtol {rtol}) {numonly}, real differences {real}')
