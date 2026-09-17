#!/bin/bash
# One event of the 1-step chain on Aurora, the way issue-16/21's run-harness.sh
# runs each event: own cwd, `lar -n 1 --nskip k ... --no-output`, /usr/bin/time,
# then the check-pr-run.sh audit and the tracking-pr.root tree count.
#
#   SL7_SETUP=$S/setup-aurora-run.sh in-aurora-sl7.sh $S/smoke-1evt.sh <outdir> <reco1.root> [nskip] [fcl]
set -u
OUT=$1; IN=$2; K=${3:-0}; FCL=${4:-wcls-img-clus-matching-xin.fcl}
WCP_SBND=${WCP_SBND:-/lus/flare/projects/neutrinoGPU/yuhw/wcp-porting-validation/sbnd}
mkdir -p "$OUT" && cd "$OUT" || exit 2
echo "host=$(hostname) start=$(date -u +%FT%TZ) fcl=$FCL nskip=$K in=$IN"
echo "WCT=$(cd ${WCT_SRC:-/lus/flare/projects/neutrinoGPU/yuhw/wire-cell-toolkit} && git rev-parse --short HEAD) LWC=$(cd /lus/flare/projects/neutrinoGPU/yuhw/larsoft-wct/v10_14_02/srcs/larwirecell 2>/dev/null && git rev-parse --short HEAD)"   # SL7 git 1.8 has no -C
t0=$(date +%s)
/usr/bin/time -v -o time.txt timeout -k 60 3600 \
    lar -n 1 --nskip "$K" -c "$FCL" -s "$IN" --no-output > lar.log 2>&1
rc=$?
t1=$(date +%s)
echo "rc=$rc wall_s=$((t1-t0)) peak_rss_kb=$(awk '/Maximum resident/ {print $NF}' time.txt)"
echo "dl_vertex_failed=$(grep -c 'DL vertex failed' lar.log) (want 0)"
grep -oE 'overall main vertex took [0-9.]+ ms' lar.log | head -2
if [ -x "$WCP_SBND/check-pr-run.sh" ]; then
    "$WCP_SBND/check-pr-run.sh" lar.log > audit.txt 2>&1 && echo audit=ok || { echo audit=FAIL; tail -5 audit.txt; }
fi
ls -la *.root *.zip *.h5 2>/dev/null
if [ -f tracking-pr.root ]; then
python3 - <<'PY'
import ROOT
f = ROOT.TFile.Open('tracking-pr.root')
keys = [k.GetName() for k in f.GetListOfKeys()]
print("tracking-pr.root trees:", len(keys), keys)
for n in ('T_tagger', 'T_kine'):
    t = f.Get(n)
    print(n, "entries", t.GetEntries() if t else None)
PY
fi
grep -iE "exception|segmentation|Aborted|std::bad|error" lar.log | grep -v -i "no error" | head -5
tail -3 lar.log
