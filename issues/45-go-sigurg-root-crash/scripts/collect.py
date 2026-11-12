#!/usr/bin/env python3
"""ai-helper #45: tabulate the grid crash test.   collect.py [result dir] [tasks.txt]
Reads every <mode>/<input>-p<pass>.<cluster>.<index>.tar.gz (summary.txt), keeps the latest try per task,
prints per mode: tasks done, crashes (rc != 0), crash signatures; per input x mode; missing tasks."""
import collections, glob, os, sys, tarfile
R = sys.argv[1] if len(sys.argv) > 1 else '/pnfs/sbnd/scratch/users/yuhw/pr543-crash-study/grid-v2'
T = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tasks.txt')
tasks = [l.split() for l in open(T) if l.strip() and not l.startswith('#')]
res = {}
for f in glob.glob(os.path.join(R, '*', '*.tar.gz')):
    try:
        with tarfile.open(f) as t:
            s = dict(l.split(' ', 1) for l in t.extractfile('summary.txt').read().decode().splitlines() if ' ' in l)
    except Exception as e:
        print('unreadable', f, e); continue
    key = (s['mode'], s['input'], s['pass'])
    if key not in res or os.path.getmtime(f) > res[key][1]: res[key] = (s, os.path.getmtime(f))
modes = list(dict.fromkeys(t[0] for t in tasks)); inputs = list(dict.fromkeys(t[1] for t in tasks))
short = lambda i: i.replace('mc-nuecc--reco1-detsim-g4-filter-gen-', '').replace('_nuecc', '')[:22]
print(f'{"mode":24s} {"done":>5s} {"crash":>6s} {"events":>7s}  signatures')
for m in modes:
    rs = [v[0] for k, v in res.items() if k[0] == m]
    cr = [s for s in rs if s['rc'] != '0']
    sig = collections.Counter(f"rc{s['rc']}:{s['signature']}" for s in cr)
    print(f'{m:24s} {len(rs):5d} {len(cr):6d} {sum(int(s["events"]) for s in rs if s["rc"] == "0"):7d}  {dict(sig)}')
print(); print(f'{"input":24s} ' + ' '.join(f'{m[:12]:>13s}' for m in modes))
for i in inputs:
    row = []
    for m in modes:
        rs = [res[k][0] for k in res if k[0] == m and k[1] == i]
        row.append(f'{sum(s["rc"] != "0" for s in rs)}/{len(rs)}'.rjust(13))
    print(f'{short(i):24s} ' + ' '.join(row))
miss = [t for t in tasks if (t[0], t[1], t[3]) not in res]
print(f'\nmissing {len(miss)} of {len(tasks)} tasks' + (': ' + ', '.join(f'{t[0]}/{short(t[1])}/p{t[3]}' for t in miss[:12]) if miss else ''))
hosts = collections.Counter((v[0]['cpu'], v[0]['flags_avx512']) for v in res.values())
print('cpus:', dict(hosts))
