#!/usr/bin/env python3
"""Summarise a WCLocal2026Nov16 grid output dir: status, events, sizes, cost.
usage: pilot-summary.py <outroot> [sample ...]  -> per-pair TSV on stdout's sidecar + summary"""
import sys, os, glob, tarfile, json, io, datetime, collections
root = sys.argv[1]; samples = sys.argv[2:] or sorted(os.listdir(root))
rows = []
for s in samples:
    for d in sorted(glob.glob(f"{root}/{s}/*/")):
        pid = os.path.basename(d.rstrip('/'))
        done = f"{d}/{pid}.done"
        if not os.path.exists(done): rows.append(dict(sample=s, pair=pid, status='NODONE')); continue
        info = dict(sample=s, pair=pid)
        files = {}
        for line in open(done):
            k, _, v = line.rstrip('\n').partition('\t')
            if k == 'status': info['status'] = v
            elif k == 'job': info['job'] = v.split()[0]; info['host'] = v.split()[4] if len(v.split())>4 else ''
            elif k == 'file': n, f = v.split('\t'); files[f] = int(n)
        info['tar_B'] = sum(n for f, n in files.items() if f.endswith('.tracking-pr.tar'))
        info['caf_B'] = sum(n for f, n in files.items() if f.endswith('.caf.root'))
        info['logs_B'] = os.path.getsize(f"{d}/{pid}.logs.tar.gz") if os.path.exists(f"{d}/{pid}.logs.tar.gz") else 0
        try:
            with tarfile.open(f"{d}/{pid}.logs.tar.gz") as t:
                names = t.getnames()
                ev = json.load(t.extractfile('events.json'))
                info['events'] = ev.get('wirecell_events'); info['caf_events'] = ev.get('caf_events')
                info['step2_failed'] = len(ev.get('step2_failed', []))
                cost = t.extractfile('cost.tsv').read().decode().splitlines()[1:]
                cpu = wall = 0.0; rss = 0; att = 0
                for c in cost:
                    f = c.split('\t'); att += 1
                    wall += float(f[4]); cpu += float(f[5]); rss = max(rss, int(f[6]))
                info.update(cpu_s=cpu, wall_s=wall, maxrss_MB=rss, attempts=att)
                v = []
                for vn in [n for n in names if n.startswith('validate') and n.endswith('.json')]:
                    v.append(json.load(t.extractfile(vn)).get('verdict'))
                info['validate'] = ','.join(sorted(v))
                dlf = 0
                for n in names:
                    if n.endswith('/dl_fail'):
                        try: dlf += int(t.extractfile(n).read().split()[0])
                        except Exception: pass
                info['dl_fail'] = dlf
                log = t.extractfile('run_pair.log').read().decode().splitlines()
                ts = lambda l: datetime.datetime.strptime(l[:19], '%Y-%m-%d %H:%M:%S')
                info['pair_wall_s'] = (ts(log[-1]) - ts(log[0])).total_seconds()
        except Exception as e:
            info['err'] = repr(e)
        rows.append(info)
cols = ['sample','pair','status','events','caf_events','step2_failed','dl_fail','validate','attempts','cpu_s','wall_s','pair_wall_s','maxrss_MB','tar_B','caf_B','logs_B','job','host','err']
with open(os.environ.get('OUT_TSV', '/dev/null'), 'w') as fo:
    fo.write('\t'.join(cols)+'\n')
    for r in rows: fo.write('\t'.join(str(r.get(c, '')) for c in cols)+'\n')
agg = collections.OrderedDict()
for r in rows:
    a = agg.setdefault(r['sample'], collections.Counter())
    a['pairs'] += 1; a['status_'+r.get('status','?')] += 1
    for k in ('events','caf_events','step2_failed','dl_fail','cpu_s','wall_s','pair_wall_s','tar_B','caf_B','logs_B'):
        a[k] += r.get(k) or 0
    a['maxrss_MB'] = max(a['maxrss_MB'], r.get('maxrss_MB') or 0)
    if r.get('validate') and r['validate'] != 'PASS,PASS': a['validate_bad'] += 1
    if (r.get('attempts') or 0) > 6: a['retried'] += 1
    if r.get('err'): a['err'] += 1
tot = collections.Counter()
print('sample\tpairs\tstatus\tevents\tcaf_ev\tstep2_failed\tdl_fail\tval_bad\tretried\tcpu_s/ev\tpairwall_s/ev\tmaxrss_MB\ttar_kB/ev\tcaf_kB/ev\tlogs_kB/ev')
for s, a in list(agg.items()) + [('TOTAL', None)]:
    if a is None: a = tot
    else:
        for k, v in a.items():
            tot[k] = max(tot[k], v) if k == 'maxrss_MB' else tot[k] + v
    st = ' '.join(f"{k[7:]}={v}" for k, v in sorted(a.items()) if k.startswith('status_'))
    e = a['events'] or 1
    print(f"{s}\t{a['pairs']}\t{st}\t{a['events']}\t{a['caf_events']}\t{a['step2_failed']}\t{a['dl_fail']}\t{a['validate_bad']}\t{a['retried']}\t{a['cpu_s']/e:.1f}\t{a['pair_wall_s']/e:.1f}\t{a['maxrss_MB']}\t{a['tar_B']/e/1e3:.0f}\t{a['caf_B']/e/1e3:.0f}\t{a['logs_B']/e/1e3:.1f}")
