#!/usr/bin/env python3
"""Config proof for deploying toolkit sbnd-dlvtx-35 in our larwirecell 2-step chain (issue 38).

Follows toolkit cfg/pgrapher/experiment/sbnd/docs/deploy-validation-2026-10-01.md sec 3 items 2-4,
on COMPILED JSON only (no output files).  Run INSIDE SL7 with sbnd/setup-ap.sh sourced, so that
WIRECELL_PATH is exactly what a `lar` job of this chain sees:

    SL7_SETUP=.../sbnd/setup-ap.sh in-gpvm-sl7.sh python3 cfg-proof.py <outdir>

Trees (each a `git archive` of the toolkit cfg/, swapped in for the checkout's cfg/ on WIRECELL_PATH):
    old    = 51b5a1fc   master before the 2026-10-01 fast-forward
    master = 0319ea67   master of 2026-10-01 (the deploy note's commit)
    dlvtx  = HEAD       sbnd-dlvtx-35 (master merged + the DL dump), the tree we deploy

Jobs (8, as issue 35 log f): step 1 (wcls-img-clus-matching{,-data}.fcl), step 2 (wct-pr.jsonnet),
and the obsolete 1-step pr-flash / pr-hits, for sim and data.  Step-1 / 1-step extVars are taken
from `fhicl-dump` of the fcl itself (params -> ext-str, structs -> ext-code), i.e. what WCLS hands
to the jsonnet.  Step 2 gets the TLAs run-2step.pbs gives it.

Checks:
  C1  old -> master: only the SBND PR jobs move, by exactly main_vertex_swap_apply (TaggerCheckNeutrino)
      and nu_particle_links (UbooneTaggerOutputVisitor); step 1 byte-identical.        (note sec 2)
  C2  master -> dlvtx with dl_vtx_dump off: all 8 byte-identical.                      (issue 35 f)
  C3  dlvtx dump on vs off (step 2): only SCEFieldTH3:sbnd_dualmap_fwd added and the dump keys of
      TaggerCheckNeutrino:pr / SbndPrMagnifyTrackingVisitor:pr changed.                 (issue 35 f)
  C4  attribution (note sec 3 item 4): dlvtx step 2 with an overlay clus.jsonnet that sets
      main_vertex_swap_apply=false and root_particle_links=false == old step 2, except an explicit
      main_vertex_swap_apply:false.
  C5  step-1 old-flash attribution config (note sec 3 item 3): compiles, and differs from step 1 only
      in the SBNDOpFlashFinder prompt_min_* keys.
  C6  no shadowing: every dlvtx job compiled with the runtime WIRECELL_PATH == compiled with a
      minimal path (toolkit cfg + wcp sbnd re-exports + wire-cell-data).
  C7  every component type of every compiled job is registered by a plugin the job loads
      (the make_<type>_factory symbol in the installed libWireCell*.so, larwirecell included).
  C8  every data file named in the compiled JSON resolves on the runtime WIRECELL_PATH; reports the
      root it resolves from and any other root holding a DIFFERENT file of that name (data shadowing).
  C9  data vs sim: the full list of keys that differ, per job, for review.
  C10 operating point snapshot of step 2 (TaggerCheckNeutrino:pr and friends) for the record.
"""
import collections, hashlib, json, os, re, subprocess, sys, tarfile, io

OUT = os.path.abspath(sys.argv[1])
WCT = '/exp/sbnd/app/users/yuhw/wire-cell-toolkit'
WCP = '/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd'
DATA = '/exp/sbnd/app/users/yuhw/wire-cell-data'
OPT = '/exp/sbnd/app/users/yuhw/opt'
LWC_LIB = OPT + '/larwirecell/v10_01_28/slf7.x86_64.e26.prof/lib'
REFS = collections.OrderedDict([('old', '51b5a1fc'), ('master', '0319ea67'), ('dlvtx', 'HEAD')])
J = 'pgrapher/experiment/sbnd'
FCLS = {  # job -> (sim fcl, data fcl)
    'step1': ('wcls-img-clus-matching.fcl', 'wcls-img-clus-matching-data.fcl'),
    'flash': ('wcls-img-clus-matching-pr-flash.fcl', 'wcls-img-clus-matching-pr-flash-data.fcl'),
    'hits': ('wcls-img-clus-matching-pr-hits.fcl', 'wcls-img-clus-matching-pr-data-hits.fcl'),
}
os.makedirs(OUT + '/json', exist_ok=True)
os.makedirs(OUT + '/trees', exist_ok=True)
REPORT = open(OUT + '/report.txt', 'w')
FAIL = []


def say(*a):
    s = ' '.join(str(x) for x in a)
    print(s); REPORT.write(s + '\n'); REPORT.flush()


def check(name, ok, detail=''):
    say('%s %s%s' % ('PASS' if ok else 'FAIL', name, (': ' + detail) if detail else ''))
    if not ok:
        FAIL.append(name)


# ---------------------------------------------------------------- trees
dirty = subprocess.run(['git', '-C', WCT, 'status', '--short', 'cfg'], capture_output=True, text=True).stdout.strip()
head = subprocess.run(['git', '-C', WCT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
branch = subprocess.run(['git', '-C', WCT, 'branch', '--show-current'], capture_output=True, text=True).stdout.strip()
say('toolkit checkout %s (%s); cfg/ working-tree changes: %s' % (head, branch, dirty or 'none'))
check('C0 toolkit cfg/ clean (HEAD == what lar compiles)', not dirty, dirty)
TREES = {}
for name, ref in REFS.items():
    d = '%s/trees/%s' % (OUT, name)
    if not os.path.isdir(d + '/cfg'):
        os.makedirs(d, exist_ok=True)
        blob = subprocess.run(['git', '-C', WCT, 'archive', ref, 'cfg'], capture_output=True, check=True).stdout
        tarfile.open(fileobj=io.BytesIO(blob)).extractall(d)
    sha = subprocess.run(['git', '-C', WCT, 'rev-parse', '--short', ref], capture_output=True, text=True).stdout.strip()
    TREES[name] = d + '/cfg'
    say('tree %-6s = %s (%s)' % (name, ref, sha))

RUNTIME = os.environ['WIRECELL_PATH'].split(':')
check('C0 runtime WIRECELL_PATH has the toolkit cfg first among cfg trees',
      WCT + '/cfg' in RUNTIME and RUNTIME.index(WCT + '/cfg') < RUNTIME.index(WCP),
      ' : '.join(RUNTIME))


def wpath(tree, minimal=False):
    if minimal:
        return ':'.join([TREES[tree], WCP, DATA + '/sbnd/photodet', DATA])
    return ':'.join(TREES[tree] if p == WCT + '/cfg' else p for p in RUNTIME)


# ---------------------------------------------------------------- extVars from the fcls
def fcl_extvars(fcl):
    txt = subprocess.run(['fhicl-dump', fcl], capture_output=True, text=True, cwd=WCP, check=True).stdout
    i = txt.index('wcls_main: {')
    depth, j = 0, i
    while True:
        c = txt[j]
        depth += (c == '{') - (c == '}')
        j += 1
        if depth == 0 and c == '}':
            break
    block = txt[i:j]

    def sub(key):
        m = re.search(r'\n\s*%s: \{(.*?)\n\s*\}' % key, block, re.S)
        out = collections.OrderedDict()
        for line in (m.group(1).strip().splitlines() if m else []):
            k, v = line.strip().split(':', 1)
            out[k.strip()] = json.loads(v.strip())
        return out
    configs = re.search(r'configs: \[\s*"([^"]+)"', block).group(1)
    plugins = re.findall(r'"(WireCell\w+)"', re.search(r'plugins: \[(.*?)\]', block, re.S).group(1))
    return dict(config=configs, params=sub('params'), structs=sub('structs'), plugins=plugins)


EXT = {}
for job, pair in FCLS.items():
    for real, fcl in zip(('sim', 'data'), pair):
        EXT[(job, real)] = fcl_extvars(fcl)
        e = EXT[(job, real)]
        say('extvars %s/%s from %s: config=%s; params=%s; structs=%s' % (job, real, fcl, e['config'], dict(e['params']), dict(e['structs'])))
json.dump({'%s/%s' % k: v for k, v in EXT.items()}, open(OUT + '/fcl-extvars.json', 'w'), indent=1)


# ---------------------------------------------------------------- compile
def compile_job(tree, job, real, extra=(), minimal=False, tag=None, path=None):
    env = dict(os.environ, WIRECELL_PATH=path or wpath(tree, minimal))
    if job == 'step2':
        args = ['-A', 'input=qlpctree.tar.gz', '-A', 'reality=' + real, J + '/wct-pr.jsonnet']
    else:
        e = EXT[(job, real)]
        args = []
        for k, v in e['params'].items():
            args += ['-V', '%s=%s' % (k, v)]
        for k, v in e['structs'].items():
            args += ['-C', '%s=%s' % (k, v)]
        args += [e['config']]
    name = tag or '%s-%s-%s%s' % (tree, job, real, '-min' if minimal else '')
    p = subprocess.run(['wcsonnet'] + list(extra) + args, capture_output=True, text=True, env=env)
    fn = '%s/json/%s.json' % (OUT, name)
    open(fn, 'w').write(p.stdout)
    if p.returncode != 0:
        say('COMPILE FAILED %s: %s' % (name, p.stderr.strip().splitlines()[-3:]))
        FAIL.append('compile ' + name)
        return None
    return p.stdout


def nodes(txt):
    return collections.OrderedDict(('%s:%s' % (n['type'], n.get('name', '')), n.get('data', {})) for n in json.loads(txt))


def flat(x, pre=''):
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            out.update(flat(v, pre + '.' + k if pre else k))
        return out if x else {pre: {}}
    if isinstance(x, list) and x and any(isinstance(v, (dict, list)) for v in x):
        out = {}
        for i, v in enumerate(x):
            out.update(flat(v, '%s[%d]' % (pre, i)))
        return out
    return {pre: x}


def ndiff(a_txt, b_txt):
    """node-by-node diff -> (only_a, only_b, {node: [(key, a, b), ...]})"""
    A, B = nodes(a_txt), nodes(b_txt)
    only_a = [k for k in A if k not in B]
    only_b = [k for k in B if k not in A]
    ch = collections.OrderedDict()
    for k in A:
        if k in B and A[k] != B[k]:
            fa, fb = flat(A[k]), flat(B[k])
            ch[k] = [(kk, fa.get(kk, '<absent>'), fb.get(kk, '<absent>')) for kk in sorted(set(fa) | set(fb)) if fa.get(kk, '<absent>') != fb.get(kk, '<absent>')]
    return only_a, only_b, ch


def short(v, n=90):
    s = json.dumps(v)
    return s if len(s) <= n else s[:n] + '...'


def show(only_a, only_b, ch, la, lb):
    for k in only_a:
        say('    only in %s: %s' % (la, k))
    for k in only_b:
        say('    only in %s: %s' % (lb, k))
    for k, kv in ch.items():
        say('    %s: %d key(s)' % (k, len(kv)))
        for kk, a, b in kv[:12]:
            say('      %s: %s -> %s' % (kk, short(a), short(b)))
        if len(kv) > 12:
            say('      ... %d more' % (len(kv) - 12))


def md5(s):
    return hashlib.md5(s.encode()).hexdigest()[:12]


JOBS = [(job, real) for job in ('step1', 'step2', 'flash', 'hits') for real in ('sim', 'data')]
C = {}
say('\n=== compile: 3 trees x 8 jobs (runtime WIRECELL_PATH)')
for tree in REFS:
    for job, real in JOBS:
        C[(tree, job, real)] = compile_job(tree, job, real)
        t = C[(tree, job, real)]
        if t:
            say('  %-6s %-5s %-4s %s %8d bytes %4d nodes' % (tree, job, real, md5(t), len(t), len(json.loads(t))))

# C1 old -> master
say('\n=== C1 old (51b5a1fc) -> master (0319ea67), every job (deploy note sec 2: only the SBND PR jobs move, by changes 2-3)')
EXPECT_C1 = {('TaggerCheckNeutrino:pr', 'main_vertex_swap_apply'), ('UbooneTaggerOutputVisitor:pr', 'nu_particle_links')}
for job, real in JOBS:
    a, b = C.get(('old', job, real)), C.get(('master', job, real))
    if not (a and b):
        continue
    if a == b:
        check('C1 %s/%s byte-identical' % (job, real), job == 'step1', 'step 1 must not move' if job == 'step1' else 'expected the PR keys to move but nothing moved')
        continue
    oa, ob, ch = ndiff(a, b)
    got = {(k, kk) for k, kv in ch.items() for kk, _, _ in kv}
    ok = job != 'step1' and not oa and not ob and got == EXPECT_C1
    check('C1 %s/%s moves by exactly main_vertex_swap_apply + nu_particle_links' % (job, real), ok)
    show(oa, ob, ch, 'old', 'master')

# C2 master -> dlvtx, knob off
say('\n=== C2 master (0319ea67) -> dlvtx (sbnd-dlvtx-35), dl_vtx_dump off: must be byte-identical')
for job, real in JOBS:
    a, b = C.get(('master', job, real)), C.get(('dlvtx', job, real))
    if a and b:
        check('C2 %s/%s byte-identical' % (job, real), a == b, md5(b))
        if a != b:
            show(*ndiff(a, b), 'master', 'dlvtx')

# C3 dump on
say('\n=== C3 dlvtx step 2 with dl_vtx_dump=true vs off')
for real in ('sim', 'data'):
    on = compile_job('dlvtx', 'step2', real, extra=['-S', 'dl_vtx_dump=true'], tag='dlvtx-step2-%s-dumpon' % real)
    off = C[('dlvtx', 'step2', real)]
    C[('dlvtx', 'step2on', real)] = on
    if not (on and off):
        continue
    oa, ob, ch = ndiff(off, on)
    ok = (not oa and ob == ['SCEFieldTH3:sbnd_dualmap_fwd'] and set(ch) <= {'TaggerCheckNeutrino:pr', 'SbndPrMagnifyTrackingVisitor:pr'}
          and all('dlvtx' in kk.lower() or 'dl_vtx' in kk.lower() or 'sce' in kk.lower() or 'truth' in kk.lower() for kv in ch.values() for kk, _, _ in kv))
    check('C3 %s: adds only SCEFieldTH3:sbnd_dualmap_fwd, changes only the dump keys of TaggerCheckNeutrino:pr / SbndPrMagnifyTrackingVisitor:pr' % real, ok, md5(on))
    show(oa, ob, ch, 'off', 'on')
    say('    SCEFieldTH3:sbnd_dualmap_fwd = %s' % short(nodes(on).get('SCEFieldTH3:sbnd_dualmap_fwd'), 400))

# C4 attribution overlay
say('\n=== C4 attribution: dlvtx step 2 + overlay clus.jsonnet (main_vertex_swap_apply=false, root_particle_links=false) vs old step 2')
ov = OUT + '/trees/overlay'
os.makedirs(ov + '/' + J, exist_ok=True)
src = open(TREES['dlvtx'] + '/' + J + '/clus.jsonnet').read()
n1 = len(re.findall(r'main_vertex_swap_apply\s*:\s*true', src))
src2 = re.sub(r'main_vertex_swap_apply\s*:\s*true', 'main_vertex_swap_apply: false', src)
src2, n2 = re.subn(r'(root_particle_links\s*=\s*)true', r'\1false', src2)
open(ov + '/' + J + '/clus.jsonnet', 'w').write(src2)
say('  overlay edits: main_vertex_swap_apply true->false x%d, root_particle_links=true->false x%d' % (n1, n2))
for real in ('sim', 'data'):
    t = compile_job('dlvtx', 'step2', real, tag='attrib-step2-%s' % real, path=ov + ':' + wpath('dlvtx'))
    old = C.get(('old', 'step2', real))
    if not (t and old):
        continue
    oa, ob, ch = ndiff(old, t)
    got = [(k, kk, a, b) for k, kv in ch.items() for kk, a, b in kv]
    ok = not oa and not ob and got == [('TaggerCheckNeutrino:pr', 'main_vertex_swap_apply', '<absent>', False)]
    check('C4 %s: == old step 2 except an explicit main_vertex_swap_apply:false' % real, ok)
    show(oa, ob, ch, 'old', 'overlay')

# C5 step-1 old-flash attribution config
say('\n=== C5 step-1 old-flash-rule config (note sec 3 item 3) vs step 1')
of = OUT + '/trees/oldflash'
os.makedirs(of, exist_ok=True)
open(of + '/step1_oldflash.jsonnet', 'w').write(
    "(import 'pgrapher/experiment/sbnd/wcls-img-clus-matching-pr-lib.jsonnet')(\n"
    "    flash_source='hits', xtpc_sc1_light_gate=true, xtpc_sc1_overpred_max=2.9, stage='ql',\n"
    "    ff={prompt_min_pe: 0, prompt_min_hits: 0, prompt_min_opdets: 0})\n")
step1_src = open(TREES['dlvtx'] + '/' + J + '/wcls-img-clus-matching.jsonnet').read()
say('  in-tree step 1 is: %s' % ' '.join(l.strip() for l in step1_src.splitlines() if l.strip() and not l.strip().startswith('//')))
for real in ('sim', 'data'):
    e = EXT[('step1', real)]
    env = dict(os.environ, WIRECELL_PATH=of + ':' + wpath('dlvtx'))
    args = sum([['-V', '%s=%s' % kv] for kv in e['params'].items()], []) + sum([['-C', '%s=%s' % kv] for kv in e['structs'].items()], [])
    p = subprocess.run(['wcsonnet'] + args + [of + '/step1_oldflash.jsonnet'], capture_output=True, text=True, env=env)
    open('%s/json/oldflash-step1-%s.json' % (OUT, real), 'w').write(p.stdout)
    if p.returncode:
        check('C5 %s compiles' % real, False, p.stderr.strip()[-300:])
        continue
    oa, ob, ch = ndiff(C[('dlvtx', 'step1', real)], p.stdout)
    keys = {kk.split('.')[-1] for kv in ch.values() for kk, _, _ in kv}
    ok = not oa and not ob and keys and keys <= {'prompt_min_pe', 'prompt_min_hits', 'prompt_min_opdets'} and all(k.startswith('SBNDOpFlashFinder') for k in ch)
    check('C5 %s: differs only in SBNDOpFlashFinder prompt_min_*' % real, ok)
    show(oa, ob, ch, 'step1', 'oldflash')

# C6 no shadowing
say('\n=== C6 runtime WIRECELL_PATH vs a minimal path (toolkit cfg + wcp sbnd + wire-cell-data): no cfg shadowing')
for job, real in JOBS:
    t = compile_job('dlvtx', job, real, minimal=True)
    check('C6 %s/%s identical under the minimal path' % (job, real), t == C[('dlvtx', job, real)])

# C7 factories
say('\n=== C7 every component type is registered by a loaded plugin')
libs = {}
for d in (OPT + '/lib', LWC_LIB):
    for f in os.listdir(d):
        if f.startswith('libWireCell') and f.endswith('.so'):
            libs[f[3:-3]] = d + '/' + f
# WIRECELL_FACTORY(NAME, ...) defines extern "C" make_NAME_factory (util NamedFactory.h); string
# search is NOT usable (the linker tail-merges literals: "QLMatching" lives inside "wclsQLMatching").
strs = {}
for name, path in libs.items():
    out = subprocess.run(['nm', '-D', '--defined-only', path], capture_output=True, text=True).stdout
    strs[name] = {m.group(1) for m in re.finditer(r' T make_(\w+)_factory$', out, re.M)}
for job, real in JOBS + [('step2on', 'sim'), ('step2on', 'data')]:
    t = C.get(('dlvtx', job, real))
    if not t:
        continue
    types = sorted({n['type'] for n in json.loads(t)})
    if job.startswith('step2'):
        plugins = [n['data'].get('plugins', []) for n in json.loads(t) if n['type'] == 'wire-cell']
        plugins = plugins[0] if plugins else []
    else:
        plugins = EXT[(job, real)]['plugins']
    # the loader also loads (and so registers the factories of) every WireCell lib a plugin NEEDs
    loaded, todo = set(), list(plugins)
    while todo:
        p = todo.pop()
        if p in loaded or p not in libs:
            continue
        loaded.add(p)
        dyn = subprocess.run(['readelf', '-d', libs[p]], capture_output=True, text=True).stdout
        todo += re.findall(r'NEEDED.*\[lib(WireCell\w+)\.so', dyn)
    missing = [ty for ty in types if ty != 'wire-cell' and not any(ty in strs.get(p, ()) for p in loaded)]
    via = sorted({p for p in loaded - set(plugins) for ty in types if ty in strs.get(p, ())})
    if via:
        say('  %s/%s: types registered by a NEEDED (not listed) lib: %s' % (job, real, {p: sorted(ty for ty in types if ty in strs[p]) for p in via}))
    nolib = [p for p in plugins if p not in libs]
    check('C7 %s/%s: %d types found in its %d plugins' % (job, real, len(types), len(plugins)), not missing and not nolib,
          'missing %s; plugins without a lib %s' % (missing, nolib) if (missing or nolib) else '')

# C8 data files
say('\n=== C8 data files named in the compiled JSON resolve on the runtime WIRECELL_PATH')
EXTS = ('.json', '.json.bz2', '.json.gz', '.xml', '.pth', '.pt', '.ts', '.root', '.npz', '.npy', '.txt', '.csv', '.tar', '.zip')
OUTKEYS = {'outname', 'bee_zip', 'output_filename', 'outfile', 'outpath', 'output', 'hdf5_filename', 'filename_out'}


def strings_in(x, key=''):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from strings_in(v, k)
    elif isinstance(x, list):
        for v in x:
            yield from strings_in(v, key)
    elif isinstance(x, str):
        yield key, x


files = collections.OrderedDict()
for (tree, job, real), t in C.items():
    if tree != 'dlvtx' or not t:
        continue
    for n in json.loads(t):
        for key, s in strings_in(n.get('data', {})):
            if s.endswith(EXTS) and not s.startswith('/') or (s.startswith('/') and s.endswith(EXTS)):
                files.setdefault(s, set()).add('%s:%s.%s' % (n['type'], n.get('name', ''), key))
nfile = 0
for f, users in files.items():
    if all(u.split('.')[-1] in OUTKEYS or u.split(':')[0].endswith('Sink') for u in users):
        say('  output (written, not read): %-40s <- %s' % (f, ', '.join(sorted(users))))
        continue
    hits = [r for r in RUNTIME if os.path.exists(os.path.join(r, f))] if not os.path.isabs(f) else ([f] if os.path.exists(f) else [])
    nfile += 1
    if not hits:
        check('C8 resolves: %s' % f, False, 'used by %s' % sorted(users)[:3])
        continue
    first = os.path.realpath(os.path.join(hits[0], f)) if not os.path.isabs(f) else f
    sums = {}
    for r in hits:
        p = os.path.join(r, f) if not os.path.isabs(f) else f
        sums[r] = hashlib.md5(open(p, 'rb').read()).hexdigest() if os.path.getsize(p) < 3e9 else 'big'
    diff = [r for r in hits[1:] if sums[r] != sums[hits[0]]]
    say('  %-62s -> %s  md5 %s%s' % (f, hits[0], sums[hits[0]][:12], ('  SHADOWS a different file in ' + ', '.join(diff)) if diff else ''))
    if diff:
        FAIL.append('C8 data shadowing ' + f)
check('C8 all %d input data files resolve, shadowing listed above' % nfile, not any(x.startswith('C8') for x in FAIL))

# C9 data vs sim
say('\n=== C9 data vs sim, per job (dlvtx tree): every differing key, for review')
for job in ('step1', 'step2', 'step2on', 'flash', 'hits'):
    s, d = C.get(('dlvtx', job, 'sim')), C.get(('dlvtx', job, 'data'))
    if s and d:
        oa, ob, ch = ndiff(s, d)
        say('  -- %s: %d node(s) only in sim, %d only in data, %d changed' % (job, len(oa), len(ob), len(ch)))
        show(oa, ob, ch, 'sim', 'data')

# C10 operating point snapshot
say('\n=== C10 step 2 (dump on, sim) operating point snapshot')
N = nodes(C[('dlvtx', 'step2on', 'sim')])
for k in ('TaggerCheckNeutrino:pr', 'UbooneTaggerOutputVisitor:pr', 'SbndPrMagnifyTrackingVisitor:pr'):
    if k in N:
        sel = {kk: v for kk, v in flat(N[k]).items() if re.search(r'dl_|dlvtx|dual|nu_per_bundle|fit_exclusion|swap|particle_links|weights|xml|output', kk)}
        say('  %s:' % k)
        for kk, v in sorted(sel.items()):
            say('    %s = %s' % (kk, short(v, 140)))
bdt = sorted({s for n in json.loads(C[('dlvtx', 'step2on', 'sim')]) for _, s in strings_in(n.get('data', {})) if s.endswith('.xml')})
say('  BDT xml files: %d (%s ... %s)' % (len(bdt), bdt[0] if bdt else '', bdt[-1] if bdt else ''))

say('\n=== RESULT: %s' % ('ALL PASS' if not FAIL else 'FAIL: ' + '; '.join(FAIL)))
sys.exit(1 if FAIL else 0)
