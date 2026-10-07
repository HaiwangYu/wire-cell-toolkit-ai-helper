#!/usr/bin/env python3
"""Summarise a run-2step-pool.sh run (issue 38).  Run in SL7 (PyROOT):

    summarize.py <run dir> [label]

Writes <run>/units-summary.tsv (one row per unit), <run>/events.tsv (one row per event) and
<run>/summary.md, and prints summary.md.

Per unit: step-1 / step-2 rc, wall, CPU, max RSS (from /usr/bin/time -v), output sizes, number of
events in the tar, the T1 gate count of "DL vertex failed".
Per event (tracking-pr.root): RSE (Trun), candidate (T_kine present), DL calls by pass
(T_dlvtx_call.pass 0 = prod, 1 = off), DL accepted, T_dlvtx_cloud points, T_truth_nu / T_truth_pf rows.
"""
import csv, glob, os, re, sys, tarfile
import ROOT
ROOT.gErrorIgnoreLevel = ROOT.kError

RUN = os.path.abspath(sys.argv[1]); LABEL = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(RUN)


def tv(path):
    out = {}
    try:
        for line in open(path):
            k, _, v = line.strip().partition(': ')
            if k.startswith('Elapsed'):
                p = [float(x) for x in v.split(':')]
                out['wall_s'] = p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]
            elif k == 'User time (seconds)':
                out['cpu_s'] = out.get('cpu_s', 0) + float(v)
            elif k == 'System time (seconds)':
                out['cpu_s'] = out.get('cpu_s', 0) + float(v)
            elif k.startswith('Maximum resident'):
                out['rss_mb'] = float(v) / 1024
    except OSError:
        pass
    return out


def rd(p, default=''):
    try:
        return open(p).read().strip()
    except OSError:
        return default


def mb(p):
    return os.path.getsize(p) / 1e6 if os.path.exists(p) else 0.0


units, events, stubs = [], [], []
for row in csv.reader(open(RUN + '/units.tsv'), delimiter='\t'):
    if not row or row[0].startswith('#'):
        continue
    u, f, k, n = row[:4]
    D = '%s/%s' % (RUN, u)
    q, p = tv(D + '/ql/time.txt'), tv(D + '/pr/time.txt')
    tar = D + '/ql/qlpctree.tar.gz'
    try:
        idents = sorted({int(m.group(1)) for nm in tarfile.open(tar).getnames()
                         for m in [re.match(r'clustering_tensorset_(\d+)_metadata.json', nm)] if m})
    except Exception:
        idents = []
    trs = sorted(glob.glob(D + '/pr/pr_evt*/tracking-pr.root'))
    U = dict(unit=u, file=os.path.basename(f), nskip=k, n=n, ql_rc=rd(D + '/ql/rc'), pr_rc=rd(D + '/pr/rc'),
             dl_fail=rd(D + '/pr/dl_fail'), n_tar_events=len(idents), n_trackpr=len(trs),
             ql_wall_s=q.get('wall_s', ''), ql_cpu_s=q.get('cpu_s', ''), ql_rss_mb=q.get('rss_mb', ''),
             pr_wall_s=p.get('wall_s', ''), pr_cpu_s=p.get('cpu_s', ''), pr_rss_mb=p.get('rss_mb', ''),
             tar_mb=mb(tar), bee_mb=mb(D + '/ql/mabc.zip'), h5_mb=mb(D + '/ql/nugraph.h5'),
             beepr_mb=mb(D + '/pr/mabc-pr.zip'), trackpr_mb=sum(mb(t) for t in trs))
    units.append(U)
    for t in trs:
        e = int(re.search(r'pr_evt(\d+)', t).group(1))
        fh = ROOT.TFile.Open(t)
        names = {k.GetName() for k in fh.GetListOfKeys()} if fh else set()
        if 'Trun' not in names:
            # a crashed step 2 leaves the previous event's file as a ~0.5 kB stub (closed lazily)
            stubs.append('%s/%s' % (u, e))
            continue
        E = dict(unit=u, ident=e, run='', subrun='', event='', candidate=int('T_kine' in names), ntrees=len(names),
                 calls_prod=0, calls_off=0, acc_prod=0, acc_off=0, cloud_pts=0, truth_nu=-1, truth_pf=-1,
                 nue_score='', numu_score='', enu='')
        tr = fh.Get('Trun')
        if tr and tr.GetEntries():
            tr.GetEntry(0)
            for a, b in (('run', 'runNo'), ('subrun', 'subRunNo'), ('event', 'eventNo')):
                E[a] = int(getattr(tr, b)) if hasattr(tr, b) else ''
        c = fh.Get('T_dlvtx_call')
        if c:
            for x in c:
                ps = 'off' if getattr(x, 'pass') == 1 else 'prod'
                E['calls_' + ps] += 1
                E['acc_' + ps] += int(x.accepted)
        cl = fh.Get('T_dlvtx_cloud')
        E['cloud_pts'] = cl.GetEntries() if cl else 0
        for nm, key in (('T_truth_nu', 'truth_nu'), ('T_truth_pf', 'truth_pf')):
            o = fh.Get(nm)
            E[key] = o.GetEntries() if o else -1
        tg = fh.Get('T_tagger')
        if tg and tg.GetEntries():
            tg.GetEntry(0)
            E['nue_score'] = round(float(tg.nue_score), 4)
            E['numu_score'] = round(float(tg.numu_score), 4)
        kn = fh.Get('T_kine')
        if kn and kn.GetEntries():
            kn.GetEntry(0)
            E['enu'] = round(float(kn.kine_reco_Enu), 2)
        fh.Close()
        events.append(E)

for name, rows in (('units-summary.tsv', units), ('events.tsv', events)):
    if rows:
        w = csv.DictWriter(open(RUN + '/' + name, 'w'), fieldnames=list(rows[0]), delimiter='\t')
        w.writeheader(); w.writerows(rows)

ok = [u for u in units if u['ql_rc'] == '0' and u['pr_rc'] == '0']
fl = lambda rows, k: [float(r[k]) for r in rows if r[k] not in ('', None)]
med = lambda v: sorted(v)[len(v) // 2] if v else float('nan')
nev_tar = sum(u['n_tar_events'] for u in units); ntr = len(events)
L = ['# %s: %s' % (LABEL, RUN), '',
     '| quantity | value |', '|---|---|',
     '| units | %d run, %d with both steps rc=0 |' % (len(units), len(ok)),
     '| failed units | %s |' % (', '.join('%s (ql %s, pr %s)' % (u['unit'], u['ql_rc'], u['pr_rc']) for u in units if u not in ok) or 'none'),
     '| events in step-1 tars / valid tracking-pr.root | %d / %d |' % (nev_tar, ntr),
     '| stub tracking-pr.root (no Trun; crashed process) | %d %s |' % (len(stubs), ' '.join(stubs[:10])),
     '| units with "DL vertex failed" > 0 | %d |' % sum(1 for u in units if u['dl_fail'] not in ('', '0')),
     '| neutrino candidates (T_kine present) | %d (%.1f %%) |' % (sum(e['candidate'] for e in events), 100.0 * sum(e['candidate'] for e in events) / max(ntr, 1)),
     '| DL calls prod / off | %d / %d |' % (sum(e['calls_prod'] for e in events), sum(e['calls_off'] for e in events)),
     '| DL accepted prod / off | %d / %d |' % (sum(e['acc_prod'] for e in events), sum(e['acc_off'] for e in events)),
     '| events with T_dlvtx_call | %d |' % sum(1 for e in events if e['calls_prod'] + e['calls_off'] > 0),
     '| T_dlvtx_cloud points | %d |' % sum(e['cloud_pts'] for e in events),
     '| events with T_truth_nu | %d |' % sum(1 for e in events if e['truth_nu'] >= 0)]
if ok:
    for st in ('ql', 'pr'):
        L.append('| step %s per process: wall median / max | %.0f / %.0f s |' % ('1' if st == 'ql' else '2', med(fl(ok, st + '_wall_s')), max(fl(ok, st + '_wall_s'))))
        L.append('| step %s CPU per event | %.1f s |' % ('1' if st == 'ql' else '2', sum(fl(ok, st + '_cpu_s')) / max(sum(u['n_tar_events'] for u in ok), 1)))
        L.append('| step %s max RSS median / max | %.0f / %.0f MB |' % ('1' if st == 'ql' else '2', med(fl(ok, st + '_rss_mb')), max(fl(ok, st + '_rss_mb'))))
    for k, nm in (('tar_mb', 'qlpctree.tar.gz'), ('bee_mb', 'step-1 mabc.zip'), ('h5_mb', 'nugraph.h5'), ('trackpr_mb', 'tracking-pr.root'), ('beepr_mb', 'mabc-pr.zip')):
        tot = sum(fl(units, k))
        L.append('| %s: per event / total | %.2f MB / %.2f GB |' % (nm, tot / max(nev_tar, 1), tot / 1e3))
txt = '\n'.join(L) + '\n'
open(RUN + '/summary.md', 'w').write(txt)
print(txt)
