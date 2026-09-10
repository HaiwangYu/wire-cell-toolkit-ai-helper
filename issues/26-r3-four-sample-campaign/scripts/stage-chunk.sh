#!/bin/bash
# stage-chunk.sh <sample> <k>  -- merge 20 reco1 files + add FrameShift -> chunkNN.root, verify the product landed
S="$1"; K="$2"
D=/exp/sbnd/data/users/yuhw/production-prep/r3-data-stage-2026-09-09
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1
set -uo pipefail
LIST=$D/$S/lists/chunk$K.lst; OUT=$D/$S/chunk$K.root; WD=$D/logs/wd_${S}_$K; mkdir -p $WD; cd $WD
[ -s "$OUT" ] && { echo "$S chunk$K exists, skip"; exit 0; }
/usr/bin/time -f "wall=%e s maxrss=%M kB" lar -c run_frameshift.fcl -S "$LIST" -o "$OUT.tmp" > $D/logs/${S}_chunk$K.log 2>&1
rc=$?
if [ $rc -ne 0 ]; then echo "$S chunk$K lar rc=$rc"; exit $rc; fi
python3 - "$OUT.tmp" <<PY || { echo "$S chunk$K FrameShift MISSING"; exit 3; }
import ROOT,sys; ROOT.gErrorIgnoreLevel=ROOT.kError
f=ROOT.TFile.Open(sys.argv[1]); t=f.Get('Events'); n=t.GetEntries()
fs=[b.GetName() for b in t.GetListOfBranches() if 'FrameShift' in b.GetName()]
print('  events=%d FrameShift=%s' % (n, fs)); sys.exit(0 if fs else 1)
PY
mv "$OUT.tmp" "$OUT"; echo "$S chunk$K OK $(ls -la $OUT | awk '{printf "%.2f GB",$5/1073741824}')"
