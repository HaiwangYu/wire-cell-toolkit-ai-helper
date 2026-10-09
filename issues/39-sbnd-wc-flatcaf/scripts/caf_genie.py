import ROOT, sys
ROOT.gErrorIgnoreLevel = ROOT.kError
f = ROOT.TFile.Open(sys.argv[1]); t = f.Get('recTree'); g = f.Get('GenieEvtRecTree')
print('GenieEvtRecTree branches:', [(b.GetName(), b.GetClassName()) for b in g.GetListOfBranches()])
nubr = [b.GetName() for b in t.GetListOfBranches() if b.GetName().startswith('rec.mc.nu.') and b.GetName().count('.') == 3]
print('rec.mc.nu scalar-ish branches:', [b for b in nubr if any(k in b.lower() for k in ('idx', 'genie', 'index', 'id'))])
hdr = [b.GetName() for b in t.GetListOfBranches() if b.GetName().startswith('rec.hdr.') and any(k in b.GetName().lower() for k in ('genie', 'idx', 'ngen', 'first', 'evtrec'))]
print('rec.hdr related:', hdr)
tot = 0
for i in range(t.GetEntries()):
    t.GetEntry(i); n = int(t.GetLeaf('rec.mc.nnu').GetValue()); tot += n
print('sum over events of rec.mc.nnu =', tot, ' GenieEvtRecTree entries =', g.GetEntries())
