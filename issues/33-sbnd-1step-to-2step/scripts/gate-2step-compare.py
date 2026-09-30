#!/usr/bin/env python3
"""G-B / G-C of gate-2step-cfg.sh (issue 33): compare compiled configs.
usage: gate-2step-compare.py <1-step hits.json> <step1.json> <step2.json> <label>

G-B  step 1 vs the 1-step: every component present in both is identical (data), except the
     wire-cell cmdline and the Pgrapher edge list; only-in-step1 is exactly TensorFileSink:ql_pctree;
     only-in-1step is inside the PR tail's closure (clus_pr + everything it references,
     labeler_tagger, TensorFileSink:clus_all_apa).
G-C  step 2 vs the 1-step: every component of step 2's PR closure exists in the 1-step with
     identical data, except the ALLOWED keys (output file names, the Bee sink, event_from_ident),
     and the 1-step's PR closure has nothing step 2 lacks."""
import json, sys
one, s1, s2 = (json.load(open(f)) for f in sys.argv[1:4]); label = sys.argv[4]
def tn(c): return c['type'] + (':' + c['name'] if c.get('name') else '')
def idx(cfg): return {tn(c): c for c in cfg}
I1, IS1, IS2 = idx(one), idx(s1), idx(s2)
FRAME = {'wire-cell', 'Pgrapher'}
def closure(I, roots):
    seen, todo = set(), [r for r in roots if r in I]
    while todo:
        k = todo.pop()
        if k in seen: continue
        seen.add(k)
        def walk(v):
            if isinstance(v, str):
                if v in I and v not in seen: todo.append(v)
            elif isinstance(v, list): [walk(x) for x in v]
            elif isinstance(v, dict): [walk(x) for x in v.values()]
        walk(I[k].get('data', {}))
    return seen
def ddiff(a, b):
    da, db = a.get('data', {}), b.get('data', {})
    return sorted(k for k in set(da) | set(db) if da.get(k) != db.get(k))
ok = True
# ---- G-B
tail1 = closure(I1, ['MultiAlgBlobClustering:clus_pr', 'wclsTensorSetLabeler:labeler_tagger', 'TensorFileSink:clus_all_apa'])
head1 = closure(I1, [k for k in I1 if k not in tail1 and k not in FRAME])
only1 = sorted(set(I1) - set(IS1)); onlys1 = sorted(set(IS1) - set(I1))
bad_only1 = [k for k in only1 if k not in tail1]
diffs = [(k, ddiff(I1[k], IS1[k])) for k in sorted(set(I1) & set(IS1)) if k not in FRAME and I1[k] != IS1[k]]
print(f'G-B {label}: 1-step {len(I1)} vs step1 {len(IS1)} components; only in 1-step {len(only1)} (all in the PR tail: {not bad_only1}); only in step1 {onlys1}; shared components differing: {len(diffs)}')
for k, keys in diffs: print(f'   DIFFERS {k}: {keys}')
if bad_only1: print('   only-in-1step OUTSIDE the PR tail:', bad_only1)
gb = (not diffs) and (not bad_only1) and onlys1 == ['TensorFileSink:ql_pctree']
print(f'G-B {label}: {"PASS" if gb else "FAIL"}'); ok &= gb
# ---- G-C
# bee_sink: step 2's own Bee zip.  bee_zip: the node's private zip name, unused when bee_sink is
# set.  event_from_ident: clus.jsonnet's required partner of evt_subdir (the RSE still comes from
# the step-1 metadata, which MABC ranks above the ident).  (reset_shower_ids_per_event is a pr()
# default since the PR 535 review, so both chains carry it and it is no longer allowed to differ.)
ALLOWED = {'MultiAlgBlobClustering:clus_pr': {'bee_sink', 'bee_zip', 'event_from_ident'},
           'SbndPrMagnifyTrackingVisitor:pr': {'output_filename'},
           'UbooneTaggerOutputVisitor:pr': {'output_filename'}}
pr1 = closure(I1, ['MultiAlgBlobClustering:clus_pr']) - {'BeeSink:mabc_shared'}
pr2 = closure(IS2, ['MultiAlgBlobClustering:clus_pr']) - {'BeeSink:mabc_pr'}
# step 2 may append TaggerBeeVisitor:pr (the tagger Bee sets the 1-step's art-side labeler_tagger writes)
EXTRA_OK = {'TaggerBeeVisitor:pr'}
missing2 = sorted(pr1 - pr2); extra2 = sorted(pr2 - pr1 - EXTRA_OK)
gc = not missing2 and not extra2
print(f'G-C {label}: PR closure 1-step {len(pr1)} vs step2 {len(pr2)} components; missing in step2 {missing2}; extra in step2 {extra2}')
for k in sorted(pr1 & pr2):
    keys = ddiff(I1[k], IS2[k])
    if not keys: continue
    bad = [x for x in keys if x not in ALLOWED.get(k, set())]
    if k == 'MultiAlgBlobClustering:clus_pr' and 'pipeline' in bad:
        p1, p2 = I1[k]['data']['pipeline'], IS2[k]['data']['pipeline']
        if p2[:len(p1)] == p1 and set(p2[len(p1):]) <= EXTRA_OK: bad.remove('pipeline')   # only the appended extras
    for x in keys:
        print(f'   {"allowed " if x not in bad else "UNEXPECTED"} {k}.{x}: 1-step={json.dumps(I1[k]["data"].get(x))} step2={json.dumps(IS2[k]["data"].get(x))}')
    if bad: gc = False
print(f'G-C {label}: {"PASS" if gc else "FAIL"}'); ok &= gc
sys.exit(0 if ok else 1)
