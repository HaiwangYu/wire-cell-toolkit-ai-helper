#!/usr/bin/env python3
"""Standalone DL-vertex inference on the dumped network input (ai-helper issue 35, M3).

Reads T_dlvtx_cloud / T_dlvtx_call from tracking-pr.root files written with
dl_vtx_dump=true.  For every recorded call it re-runs the SAME Python entry point
production uses -- SCN_Vertex.SCN_Vertex (pyutil/python/SCN_Vertex.py, which
WCPPyUtil::SCN_Vertex imports) -- on the recorded float32 cloud, with the recorded
top_k and the same weights file, then compares the result with the recorded payload.

Run INSIDE SL7 with setup-aurora-run.sh sourced (PyROOT + the scn venv + $OPT/python):
  dlvtx-replay.py [--weights <path or WIRECELL_PATH-relative>] [--json out.json] <tracking-pr.root> ...

Default weights: the SBND production dl_weights, uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth,
resolved along WIRECELL_PATH exactly as TaggerCheckNeutrino resolves it (Persist::resolve).
Also prints, per pass, how often the DL was accepted and (MC) the distance of the
traditional / DL / final vertex to the truth vertex in the cloud frame."""
import argparse, collections, json, math, os, sys
import numpy as np
import ROOT
import SCN_Vertex

ROOT.gErrorIgnoreLevel = ROOT.kError
PROD_WEIGHTS = 'uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth'


def resolve(path):
    if os.path.isabs(path) and os.path.exists(path):
        return path
    for d in os.environ.get('WIRECELL_PATH', '').split(':'):
        p = os.path.join(d, path)
        if d and os.path.exists(p):
            return p
    raise SystemExit('cannot resolve weights %s along WIRECELL_PATH' % path)


def load(fn):
    """{(nu_index, call_index): call dict with the cloud attached}."""
    f = ROOT.TFile.Open(fn)
    tc, tp = f.Get('T_dlvtx_call'), f.Get('T_dlvtx_cloud')
    if not tc or not tp:
        return {}, None
    calls = {}
    for e in tc:
        key = (e.nu_index, e.call_index)
        calls[key] = dict(rse=(e.runNo, e.subRunNo, e.eventNo), pass_=getattr(e, 'pass'),
                          top_k=e.top_k, n_points=e.n_points, n_vertex_rows=e.n_vertex_rows,
                          payload=np.array(list(e.payload), dtype=np.float32), payload_from_off=e.payload_from_off,
                          trad=(e.trad_valid, e.trad_x, e.trad_y, e.trad_z), accepted=e.accepted,
                          dl=(e.dl_x, e.dl_y, e.dl_z), final=(e.final_valid, e.final_x, e.final_y, e.final_z),
                          truth=(e.truth_valid, e.truth_reco_x, e.truth_reco_y, e.truth_reco_z),
                          pts=[[], [], [], []])
    for e in tp:
        c = calls[(e.nu_index, e.call_index)]
        for i, v in enumerate((e.x, e.y, e.z, e.q)):
            c['pts'][i].append(v)
    return calls, f


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--weights', default=PROD_WEIGHTS)
    ap.add_argument('--json', default=None)
    ap.add_argument('files', nargs='+')
    a = ap.parse_args()
    weights = resolve(a.weights)
    print('weights:', weights)
    n = n_exact = n_skip = 0
    worst = 0.0
    rows = []
    perpass = collections.defaultdict(lambda: collections.Counter())
    dists = collections.defaultdict(list)
    for fn in a.files:
        calls, f = load(fn)
        for (nu, ci), c in sorted(calls.items()):
            pname = 'off' if c['pass_'] == 1 else 'prod'
            perpass[pname]['calls'] += 1
            perpass[pname]['accepted'] += c['accepted']
            if c['payload_from_off']:
                n_skip += 1      # dual-chain voxels mode: no inference in this call
                continue
            x, y, z, q = (np.array(v, dtype=np.float32) for v in c['pts'])
            assert len(x) == c['n_points']
            out = np.frombuffer(SCN_Vertex.SCN_Vertex(weights, x.tobytes(), y.tobytes(), z.tobytes(), q.tobytes(),
                                                      'float32', int(c['top_k'])), dtype=np.float32)
            same_len = len(out) == len(c['payload'])
            d = float(np.max(np.abs(out - c['payload']))) if same_len and len(out) else (0.0 if same_len else float('inf'))
            exact = same_len and bool(np.array_equal(out, c['payload']))
            n += 1; n_exact += exact; worst = max(worst, d)
            rows.append(dict(file=fn, rse=c['rse'], nu_index=nu, call_index=ci, pass_=pname, top_k=c['top_k'],
                             n_points=c['n_points'], exact=exact, max_abs=d))
            if not exact:
                print('MISMATCH %s rse=%s nu=%d call=%d pass=%s: len %d vs %d, max |diff| %.3g'
                      % (os.path.basename(fn), c['rse'], nu, ci, pname, len(out), len(c['payload']), d))
            tv, tx, ty, tz = c['truth']
            if tv:
                t = (tx, ty, tz)
                if c['trad'][0]: dists[pname + ':trad'].append(dist(c['trad'][1:], t))
                if c['accepted']: dists[pname + ':dl'].append(dist(c['dl'], t))
                if c['final'][0] and pname == 'prod': dists['final'].append(dist(c['final'][1:], t))
    print('=> %d calls re-run: %d bit-identical, worst |diff| %.3g; %d skipped (payload from the OFF pass)'
          % (n, n_exact, worst, n_skip))
    for p, cnt in sorted(perpass.items()):
        print('   pass %-4s: %d calls, DL accepted in %d' % (p, cnt['calls'], cnt['accepted']))
    for k, v in sorted(dists.items()):
        v = np.array(v)
        print('   truth distance %-10s n=%-4d median %.2f cm, <1 cm %d, <3 cm %d' % (k, len(v), np.median(v), (v < 1).sum(), (v < 3).sum()))
    if a.json:
        json.dump(dict(weights=weights, calls=rows, n=n, n_exact=n_exact, worst=worst), open(a.json, 'w'), indent=1)
    sys.exit(0 if n_exact == n else 1)


if __name__ == '__main__':
    main()
