import ROOT, sys, collections
ROOT.gErrorIgnoreLevel = ROOT.kError
types = collections.Counter()
for fn in sys.argv[1:]:
    f = ROOT.TFile.Open(fn); print('==', fn.split('/')[-3:])
    for k in f.GetListOfKeys():
        o = k.ReadObj()
        if not isinstance(o, ROOT.TTree): print('  non-tree key', k.GetName(), k.GetClassName()); continue
        bs = []
        for b in o.GetListOfBranches():
            cls = b.GetClassName(); l = b.GetListOfLeaves()[0]
            t = cls if cls else (l.GetTypeName() + ('[%s]' % l.GetLeafCount().GetName() if l.GetLeafCount() else ('[%d]' % l.GetLen() if l.GetLen() > 1 else '')))
            types[t.split('[')[0] + ('[]' if '[' in t else '')] += 1; bs.append(t)
        print('  %-14s entries %5d  branches %3d  types %s' % (k.GetName(), o.GetEntries(), len(bs), dict(collections.Counter(x.split('[')[0] + ('[]' if '[' in x else '') for x in bs))))
print('ALL TYPES', dict(types))
