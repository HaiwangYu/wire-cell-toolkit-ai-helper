#!/usr/bin/env python3
"""Issue 48 P2: compare a new step-1 qlpctree.tar.gz with the kept one, tensor by tensor (the #41 V1b method).
   compare-qlpctree.py <new.tar.gz> <kept.tar.gz> [--json out.json]
Every member <x>_metadata.json / <x>_array.npy pair is keyed by its metadata datapath.  Equal means: the same
datapaths, the same array bytes (npy header + data), and the same metadata apart from 'input_file' (WCLS
input-file stamping differs by production).  Prints a JSON summary (last line); exit 0 if equal."""
import json, sys, tarfile, collections
new, old = sys.argv[1], sys.argv[2]
out = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
IGN = {'input_file'}


def load(path):
    raw = {}
    with tarfile.open(path) as t:
        for m in t.getmembers():
            if m.isfile():
                raw[m.name] = t.extractfile(m).read()
    ten, other = {}, {}
    for n, b in raw.items():
        if n.endswith('_metadata.json'):
            md = json.loads(b)
            dp = md.get('datapath', n)
            key = dp if dp not in ten else dp + '#' + n
            ten[key] = (md, raw.get(n[:-len('_metadata.json')] + '_array.npy'))
        elif not n.endswith('_array.npy'):
            other[n] = b
    return ten, other


A, oa = load(new)
B, ob = load(old)
r = collections.OrderedDict(new=new, kept=old, tensors_new=len(A), tensors_kept=len(B), arrays_equal=0,
                            only_new=sorted(set(A) - set(B))[:10], only_kept=sorted(set(B) - set(A))[:10],
                            n_only_new=len(set(A) - set(B)), n_only_kept=len(set(B) - set(A)),
                            array_diffs=[], metadata_diffs=collections.Counter(), ignored_metadata=collections.Counter(),
                            other_members_differ=sorted(k for k in set(oa) | set(ob) if oa.get(k) != ob.get(k))[:10])
for k in sorted(set(A) & set(B)):
    (ma, xa), (mb, xb) = A[k], B[k]
    if xa == xb:
        r['arrays_equal'] += 1
    else:
        r['array_diffs'].append(k)
    for f in set(ma) | set(mb):
        if ma.get(f) != mb.get(f):
            r['ignored_metadata' if f in IGN else 'metadata_diffs'][f] += 1
r['n_array_diffs'] = len(r['array_diffs']); r['array_diffs'] = r['array_diffs'][:10]
r['identical'] = (r['n_only_new'] == 0 and r['n_only_kept'] == 0 and r['n_array_diffs'] == 0
                  and not r['metadata_diffs'] and not r['other_members_differ'])
if out:
    json.dump(r, open(out, 'w'), indent=1)
print(json.dumps(r))
sys.exit(0 if r['identical'] else 1)
