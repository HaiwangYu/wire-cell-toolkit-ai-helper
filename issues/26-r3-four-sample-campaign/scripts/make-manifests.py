# per chunk: read EventAuxiliary RSE for every entry, sort into art FileIndex order, assign --nskip k; cap total at 10000
import ROOT,glob,sys; ROOT.gErrorIgnoreLevel=ROOT.kError
D=sys.argv[1]; CAP=10000
for s in ['beam-on','beam-off']:
    rows=[]; seen={}; dup=0; runs={}
    for f in sorted(glob.glob('%s/%s/chunk*.root'%(D,s))):
        tf=ROOT.TFile.Open(f); t=tf.Get('Events'); t.SetBranchStatus('*',0); t.SetBranchStatus('EventAuxiliary',1)
        rse=[]
        for i in range(int(t.GetEntries())):
            t.GetEntry(i); a=t.EventAuxiliary.id(); rse.append((int(a.run()),int(a.subRun()),int(a.event())))
        rse.sort()
        for k,r in enumerate(rse):
            if r in seen: dup+=1; continue
            seen[r]=f; rows.append((f,k)+r); runs[r[0]]=runs.get(r[0],0)+1
        tf.Close()
    rows=rows[:CAP]
    with open('%s/%s/%s.manifest'%(D,s,s),'w') as fh:
        for r in rows: fh.write('%s\t%d\t%d\t%d\t%d\n'%r)
    print(s,'events',len(rows),'duplicates dropped',dup,'runs',len(runs),'->',sorted(runs.items())[:3],'...')
