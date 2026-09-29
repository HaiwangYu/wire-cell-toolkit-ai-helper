#!/usr/bin/env python3
"""Markdown table, one row per event, of the 1-step vs 2-step comparison of a run-2step.pbs run.
No ROOT needed (reads the job's outputs).
usage: evt-table-2step.py <2-step run dir> <1-step ref run dir> <title> [<evt-diff json>]
  <run>/cmp/evt-diff-all.json   every branch of every tree, per event (evt-branch-diff.py, all trees)
                                (or the 4th argument)
  <run>/cmp/bee_diff.txt        every Bee layer, per event (bee-diff.py)
  <run>/cmp/summary-{1,2}step.json  Enu / scores / truth per event (evt-summary.py)
  <run>/bee-upload/bee-order.txt    Bee index -> event (both uploads use this order)
  <ref>/rse-by-nskip.tsv        run / subrun of each event"""
import json, os, re, sys
R, REF, title = sys.argv[1:4]
J = json.load(open(sys.argv[4] if len(sys.argv) > 4 else R + '/cmp/evt-diff-all.json'))
S1 = json.load(open(R + '/cmp/summary-1step.json')); S2 = json.load(open(R + '/cmp/summary-2step.json'))
order = [l.split() for l in open(R + '/bee-upload/bee-order.txt')]
bee = {}
for l in open(R + '/cmp/bee_diff.txt'):
    m = re.match(r'(\d+): (.*)', l)
    if m: bee[m.group(1)] = m.group(2)
rse = {}
for l in open(REF + '/rse-by-nskip.tsv'):
    f = l.split('\t')
    if f[0] != 'nskip' and f[3] != '-': rse[f[3]] = (f[1], f[2])
FL = {12: 'nue', -12: 'anti-nue', 14: 'numu', -14: 'anti-numu', 16: 'nutau', -16: 'anti-nutau'}
def num(v, f='%.1f'): return '–' if v is None else f % v
def pair(a, b, f):
    if a == b: return num(a, f) + ' / =' if a is not None else '– / –'
    return '**%s / %s**' % (num(a, f), num(b, f))
rows = []; n_tr = n_bee = 0; is_mc = any(S2[e].get('truth') for e in S2)
for idx, e in order:
    T = J[e]['trees']
    diffs, only = [], []
    for tn, t in T.items():
        if 'only_in' in t: only.append('%s only in %s' % (tn, {'ref': '1-step', 'arm': '2-step'}[t['only_in']])); continue
        if t['entries'][0] != t['entries'][1]: diffs.append('%s entries %d vs %d' % (tn, *t['entries']))
        if t.get('branches'): diffs.append('%s: %s' % (tn, ', '.join(sorted(t['branches']))))
    shared = [tn for tn, t in T.items() if 'only_in' not in t]
    if not diffs:
        n_tr += 1
        ent = {tn: T[tn]['entries'][0] for tn in ('T_cluster', 'T_rec_charge') if tn in T}
        tr = 'identical, every branch of %d trees (T_cluster %s, T_rec_charge %s entries)' % (len(shared), ent.get('T_cluster', '–'), ent.get('T_rec_charge', '–'))
        if only: tr += '; ' + '; '.join(only)
    else:
        tr = '**differs**: ' + '; '.join(diffs) + ('; ' + '; '.join(only) if only else '')
    b = bee.get(e, 'not compared')
    if b.startswith('identical'): n_bee += 1
    else: b = '**' + b + '**'
    s1, s2 = S1.get(e, {}), S2.get(e, {})
    cells = ['%d' % (int(idx) + 1), '%s %s %s' % (*rse.get(e, ('?', '?')), e), tr, b,
             pair(s1.get('kine_reco_Enu'), s2.get('kine_reco_Enu'), '%.1f'),
             pair(s1.get('numu_score'), s2.get('numu_score'), '%.3f'),
             pair(s1.get('nue_score'), s2.get('nue_score'), '%.3f')]
    if is_mc:
        t = s2.get('truth')
        if t:
            # the interaction that deposits in the detector (max edep); rockbox events also carry
            # dirt interactions outside it (edep 0), counted separately
            k = max(range(t['n_nu']), key=lambda i: t['nu'][i]['edep']); nu = t['nu'][k]
            txt = '%s %s, E %.0f MeV, Edep %.0f MeV, vtx (%.0f, %.0f, %.0f) cm' % (FL.get(nu['pdg'], nu['pdg']), 'NC' if nu['ccnc'] == 1 else 'CC', nu['E'] * 1e3, nu['edep'] * 1e3, nu['vtx_x'], nu['vtx_y'], nu['vtx_z'])
            others = [t['nu'][i] for i in range(t['n_nu']) if i != k]
            if others: txt += ' (+%d more: %s)' % (len(others), ', '.join('%s %s Edep %.0f MeV' % (FL.get(o['pdg'], o['pdg']), 'NC' if o['ccnc'] == 1 else 'CC', o['edep'] * 1e3) for o in others))
            txt += '; %d pf particles' % t['n_pf']
        else: txt = '–'
        cells.append(txt)
    rows.append('| ' + ' | '.join(cells) + ' |')
print('**%s**: %d events; `tracking-pr.root` identical %d/%d, Bee identical %d/%d' % (title, len(rows), n_tr, len(rows), n_bee, len(rows)))
print()
hdr = ['# (Bee)', 'run subrun event', '`tracking-pr.root` (2-step vs 1-step)', 'Bee (every layer)', 'reco Enu [MeV] 1-step / 2-step', 'numu score', 'nue score']
if is_mc: hdr.append('truth (2-step `T_truth_nu` / `T_truth_pf`)')
print('| ' + ' | '.join(hdr) + ' |'); print('|' + '---|' * len(hdr))
print('\n'.join(rows))
print()
print('"=" means the 2-step value equals the 1-step value exactly; a difference would be shown in bold as "1-step / 2-step". '
      '"–": no neutrino candidate, so no T_tagger / T_kine (8 instead of 10 trees) in either arm.')
if is_mc: print('Truth: the interaction depositing in the detector (max Edep); the gen2 CV sample also carries dirt interactions (Edep 0), listed after it.')
