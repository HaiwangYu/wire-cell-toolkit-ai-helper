#!/bin/bash
# step 4b: chain B (Xin's drivers) on 10 random beam-off CANDIDATE events (kine_reco_Enu>0 in chain C), exact compare
O=/exp/sbnd/data/users/yuhw/production-prep/r3-beam-off-2026-09-11; X=$O/step4b
R=/exp/sbnd/data/users/yuhw/production-prep/step1a-runner-scratch/sbnd/sbnd_xin
SL7=/exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh
$SL7 python3 - $O $X <<'PY' 2>&1 | grep -v X11
import ROOT,csv,sys,random,glob,json; ROOT.gErrorIgnoreLevel=ROOT.kError
O,X=sys.argv[1:3]
rows=list(csv.DictReader(open(O+'/run/summary.csv'))); random.seed(20260911); random.shuffle(rows)
cand=[]
for x in rows:
    f=ROOT.TFile.Open('%s/run/tracking-pr/tracking-pr_r%s_s%s_e%s.root'%(O,x['run'],x['subrun'],x['event']))
    if f.Get('T_kine'): cand.append((int(x['run']),int(x['subrun']),int(x['event'])))
    f.Close()
    if len(cand)>=10: break
man={}
for l in open(O+'/lists/beam-off.manifest'):
    f,k,r,s,e=l.rstrip('\n').split('\t'); man[(int(r),int(s),int(e))]=f
# map each candidate to (chunk file, tree entry index) -> reader group = entry//16
jobs={}
for rse in cand:
    f=man[rse]; tf=ROOT.TFile.Open(f); t=tf.Get('Events'); t.SetBranchStatus('*',0); t.SetBranchStatus('EventAuxiliary',1)
    for i in range(int(t.GetEntries())):
        t.GetEntry(i); a=t.EventAuxiliary.id()
        if (int(a.run()),int(a.subRun()),int(a.event()))==rse: jobs.setdefault(f,set()).add(i//16); break
    tf.Close()
json.dump({'cand':cand,'jobs':{f:sorted(g) for f,g in jobs.items()}},open(X+'/plan.json','w'),indent=1)
print('candidates',cand); print('groups per chunk',{f.split('/')[-1]:sorted(g) for f,g in jobs.items()})
PY
$SL7 bash -c "
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1; source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-ap.sh >/dev/null 2>&1; source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-dlvtx.sh >/dev/null 2>&1
_kept=''; IFS=':' read -ra _dirs <<< \"\$LD_LIBRARY_PATH\"
for _d in \"\${_dirs[@]}\"; do case \"\$_d\" in *lardataobj*|*/canvas*|*sbndcode*|*sbnobj*|*artdaq*|*lardataalg*) ;; *) _kept=\"\${_kept:+\$_kept:}\$_d\";; esac; done
export LD_LIBRARY_PATH=\"\$_kept\"
export SBND_RECO1=/exp/sbnd/app/users/yuhw/wire-cell-sbnd-reco1/install
export WIRECELL_PATH=/exp/sbnd/app/users/yuhw/wire-cell-toolkit/cfg:/exp/sbnd/app/users/yuhw/wire-cell-data:/exp/sbnd/app/users/yuhw/wire-cell-data/sbnd/photodet:\${WIRECELL_PATH:-}
export PYTHONPATH=/exp/sbnd/app/users/yuhw/wire-cell-toolkit/pyutil/python:\${PYTHONPATH:-}
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
cd $X
python3 -c \"import json; [print(f, ','.join(map(str,g))) for f,g in json.load(open('$X/plan.json'))['jobs'].items()]\" | while read f groups; do
  tag=\$(basename \$f .root); echo \"== \$tag groups \$groups\"
  SBND_MAX_JOBS=3 $R/run_chain_group.sh \$f $X/work-B-\$tag data --size 16 --groups \$groups --layout perevt; echo STAGEA_RC=\$?
  export PR_JOBS=8 PR_EXTRA_STAGES=pr_display PR_CFG_TREE=/exp/sbnd/app/users/yuhw/wire-cell-toolkit/cfg
  $R/run_pr_chain_batch.sh $X/work-B-\$tag $X/work-Bpr-\$tag data; echo STAGEB_RC=\$?
done" > $X/chainB.log 2>&1
grep -E "^== |STAGEA_RC|STAGEB_RC" $X/chainB.log | tr '\n' ' '; echo
# compare only the 10 candidates: chain B tracking-pr vs chain C
C=$X/cmp; rm -rf $C; mkdir -p $C/ours
python3 -c "import json; [print(*c) for c in json.load(open('$X/plan.json'))['cand']]" | while read r s e; do
  b=$(ls $X/work-Bpr-*/pr_evt$e/tracking-pr.root 2>/dev/null | head -1); [ -n "$b" ] && { mkdir -p $C/evt_$e; ln -s $b $C/evt_$e/; ln -s $O/run/tracking-pr/tracking-pr_r${r}_s${s}_e${e}.root $C/ours/tracking-pr_$e.root; } || echo "MISSING chain B for $r/$s/$e"
done
$SL7 bash -c "python3 /exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/20-campaign-summary/scripts/deep_compare.py $C $C/ours 'chain C' 2>&1 | grep -E 'IDENTICAL|DIFF|exact'" 2>&1 | grep -v X11
echo "STEP4B_DONE $(/bin/date +%H:%M)"
