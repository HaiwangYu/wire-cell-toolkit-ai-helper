#!/usr/bin/env python3
"""Gate G1/G2 (ai-helper issue 44): compare two step-2 output dirs (<arm>/pr) by CONTENT.

    compare-arms.py <ref pr dir> <arm pr dir> [--allow-new T_dlvtx_space,T_dlvtx_call.space_cluster_id,...]

tracking-pr.root of every pr_evt*: the same trees with the same entries and, branch by branch,
the same values (vectors element-wise; doubles/floats exactly).  Trees/branches named in
--allow-new may exist only in the arm.  recTreeWireCell (the flat copy of all trees) is
compared the same way.  Trun.wct_version is reported, not counted.
mabc-pr.zip: every member's JSON equal (members only in one zip are differences).
Run with PyROOT (setup-uan-root.sh on the UAN)."""
import sys, os, glob, json, zipfile
import uproot, awkward as ak, numpy as np
args = sys.argv[1:]
allow = set()
if '--allow-new' in args:
    i = args.index('--allow-new'); allow = set(args[i + 1].split(',')); del args[i:i + 2]
REF, ARM = args
IGNORE = {'Trun.wct_version', 'recTreeWireCell.wc.Trun.wct_version'}

def flat(x):
    parts = []
    while True:
        try:
            parts.append(np.asarray(ak.flatten(x, axis=None)))
            break
        except Exception:
            return None
    return parts

def same(x, y):
    try:
        d = x.ndim
    except Exception:
        d = 1
    try:
        fx, fy = np.asarray(ak.flatten(x, axis=None)), np.asarray(ak.flatten(y, axis=None))
        if fx.shape != fy.shape: return False
        if fx.dtype.kind == 'f':
            if not np.array_equal(fx, fy, equal_nan=True): return False
        elif not np.array_equal(fx, fy): return False
        for ax in range(1, d):
            if not np.array_equal(np.asarray(ak.flatten(ak.num(x, axis=ax), axis=None)),
                                  np.asarray(ak.flatten(ak.num(y, axis=ax), axis=None))): return False
        return True
    except Exception:
        return ak.to_list(x) == ak.to_list(y)

def trees(f):
    return {k.split(';')[0]: f[k] for k, c in f.classnames().items() if c == 'TTree'}

def cmp_file(fr, fa, tag, out):
    r, a = uproot.open(fr), uproot.open(fa)
    tr_, ta_ = trees(r), trees(a)
    for k in sorted(set(tr_) - set(ta_)): out.append('%s: tree %s missing in arm' % (tag, k))
    for k in sorted(set(ta_) - set(tr_)):
        if k not in allow: out.append('%s: tree %s only in arm' % (tag, k))
    for k in sorted(set(tr_) & set(ta_)):
        tr, ta = tr_[k], ta_[k]
        nr, na = list(tr.keys()), list(ta.keys())
        for b in na:
            if b not in nr and '%s.%s' % (k, b) not in allow and not any(
                    p.endswith('*') and ('%s.%s' % (k, b)).startswith(p[:-1]) for p in allow):
                out.append('%s: %s.%s only in arm' % (tag, k, b))
        for b in nr:
            if b not in na: out.append('%s: %s.%s missing in arm' % (tag, k, b))
        if tr.num_entries != ta.num_entries:
            out.append('%s: %s entries %d vs %d' % (tag, k, tr.num_entries, ta.num_entries)); continue
        common = [b for b in nr if b in na and '%s.%s' % (k, b) not in IGNORE]
        try:
            A = tr.arrays(common, library='ak'); B = ta.arrays(common, library='ak')
        except Exception as e:
            out.append('%s: %s unreadable (%s)' % (tag, k, str(e)[:80])); continue
        for b in common:
            if not same(A[b], B[b]):
                x, y = ak.to_list(A[b]), ak.to_list(B[b])
                bad = [i for i in range(len(x)) if x[i] != y[i]]
                out.append('%s: %s.%s differs in %d/%d entries, e.g. %s vs %s'
                           % (tag, k, b, len(bad), len(x), str(x[bad[0]])[:70] if bad else '', str(y[bad[0]])[:70] if bad else ''))

out = []
er = sorted(os.path.basename(p) for p in glob.glob(os.path.join(REF, 'pr_evt*')))
ea = sorted(os.path.basename(p) for p in glob.glob(os.path.join(ARM, 'pr_evt*')))
if er != ea: out.append('event dirs differ: %d vs %d (%s)' % (len(er), len(ea), sorted(set(er) ^ set(ea))[:5]))
n = 0
for e in sorted(set(er) & set(ea)):
    fr, fa = os.path.join(REF, e, 'tracking-pr.root'), os.path.join(ARM, e, 'tracking-pr.root')
    if os.path.exists(fr) and os.path.exists(fa):
        cmp_file(fr, fa, e, out); n += 1
zr, za = os.path.join(REF, 'mabc-pr.zip'), os.path.join(ARM, 'mabc-pr.zip')
nz = 0
if os.path.exists(zr) and os.path.exists(za):
    Zr, Za = zipfile.ZipFile(zr), zipfile.ZipFile(za)
    mr, ma = set(Zr.namelist()), set(Za.namelist())
    for m in sorted(mr ^ ma): out.append('bee: member %s only in %s' % (m, 'ref' if m in mr else 'arm'))
    for m in sorted(mr & ma):
        dr, da = Zr.read(m), Za.read(m)
        if dr == da: nz += 1; continue
        try:
            if json.loads(dr) == json.loads(da): nz += 1; continue
        except ValueError:
            pass
        out.append('bee: member %s differs' % m)
else:
    out.append('bee: zip missing (%s %s)' % (os.path.exists(zr), os.path.exists(za)))
print('%s vs %s: %d events compared, %d Bee members equal, %d differences' % (REF, ARM, n, nz, len(out)))
for l in out[:60]: print('  ' + l)
sys.exit(1 if out else 0)
