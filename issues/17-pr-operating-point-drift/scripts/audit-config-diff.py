#!/usr/bin/env python3
"""Diff two compiled WCT configs component-by-component.

  audit-config-diff.py <a.json> <b.json> [--label-a X --label-b Y]

Input is `wcsonnet` output: a JSON list of {type, name, data} components.
Components are keyed by (type, name); for each key present in both, the `data`
dicts are compared key by key.  Exit status is the number of differences, so
this works as a CI gate: 0 means the two configs are equivalent.

Why a script and not `diff`: wcsonnet emits components in graph order, which is
not stable between two different graphs (a 1-step chain and a 2-step step share
components but not ordering), so a textual diff is all noise.
"""
import json, sys, argparse

ap = argparse.ArgumentParser()
ap.add_argument('a'); ap.add_argument('b')
ap.add_argument('--label-a', default='A'); ap.add_argument('--label-b', default='B')
ap.add_argument('--skip-type', action='append', default=[],
                help='component type to ignore (repeatable); e.g. Pgrapher, wire-cell')
ap.add_argument('--expected-key', action='append', default=[],
                help=('data key whose difference is EXPECTED and does not count '
                      'towards the exit status (repeatable).  Use only for '
                      'deliberate design differences, never to hide a knob.'))
args = ap.parse_args()

def idx(path):
    d = {}
    for c in json.load(open(path)):
        if isinstance(c, dict) and 'type' in c:
            d[(c['type'], c.get('name', ''))] = c.get('data', {})
    return d

A, B = idx(args.a), idx(args.b)
print("%s: %d components | %s: %d components" % (args.label_a, len(A), args.label_b, len(B)))
shared = sorted(set(A) & set(B))
print("shared: %d\n" % len(shared))

total = 0
for key in shared:
    if key[0] in args.skip_type:
        continue
    da, db = A[key], B[key]
    only_a = sorted(set(da) - set(db))
    only_b = sorted(set(db) - set(da))
    differ = sorted(k for k in set(da) & set(db) if da[k] != db[k])
    exp = set(args.expected_key)
    only_a_r = [k for k in only_a if k not in exp]
    only_b_r = [k for k in only_b if k not in exp]
    differ_r = [k for k in differ if k not in exp]
    if not (only_a_r or only_b_r or differ_r):
        if (only_a or only_b or differ):
            print("### %s:%s  -- only expected differences" % key)
        continue
    print("### %s:%s" % key)
    for k in only_a:
        print("    only in %s : %-36s = %s" % (args.label_a, k, json.dumps(da[k])[:70]))
    for k in only_b:
        print("    only in %s : %-36s = %s" % (args.label_b, k, json.dumps(db[k])[:70]))
    for k in differ:
        print("    DIFFER      : %-36s %s=%s | %s=%s"
              % (k, args.label_a, json.dumps(da[k])[:50],
                    args.label_b, json.dumps(db[k])[:50]))
    total += len(only_a_r) + len(only_b_r) + len(differ_r)

print("\n%d differences" % total)
sys.exit(0 if total == 0 else 1)
