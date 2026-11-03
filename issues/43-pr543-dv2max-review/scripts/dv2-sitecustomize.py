# ai-helper #43 Q2 debug: when DV2_REC_DIR is set, every DV2-MAX call also pickles its intermediates
# (the event arrays, cached features, pass-1/pass-2 CNN records, ranker rows/sources/features/scores).
# Loaded by the (embedded or plain) interpreter at start-up through PYTHONPATH; the PR install is untouched.
import os
if os.environ.get('DV2_REC_DIR'):
    import pickle, itertools
    import dv2max_vertexer.vertexer as _vx
    _orig = _vx.Vertexer.run
    _n = itertools.count()
    def _run(self, ev, with_records=False):
        r = _orig(self, ev, with_records=True)
        k = next(_n)
        rec = dict(n=int(ev.n_points), tag_nu=ev.tag_nu, cand_xyz=ev.cand_xyz, xyz=ev.points_xyz, q=ev.points_q, features=getattr(ev, 'features', None), out=r)
        with open(os.path.join(os.environ['DV2_REC_DIR'], 'call-%03d-n%d.pkl' % (k, ev.n_points)), 'wb') as f:
            pickle.dump(rec, f)
        if r is not None and not with_records:
            for x in ('rec1', 'rec2', 'rows', 'sources', 'X', 's'):
                r.pop(x, None)
        return r
    _vx.Vertexer.run = _run
