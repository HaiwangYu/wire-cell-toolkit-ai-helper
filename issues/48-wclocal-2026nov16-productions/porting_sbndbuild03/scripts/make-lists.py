#!/usr/bin/env python3
"""Issue 48: the WCLocal2026Nov16-FermiGrid pair lists, from the kept productions' lists (read only).
   make-lists.py <outdir> [pilot_every=100]
Per sample:
  pairs-<sample>-step2.tsv  status OK in the earlier production AND one unsliced kept qlpctree: id reality reco1 caf events kept_qlpctree
  pairs-<sample>-full.tsv   every other pair (PARTIAL / sliced / EMPTY): id reality reco1 caf events (run from reco1)
  pilot-<sample>-step2.tsv  every <pilot_every>-th line of the step2 list (the ~1 % pilot, P4); P5 submits the
                            whole list and the jobs skip the pairs already finished (job.sh: <id>.done)"""
import collections, os, sys
out = sys.argv[1]; every = int(sys.argv[2]) if len(sys.argv) > 2 else 100
P = '/pnfs/sbnd/persistent/users/yuhw'
A = '/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/40-sbnd-opendata-fixeddev-caf-merge/lists'
S = {'mc-cv': ('fg1/lists/pairs-mc-cv.tsv', 'fg1/lists/status-mc-cv.tsv', 'fg1/lists/mc-cv.qlpctree-scratch.txt'),
     'mc-nuecc': ('fg1/lists/pairs-mc-nuecc.tsv', 'fg1/lists/status-mc-nuecc.tsv', 'fg1/lists/mc-nuecc.qlpctree-scratch.txt'),
     'beam-off': ('fg1/lists/pairs-beam-off.tsv', 'fg1/lists/status-beam-off.tsv', 'fg1/lists/beam-off.qlpctree-scratch.txt'),
     'run3bnb': ('run3bnb/lists/pairs-bnb-data.tsv', 'run3bnb/lists/status-bnb-data.tsv', 'run3bnb/lists/bnb-data.qlpctree-scratch.txt'),
     'opendata': (A + '/pairs.tsv', A + '/status.tsv', P + '/prod-sbndbuild03/opendata-fixeddev/lists/qlpctree.txt')}
os.makedirs(out, exist_ok=True)
H = '#id\treality\treco1\tcaf\treco1_events\tkept_qlpctree\n'
for name, files in S.items():
    pl, sl, ql = [f if f.startswith('/') else P + '/prod-fermigrid/' + f for f in files]
    pairs = [l.rstrip('\n').split('\t') for l in open(pl) if l.strip() and not l.startswith('#')]
    st = {l.split('\t')[0]: l.split('\t')[1].strip().split()[0] for l in open(sl) if l.strip() and not l.startswith('#')}
    tars = collections.defaultdict(list)
    for l in open(ql):
        l = l.strip()
        if l:
            tars[l.split('/')[-2]].append(l)
    s2, full = [], []
    for r in pairs:
        t = tars.get(r[0], [])
        if st.get(r[0]) == 'OK' and len(t) == 1 and t[0].endswith('/%s.qlpctree.tar.gz' % r[0]) and r[4].isdigit() and int(r[4]) > 0:
            s2.append(r[:5] + [t[0]])
        else:
            full.append(r[:5])
    for fn, rows, h in (('pairs-%s-step2.tsv' % name, s2, H), ('pairs-%s-full.tsv' % name, full, H.replace('\tkept_qlpctree', '')),
                        ('pilot-%s-step2.tsv' % name, s2[::every], H)):
        with open(os.path.join(out, fn), 'w') as f:
            f.write(h); f.writelines('\t'.join(r) + '\n' for r in rows)
    print('%-9s pairs %6d  step2 %6d (%7d ev)  full %3d  pilot %4d (%6d ev)' % (name, len(pairs), len(s2), sum(int(r[4]) for r in s2),
          len(full), len(s2[::every]), sum(int(r[4]) for r in s2[::every])))
