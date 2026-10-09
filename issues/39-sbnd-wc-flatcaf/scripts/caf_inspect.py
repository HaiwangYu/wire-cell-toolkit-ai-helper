import ROOT, sys, collections
ROOT.gErrorIgnoreLevel = ROOT.kError
f = ROOT.TFile.Open(sys.argv[1])
for k in f.GetListOfKeys():
    o = k.ReadObj()
    print('KEY', k.GetName(), k.GetClassName(), (o.GetEntries() if hasattr(o, 'GetEntries') else ''))
t = f.Get('recTree')
br = [b.GetName() for b in t.GetListOfBranches()]
print('recTree branches:', len(br))
# group by top-level path depth 2
grp = collections.Counter('.'.join(b.split('.')[:2]) for b in br)
for g, n in sorted(grp.items()): print('  %-40s %d' % (g, n))
lens = [b for b in br if b.endswith('..length')]
idx = [b for b in br if b.endswith('..idx')]
print('..length branches:', len(lens), lens[:40])
print('..idx branches:', len(idx), idx[:40])
