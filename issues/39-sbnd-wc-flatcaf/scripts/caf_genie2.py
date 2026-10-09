import ROOT, sys
ROOT.gErrorIgnoreLevel = ROOT.kError
f = ROOT.TFile.Open(sys.argv[1]); t = f.Get('recTree'); g = f.Get('GenieEvtRecTree')
def arr(tr, n):
    l = tr.GetLeaf(n); return [l.GetValue(j) for j in range(l.GetLen())] if l else None
for i in range(5):
    t.GetEntry(i)
    print('rec %d evt %d nnu %d genie_evtrec_idx %s nu.index %s E %s' % (i, t.GetLeaf('rec.hdr.evt').GetValue(), t.GetLeaf('rec.mc.nnu').GetValue(),
          arr(t, 'rec.mc.nu.genie_evtrec_idx'), arr(t, 'rec.mc.nu.index'), [round(x,3) for x in arr(t, 'rec.mc.nu.E')]))
for j in range(6):
    g.GetEntry(j)
    p4 = arr(g, 'GenieEvtRec.StdHepP4'); pdg = arr(g, 'GenieEvtRec.StdHepPdg')
    print('genie %d GENIEEntry %s EvtNum %s SourceFileHash %s  first particle pdg %s E %.3f' % (j, arr(g,'GENIEEntry'), arr(g,'GenieEvtRec.EvtNum'), arr(g,'SourceFileHash'), pdg[0] if pdg else None, p4[3] if p4 else -1))
l = g.GetLeaf('GENIEEntry'); print('GENIEEntry leaf', l.GetTypeName(), l.GetTitle())
