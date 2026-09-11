import ROOT,sys,os; ROOT.gErrorIgnoreLevel=ROOT.kError
for line in open(sys.argv[1]):
    d,p=line.split()[0],line.split()[1]
    f=ROOT.TFile.Open(p)
    if not f: print(d,'OPEN FAILED'); continue
    size=os.lstat(p).st_size if os.path.exists(p) else -1
    rows=[]; nev=None
    def walk(dirobj,prefix=''):
        for k in dirobj.GetListOfKeys():
            o=k.ReadObj()
            if o.InheritsFrom('TTree'): rows.append((prefix+k.GetName(),o.GetEntries(),o.GetZipBytes(),o.GetTotBytes()))
            elif o.InheritsFrom('TDirectory'): walk(o,prefix+k.GetName()+'/')
    walk(f)
    rec=[r for r in rows if r[0] in ('recTree','rec')]; nev=rec[0][1] if rec else None
    print('==',d.split('_v10')[0][-45:],'| file bytes',size,'| events(recTree)',nev)
    for r in sorted(rows,key=lambda r:-r[2])[:12]: print('   %-32s entries %8d  zip %10d  tot %10d'%r)
    print('   sum zip of trees',sum(r[2] for r in rows))
