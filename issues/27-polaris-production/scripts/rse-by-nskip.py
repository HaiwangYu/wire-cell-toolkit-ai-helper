#!/usr/bin/env python3
"""Write <rundir>/rse-by-nskip.tsv from each evtK/tracking-pr.root Trun tree (run INSIDE SL7)."""
import sys, os, glob, ROOT
ROOT.gErrorIgnoreLevel = ROOT.kError
R = sys.argv[1]
rows = ["nskip\trun\tsubrun\tevent\ttrees\ttrackpr_bytes"]
for d in sorted([p for p in glob.glob(R + '/evt[0-9]*') if os.path.isdir(p)], key=lambda p: int(os.path.basename(p)[3:])):
    k = os.path.basename(d)[3:]; fn = d + '/tracking-pr.root'
    if not os.path.exists(fn): rows.append(f"{k}\t-\t-\t-\t0\t0"); continue
    f = ROOT.TFile.Open(fn); t = f.Get("Trun"); t.GetEntry(0)
    rows.append(f"{k}\t{t.runNo}\t{t.subRunNo}\t{t.eventNo}\t{len(f.GetListOfKeys())}\t{os.path.getsize(fn)}")
open(R + '/rse-by-nskip.tsv', 'w').write("\n".join(rows) + "\n"); print("\n".join(rows))
