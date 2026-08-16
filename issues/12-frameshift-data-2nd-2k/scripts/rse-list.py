# Dump run/subrun/event via EventAuxiliary (NOT `lar -c eventdump.fcl`).
import ROOT, sys
f = ROOT.TFile.Open(sys.argv[1]); t = f.Get("Events")
b = [x.GetName() for x in t.GetListOfBranches() if "EventAuxiliary" in x.GetName()][0]
out = open(sys.argv[2], "w")
for i in range(t.GetEntries()):
    t.GetEntry(i); a = getattr(t, b)
    out.write("%d %d %d\n" % (a.run(), a.subRun(), a.event()))
out.close()
print(sys.argv[1].split('/')[-1], t.GetEntries())
