import ROOT, sys
ROOT.gErrorIgnoreLevel = ROOT.kError
f = ROOT.TFile.Open(sys.argv[1]); t = f.Get('recTree')
def leaf(name):
    b = t.GetBranch(name); l = b.GetListOfLeaves()[0]
    return '%s  type=%s  title=%s' % (name, l.GetTypeName(), l.GetTitle())
for n in ['rec.nslc', 'rec.slc..length', 'rec.slc.vertex.x', 'rec.slc.reco.npfp', 'rec.slc.reco.pfp..length', 'rec.slc.reco.pfp..idx',
          'rec.slc.reco.pfp.trk.len', 'rec.slc.reco.pfp.trk.chi2pid..length', 'rec.slc.reco.pfp.trk.chi2pid..idx', 'rec.slc.reco.pfp.trk.chi2pid.chi2_muon',
          'rec.mc.nnu', 'rec.mc.nu..length', 'rec.mc.nu.E', 'rec.mc.nu.genieIdx', 'rec.mc.nu.prim..length', 'rec.mc.nu.prim..idx', 'rec.mc.nu.prim.pdg',
          'rec.slc.truth.index', 'rec.slc.tmatch.index', 'rec.hdr.run', 'rec.hdr.subrun', 'rec.hdr.evt', 'rec.hdr.ngenevt', 'rec.hdr.sourceName']:
    try: print(leaf(n))
    except Exception as e: print(n, 'MISSING')
print()
for i in range(3):
    t.GetEntry(i)
    g = lambda n: t.GetLeaf(n)
    def arr(n):
        l = t.GetLeaf(n); return [l.GetValue(j) for j in range(l.GetLen())]
    print('entry', i, 'rse', int(g('rec.hdr.run').GetValue()), int(g('rec.hdr.subrun').GetValue()), int(g('rec.hdr.evt').GetValue()),
          '| nslc', int(g('rec.nslc').GetValue()), 'slc..length', int(g('rec.slc..length').GetValue()))
    print('   slc.reco.npfp', arr('rec.slc.reco.npfp'), ' pfp..length', arr('rec.slc.reco.pfp..length'), ' pfp..idx', arr('rec.slc.reco.pfp..idx'))
    print('   pfp.trk.len (flat, %d)' % len(arr('rec.slc.reco.pfp.trk.len')), [round(x,1) for x in arr('rec.slc.reco.pfp.trk.len')][:12])
    print('   mc.nnu', arr('rec.mc.nnu'), 'nu.E', [round(x,3) for x in arr('rec.mc.nu.E')], 'nu.genieIdx', arr('rec.mc.nu.genieIdx') if t.GetLeaf('rec.mc.nu.genieIdx') else '-')
    print('   slc.tmatch.index', arr('rec.slc.tmatch.index') if t.GetLeaf('rec.slc.tmatch.index') else '-')
