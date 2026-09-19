#!/bin/bash
X=/exp/sbnd/data/users/yuhw/production-prep/xin-round3-samples/beam-off
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1; source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1
mkdir -p $X/wd && cd $X/wd
export FHICL_FILE_PATH=$X:$FHICL_FILE_PATH; lar -c run_frameshift_nofastclone.fcl -S $X/lists/reco1-source-files.lst -n 1000 -o $X/reco1/data_SBND2026A_InTime-Run1_reco1_frameshift_1000evt.root > $X/frameshift.log 2>&1; echo "lar rc=$?"
python3 - $X/reco1/data_SBND2026A_InTime-Run1_reco1_frameshift_1000evt.root <<'PY'
import ROOT,sys; ROOT.gErrorIgnoreLevel=ROOT.kError
f=ROOT.TFile.Open(sys.argv[1]); t=f.Get('Events'); n=t.GetEntries()
fs=[b.GetName() for b in t.GetListOfBranches() if 'FrameShift' in b.GetName()]
t.SetBranchStatus('*',0); t.SetBranchStatus('EventAuxiliary',1); rse=[]
for i in range(n):
    t.GetEntry(i); a=t.EventAuxiliary.id(); rse.append((int(a.run()),int(a.subRun()),int(a.event())))
open(sys.argv[1].replace('reco1/','lists/').replace('.root','.rse.tsv'),'w').write('run\tsubrun\tevent\n'+''.join('%d\t%d\t%d\n'%r for r in rse))
print('events',n,'unique',len(set(rse)),'runs',len(set(r for r,_,_ in rse)),'FrameShift',fs)
PY
echo FRAMESHIFT_DONE
