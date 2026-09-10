import ROOT,glob,sys; ROOT.gErrorIgnoreLevel=ROOT.kError
files=sorted(glob.glob(sys.argv[1]+'/*.root')); tot=len(files); cand=0; nue=0; trees8=0; bad=[]
for p in files:
    f=ROOT.TFile.Open(p)
    if not f or f.IsZombie(): bad.append(p); continue
    keys=set(k.GetName() for k in f.GetListOfKeys()); 
    if len(keys)>=8: trees8+=1
    tk=f.Get('T_kine'); tt=f.Get('T_tagger')
    if tk and tk.GetEntries()>0:
        tk.GetEntry(0)
        if tk.kine_reco_Enu>0:
            cand+=1
            if tt and tt.GetEntries()>0:
                tt.GetEntry(0)
                if tt.nue_score>0: nue+=1
    f.Close()
print('files %d  >=8 trees %d  unreadable %d  candidates(kine_reco_Enu>0) %d (%.2f%%)  nue_score>0 %d (%.2f%%)'%(tot,trees8,len(bad),cand,100.*cand/tot,nue,100.*nue/tot))
for b in bad[:5]: print('  BAD',b)
