#!/usr/bin/env python3
"""Issue 48 P2: pick N pairs per sample (status OK, seeded random) for the step-1 reuse test.
   pick-p2-pairs.py <out.tsv> [N=5] [seed=48]
Writes pairs rows (id reality reco1 caf events) with a 6th column: sample, and a 7th: the kept qlpctree."""
import random, sys
out = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 5; seed = int(sys.argv[3]) if len(sys.argv) > 3 else 48
P = '/pnfs/sbnd/persistent/users/yuhw'
A = '/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/40-sbnd-opendata-fixeddev-caf-merge/lists'
S = {  # sample: pairs, status, kept tar template
    'mc-cv':    (P + '/prod-fermigrid/fg1/lists/pairs-mc-cv.tsv', P + '/prod-fermigrid/fg1/lists/status-mc-cv.tsv',
                 '/pnfs/sbnd/scratch/users/yuhw/prod-fermigrid/fg1/mc-cv/{id}/{id}.qlpctree.tar.gz'),
    'mc-nuecc': (P + '/prod-fermigrid/fg1/lists/pairs-mc-nuecc.tsv', P + '/prod-fermigrid/fg1/lists/status-mc-nuecc.tsv',
                 '/pnfs/sbnd/scratch/users/yuhw/prod-fermigrid/fg1/mc-nuecc/{id}/{id}.qlpctree.tar.gz'),
    'beam-off': (P + '/prod-fermigrid/fg1/lists/pairs-beam-off.tsv', P + '/prod-fermigrid/fg1/lists/status-beam-off.tsv',
                 '/pnfs/sbnd/scratch/users/yuhw/prod-fermigrid/fg1/beam-off/{id}/{id}.qlpctree.tar.gz'),
    'run3bnb':  (P + '/prod-fermigrid/run3bnb/lists/pairs-bnb-data.tsv', P + '/prod-fermigrid/run3bnb/lists/status-bnb-data.tsv',
                 '/pnfs/sbnd/scratch/users/yuhw/prod-fermigrid/run3bnb/bnb-data/{id}/{id}.qlpctree.tar.gz'),
    'opendata': (A + '/pairs.tsv', A + '/status.tsv',
                 P + '/prod-sbndbuild03/opendata-fixeddev/bnb-data/{id}/{id}.qlpctree.tar.gz'),
}
rng = random.Random(seed)
with open(out, 'w') as fo:
    fo.write('#id\treality\treco1\tcaf\treco1_events\tsample\tkept_qlpctree\n')
    for name, (pl, sl, tpl) in S.items():
        ok = {l.split('\t')[0] for l in open(sl) if not l.startswith('#') and l.split('\t')[1].strip().startswith('OK')}
        rows = [l.rstrip('\n').split('\t') for l in open(pl) if l.strip() and not l.startswith('#')]
        rows = sorted(r for r in rows if r[0] in ok)
        for r in rng.sample(rows, N):
            fo.write('\t'.join(r[:5] + [name, tpl.format(id=r[0])]) + '\n')
        print(name, len(rows), 'OK pairs; picked', N)
