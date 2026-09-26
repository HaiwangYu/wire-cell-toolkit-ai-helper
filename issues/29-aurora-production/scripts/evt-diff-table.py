#!/usr/bin/env python3
"""Markdown table, one row per event, of EXACTLY what differs between an Aurora 1-step run
and Xin's arm, from cmp-xin/evt-diff.json (evt-branch-diff.py --json), bee-upload/bee-order.txt
and cmp-xin/bee_content.txt (compare-bee-content.py).  No ROOT needed.
usage: evt-diff-table.py <run dir> [<title>]"""
import json, os, re, sys
R = sys.argv[1]; title = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(R)
J = json.load(open(R + '/cmp-xin/evt-diff.json'))
order = [l.split() for l in open(R + '/bee-upload/bee-order.txt')]          # idx rR_sS_eE nskip
bee = {}
if os.path.exists(R + '/cmp-xin/bee_content.txt'):
    for l in open(R + '/cmp-xin/bee_content.txt'):
        m = re.match(r'bee_(\d+)\.zip DIFFERS: (.*)', l)
        if m: bee[m.group(1)] = m.group(2).replace('.json', '')
def g(v): return '%g' % v
def fmtv(ex):
    a, b = ex['ref'], ex['arm']
    if ex['len'][0] != ex['len'][1]: return 'len %d vs %d' % tuple(ex['len'])
    if len(a) == 1: return '%s -> %s' % (g(a[0]), g(b[0]))
    return '[%s] -> [%s]' % (', '.join(g(x) for x in a[:4]) + (', ..' if len(a) > 4 else ''), ', '.join(g(x) for x in b[:4]) + (', ..' if len(b) > 4 else ''))
rows = []; n_ident = 0; n_fp = 0; n_disc = 0
for idx, rse, k in order:
    e = rse.split('_e')[1]; S = J[e]; T = S['trees']
    tr = T.get('T_rec_charge', {}); rc_ent = tr.get('entries', [0, 0]); rc_br = tr.get('branches', {})
    other = {tn: T[tn]['branches'] for tn in T if tn != 'T_rec_charge' and T[tn].get('branches')}
    if not other and not rc_br:
        n_ident += 1; what = 'identical (every branch of all 8 trees)'; cls = 'exact'
    elif not other and rc_ent[0] == rc_ent[1]:
        n_fp += 1; mr = max(v['max_rel'] for v in rc_br.values())
        what = 'T_rec_charge only, same %d points: %s at <= %.1e relative (float-precision residual)' % (rc_ent[0], ', '.join(sorted(rc_br, key=lambda b: -rc_br[b]['max_rel'])), mr)
        cls = 'fp'
    else:
        n_disc += 1; parts = []
        if rc_ent[0] != rc_ent[1]: parts.append('T_rec_charge %d vs %d points' % tuple(rc_ent))
        elif rc_br: parts.append('T_rec_charge %s at <= %.1e rel' % (', '.join(sorted(rc_br)), max(v['max_rel'] for v in rc_br.values())))
        for tn in ('Trun', 'T_cluster', 'T_kine', 'T_tagger', 'T_bad_ch', 'T_proj', 'T_proj_data'):
            br = other.get(tn)
            if not br: continue
            items = list(br.items())
            # show every branch for small sets, the headline ones + count for large sets
            if len(items) <= 12:
                parts.append('%s (%d): ' % (tn, len(items)) + '; '.join('`%s` %s' % (nm, fmtv(v['example'])) for nm, v in items))
            else:
                head = [(nm, v) for nm, v in items if re.match(r'(nu_[xyz]|mip_energy|gap_energy|mip_length_main|mip_n_lowest|shw_sp_|numu_score|nue_score|ssm_offvtx|kine_)', nm)][:10]
                parts.append('%s (%d branches): ' % (tn, len(items)) + '; '.join('`%s` %s' % (nm, fmtv(v['example'])) for nm, v in head) + '; ...')
        if S['headline']:
            parts.append('HEADLINE ' + '; '.join('`%s` %s -> %s' % (k, g(v[0][0]), g(v[1][0])) for k, v in S['headline'].items()))
        what = ' / '.join(parts); cls = 'discrete'
    b = bee.get(e, 'identical (7 layers)')
    rows.append('| %s | %s | %s | %s | %s |' % (int(idx) + 1, rse.replace('_', ' '), cls, what, b))
print('**%s** -- %d events: exact %d, float-precision residual only %d, discrete difference %d' % (title, len(rows), n_ident, n_fp, n_disc))
print()
print('| # (Bee) | run subrun event | class | tracking-pr.root: what exactly differs (Xin -> Aurora) | Bee content (Xin\'s 7 layers) |')
print('|---|---|---|---|---|')
print('\n'.join(rows))
