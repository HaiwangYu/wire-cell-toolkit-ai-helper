#!/usr/bin/env python3
"""M3 check (issue 33): the truth tables wclsTruthInformationAttacher appends to the step-1 tar,
against what wclsTensorSetLabeler (labeler_truth) independently wrote into the same set's metadata.
Pure python (tarfile + numpy); runs on a UAN.

usage: check-truth.py <qlpctree.tar.gz> [...]

per event (tensor set):
  truth_nu  vs the labeler's nu_* arrays: nu_idx, pdg, ccnc, int_type, E, vtx_x/y/z, edep (exact),
            flavor (code vs name)
  truth_pf  vs the labeler's Bee "mc" particle tree (set metadata "bee_pf_truth", MC only): the same
            particle ids; each particle's parent (the tree nesting; a neutrino node = 0) equals
            parent_trackid; KE (the node text, 0.1 MeV) and start/end (cm, float32 JSON) agree
Data sets (no truth tables): must carry no truth tensors and n_nu == 0."""
import io, json, re, sys, tarfile
import numpy as np
FLAV = {'none': 0, 'nue': 1, 'numu': 2, 'nutau': 3, 'nc': 4}
bad = 0
def fail(msg):
    global bad; bad += 1; print('  FAIL', msg)
for tp in sys.argv[1:]:
    t = tarfile.open(tp); names = t.getnames()
    sets = sorted({int(m.group(1)) for n in names for m in [re.match(r'.*tensorset_(\d+)_metadata\.json$', n)] if m})
    pre = names[0].split('tensorset_')[0] if 'tensorset_' in names[0] else 'clustering_'
    print(f'{tp}: {len(sets)} tensor sets')
    for ident in sets:
        md = json.load(t.extractfile(f'{pre}tensorset_{ident}_metadata.json'))
        tabs = {}
        k = 0
        while f'{pre}tensor_{ident}_{k}_metadata.json' in names:
            tm = json.load(t.extractfile(f'{pre}tensor_{ident}_{k}_metadata.json'))
            if tm.get('datatype') in ('truth_nu', 'truth_pf'):
                a = np.load(io.BytesIO(t.extractfile(f'{pre}tensor_{ident}_{k}_array.npy').read()))
                tabs[tm['datatype']] = (tm, a.reshape(-1, len(tm['columns'])))
            k += 1
        rse = (md.get('runNo'), md.get('subRunNo'), md.get('eventNo'))
        nnu = md.get('n_nu', 0)
        if 'truth_nu' not in tabs:
            ok = nnu == 0 and 'truth_pf' not in tabs
            print(f' {ident} rse={rse}: no truth tables, labeler n_nu={nnu} -> {"ok (data)" if ok else "MISMATCH"}')
            if not ok: fail(f'{ident}: labeler has {nnu} nu but no truth_nu table')
            continue
        nm, nu = tabs['truth_nu']; C = {c: i for i, c in enumerate(nm['columns'])}
        pm, pf = tabs.get('truth_pf', ({'columns': []}, np.zeros((0, 0))))
        P = {c: i for i, c in enumerate(pm['columns'])}
        msgs = []
        if nu.shape[0] != nnu: fail(f'{ident}: truth_nu {nu.shape[0]} rows vs labeler n_nu {nnu}')
        for r in range(min(nu.shape[0], nnu)):
            for col, key in (('nu_idx', 'nu_idx'), ('pdg', 'nu_pdg'), ('ccnc', 'nu_ccnc'), ('int_type', 'nu_int_type'),
                             ('E', 'nu_energy'), ('vtx_x', 'nu_vtx_x'), ('vtx_y', 'nu_vtx_y'), ('vtx_z', 'nu_vtx_z'), ('edep', 'nu_edep')):
                a, b = nu[r, C[col]], md[key][r]
                if not np.isclose(a, b, rtol=1e-12, atol=0): fail(f'{ident} nu row {r}: {col} {a!r} vs labeler {key} {b!r}')
            if nu[r, C['flavor']] != FLAV.get(md['nu_flavor'][r], -1): fail(f'{ident} nu row {r}: flavor {nu[r, C["flavor"]]} vs {md["nu_flavor"][r]}')
        # the labeler's particle tree -> {id: (parent id, KE MeV, start, end)}
        tree = {}
        def walk(node, parent):
            nid = int(node['id'])
            if nid >= 9000000 and nid < 9100000:          # the synthetic neutrino node
                for ch in node.get('children', []): walk(ch, 0)
                return
            m = re.search(r'([-0-9.]+) MeV', node.get('text', ''))
            tree[nid] = (parent, float(m.group(1)) if m else None, node.get('data', {}).get('start'), node.get('data', {}).get('end'))
            for ch in node.get('children', []): walk(ch, nid)
        for node in md.get('bee_pf_truth', []): walk(node, 0)
        rows = {int(pf[i, P['trackid']]): pf[i] for i in range(pf.shape[0])} if pf.size else {}
        if set(rows) != set(tree):
            fail(f'{ident}: truth_pf ids {len(rows)} vs labeler tree {len(tree)}; only table {sorted(set(rows) - set(tree))[:8]} only tree {sorted(set(tree) - set(rows))[:8]}')
        for tid in sorted(set(rows) & set(tree)):
            row, (par, ke, st, en) = rows[tid], tree[tid]
            if int(row[P['parent_trackid']]) != par: fail(f'{ident} track {tid}: parent {int(row[P["parent_trackid"]])} vs tree {par}')
            if ke is not None and abs(row[P['KE']] * 1e3 - ke) > 0.051: fail(f'{ident} track {tid}: KE {row[P["KE"]]*1e3:.3f} MeV vs tree {ke}')
            for lab, xyz, cols in (('start', st, ('start_x', 'start_y', 'start_z')), ('end', en, ('end_x', 'end_y', 'end_z'))):
                if xyz and not np.allclose([row[P[c]] for c in cols], xyz, rtol=1e-6, atol=1e-4): fail(f'{ident} track {tid}: {lab} {[row[P[c]] for c in cols]} vs tree {xyz}')
        nrow = [int(x) for x in pf[:, P['nu_row']]] if pf.size else []
        print(f' {ident} rse={rse}: truth_nu {nu.shape[0]} rows (labeler n_nu {nnu}), truth_pf {pf.shape[0]} rows '
              f'(labeler tree {len(tree)}; nu_row counts {dict((r, nrow.count(r)) for r in sorted(set(nrow)))})')
print(f'=> {"PASS" if not bad else "FAIL (%d)" % bad}')
sys.exit(1 if bad else 0)
