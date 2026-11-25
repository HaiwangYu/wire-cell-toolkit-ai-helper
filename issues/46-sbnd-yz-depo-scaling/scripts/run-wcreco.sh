#!/bin/bash
# Wire-Cell reconstruction of one reco1 file with the WCLocal2026Nov16 release (WCT 0.38.0),
# as in the Nov16 MC production (issue 48), for the issue-46 YZ off/on comparison:
#   step 1: lar -c wcls-img-clus-matching.fcl (imaging, clustering, Q/L matching, truth labels)
#           -> step1/qlpctree.tar.gz           (= sbnd-wirecell-production aurora/bin/step1.sh, sim)
#   step 2: wire-cell -c pgrapher/experiment/sbnd/wct-pr.jsonnet, production pass "split":
#           vertex_method dv2_split_move, dv2_bundle dv2max/sbnd/aurora_space/bundle.json,
#           dl_vtx_dump true, dl_vtx_dump_space true, flat_tree true, truth_match true,
#           evt_subdir pr_evt{run}_{subrun}_{event}
#           -> step2/pr_evt*/tracking-pr.root   (= issue-48 run-step2.sh "split")
# Each step runs under /usr/bin/time -v (step{1,2}/time.txt) pinned to one CPU with one thread.
#
# Usage: run-wcreco.sh <reco1.root> <outdir> [cpu=<none>] [steps=12] [nevents=all]
#   steps: "1", "2" or "12".  Needs nothing set up: it starts the SL7 container and sources
#   issues/48-.../porting_sbndbuild03/scripts/setup-wcl.sh (SETUP overrides it).
#   XPATH=<dir>: prepended to WIRECELL_PATH (a cfg overlay; e.g. the issue-46 muon test shadows
#   pgrapher/experiment/sbnd/clus.jsonnet with beam_window=[0,0]).  Unset = production cfg.
set -u
R1=$(readlink -f "${1:?reco1.root}"); OUT=${2:?outdir}; CPU=${3:-}; STEPS=${4:-12}; NEV=${5:-all}
NARG=; [ "$NEV" = all ] || NARG="-n $NEV"
SETUP=${SETUP:-/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/48-wclocal-2026nov16-productions/porting_sbndbuild03/scripts/setup-wcl.sh}
SL7=/exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh
mkdir -p "$OUT" && OUT=$(cd "$OUT" && pwd) || exit 2
PIN=; [ -n "$CPU" ] && PIN="taskset -c $CPU"
ENVS="${XPATH:+export WIRECELL_PATH=$XPATH:\$WIRECELL_PATH;} export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 DV2_THREADS=1 GOMAXPROCS=1 GODEBUG=asyncpreemptoff=1"
summ() { echo "$1 rc=$(cat "$2/rc" 2>/dev/null) wall=$(grep 'Elapsed (wall' "$2/time.txt" | awk '{print $NF}') cpu_s=$(awk -F': ' '/User time|System time/ {s+=$2} END {printf "%.0f", s}' "$2/time.txt") maxrss_MB=$(grep 'Maximum resident' "$2/time.txt" | awk '{printf "%d", $NF/1024}')"; }

if [[ $STEPS == *1* ]]; then
  D=$OUT/step1; rm -rf "$D"; mkdir -p "$D"
  echo "$(date '+%F %T') step1 $R1" > "$D/cmd"
  SL7_SETUP=$SETUP $SL7 bash -c "cd $D; $ENVS
    $PIN /usr/bin/time -v -o time.txt lar $NARG --nskip 0 -c wcls-img-clus-matching.fcl -s $R1 --no-output > lar.log 2>&1
    echo \$? > rc; gzip -f lar.log" > "$D/run.out" 2>&1
  summ step1 "$D" | tee "$D/summary.txt"
  [ "$(cat "$D/rc")" = 0 ] && [ -s "$D/qlpctree.tar.gz" ] || { echo "step1 failed" >&2; exit 1; }
fi
if [[ $STEPS == *2* ]]; then
  D=$OUT/step2; rm -rf "$D"; mkdir -p "$D"
  TAR=$OUT/step1/qlpctree.tar.gz
  echo "$(date '+%F %T') step2 $TAR" > "$D/cmd"
  SL7_SETUP=$SETUP $SL7 bash -c "cd $D; $ENVS
    $PIN /usr/bin/time -v -o time.txt wire-cell -l stdout -L debug -c pgrapher/experiment/sbnd/wct-pr.jsonnet \
      --tla-str input=$TAR --tla-str reality=sim --tla-str 'evt_subdir=pr_evt{run}_{subrun}_{event}' \
      --tla-str vertex_method=dv2_split_move --tla-str dv2_bundle=dv2max/sbnd/aurora_space/bundle.json \
      --tla-code dl_vtx_dump=true --tla-code dl_vtx_dump_space=true --tla-code flat_tree=true --tla-code truth_match=true > wct.log 2>&1
    echo \$? > rc
    grep -c 'DL vertex failed' wct.log > dl_fail
    gzip -f wct.log" > "$D/run.out" 2>&1
  summ step2 "$D" | tee "$D/summary.txt"
  echo "dl_fail=$(cat "$D/dl_fail") tracking-pr.root files: $(ls "$D"/pr_evt*/tracking-pr.root 2>/dev/null | wc -l)" | tee -a "$D/summary.txt"
fi
