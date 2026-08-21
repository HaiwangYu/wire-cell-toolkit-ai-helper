#!/usr/bin/env python3
"""Print one "run subrun event" line per entry of an art file's Events tree.

Read from EventAuxiliary rather than `lar -c eventdump.fcl` (memory
feedback-pyroot-eventauxiliary): no fhicl parse, no service init, no
tf-default.root/memory.db droppings in cwd.  All branches but EventAuxiliary
are disabled so the read stays small even on a big reco1 file.

Exit non-zero (and print nothing) if the file cannot be opened or has no
Events tree, so the caller can mark the file UNREADABLE and move on.
"""
import sys
import ROOT
ROOT.gErrorIgnoreLevel = ROOT.kError
ROOT.PyConfig.IgnoreCommandLineOptions = True

path = sys.argv[1]
f = ROOT.TFile.Open(path)
if not f or f.IsZombie():
    sys.exit(1)
t = f.Get('Events')
if not t:
    sys.exit(1)
t.SetBranchStatus('*', 0)
t.SetBranchStatus('EventAuxiliary', 1)
out = []
for i in range(int(t.GetEntries())):
    t.GetEntry(i)
    rid = t.EventAuxiliary.id()
    out.append("%d %d %d" % (rid.run(), rid.subRun(), rid.event()))
if not out:
    sys.exit(1)
print("\n".join(out))
