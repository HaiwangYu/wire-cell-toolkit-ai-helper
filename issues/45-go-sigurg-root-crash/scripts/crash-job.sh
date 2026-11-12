#!/bin/bash
# ai-helper #45: one FermiGrid job = one wire-cell step 2 (one qlpctree, one mode, one pass), exactly the
# command of the local PR #543 review runs (production-prep/pr543-review/v2/run-step2.sh).
#   crash-job.sh <tasks.txt name> <input base on /pnfs> <output base on /pnfs> [extra env for every mode, e.g. GOMAXPROCS=64]
#   (grid slots are pinned to 1 CPU, so Go runs with GOMAXPROCS=1 unless told otherwise; sbndbuild03 jobs saw 64)
# tasks.txt line (job index + 1):  <mode> <input id> <sim|data> <pass>
#   mode: master | pr-original | pr-dv2_split_move | pr-original-nopreempt (= pr-original + GODEBUG=asyncpreemptoff=1)
# Writes <output base>/<mode>/<input id>-p<pass>.<cluster>.<index>.tar.gz: summary.txt, rc, time.txt, wct.log.gz.
# Exit 0 whenever the result arrived (a wire-cell crash is a RESULT, not a job failure).
set -u
TASKS=${1:?tasks}; INBASE=${2:?input base}; OUTBASE=${3:?output base}; XENV=${4:-}
if [ -n "${DAGMANJOBID:-}" ] && [ -n "${JOBSUBJOBSECTION:-}" ]; then P=$JOBSUBJOBSECTION; else P=${PROCESS:-0}; fi
tf=${CONDOR_DIR_INPUT:-.}/$(basename "$TASKS"); [ -f "$tf" ] || tf=$TASKS
read -r MODE INPUT REAL PASS < <(grep -v '^#' "$tf" | sed -n "$((P + 1))p")
[ -n "${PASS:-}" ] || { echo "no task for index $P"; exit 2; }
export WC_TOP=${INPUT_TAR_DIR_LOCAL:?}/wc
S=${_CONDOR_SCRATCH_DIR:-$PWD}/crashjob; mkdir -p "$S/run"; cd "$S"
echo "crash-job $(date '+%F %T') host $(hostname) index $P: $MODE $INPUT $REAL pass $PASS"
VM=; ENVX=
case $MODE in
  master)                SETUP=$WC_TOP/sbnd-wirecell-production/aurora/env/fnal/setup-fnal-run.sh ;;
  pr-original)           SETUP=$WC_TOP/setup-pr543v2.sh; VM="--tla-str vertex_method=original" ;;
  pr-dv2_split_move)     SETUP=$WC_TOP/setup-pr543v2.sh; VM="--tla-str vertex_method=dv2_split_move" ;;
  pr-original-nopreempt) SETUP=$WC_TOP/setup-pr543v2.sh; VM="--tla-str vertex_method=original"; ENVX=GODEBUG=asyncpreemptoff=1 ;;
  *) echo "unknown mode $MODE"; exit 2 ;;
esac
set +u; source "$SETUP" > setup.log 2>&1; set -u
command -v wire-cell > /dev/null || { echo "setup failed"; tail -20 setup.log; exit 3; }
# locally the venv's site-packages follow PYTHONPATH (its python3 is first on PATH); the same here, every mode
export PYTHONPATH=$PYTHONPATH:$WC_TOP/venv-site
# the input: ifdh on the grid, cp in emulation (CRASH_EMULATE=1); the size must match
IN=$INBASE/$INPUT.qlpctree.tar.gz; L=$S/$INPUT.qlpctree.tar.gz
for k in 1 2 3; do
  if [ "${CRASH_EMULATE:-0}" = 1 ]; then cp "$IN" "$L"; want=$(stat -c %s "$IN"); else ifdh cp "$IN" "$L"; want=$(ifdh ll "$IN" 0 2>/dev/null | awk '$1 ~ /^-/ {print $5; exit}'); fi
  [ -n "$want" ] && [ "$(stat -c %s "$L" 2>/dev/null)" = "$want" ] && break
  echo "fetch try $k failed"; rm -f "$L"; sleep $((60 * k))
done
[ -f "$L" ] || { echo "FETCH FAILED $IN"; exit 4; }
TM=false; [ "$REAL" = sim ] && TM=true
cd run
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 DV2_THREADS=1 DV2_HOOK_LOG=$S/run/dv2-hook.jsonl
[ -n "$ENVX" ] && export "$ENVX"
[ -n "$XENV" ] && export "$XENV"
/usr/bin/time -v -o time.txt wire-cell -l stdout -L debug -c pgrapher/experiment/sbnd/wct-pr.jsonnet \
  --tla-str input=$L --tla-str reality=$REAL $VM \
  --tla-code dl_vtx_dump=true --tla-code flat_tree=true --tla-code truth_match=$TM > wct.log 2>&1
rc=$?; echo $rc > rc
# the crash signature: Go fatal / jump to 0 / glibc; which thread got the signal; where the main thread was
sig=$(grep -m1 -oE 'fatal error: [a-z ]+|corrupted [a-z -]+|double free[a-z ]*|0x0000000000000000 in \?\? \(\)' wct.log)
{ echo "mode $MODE"; echo "input $INPUT"; echo "reality $REAL"; echo "pass $PASS"; echo "env ${ENVX:-none}"; echo "xenv ${XENV:-none}"; echo "rc $rc"
  echo "signature ${sig:-none}"; echo "host $(hostname)"; echo "nproc $(nproc)"; echo "cpus_online $(getconf _NPROCESSORS_ONLN)"
  echo "cpu $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | sed 's/^ *//')"
  echo "flags_avx512 $(grep -m1 -c avx512f /proc/cpuinfo)"
  echo "wire_cell $(command -v wire-cell)"; echo "wall $(grep 'Elapsed (wall' time.txt | awk '{print $NF}')"
  echo "maxrss_MB $(grep 'Maximum resident' time.txt | awk '{printf "%d", $NF/1024}')"
  echo "events $(ls -d pr_evt* 2>/dev/null | wc -l)"; echo "cluster ${CLUSTER:-} index $P"; } > summary.txt
cat summary.txt
gzip -f wct.log; cp ../setup.log . 2>/dev/null
R=$INPUT-p$PASS.${CLUSTER:-0}.$P.tar.gz; tar -czf "$S/$R" summary.txt rc time.txt wct.log.gz setup.log $(ls dv2-hook.jsonl 2>/dev/null)
D=$OUTBASE/$MODE
for k in 1 2 3; do
  if [ "${CRASH_EMULATE:-0}" = 1 ]; then mkdir -p "$D"; cp "$S/$R" "$D/" && exit 0
  else ifdh cp "$S/$R" "$D/$R" && [ "$(ifdh ll "$D/$R" 0 2>/dev/null | awk '$1 ~ /^-/ {print $5; exit}')" = "$(stat -c %s "$S/$R")" ] && exit 0; fi
  echo "put try $k failed"; sleep $((60 * k))
done
echo "PUT FAILED $D/$R"; exit 5
