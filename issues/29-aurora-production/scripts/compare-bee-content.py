#!/usr/bin/env python3
"""Content comparison of Xin's standalone PR-job Bee zips against the 1-step's mabc.zip.
usage: compare-bee-content.py <dir of Xin bee_<E>.zip> <dir of 1-step bee_<E>.zip>

Layer by layer (json.loads equality, i.e. exact numbers), after the three differences
the two chains have BY CONSTRUCTION (issue 32, measured 2026-09-26):
  * Xin's "clustering-global" layer is the PR-stage grouping; the 1-step writes that same
    content as "clustering-pr-global" (its own "clustering-global" is the pre-PR grouping)
    -> compare Xin clustering-global with ours clustering-pr-global, ignoring the "type"
       string (the layer's own name label);
  * the 1-step's layers carry an extra "opflash_time" per-point key (ignored);
  * the Bee "mc" node's text line: Xin's PR job writes "numu 0.000 nue 0.000" (the scores
    are not in its text), the 1-step writes the BDT scores (ignored; the scores themselves
    are compared through tracking-pr.root T_kine).
Everything else must be equal.  No ROOT needed."""
import glob, json, os, re, sys
A, B = sys.argv[1], sys.argv[2]
pat = re.compile(r'^([^/]+)/(\d+)/(\d+)-(.*)$')
import zipfile
def mem(z):
    zf = zipfile.ZipFile(z); return {pat.match(n).group(4): zf.read(n) for n in zf.namelist() if pat.match(n)}
ident = tot = 0; bad = []
for za in sorted(glob.glob(A + '/*.zip')):
    b = os.path.basename(za); zb = os.path.join(B, b)
    if not os.path.exists(zb): print('MISSING in B:', b); continue
    ma, mb = mem(za), mem(zb); tot += 1; ev = []
    for k in sorted(ma):
        kb = 'clustering-pr-global.json' if k == 'clustering-global.json' else k
        if kb not in mb: ev.append(k + ' (absent in B)'); continue
        ja, jb = json.loads(ma[k]), json.loads(mb[kb])
        if isinstance(jb, dict):
            jb.pop('opflash_time', None)
            if k == 'clustering-global.json': ja.pop('type', None); jb.pop('type', None)
        if k == 'mc.json':
            for j in (ja, jb):
                for node in j: node.pop('text', None)
        if ja != jb: ev.append(k)
    if ev: bad.append((b, ev))
    else: ident += 1
for b, ev in bad: print(b, 'DIFFERS:', ', '.join(ev))
print(f'=> {tot} events: Bee content identical {ident}, differing {len(bad)}  (layers of the reference; structural differences excluded, see the docstring)')
