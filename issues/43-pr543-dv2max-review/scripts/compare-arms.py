#!/usr/bin/env python3
"""compare-arms.py <run dir A> <run dir B> [--ignore TREE.BRANCH ...]
Value-by-value comparison of every pr_evt<E>/tracking-pr.root of two step-2 runs of the same input (uproot +
awkward, exact, NaN == NaN): trees, entries, branch lists, every branch.  Prints a JSON verdict as the last
line; exit 0 if identical apart from --ignore'd branches.  Run with the wire-cell-python venv (uproot)."""
import argparse, collections, glob, json, os, sys
import awkward as ak, numpy as np, uproot

ap = argparse.ArgumentParser()
ap.add_argument('a'); ap.add_argument('b')
ap.add_argument('--ignore', nargs='*', default=[])
a = ap.parse_args()
res = dict(events=0, trees=0, branches=0, diffs=collections.Counter(), ignored=collections.Counter(), unreadable=collections.Counter())


def equal(x, y):
    try:
        if ak.to_list(ak.num(x, axis=0)) != ak.to_list(ak.num(y, axis=0)):
            return False
        fx, fy = ak.flatten(x, axis=None), ak.flatten(y, axis=None)
        nx, ny = ak.to_numpy(fx), ak.to_numpy(fy)
        if nx.shape != ny.shape:
            return False
        if nx.dtype.kind == 'f' or ny.dtype.kind == 'f':
            return bool(np.array_equal(nx, ny, equal_nan=True))
        return bool(np.array_equal(nx, ny))
    except Exception:
        return ak.to_list(x) == ak.to_list(y)


def ignored(key):
    return any(key == g or key.startswith(g + '.') for g in a.ignore)


def evs(d):
    return {os.path.basename(os.path.dirname(f)): f for f in glob.glob(os.path.join(d, 'pr_evt*', 'tracking-pr.root'))}


A, B = evs(a.a), evs(a.b)
for e in sorted(set(A) ^ set(B)):
    res['diffs']['event %s only in %s' % (e, 'A' if e in A else 'B')] += 1
for e in sorted(set(A) & set(B)):
    res['events'] += 1
    fa, fb = uproot.open(A[e]), uproot.open(B[e])
    ka = {k.split(';')[0]: c for k, c in fa.classnames().items()}
    kb = {k.split(';')[0]: c for k, c in fb.classnames().items()}
    for k in sorted(set(ka) ^ set(kb)):
        res['diffs']['object %s only in %s' % (k, 'A' if k in ka else 'B')] += 1
    for name in sorted(set(ka) & set(kb)):
        if ka[name] != 'TTree':
            continue
        ta, tb = fa[name], fb[name]
        res['trees'] += 1
        if ta.num_entries != tb.num_entries:
            res['diffs']['%s entries' % name] += 1
            continue
        for br in ta.keys():
            if br not in tb.keys():
                res['diffs']['%s.%s only in A' % (name, br)] += 1
                continue
            key = '%s.%s' % (name, br)
            try:
                x, y = ta[br].array(library='ak'), tb[br].array(library='ak')
            except Exception:
                res['unreadable'][key] += 1
                continue
            res['branches'] += 1
            if not equal(x, y):
                res['ignored' if ignored(key) else 'diffs'][key] += 1
for k in ('diffs', 'ignored', 'unreadable'):
    res[k] = dict(res[k])
res['identical'] = not res['diffs']
print(json.dumps(res))
sys.exit(0 if res['identical'] else 1)
