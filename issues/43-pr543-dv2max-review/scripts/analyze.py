#!/usr/bin/env python3
"""analyze.py <runs dir> <out.json>: the metrics of ai-helper #43 for every arm.
runs/<arm>/<unit>/: one step-2 run (run-step2.sh); unit = mc-cv--<id> | mc-nuecc--<id> | data--<file slice>.
Per arm:
  vertex (MC): per event, the candidate whose DL-vertex cloud has a point within 3 cm of the SCE-shifted truth
    vertex (T_dlvtx_call truth_reco_*; #35 dlvtx-truth-eval rule); d = |final - truth_reco|.  Only events where
    every arm has that candidate are compared (the same event set for all arms).
  selection (MC): truth class from T_truth_nu, the interaction with the largest edep, vertex in the active
    volume (|x|,|y| < 200, 0 < z < 500): nue CC, numu CC, NC; T_tagger: generic nu = numu_cc_flag >= 0,
    nue = generic && nue_score > 7, numu = generic && numu_score > 0.9 (the PR's cuts).
  data: per event the same flags; counts and event-by-event changes vs master.
  cost: per run /usr/bin/time (CPU, peak RSS), per candidate 'overall main vertex took X ms', DV2 hook records.
"""
import collections, glob, gzip, json, math, os, re, sys
import numpy as np, uproot

R, OUT = sys.argv[1], sys.argv[2]
ARMS = ['master', 'pr-original', 'pr-dv2_snap', 'pr-dv2_split', 'pr-dv2_split_move']


def inside(x, y, z):
    return abs(x) < 200 and abs(y) < 200 and 0 < z < 500


def event_info(fn):
    """-> key (run, subrun, event), dict(scores, truth, vertex candidates)"""
    u = uproot.open(fn)
    info = dict(generic=False, nue=False, numu=False, nue_score=None, numu_score=None, truth=None, cands={})
    t = u['T_tagger'] if 'T_tagger' in u else None
    key = None
    if t is not None and t.num_entries:
        a = t.arrays(['run', 'subrun', 'event', 'numu_cc_flag', 'nue_score', 'numu_score'], library='np')
        key = (int(a['run'][0]), int(a['subrun'][0]), int(a['event'][0]))
        g = a['numu_cc_flag'][0] >= 0
        info.update(generic=bool(g), nue=bool(g and a['nue_score'][0] > 7), numu=bool(g and a['numu_score'][0] > 0.9),
                    nue_score=float(a['nue_score'][0]), numu_score=float(a['numu_score'][0]))
    if 'T_truth_nu' in u and u['T_truth_nu'].num_entries:
        n = u['T_truth_nu'].arrays(['runNo', 'subRunNo', 'eventNo', 'pdg', 'ccnc', 'edep', 'vtx_x', 'vtx_y', 'vtx_z'], library='np')
        key = key or (int(n['runNo'][0]), int(n['subRunNo'][0]), int(n['eventNo'][0]))
        i = int(np.argmax(n['edep']))
        if n['edep'][i] > 0 and inside(n['vtx_x'][i], n['vtx_y'][i], n['vtx_z'][i]):
            pdg, cc = abs(int(n['pdg'][i])), int(n['ccnc'][i]) == 0
            info['truth'] = 'nueCC' if (pdg == 12 and cc) else ('numuCC' if (pdg == 14 and cc) else ('NC' if not cc else 'other'))
    if 'T_dlvtx_call' in u and u['T_dlvtx_call'].num_entries:
        c = u['T_dlvtx_call'].arrays(['runNo', 'subRunNo', 'eventNo', 'nu_index', 'call_index', 'pass', 'final_valid', 'final_x', 'final_y', 'final_z',
                                      'truth_valid', 'truth_reco_x', 'truth_reco_y', 'truth_reco_z'], library='np')
        key = key or (int(c['runNo'][0]), int(c['subRunNo'][0]), int(c['eventNo'][0]))
        p = u['T_dlvtx_cloud'].arrays(['nu_index', 'call_index', 'pass', 'x', 'y', 'z'], library='np')
        for i in range(len(c['nu_index'])):
            if not c['truth_valid'][i] or not c['final_valid'][i]:
                continue
            tv = np.array([c['truth_reco_x'][i], c['truth_reco_y'][i], c['truth_reco_z'][i]])
            m = (p['nu_index'] == c['nu_index'][i]) & (p['call_index'] == c['call_index'][i]) & (p['pass'] == c['pass'][i])
            if not m.any():
                continue
            dmin = float(np.min(np.sqrt((p['x'][m] - tv[0]) ** 2 + (p['y'][m] - tv[1]) ** 2 + (p['z'][m] - tv[2]) ** 2)))
            d = math.dist(tv, (c['final_x'][i], c['final_y'][i], c['final_z'][i]))
            nu = int(c['nu_index'][i])
            if nu not in info['cands'] or dmin < info['cands'][nu][0]:
                info['cands'][nu] = (dmin, d)
    return key, info


def run_cost(d):
    r = dict(rc=None, cpu=None, rss=None, vtx_ms=[], hook_ms=[], hook_nopred=0, first_call_ms=None)
    try:
        r['rc'] = int(open(os.path.join(d, 'rc')).read())
        t = open(os.path.join(d, 'time.txt')).read()
        r['cpu'] = sum(float(x) for x in re.findall(r'(?:User|System) time \(seconds\): ([\d.]+)', t))
        r['rss'] = int(re.search(r'Maximum resident set size \(kbytes\): (\d+)', t).group(1)) / 1024
    except Exception:
        pass
    with gzip.open(os.path.join(d, 'wct.log.gz'), 'rt', errors='replace') as f:
        for l in f:
            m = re.search(r'overall main vertex took ([\d.]+) ms', l)
            if m:
                r['vtx_ms'].append(float(m.group(1)))
    hp = os.path.join(d, 'dv2-hook.jsonl')
    if os.path.exists(hp):
        for l in open(hp):
            h = json.loads(l)
            r['hook_ms'].append(h['ms'])
            r['hook_nopred'] += 0 if h.get('pred') else 1
            if 'first_call_ms' in h:
                r['first_call_ms'] = h['first_call_ms']
    return r


ev = {a: {} for a in ARMS}
cost = {a: {} for a in ARMS}
for a in ARMS:
    for d in sorted(glob.glob(os.path.join(R, a, '*'))):
        unit = os.path.basename(d)
        cost[a][unit] = run_cost(d)
        for fn in glob.glob(os.path.join(d, 'pr_evt*', 'tracking-pr.root')):
            k, inf = event_info(fn)
            if k:
                ev[a][(unit.split('--')[0],) + k] = inf

res = {}
# vertex: events where every arm has the truth-containing candidate (within 3 cm)
def best(inf):
    c = [v for v in inf['cands'].values() if v[0] < 3.0]
    return min(c)[1] if c else None
for sample in ('mc-cv', 'mc-nuecc', 'mc'):
    keys = [k for k in ev['master'] if (k[0] == sample or (sample == 'mc' and k[0].startswith('mc')))]
    common = [k for k in keys if all(k in ev[a] and best(ev[a][k]) is not None for a in ARMS)]
    res['vertex_' + sample] = {'n_events': len(common)}
    for a in ARMS:
        d = np.array([best(ev[a][k]) for k in common])
        res['vertex_' + sample][a] = dict(lt1=float(np.mean(d < 1)) if len(d) else None, lt2=float(np.mean(d < 2)) if len(d) else None,
                                          median=float(np.median(d)) if len(d) else None)
# selection on MC
for a in ARMS:
    s = collections.Counter()
    for k, inf in ev[a].items():
        if not k[0].startswith('mc') or inf['truth'] is None:
            continue
        s['n_' + inf['truth']] += 1
        s['nue_' + inf['truth']] += inf['nue']
        s['numu_' + inf['truth']] += inf['numu']
        s['generic_' + inf['truth']] += inf['generic']
    res.setdefault('selection_mc', {})[a] = dict(s)
# data
for a in ARMS:
    s = collections.Counter()
    for k, inf in ev[a].items():
        if k[0] != 'data':
            continue
        s['events'] += 1; s['generic'] += inf['generic']; s['nue'] += inf['nue']; s['numu'] += inf['numu']
    res.setdefault('data', {})[a] = dict(s)
    if a != 'master':
        ch = collections.Counter()
        for k, inf in ev[a].items():
            if k[0] != 'data' or k not in ev['master']:
                continue
            m = ev['master'][k]
            for f in ('generic', 'nue', 'numu'):
                if inf[f] != m[f]:
                    ch[f + ('_gained' if inf[f] else '_lost')] += 1
        res['data'][a]['vs_master'] = dict(ch)
# cost
for a in ARMS:
    c = cost[a]
    vt = [x for u in c.values() for x in u['vtx_ms']]
    hk = [x for u in c.values() for x in u['hook_ms']]
    res.setdefault('cost', {})[a] = dict(
        runs=len(c), failed=[u for u, v in c.items() if v['rc'] != 0],
        cpu_s_total=round(sum(v['cpu'] or 0 for v in c.values()), 1), rss_mb_max=round(max((v['rss'] or 0) for v in c.values()), 0),
        rss_mb_median=round(float(np.median([v['rss'] for v in c.values() if v['rss']])), 0) if c else None,
        vertex_calls=len(vt), vertex_ms_median=round(float(np.median(vt)), 1) if vt else None,
        vertex_ms_p90=round(float(np.percentile(vt, 90)), 1) if vt else None, vertex_s_total=round(sum(vt) / 1e3, 1),
        dv2_calls=len(hk), dv2_ms_median=round(float(np.median(hk)), 1) if hk else None, dv2_nopred=sum(v['hook_nopred'] for v in c.values()))
# per-unit pairs vs master: CPU and RSS on the same input
for a in ARMS[1:]:
    dc, dr = [], []
    for u, v in cost[a].items():
        m = cost['master'].get(u)
        if m and v['cpu'] and m['cpu']:
            dc.append(v['cpu'] - m['cpu']); dr.append(v['rss'] - m['rss'])
    res['cost'][a]['vs_master_cpu_s_median'] = round(float(np.median(dc)), 1) if dc else None
    res['cost'][a]['vs_master_rss_mb_median'] = round(float(np.median(dr)), 0) if dr else None
json.dump(res, open(OUT, 'w'), indent=1)
print(json.dumps(res, indent=1))
