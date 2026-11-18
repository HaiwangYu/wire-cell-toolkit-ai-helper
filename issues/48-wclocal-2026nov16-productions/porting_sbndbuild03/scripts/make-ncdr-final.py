#!/usr/bin/env python3
"""Issue 48, NC delta-rad (added 2026-11-18): write the mc-ncdr rows of the final-pairs table that
caf-copy-plan.py and make-catalog.py read (porting_sbndbuild03).
usage: make-ncdr-final.py <out.tsv>
Rows: sample id mode pilot|p5 status list_events caf_events None why (no header), like final-pairs-first-try.tsv.
- The 9,150 step-2 pairs (lists/pairs-mc-ncdr-step2.tsv): status from <id>.done on scratch (NODONE if absent);
  caf_events from the fg1-config ncdr production's status list (the CAF is the official one, unchanged).
- The 6,626 pairs whose reco1 has no events (lists/pairs-mc-ncdr-full.tsv) are not rerun: EMPTY, mode '-'."""
import sys
L = '/exp/sbnd/data/users/yuhw/wclocal-nov16/lists'
SCR = '/pnfs/sbnd/scratch/users/yuhw/prod-fermigrid/WCLocal2026Nov16/mc-ncdr'
OLD = '/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/ncdr/lists/status-mc-ncdr.tsv'
rd = lambda f: [l.rstrip('\n').split('\t') for l in open(f) if not l.startswith('#')]
old = {r[0]: r for r in rd(OLD)}
pilot = {r[0] for r in rd(f'{L}/pilot-mc-ncdr-step2.tsv')}
n = {}
with open(sys.argv[1], 'w') as o:
    for r in rd(f'{L}/pairs-mc-ncdr-step2.tsv'):
        i = r[0]
        try: st = open(f'{SCR}/{i}/{i}.done').readline().split('\t')[1].split()[0]
        except OSError: st = 'NODONE'
        ce = old[i][2] if i in old and old[i][1] == 'OK' else 'None'
        o.write(f'mc-ncdr\t{i}\tstep2\t{"pilot" if i in pilot else "p5"}\t{st}\t{r[4]}\t{ce}\tNone\t\n'); n[st] = n.get(st, 0) + 1
    for r in rd(f'{L}/pairs-mc-ncdr-full.tsv'):
        o.write(f'mc-ncdr\t{r[0]}\t-\t-\tEMPTY\t0\t0\tNone\tno events in reco1 or CAF\n'); n['EMPTY'] = n.get('EMPTY', 0) + 1
print(n, file=sys.stderr)
