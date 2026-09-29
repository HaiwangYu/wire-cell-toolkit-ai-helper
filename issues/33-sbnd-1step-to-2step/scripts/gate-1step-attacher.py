#!/usr/bin/env python3
"""G-A fallback (issue 33 M3): when the 1-step job is no longer byte-identical to <ref>, the ONLY
allowed change is the attacher swap -- wclsTensorSetMetadataAttacher:{rse_apa0,rse_apa1,rse_all_apa}
(data {}) -> wclsTruthInformationAttacher:{same, data {truth: false}} + wclsTruthInformationAttacher:truth
(spliced between labeler_truth and the PR MABC), and the Pgrapher edges that splice implies.
usage: gate-1step-attacher.py <pre.json> <new.json> <label>"""
import json, sys
pre, new, label = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3]
tn = lambda c: c['type'] + (':' + c['name'] if c.get('name') else '')
A, B = {tn(c): c for c in pre}, {tn(c): c for c in new}
RSE = ['rse_apa0', 'rse_apa1', 'rse_all_apa']
exp_a = {'wclsTensorSetMetadataAttacher:' + n for n in RSE}
exp_b = {'wclsTruthInformationAttacher:' + n for n in RSE} | {'wclsTruthInformationAttacher:truth'}
ok = set(A) - set(B) == exp_a and set(B) - set(A) == exp_b
for n in RSE:
    ok &= B.get('wclsTruthInformationAttacher:' + n, {}).get('data') == {'truth': False}
diff = [k for k in set(A) & set(B) if A[k] != B[k] and k != 'Pgrapher']
ok &= not diff
# edges: rename, and labeler_truth -> X becomes labeler_truth -> truth -> X
ren = lambda s: s.replace('wclsTensorSetMetadataAttacher:', 'wclsTruthInformationAttacher:')
ea = sorted((ren(e['tail']['node']), ren(e['head']['node'])) for e in A['Pgrapher']['data']['edges'])
eb = sorted((e['tail']['node'], e['head']['node']) for e in B['Pgrapher']['data']['edges'])
lt, tr = 'wclsTensorSetLabeler:labeler_truth', 'wclsTruthInformationAttacher:truth'
spliced = sorted([(t, h) for t, h in ea if t != lt] + [(lt, tr)] + [(tr, h) for t, h in ea if t == lt])
ok &= spliced == eb
print(f'G-A {label}: attacher swap only -> {"PASS" if ok else "FAIL"} (only pre {sorted(set(A) - set(B))}, only new {sorted(set(B) - set(A))}, other differing {sorted(diff)}, edges spliced {spliced == eb})')
sys.exit(0 if ok else 1)
