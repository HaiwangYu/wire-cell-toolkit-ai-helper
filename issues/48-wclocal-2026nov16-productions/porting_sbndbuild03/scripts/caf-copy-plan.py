#!/usr/bin/env python3
"""Issue 48: plan the copy of the merged CAFs to persistent (porting_sbndbuild03).
usage: caf-copy-plan.py <final-pairs.tsv> <out plan.tsv> [skip-id ...]
final-pairs.tsv: sample id mode pilot|p5 status nev wc_events caf_events why (no header)
One CAF per pair: <sample>-mem8g/<id>/ when its .done says OK, else <sample>/<id>/; EMPTY pairs
have no CAF; ids given as skip-id are left out (rerun still running).
plan.tsv: sample id src dst from(orig|mem8g) status"""
import sys, os, glob
SCR = '/pnfs/sbnd/scratch/users/yuhw/prod-fermigrid/WCLocal2026Nov16'
PER = '/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/WCLocal2026Nov16'
fp, out, skip = sys.argv[1], sys.argv[2], set(sys.argv[3:])
def status(d, i):
    try: return open(f'{d}/{i}.done').readline().split('\t')[1].split()[0]
    except Exception: return None
n = 0
with open(out, 'w') as o:
    for line in open(fp):
        s, i, mode, ph, st = line.rstrip('\n').split('\t')[:5]
        if st == 'EMPTY' or i in skip: continue
        frm, d = 'orig', f'{SCR}/{s}/{i}'
        if status(f'{SCR}/{s}-mem8g/{i}', i) == 'OK': frm, d, st = 'mem8g', f'{SCR}/{s}-mem8g/{i}', 'OK'
        cafs = glob.glob(f'{d}/*.wc.flat.caf.root')
        if len(cafs) != 1: print('no/multiple CAF', s, i, cafs, file=sys.stderr); continue
        o.write(f'{s}\t{i}\t{cafs[0]}\t{PER}/{s}/{i}/{os.path.basename(cafs[0])}\t{frm}\t{st}\n'); n += 1
print(n, 'files planned', file=sys.stderr)
