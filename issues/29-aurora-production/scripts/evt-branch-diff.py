#!/usr/bin/env python3
"""Every differing branch, with values, of tracking-pr.root for GIVEN events, between a
reference layout (<ref>/evt_<E>/tracking-pr.root) and an arm (<arm>/tracking-pr_<E>.root) --
the per-event drill-down the census (branch-diff-tracking-pr.py, one example per branch)
does not give.  Run INSIDE SL7 (ROOT).
usage: evt-branch-diff.py [--json out.json] [--max N] <ref dir> <arm dir> <E> [<E> ...]
  --json  also write a machine-readable summary (per event, per tree, per branch: ref, arm,
          lengths; T_rec_charge: entries and, when equal, the max abs / rel difference per branch)
  --max   lines of branch detail printed per tree (default 40; 0 = all)"""
import sys, json, math, ROOT
ROOT.gErrorIgnoreLevel = ROOT.kFatal
args = sys.argv[1:]; JSON = None; MAX = 40
while args and args[0].startswith('--'):
    if args[0] == '--json': JSON = args[1]; args = args[2:]
    elif args[0] == '--max': MAX = int(args[1]); args = args[2:]
    else: break
REF, ARM = args[0], args[1]
TREES = ['Trun', 'T_kine', 'T_tagger', 'T_cluster', 'T_rec_charge', 'T_bad_ch', 'T_proj', 'T_proj_data']
KEYS = ['numu_score', 'nue_score', 'numu_cc_flag', 'nue_cc_flag', 'kine_reco_Enu', 'kine_pio_mass', 'kine_pio_flag',
        'event_type', 'flag_main_cluster', 'match_isFC', 'stm_lowenergy', 'stm_LM', 'stm_TGM', 'stm_STM', 'stm_FullDead']
def vals(t, nm):
    v = getattr(t, nm)
    if hasattr(v, '__len__') and not isinstance(v, str): return [float(x) for x in v]
    return [float(v)]
def fmt(v): return ('%g' % v[0]) if len(v) == 1 else ('[' + ', '.join('%g' % x for x in v[:6]) + (', ...' if len(v) > 6 else '') + ']')
summary = {}
for e in args[2:]:
    fa = ROOT.TFile.Open('%s/evt_%s/tracking-pr.root' % (REF, e)); fb = ROOT.TFile.Open('%s/tracking-pr_%s.root' % (ARM, e))
    print('=== event', e); S = summary[e] = {'trees': {}, 'headline': {}}
    for tn in TREES:
        ta, tb = fa.Get(tn), fb.Get(tn)
        if not ta or not tb:
            if ta or tb: print('  %s: present only in %s' % (tn, 'ref' if ta else 'arm')); S['trees'][tn] = {'only_in': 'ref' if ta else 'arm'}
            continue
        na, nb = ta.GetEntries(), tb.GetEntries()
        T = S['trees'][tn] = {'entries': [na, nb], 'branches': {}}
        if na != nb: print('  %s entries %d vs %d' % (tn, na, nb))
        # per-branch: number of entries differing, max abs / rel, first example
        for b in ta.GetListOfBranches():
            nm = b.GetName(); ndiff = 0; mabs = 0.0; mrel = 0.0; ex = None
            for i in range(min(na, nb)):
                ta.GetEntry(i); tb.GetEntry(i)
                try: va, vb = vals(ta, nm), vals(tb, nm)
                except Exception: break
                if va == vb: continue
                ndiff += 1
                if len(va) == len(vb):
                    for x, y in zip(va, vb):
                        d = abs(x - y); mabs = max(mabs, d)
                        r = d / max(abs(x), abs(y)) if max(abs(x), abs(y)) > 0 else 0.0
                        if not math.isnan(r): mrel = max(mrel, r)
                if ex is None: ex = (i, va, vb)
            if ndiff:
                T['branches'][nm] = {'nentries_differ': ndiff, 'max_abs': mabs, 'max_rel': mrel,
                                     'example': {'entry': ex[0], 'ref': ex[1][:12], 'arm': ex[2][:12], 'len': [len(ex[1]), len(ex[2])]}}
        nb_ = len(T['branches'])
        if tn == 'T_rec_charge':
            print('  T_rec_charge entries %d vs %d; %d branches differ%s' % (na, nb, nb_, ('' if na != nb else ', max rel %.2e' % max([v['max_rel'] for v in T['branches'].values()] + [0]))))
        else:
            shown = 0
            for nm, v in T['branches'].items():
                if MAX and shown >= MAX: break
                ex = v['example']
                print('    %-10s %-42s ref=%s arm=%s%s' % (tn, nm, fmt(ex['ref']), fmt(ex['arm']), '' if ex['len'][0] == ex['len'][1] else ' (len %d vs %d)' % tuple(ex['len'])))
                shown += 1
            print('  %s: %d differing branches' % (tn, nb_))
    for tn in ('T_kine', 'T_tagger'):
        ta, tb = fa.Get(tn), fb.Get(tn)
        if not ta or not tb or not ta.GetEntries() or not tb.GetEntries(): continue
        ta.GetEntry(0); tb.GetEntry(0)
        for k in KEYS:
            if ta.GetBranch(k):
                va, vb = vals(ta, k), vals(tb, k)
                if va != vb: print('    HEADLINE %s.%s ref=%s arm=%s' % (tn, k, fmt(va), fmt(vb))); S['headline'][k] = [va, vb]
if JSON:
    json.dump(summary, open(JSON, 'w'), indent=1); print('wrote', JSON)
