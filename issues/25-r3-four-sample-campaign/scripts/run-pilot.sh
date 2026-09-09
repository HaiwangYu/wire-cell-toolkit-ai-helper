#!/bin/bash
# r3 pilot: chain B (Xin's 2-step drivers, reality=sim) vs chain C (our 1-step, MC fcl) on one MC CV reco1 file.
set -o pipefail
P=/exp/sbnd/data/users/yuhw/production-prep/r3-pilot-mccv
IN=$(cat $P/input.txt)
R=/exp/sbnd/data/users/yuhw/production-prep/step1a-runner-scratch/sbnd/sbnd_xin
H=/exp/sbnd/data/users/yuhw/wcp-porting-img/sbnd/img-clus-matching-eval/prabhjot-100file-Aug5-debug-25evt/chain/scripts/run-harness.sh
SL7=/exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh
echo "=== chain B stage A ($(date +%H:%M)) ==="
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
SBND_MAX_JOBS=2 $R/run_chain_group.sh $IN $P/work-B sim --size 16 --layout perevt; echo STAGEA_RC=\$?
echo '=== chain B stage B ==='
export PR_JOBS=18 PR_EXTRA_STAGES=pr_display PR_CFG_TREE=/exp/sbnd/app/users/yuhw/wire-cell-toolkit/cfg
$R/run_pr_chain_batch.sh $P/work-B $P/work-Bpr sim; echo STAGEB_RC=\$?" > $P/chainB.log 2>&1
echo "=== chain C ($(date +%H:%M)) ==="
grep "$IN" /exp/sbnd/data/users/yuhw/production-prep/img-clus-match-tag-pr-mc-1000file-sync-2026-08-30/lists/mc.manifest > $P/pilot.manifest
$SL7 bash -c "$H $P/pilot.manifest $P/run-C 18 1 wcls-img-clus-matching-xin.fcl" > $P/chainC.log 2>&1
echo "PILOT_DONE $(date +%H:%M)"
