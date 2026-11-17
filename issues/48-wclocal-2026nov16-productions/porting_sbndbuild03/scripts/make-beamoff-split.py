#!/usr/bin/env python3
"""Issue 48: the WCLocal2026Nov16 beam-off train/eval split, as fg1's (porting_sbndbuild03).
usage: make-beamoff-split.py <catalog dir> <out dir>
Pairs with events are split by run parity (every file has art subrun 1): odd runs -> beam-off-train,
even runs -> beam-off-eval.  Writes <out>/beam-off-{train,eval}/lists/ (pairs.tsv, status.tsv,
events.tsv.gz with CAF paths through the split folder, merged-caf.txt, tracking-pr-scratch.txt,
qlpctree-scratch.txt) and <out>/links-{train,eval}.txt (ids to link).  Checks the split against fg1's."""
import sys, os, gzip, collections
cat, out = sys.argv[1:3]
PER = '/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/WCLocal2026Nov16'
FG1 = '/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/fg1'
runs = collections.defaultdict(set); ev = collections.defaultdict(list)
for l in gzip.open(f'{cat}/events-beam-off.tsv.gz', 'rt'):
    if l.startswith('#'): continue
    x = l.rstrip('\n').split('\t'); runs[x[0]].add(int(x[1])); ev[x[0]].append(x)
bad = {i: r for i, r in runs.items() if len({v % 2 for v in r}) != 1}
if bad: sys.exit(f'pairs with runs of both parities: {list(bad.items())[:3]}')
side = {i: ('train' if min(r) % 2 else 'eval') for i, r in runs.items()}
pairs = {l.split('\t')[0]: l for l in open(f'{cat}/pairs-beam-off.tsv') if not l.startswith('#')}
status = {l.split('\t')[0]: l for l in open(f'{cat}/status-beam-off.tsv') if not l.startswith('#')}
def lines(f): return [l for l in open(f'{cat}/{f}')]
mc, tp, qp = lines('beam-off.merged-caf.txt'), lines('beam-off.tracking-pr-scratch.txt'), lines('beam-off.qlpctree-scratch.txt')
def pick(ls, i): return [l for l in ls if f'/{i}/' in l or f'/{i}.' in l]
for s in ('train', 'eval'):
    ids = sorted(i for i in side if side[i] == s)
    d = f'{out}/beam-off-{s}/lists'; os.makedirs(d, exist_ok=True)
    open(f'{d}/pairs.tsv', 'w').write('#id\treality\treco1\tcaf\treco1_events\n' + ''.join(pairs[i] for i in ids))
    open(f'{d}/status.tsv', 'w').write('#id\tstatus\tfrom\tcaf_events\twc_split\twc_snap\tcause\n' + ''.join(status[i] for i in ids))
    with gzip.open(f'{d}/events.tsv.gz', 'wt') as o:
        o.write('#pair_id\trun\tsubrun\tevent\twc_split\twc_snap\tcaf\n')
        for i in ids:
            for x in ev[i]: o.write('\t'.join(x[:6] + [x[6].replace(f'{PER}/beam-off/', f'{PER}/beam-off-{s}/')]) + '\n')
    open(f'{d}/merged-caf.txt', 'w').write(''.join(l.replace(f'{PER}/beam-off/', f'{PER}/beam-off-{s}/') for i in ids for l in pick(mc, i)))
    open(f'{d}/tracking-pr-scratch.txt', 'w').write(''.join(l for i in ids for l in pick(tp, i)))
    open(f'{d}/qlpctree-scratch.txt', 'w').write(''.join(l for i in ids for l in pick(qp, i)))
    open(f'{out}/links-{s}.txt', 'w').write(''.join(i + '\n' for i in ids))
    rr = sorted({r for i in ids for r in runs[i]})
    fg = {l.split('\t')[0] for l in open(f'{FG1}/beam-off-{s}/lists/pairs.tsv') if not l.startswith('#')}
    print(f'{s}: {len(ids)} files, {sum(len(ev[i]) for i in ids)} events, {sum(int(x[4]) for i in ids for x in ev[i])} with split-pass WC, '
          f'{len(rr)} runs {rr[0]}-{rr[-1]}; vs fg1 {s}: same {len(fg & set(ids))}, only here {len(set(ids) - fg)}, only fg1 {len(fg - set(ids))}')
