#!/bin/bash
# spotcheck.sh <beam-on|beam-off> <group K>   -- chain B (Xin's drivers, data) vs chain C on one 16-entry group of chunk00
S=$1; K=$2
D=/exp/sbnd/data/users/yuhw/production-prep/r3-data-stage-2026-09-09; P=$D/spot-$S; mkdir -p $P
IN=$D/$S/chunk00.root
R=/exp/sbnd/data/users/yuhw/production-prep/step1a-runner-scratch/sbnd/sbnd_xin
H=/exp/sbnd/data/users/yuhw/wcp-porting-img/sbnd/img-clus-matching-eval/prabhjot-100file-Aug5-debug-25evt/chain/scripts/run-harness.sh
SL7=/exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh
echo "=== $S chain B group $K ($(/bin/date +%H:%M)) ==="
$SL7 bash -c "
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1; source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-ap.sh >/dev/null 2>&1; source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-dlvtx.sh >/dev/null 2>&1
_kept=''; IFS=':' read -ra _dirs <<< \"\$LD_LIBRARY_PATH\"
for _d in \"\${_dirs[@]}\"; do case \"\$_d\" in *lardataobj*|*/canvas*|*sbndcode*|*sbnobj*|*artdaq*|*lardataalg*) ;; *) _kept=\"\${_kept:+\$_kept:}\$_d\";; esac; done
export LD_LIBRARY_PATH=\"\$_kept\"
export SBND_RECO1=/exp/sbnd/app/users/yuhw/wire-cell-sbnd-reco1/install
export WIRECELL_PATH=/exp/sbnd/app/users/yuhw/wire-cell-toolkit/cfg:/exp/sbnd/app/users/yuhw/wire-cell-data:/exp/sbnd/app/users/yuhw/wire-cell-data/sbnd/photodet:\${WIRECELL_PATH:-}
export PYTHONPATH=/exp/sbnd/app/users/yuhw/wire-cell-toolkit/pyutil/python:\${PYTHONPATH:-}
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
cd $P
SBND_MAX_JOBS=1 $R/run_chain_group.sh $IN $P/work-B data --size 16 --group $K --layout perevt; echo STAGEA_RC=\$?
export PR_JOBS=6 PR_EXTRA_STAGES=pr_display PR_CFG_TREE=/exp/sbnd/app/users/yuhw/wire-cell-toolkit/cfg
$R/run_pr_chain_batch.sh $P/work-B $P/work-Bpr data; echo STAGEB_RC=\$?" > $P/chainB.log 2>&1
grep -E "STAGEA_RC|STAGEB_RC" $P/chainB.log | tr '\n' ' '; echo
# chain C on the same events: match the group's RSE against the sample manifest
python3 - $P $D/$S/$S.manifest <<'PY'
import json,sys,glob
P,M=sys.argv[1:3]
rse=json.load(open(glob.glob(P+'/work-B/g*/rse.json')[0]))
# rse.json: {"<event>": [run, subrun], ...}
want=set((int(v[0]),int(v[1]),int(e)) for e,v in rse.items())
n=0
with open(P+'/spot.manifest','w') as fh:
    for l in open(M):
        f,k,r,s,e=l.rstrip('\n').split('\t')
        if (int(r),int(s),int(e)) in want: fh.write(l); n+=1
print('group events',len(want),'manifest rows',n)
PY
echo "=== $S chain C ($(/bin/date +%H:%M)) ==="
$SL7 bash -c "$H $P/spot.manifest $P/run-C 6 1 wcls-img-clus-matching-xin-data.fcl" > $P/chainC.log 2>&1
tail -1 $P/chainC.log
# P2
C=$P/cmpB; rm -rf $C; mkdir -p $C/ours
for d in $P/work-Bpr/pr_evt*; do e=${d##*pr_evt}; mkdir -p $C/evt_$e; ln -s $d/tracking-pr.root $C/evt_$e/; done
for f in $P/run-C/tracking-pr/tracking-pr_r*_e*.root; do e=$(basename $f | sed 's/.*_e\([0-9]*\)\.root/\1/'); ln -s $f $C/ours/tracking-pr_$e.root; done
$SL7 bash -c "python3 /exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/20-campaign-summary/scripts/deep_compare.py $C $C/ours 'chain C' 2>&1 | tail -1" 2>&1 | grep -v X11
echo "SPOT_DONE $S $(/bin/date +%H:%M)"
