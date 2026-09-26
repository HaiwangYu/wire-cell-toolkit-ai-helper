#!/usr/bin/env python3
"""Every differing branch, with values, of tracking-pr.root for GIVEN events, between a
reference layout (<ref>/evt_<E>/tracking-pr.root) and an arm (<arm>/tracking-pr_<E>.root) --
the per-event drill-down the census (branch-diff-tracking-pr.py, one example per branch)
does not give.  Run INSIDE SL7 (ROOT).
usage: evt-branch-diff.py <ref dir> <arm dir> <E> [<E> ...]"""
import sys, ROOT
ROOT.gErrorIgnoreLevel = ROOT.kFatal
REF, ARM = sys.argv[1], sys.argv[2]
TREES = ['Trun', 'T_kine', 'T_tagger', 'T_cluster', 'T_rec_charge']
KEYS = ['numu_score', 'nue_score', 'numu_cc_flag', 'nue_cc_flag', 'kine_reco_Enu', 'kine_pio_mass', 'kine_pio_flag',
        'event_type', 'flag_main_cluster', 'match_isFC', 'stm_lowenergy', 'stm_LM', 'stm_TGM', 'stm_STM', 'stm_FullDead']
def vals(t, nm):
    v = getattr(t, nm)
    if hasattr(v, '__len__') and not isinstance(v, str): return [float(x) for x in v]
    return [float(v)]
for e in sys.argv[3:]:
    fa = ROOT.TFile.Open('%s/evt_%s/tracking-pr.root' % (REF, e)); fb = ROOT.TFile.Open('%s/tracking-pr_%s.root' % (ARM, e))
    print('=== event', e)
    for tn in TREES:
        ta, tb = fa.Get(tn), fb.Get(tn)
        if not ta or not tb: print('  %s: missing' % tn); continue
        na, nb = ta.GetEntries(), tb.GetEntries()
        if tn == 'T_rec_charge':
            print('  T_rec_charge entries %d vs %d' % (na, nb)); continue
        if na != nb: print('  %s entries %d vs %d' % (tn, na, nb))
        ndiff = 0; shown = 0
        for i in range(min(na, nb)):
            ta.GetEntry(i); tb.GetEntry(i)
            for b in ta.GetListOfBranches():
                nm = b.GetName()
                try: va, vb = vals(ta, nm), vals(tb, nm)
                except Exception: continue
                if va != vb:
                    ndiff += 1
                    if shown < 40:
                        sa, sb = (str(va[:6]) if len(va) > 1 else '%g' % va[0]), (str(vb[:6]) if len(vb) > 1 else '%g' % vb[0])
                        print('    %-10s %-42s ref=%s arm=%s%s' % (tn, nm, sa, sb, '' if len(va) == len(vb) else ' (len %d vs %d)' % (len(va), len(vb))))
                        shown += 1
        print('  %s: %d differing branches' % (tn, ndiff))
    # the headline scalars, whatever tree holds them
    for tn in ('T_kine', 'T_tagger'):
        ta, tb = fa.Get(tn), fb.Get(tn)
        if not ta or not tb: continue
        ta.GetEntry(0); tb.GetEntry(0)
        for k in KEYS:
            if ta.GetBranch(k):
                va, vb = vals(ta, k), vals(tb, k)
                if va != vb: print('    HEADLINE %s.%s ref=%s arm=%s' % (tn, k, va, vb))
