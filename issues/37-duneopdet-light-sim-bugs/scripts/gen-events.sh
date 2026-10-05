#!/bin/bash
# Issue 37: regenerate fdvd_sim doc 02 events (FD-VD 1x8x14, dunesw v10_26_00d00) with Xin's Stage A seeds, so that
# the doc 08a numbers can be checked here on FNAL disk.  Same chain and seeds as
# wcp-porting-validation/fdvd_sim/stageA/run_stageA.sh steps 1-5 (gen, g4s1, g4s2, detsim light-only, reco
# light-only); the depo-extraction and truth.npz steps are skipped (not needed for the light).
#   gen-events.sh <mix|sol> <idx>          (self re-execs into SL7 via in-sl7.sh)
# Output: $WA/fdvd02/<s>/evt<i>/{reco.root,job_*.fcl,*.log,status.txt}
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -n "${APPTAINER_NAME:-}" ] || exec $HERE/in-sl7.sh /bin/bash "$0" "$@"
SAMPLE=$1; IDX=$2
case "$SAMPLE" in
  mix) GENFCL=prodmarley_solar_cc_flat_radiological_decay0_dunevd10kt_1x8x14_3view_30deg.fcl; SEED0=100000; RUN=1 ;;
  sol) GENFCL=prodmarley_solar_cc_flat_dunevd10kt_1x8x14_3view_30deg.fcl;                     SEED0=200000; RUN=2 ;;
  *) echo "usage: $0 mix|sol <idx>" >&2; exit 2 ;;
esac
WA=${WA:-/exp/dune/data/users/yuhw/wire-cell-toolkit-ai-helper-workarea/issue-37}
STAGEA=${STAGEA:-/exp/dune/data/users/yuhw/wcp-porting-validation/fdvd_sim/stageA}
W=$WA/fdvd02/$SAMPLE/evt$IDX
grep -q DONE $W/status.txt 2>/dev/null && { echo "$SAMPLE $IDX skip"; exit 0; }
mkdir -p $W && cd $W || exit 3
: > status.txt
export FHICL_FILE_PATH="$STAGEA:$FHICL_FILE_PATH"
wrap() {
  { echo "#include \"$2\""
    echo "services.NuRandomService.policy: \"random\""
    echo "services.NuRandomService.masterSeed: $((SEED0 + 10*IDX + $3))"
    echo "services.NuRandomService.endOfJobSummary: true"
    [ "$1" = gen ] && { echo "source.firstRun: $RUN"; echo "source.firstSubRun: $((IDX + 1))"; }
  } > job_$1.fcl
}
step() {
  local name=$1; shift
  /usr/bin/time -v lar "$@" > $name.log 2>&1
  local rc=$?
  echo "$name rc=$rc" >> status.txt
  [ $rc -eq 0 ] || { echo "FAILED at $name" >> status.txt; exit $rc; }
}
wrap gen    $GENFCL 1
wrap g4s1   supernova_g4stage1_dunevd10kt_1x8x14_3view_30deg.fcl 2
wrap g4s2   standard_g4stage2_dunevd10kt_1x8x14_3view_30deg.fcl 3
wrap detsim detsim_light_only.fcl 4
wrap reco   reco_light_only.fcl 5
step gen    -c job_gen.fcl    -n 1 -o gen.root
step g4s1   -c job_g4s1.fcl   -s gen.root    -o g4s1.root
step g4s2   -c job_g4s2.fcl   -s g4s1.root   -o g4s2.root
step detsim -c job_detsim.fcl -s g4s2.root   -o detsim.root
step reco   -c job_reco.fcl   -s detsim.root -o reco.root
[ "${KEEP_INTERMEDIATE:-0}" = 1 ] || rm -f gen.root g4s1.root g4s2.root detsim.root
echo "DONE" >> status.txt
echo "$SAMPLE $IDX done $(date +%T)"
