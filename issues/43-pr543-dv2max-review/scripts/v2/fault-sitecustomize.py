# PR #543 re-review, fault injection: with DV2_FAULT_CALL=k, the k-th DV2-MAX call (0-based) raises inside
# Vertexer.run, i.e. a Python error during an event.  Loaded by the embedded interpreter through PYTHONPATH.
import os
if os.environ.get('DV2_FAULT_CALL'):
    import itertools
    import dv2max_vertexer.vertexer as _vx
    _orig = _vx.Vertexer.run
    _n = itertools.count()
    _k = int(os.environ['DV2_FAULT_CALL'])
    def _run(self, ev, *a, **kw):
        if next(_n) == _k:
            raise RuntimeError('injected fault (DV2_FAULT_CALL=%d)' % _k)
        return _orig(self, ev, *a, **kw)
    _vx.Vertexer.run = _run
