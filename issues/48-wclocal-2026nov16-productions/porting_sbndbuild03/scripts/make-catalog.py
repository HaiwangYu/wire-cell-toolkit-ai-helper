#!/usr/bin/env python3
"""Issue 48: build the WCLocal2026Nov16 catalog lists from the persistent CAF copies (porting_sbndbuild03).
usage: make-catalog.py <caf-copy-plan.tsv> <caf-copy-verify.tsv> <final-pairs-first-try.tsv> <p5-not-ok-pairs.tsv> <outdir> [procs]
Reads every copied CAF (uproot): recTree rec.hdr.run/subrun/evt and wc.valid of recTreeWireCell (split
pass, dv2_split_move) and recTreeWireCell_dv2snap (snap pass).  Writes, per sample <s>:
  pairs-<s>.tsv            id reality reco1 caf reco1_events   (the production list, from wclocal-nov16/lists)
  status-<s>.tsv           id status from caf_events wc_split wc_snap cause
  events-<s>.tsv.gz        pair_id run subrun event wc_split wc_snap caf
  <s>.merged-caf.txt       persistent CAF paths
  <s>.tracking-pr-scratch.txt, <s>.qlpctree-scratch.txt   scratch paths (step-1 tars of step-2-only pairs are the earlier productions')
Speed: reading a CAF over dCache NFS takes ~2 s, so for an OK pair whose earlier production's events list (fg1,
run3bnb, ncdr; the recTree is the official CAF, unchanged) has as many events as the pair's CAF, the run/subrun/event come
from that list with wc_split = wc_snap = 1 (OK = every CAF event has both trees).  Read from the CAF: every
non-OK pair, every open-data pair (no earlier events list), count mismatches, and a random check sample of
OK pairs (WC_CHECK_N, default 150), which must agree with the list."""
import sys, os, gzip, csv, glob, collections
import multiprocessing
Pool = multiprocessing.get_context("fork").Pool   # python 3.14 defaults to forkserver, which re-runs this unguarded script
import uproot, numpy as np
plan, verify, first, notok, out = sys.argv[1:6]; procs = int(sys.argv[6]) if len(sys.argv) > 6 else 8
L = '/exp/sbnd/data/users/yuhw/wclocal-nov16/lists'
SCR = '/pnfs/sbnd/scratch/users/yuhw/prod-fermigrid/WCLocal2026Nov16'
SAMPLES = ['mc-cv', 'mc-nuecc', 'beam-off', 'run3bnb', 'opendata', 'mc-ncdr']   # mc-ncdr added 2026-11-18
def read(row):
    s, i, src, dst = row[:4]
    try:
        with uproot.open(dst) as f:
            h = f['recTree'].arrays(['rec.hdr.run', 'rec.hdr.subrun', 'rec.hdr.evt'], library='np')
            v1 = f['recTreeWireCell']['wc.valid'].array(library='np')
            v2 = f['recTreeWireCell_dv2snap']['wc.valid'].array(library='np')
        return s, i, [(int(a), int(b), int(c), int(x), int(y)) for a, b, c, x, y in
                      zip(h['rec.hdr.run'], h['rec.hdr.subrun'], h['rec.hdr.evt'], v1, v2)], None
    except Exception as e:
        return s, i, None, repr(e)
rows = [l.rstrip('\n').split('\t') for l in open(plan)]
ver = {(r[0], r[1]): r[5] for r in (l.rstrip('\n').split('\t') for l in open(verify))}
bad = [(r[0], r[1]) for r in rows if ver.get((r[0], r[1])) != 'OK']
if bad: sys.exit(f'{len(bad)} copies not verified OK, e.g. {bad[:3]}')
cause = {(r[0], r[1]): r[9] for r in (l.rstrip('\n').split('\t') for l in open(notok) if not l.startswith('#'))}
firstst = {(r[0], r[1]): (r[4], r[2]) for r in (l.rstrip('\n').split('\t') for l in open(first))}
CACHE = f'{out}/.events-cache.tsv.gz'   # dst -> events, so a rebuild reads only new CAFs
cache = collections.defaultdict(list)
if os.path.exists(CACHE):
    seen = set()   # a line written twice (an interrupted earlier build) counts once
    for l in gzip.open(CACHE, 'rt'):
        if l in seen: continue
        seen.add(l); d, *x = l.rstrip('\n').split('\t'); cache[d].append(tuple(int(v) for v in x)) if x else cache[d]
KNOWN = {'mc-cv': '/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/fg1/lists/events-mc-cv.tsv.gz',
         'mc-nuecc': '/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/fg1/lists/events-mc-nuecc.tsv.gz',
         'beam-off': '/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/fg1/lists/events-beam-off.tsv.gz',
         'run3bnb': '/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/run3bnb/lists/events-bnb-data.tsv.gz',
         'mc-ncdr': '/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/ncdr/lists/events-mc-ncdr.tsv.gz'}
known = collections.defaultdict(list)
for smp, f in KNOWN.items():
    for l in gzip.open(f, 'rt'):
        if l.startswith('#'): continue
        x = l.split('\t'); known[smp, x[0]].append((int(x[1]), int(x[2]), int(x[3]), 1, 1))
# first try's Wire-Cell event count (column 7); for an OK pair it equals the CAF's event count
ncaf = {(r[0], r[1]): int(r[6]) for r in (l.rstrip('\n').split('\t') for l in open(first)) if r[6] not in ('None', '')}
import random
fromlist = {}
for r in rows:
    k = (r[0], r[1])
    if r[5] == 'OK' and k in known and len(known[k]) == ncaf.get(k, -1): fromlist[k] = known[k]
check = set(random.Random(48).sample(sorted(fromlist), min(int(os.environ.get('WC_CHECK_N', 150)), len(fromlist))))
todo = [r for r in rows if r[3] not in cache and ((r[0], r[1]) not in fromlist or (r[0], r[1]) in check)]
print(len(fromlist), 'pairs from the earlier lists,', len(check), 'of them also read as a check', file=sys.stderr)
print(len(rows) - len(todo), 'CAFs from the cache,', len(todo), 'to read', file=sys.stderr)
with Pool(procs) as p: res = p.map(read, todo, chunksize=20)
os.makedirs(out, exist_ok=True)
with gzip.open(CACHE, 'at') as c:
    for (s, i, e, err), r in zip(res, todo):
        if err: continue
        c.write(r[3] + '\n' if not e else ''.join(r[3] + '\t' + '\t'.join(map(str, x)) + '\n' for x in e))
        cache[r[3]] = e
ev = {(r[0], r[1]): cache[r[3]] for r in rows if r[3] in cache}
bad = [k for k in check if k in ev and sorted(ev[k]) != sorted(fromlist[k])]
if bad: sys.exit(f'{len(bad)} check pairs disagree with the earlier list, e.g. {bad[:3]}')
print('check pairs read:', sum(k in ev for k in check), 'all agree', file=sys.stderr)
for k, e in fromlist.items(): ev.setdefault(k, e)
errs = [(s, i, err) for s, i, e, err in res if err]
if errs: sys.exit(f'{len(errs)} CAFs unreadable, e.g. {errs[:3]}')
byp = {(r[0], r[1]): r for r in rows}
os.makedirs(out, exist_ok=True); tot = collections.Counter()
for s in SAMPLES:
    lst = []
    for kind in ('step2', 'full'):
        f = f'{L}/pairs-{s}-{kind}.tsv'
        lst += [l.rstrip('\n').split('\t') for l in open(f) if not l.startswith('#')]
    with open(f'{out}/pairs-{s}.tsv', 'w') as o:
        o.write('#id\treality\treco1\tcaf\treco1_events\n')
        for r in sorted(lst): o.write('\t'.join(r[:5]) + '\n')
    st = open(f'{out}/status-{s}.tsv', 'w'); st.write('#id\tstatus\tfrom\tcaf_events\twc_split\twc_snap\tcause\n')
    eo = gzip.open(f'{out}/events-{s}.tsv.gz', 'wt'); eo.write('#pair_id\trun\tsubrun\tevent\twc_split\twc_snap\tcaf\n')
    mc, tp, qp = open(f'{out}/{s}.merged-caf.txt', 'w'), open(f'{out}/{s}.tracking-pr-scratch.txt', 'w'), open(f'{out}/{s}.qlpctree-scratch.txt', 'w')
    for r in sorted(lst):
        i = r[0]; k = (s, i); fs, mode = firstst.get(k, ('?', '?'))
        if k in byp:
            _, _, src, dst, frm, status = byp[k]; e = ev[k]
            n1 = sum(x[3] for x in e); n2 = sum(x[4] for x in e)
            if status == 'OK' and (n1 != len(e) or n2 != len(e)): status = 'OK?'
            st.write(f'{i}\t{status}\t{frm}\t{len(e)}\t{n1}\t{n2}\t{cause.get(k, "")}\n')
            for a, b, c, x, y in e: eo.write(f'{i}\t{a}\t{b}\t{c}\t{x}\t{y}\t{dst}\n')
            mc.write(dst + '\n'); d = os.path.dirname(src)
            # paths from the workflow's layout, not from dCache listings (~0.3 s each over NFS): the step-2 tar
            # is <pair dir>/<id>.tracking-pr.tar; the step-1 tar is the kept one of the step-2 list (column 6)
            # for step-2-only pairs, <pair dir>/<id>.qlpctree.tar.gz for pairs run from reco1
            tp.write(f'{d}/{i}.tracking-pr.tar\n')
            qp.write((r[5] if len(r) > 5 and r[5] else f'{d}/{i}.qlpctree.tar.gz') + '\n')
            tot[s, 'caf'] += len(e); tot[s, 'split'] += n1; tot[s, 'snap'] += n2; tot[s, status] += 1
        else:
            stt = fs if fs == 'EMPTY' else 'PENDING'
            st.write(f'{i}\t{stt}\t-\t0\t0\t0\t{cause.get(k, "no events in reco1 or CAF" if stt == "EMPTY" else "rerun running")}\n'); tot[s, stt] += 1
    for f in (st, eo, mc, tp, qp): f.close()
    print(s, {k[1]: v for k, v in tot.items() if k[0] == s})
